import io
import uuid
import os
import time
import shutil
from django.db.models import Count, Max
from io import BytesIO
from datetime import datetime, timedelta
from api.models.analysis_request import AnalysisRequest
from api.models.machine_learning_model import MachineLearningModel
from api.models.analysis import Analysis
from api.models.analysis_machine_learning_model import (
    AnalysisMachineLearningModel,
)
from api.models.analysis import AnalysisGroup
from api.enums.analysis_request_status_enum import AnalysisRequestStatusEnum
from .services.satellite import SatelliteImageExtractor
from .services.drive import DriveService
from .services.ml_processor import WaterQualityPredictor
from .services.maps import MapGenerator
from .config import ParallelProcessingConfig
from django.db.models import Count
from api.models.unprocessed_satellite_image import UnprocessedSatelliteImage
from django.conf import settings
import rasterio


def wait_for_export_tasks(tasks_info, max_wait_time=6000000, check_interval=30):
    """
    Função que aguarda a conclusão de tarefas de exportação do Google Earth Engine, checando o seu 'state' a cada 'check_interval' segundos.
    """
    import ee

    start_time = time.time()

    while True:
        if time.time() - start_time > max_wait_time:
            raise TimeoutError(
                "Export tasks did not complete within the maximum wait time"
            )

        all_completed = True
        for task_info in tasks_info:
            # Handle direct download tasks (no Earth Engine task needed)
            if task_info["task_id"].startswith("direct_download_"):
                if task_info["status"] == "COMPLETED":
                    print(f"Direct download {task_info['task_id']} completed successfully")
                    continue
                else:
                    print(f"Direct download {task_info['task_id']} failed")
                    all_completed = False
                    break
            elif task_info["task_id"].startswith("failed_download_"):
                raise Exception(f"Direct download failed: {task_info.get('error', 'Unknown error')}")
            else:
                # Handle traditional Earth Engine export tasks
                task = ee.batch.Task.list()
                current_task = next(
                    (t for t in task if t.id == task_info["task_id"]), None
                )

                if not current_task:
                    raise Exception(f"Task {task_info['task_id']} not found")

                state = current_task.state

                if state in ["FAILED", "CANCELLED"]:
                    raise Exception(f"Task {task_info['task_id']} {state}")
                elif state != "COMPLETED":
                    print(f"Task {task_info['task_id']} is {state}")
                    all_completed = False
                    break

        if all_completed:
            print("All export tasks completed successfully!")
            break

        print(
            f"Tasks still running, checking again in {check_interval} seconds..."
        )
        time.sleep(check_interval)


def check_for_new_requests():
    """
    Ceca periodicamente a tabela de análises em busca de novas análises com status "QUEUED" e as processa.
    """
    new_requests = AnalysisRequest.objects.filter(
        analysis_request_status_id=AnalysisRequestStatusEnum.QUEUED.value
    )
    for request in new_requests:
        process_request(request.id)

def process_request(request_id):
    request = AnalysisRequest.objects.get(id=request_id)
    try:
        print(f"Processing request {request_id}")
        model_ids = request.properties.get("model_ids", [])
        models = MachineLearningModel.objects.filter(id__in=model_ids)

        distinct_reservoirs = models.values("reservoir").distinct()
        if distinct_reservoirs.count() > 1:
            raise ValueError("All models must be from the same reservoir")

        parameter_counts = models.values("parameter").annotate(count=Count("parameter"))
        duplicate_parameters = [p["parameter"] for p in parameter_counts if p["count"] > 1]

        if duplicate_parameters:
            raise ValueError(f"Multiple models found for the same parameter(s): {duplicate_parameters}")

        reservoir = models.first().reservoir
        #print(f"Using reservoir: {reservoir.name}")

        analysis_group = AnalysisGroup.objects.create(
            reservoir=reservoir,
            identifier_code=uuid.uuid4(),
            start_date=request.start_date,
            end_date=request.end_date,
        )
        request.analysis_group = analysis_group
        request.analysis_request_status_id = AnalysisRequestStatusEnum.DOWNLOADING_IMAGES.value
        request.save()

        marked_images = UnprocessedSatelliteImage.objects.filter(
            reservoir=reservoir,
            image_date__range=(request.start_date, request.end_date)
        )
        
        last_marked_date = marked_images.aggregate(Max('image_date'))['image_date__max']

        if last_marked_date and last_marked_date < request.end_date:
            new_start_date = last_marked_date + timedelta(days=1)
            new_end_date = request.end_date
        elif not last_marked_date:
            new_start_date = request.start_date
            new_end_date = request.end_date
        else:
            new_start_date = None
            new_end_date = None

        if new_start_date and new_end_date and new_start_date == new_end_date:
            new_end_date += timedelta(days=1)
            
        if new_start_date and new_end_date:
            #print(f"Downloading new images from {new_start_date} to {new_end_date}")
            folder_name = f"unprocessed_images_{reservoir.id}"
            
            extractor = SatelliteImageExtractor()
            tasks_info = extractor.create_export_tasks(
            coordinates=reservoir.coordinates,
            start_date=new_start_date.isoformat(),
            end_date=new_end_date.isoformat(),
            folder_name=folder_name,
        )
            #print("Tasks info before wait:", tasks_info)
            
            wait_for_export_tasks(tasks_info)
            #print("Tasks info after wait:", tasks_info)
            
            # Process direct download data instead of Drive files
            print(f"Processing {len(tasks_info)} directly downloaded satellite images")
            for task_info in tasks_info:
                if task_info.get("status") == "COMPLETED" and "sample_data" in task_info:
                    # Extract image date from task info
                    image_date_str = task_info.get("date")
                    image_date = datetime.strptime(image_date_str, "%Y-%m-%d").date()
                    cloud_percentage = task_info.get("cloud_percentage", 0)
                    
                    print(f"Saving directly downloaded image for {image_date} with cloud percentage: {cloud_percentage}")
                    
                    # Convert sample data to a format for processing
                    # For now, we'll store the sample data as JSON in the image_file field
                    import json
                    sample_data_json = json.dumps(task_info["sample_data"]).encode('utf-8')
                    
                    # Use get_or_create to avoid duplicate key errors
                    unprocessed_image, created = UnprocessedSatelliteImage.objects.get_or_create(
                        reservoir=reservoir,
                        image_date=image_date,
                        defaults={
                            'image_file': sample_data_json,  # Store sample data as JSON
                            'cloud_percentage': cloud_percentage
                        }
                    )
                    if created:
                        print(f"Created UnprocessedSatelliteImage with id: {unprocessed_image.id}, cloud_percentage: {unprocessed_image.cloud_percentage}")
                    else:
                        print(f"Image for date {image_date} already exists (id: {unprocessed_image.id}), skipping")
                else:
                    print(f"Skipping incomplete task: {task_info.get('task_id', 'unknown')}")
        else:
            print("No new images to download")

        all_images = UnprocessedSatelliteImage.objects.filter(
            reservoir=reservoir,
            image_date__range=(request.start_date, request.end_date)
        )

        request.analysis_request_status_id = AnalysisRequestStatusEnum.PROCESSING_IMAGES.value
        request.save()

        #print("\n=== Starting ML Processing with Configurable Parallel Processing ===")
        ParallelProcessingConfig.print_config()
        
        for index, model in enumerate(models, 1):
            #print(f"Processing with model {index}/{len(models)} (ID: {model.id})")

            # Use configuration-driven parallel processing
            predictor = WaterQualityPredictor(
                model.model_file, 
                model.scaler_file,
                use_parallel=ParallelProcessingConfig.ENABLE_PARALLEL_PROCESSING,
                max_workers=ParallelProcessingConfig.get_max_workers()
            )

            for image in all_images:
                try:
                    # Check if this is sample data (JSON) or raster file
                    import json
                    try:
                        # Try to parse as JSON (our new direct download format)
                        # Handle both bytes and memoryview objects
                        image_data = image.image_file
                        if isinstance(image_data, memoryview):
                            image_data = bytes(image_data)
                        sample_data = json.loads(image_data.decode('utf-8'))
                        print(f"Processing sample data for {image.image_date} with {len(sample_data['features'])} pixels")
                        
                        # Process sample data directly - create predictions for each pixel
                        predictions = []
                        predicted_points = []  # Store predictions with coordinates for map generation
                        
                        # Calculate temporal features from image date
                        month = image.image_date.month
                        season = (month % 12 + 3) // 3  # 1=Spring, 2=Summer, 3=Fall, 4=Winter
                        
                        for feature in sample_data['features']:
                            pixel_data = feature['properties']
                            # Create a feature vector from the spectral data (15 features total)
                            feature_vector = [
                                # Band columns (6)
                                pixel_data.get('B2', 0), pixel_data.get('B3', 0), pixel_data.get('B4', 0),
                                pixel_data.get('B5', 0), pixel_data.get('B8', 0), pixel_data.get('B11', 0),
                                # Index columns (7)
                                pixel_data.get('NDCI', 0), pixel_data.get('NDVI', 0), pixel_data.get('FAI', 0),
                                pixel_data.get('MNDWI', 0), pixel_data.get('B3_B2_ratio', 0), 
                                pixel_data.get('B4_B3_ratio', 0), pixel_data.get('B5_B4_ratio', 0),
                                # Temporal columns (2)
                                month, season
                            ]
                            
                            # Use the ML model to predict water quality for this pixel
                            prediction = predictor.predict_single_pixel(feature_vector)
                            predictions.append(prediction)
                            
                            # Store prediction with coordinates for map generation
                            if 'geometry' in feature and 'coordinates' in feature['geometry']:
                                coords = feature['geometry']['coordinates']
                                predicted_points.append({
                                    'lon': coords[0],
                                    'lat': coords[1],
                                    'prediction': prediction
                                })
                        
                        # Calculate average prediction for the image
                        avg_prediction = sum(predictions) / len(predictions) if predictions else 0
                        print(f"Average {model.parameter.name} prediction: {avg_prediction:.3f}")
                        
                        # For sample data, store the predictions with coordinates for map generation
                        is_sample_data = True
                        sample_result = {
                            'type': 'sample_data',
                            'points': predicted_points,
                            'average': avg_prediction,
                            'count': len(predictions),
                            'parameter': model.parameter.name
                        }
                        processed_image = json.dumps(sample_result).encode('utf-8')
                        
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Fall back to raster processing for legacy data
                        print(f"Processing raster file for {image.image_date}")
                        is_sample_data = False
                        with BytesIO(image.image_file) as input_file, BytesIO() as output_file:
                            predictor.process_image(input_file, output_file)
                            output_file.seek(0)
                            processed_image = output_file.getvalue()
                    
                    # Only validate raster data if not sample-based
                    if not is_sample_data:
                        # Check if the processed image has any valid data
                        with rasterio.MemoryFile(processed_image) as memfile:
                            with memfile.open() as src:
                                data = src.read(1)
                                valid_data = data[data != -9999]
                                
                                if len(valid_data) == 0:
                                    print(f"No valid data for image dated {image.image_date}. Skipping.")
                                    continue  # Skip to the next image

                    # Create analysis record
                    analysis = Analysis.objects.create(
                        analysis_group=analysis_group,
                        identifier_code=uuid.uuid4(),
                        analysis_date=image.image_date,
                        cloud_percentage=image.cloud_percentage
                    )

                    # Generate maps based on data type
                    html_map = None
                    static_map = None
                    
                    if is_sample_data:
                        # Generate maps from sample points
                        print(f"Generating maps from sample data (date {image.image_date})")
                        try:
                            from .services.sample_map_generator import SampleMapGenerator
                            sample_result = json.loads(processed_image.decode('utf-8'))
                            map_generator = SampleMapGenerator(sample_result, analysis.analysis_date)
                            html_map = map_generator.create_interactive_map()
                            static_map = map_generator.create_static_map()
                            print(f"Successfully generated maps from {len(sample_result['points'])} sample points")
                        except Exception as e:
                            print(f"Error generating maps from sample data: {str(e)}")
                            import traceback
                            traceback.print_exc()
                    else:
                        # Generate maps from raster data
                        map_generator = MapGenerator(processed_image, analysis.analysis_date)
                        try:
                            html_map = map_generator.create_interactive_map()
                            static_map = map_generator.create_static_map()
                            print(f"Successfully generated maps for image dated {image.image_date}")
                        except Exception as e:
                            print(f"Error generating maps: {str(e)}")

                    analysis_ml_model = AnalysisMachineLearningModel.objects.create(
                        analysis=analysis,
                        machine_learning_model=model,
                        raster_file=processed_image,
                        intensity_map=html_map,
                        static_map=static_map,
                    )
                    print(f"Created AnalysisMachineLearningModel record: {analysis_ml_model.id}")

                except Exception as e:
                    print(f"Error processing image for date {image.image_date}: {str(e)}")
                    continue  # Skip to the next image instead of raising an exception

        request.analysis_request_status_id = AnalysisRequestStatusEnum.COMPLETED.value
        request.save()
        #print(f"Completed processing request {request_id}")

    except Exception as e:
        #print(f"\n!!! Error processing request {request_id} !!!")
        #print(f"Error details: {str(e)}")
        request.analysis_request_status_id = AnalysisRequestStatusEnum.FAILED.value
        request.save()
        raise


def extract_date_from_filename(filename):
    import re
    match = re.search(r'\d{4}-\d{2}-\d{2}', os.path.basename(filename))
    if match:
        return datetime.strptime(match.group(), '%Y-%m-%d').date()
    raise ValueError(f"Could not extract date from filename: {filename}")

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)
import uuid
import os
import time
import shutil
from datetime import datetime
from api.models.analysis_request import AnalysisRequest
from api.models.machine_learning_model import MachineLearningModel
from api.models.analysis import Analysis
from api.models.analysis_machine_learning_model import AnalysisMachineLearningModel
from api.enums.analysis_request_status_enum import AnalysisRequestStatusEnum
from .services.satellite import SatelliteImageExtractor
from .services.drive import DriveService
from .services.ml_processor import WaterQualityPredictor
from .services.maps import MapGenerator
from django.db.models import Count
from django.conf import settings


def wait_for_export_tasks(tasks_info, max_wait_time=60000, check_interval=30):
    """
    Wait for Earth Engine export tasks to complete.
    """
    import ee
    start_time = time.time()
    
    while True:
        # Check if we've exceeded max wait time
        if time.time() - start_time > max_wait_time:
            raise TimeoutError("Export tasks did not complete within the maximum wait time")
            
        # Check status of all tasks
        all_completed = True
        for task_info in tasks_info:
            task = ee.batch.Task.list()
            current_task = next((t for t in task if t.id == task_info['task_id']), None)
            
            if not current_task:
                raise Exception(f"Task {task_info['task_id']} not found")
            
            state = current_task.state
            
            if state in ['FAILED', 'CANCELLED']:
                raise Exception(f"Task {task_info['task_id']} {state}")
            elif state != 'COMPLETED':
                print(f"Task {task_info['task_id']} is {state}")
                all_completed = False
                break
                
        if all_completed:
            print("All export tasks completed successfully!")
            break
            
        print(f"Tasks still running, checking again in {check_interval} seconds...")
        time.sleep(check_interval)


def check_for_new_requests():
    """
    Check for new analysis requests in QUEUED status and process them
    """
    new_requests = AnalysisRequest.objects.filter(
        analysis_request_status_id=AnalysisRequestStatusEnum.QUEUED.value
    )
    for request in new_requests:
        process_request(request.id)


def process_request(request_id):
    request = AnalysisRequest.objects.get(id=request_id)
    try:
        # Get models
        print(f"Processing request {request_id}")
        model_ids = request.properties.get('model_ids', [])
        models = MachineLearningModel.objects.filter(id__in=model_ids)
        
        # Validate all models are from the same reservoir
        distinct_reservoirs = models.values('reservoir').distinct()
        if distinct_reservoirs.count() > 1:
            raise ValueError("All models must be from the same reservoir")
        
        # Check for duplicate parameters
        parameter_counts = models.values('parameter').annotate(count=Count('parameter'))
        duplicate_parameters = [p['parameter'] for p in parameter_counts if p['count'] > 1]
        
        if duplicate_parameters:
            raise ValueError(f"Multiple models found for the same parameter(s): {duplicate_parameters}")
            
        # Get the reservoir (now we know all models have the same reservoir)
        reservoir = models.first().reservoir
        print(f"Using reservoir: {reservoir.name}")
        
        # Update status to DOWNLOADING_IMAGES
        request.analysis_request_status_id = AnalysisRequestStatusEnum.DOWNLOADING_IMAGES.value
        request.save()

        folder_name = f"analysis_{request.id}"
        
        # Create export tasks
        print("Creating Earth Engine export tasks...")
        extractor = SatelliteImageExtractor()
        tasks_info = extractor.create_export_tasks(
            coordinates=reservoir.coordinates,
            start_date=request.start_date.isoformat(),
            end_date=request.end_date.isoformat(),
            folder_name=folder_name
        )
        
        # Store task information in properties
        request.properties['tasks'] = tasks_info
        request.save()
        print(f"Created {len(tasks_info)} export tasks")

        # Wait for tasks to complete
        print("Waiting for export tasks to complete...")
        wait_for_export_tasks(tasks_info)
        
        # Download images
        print("Downloading images from Drive...")
        drive_service = DriveService()
        local_folder = os.path.join(settings.MEDIA_ROOT, 'satellite_images', folder_name)
        downloaded_files = drive_service.download_folder_contents(folder_name, local_folder)
        
        # Update request properties with local file paths
        request.properties['local_files'] = downloaded_files
        request.save()
        print(f"Downloaded {len(downloaded_files)} files")
        
        # Update status to start processing
        request.analysis_request_status_id = AnalysisRequestStatusEnum.PROCESSING_IMAGES.value
        request.save()

        # Create Analysis records for each image
        analysis_records = {}  # To store analysis records by image path
        for image_path in downloaded_files:
            try:
                # Extract date from image filename
                filename = os.path.basename(image_path)
                
                # Remove the .tif extension
                filename_without_ext = filename.replace('.tif', '')
                
                import re
                match = re.search(r'\d{4}-\d{2}-\d{2}', filename_without_ext)
                if match:
                    date_part = match.group(0)  # Extract matched date
                    image_date = datetime.strptime(date_part, '%Y-%m-%d').date()
                    print(f"Successfully parsed date {image_date} from filename: {filename}")
                else:
                    raise ValueError(f"Failed to parse date from filename {filename}")
                
                # Create Analysis record for this image
                analysis = Analysis.objects.create(
                    reservoir=reservoir,
                    identifier_code=uuid.uuid4(),
                    analysis_date=image_date
                )
                analysis_records[image_path] = analysis
                print(f"Created analysis record for {image_date} with ID: {analysis.id}")
                
            except ValueError as e:
                print(f"Error parsing date from filename {filename}")
                print(f"Extracted date part: {date_part if 'date_part' in locals() else 'Not extracted'}")
                raise ValueError(f"Failed to parse date from filename {filename}: {str(e)}")
            except Exception as e:
                print(f"Unexpected error processing filename {filename}: {str(e)}")
                raise

        # Process each model
        print("\n=== Starting ML Processing ===")
        for index, model in enumerate(models, 1):
            print(f"Processing with model {index}/{len(models)} (ID: {model.id})")
            
            # Create relative directory for this model's outputs
            relative_dir = os.path.join('processed_images', 
                                      folder_name, 
                                      f"model_{model.id}")
            output_dir = os.path.join(settings.MEDIA_ROOT, relative_dir)
            os.makedirs(output_dir, exist_ok=True)

            # Initialize predictor with model from database
            predictor = WaterQualityPredictor(model.model_file, model.scaler_file)

            # Process each image
            for image_path in downloaded_files:
                try:
                    output_path = predictor.process_image(image_path, output_dir)
                    # Convert to relative path
                    relative_path = os.path.relpath(output_path, settings.MEDIA_ROOT)
                    
                    # Get the corresponding analysis record for this image
                    analysis = analysis_records[image_path]
                    
                    # Generate maps
                    map_generator = MapGenerator(output_path,image_date)  # Use full path for map generation
                    try:
                        html_map = map_generator.create_interactive_map()
                        static_map = map_generator.create_static_map()
                        print(f"Successfully generated maps for {output_path}")
                    except Exception as e:
                        print(f"Error generating maps: {str(e)}")
                        html_map = ""
                        static_map = None
                    
                    # Create AnalysisMachineLearningModel record
                    analysis_ml_model = AnalysisMachineLearningModel.objects.create(
                        analysis=analysis,
                        machine_learning_model=model,
                        raster_path=relative_path,
                        intensity_map=html_map,
                        static_map=static_map
                    )
                    print(f"Created AnalysisMachineLearningModel record: {analysis_ml_model.id}")
                    
                except Exception as e:
                    print(f"Error processing {image_path}: {str(e)}")
                    raise

        # Cleanup: Remove downloaded satellite images after processing
        print("Cleaning up downloaded files...")
        satellite_images_dir = os.path.join(settings.MEDIA_ROOT, 'satellite_images', folder_name)
        if os.path.exists(satellite_images_dir):
            shutil.rmtree(satellite_images_dir)
            print(f"Removed directory: {satellite_images_dir}")

        # Update status to completed
        request.analysis_request_status_id = AnalysisRequestStatusEnum.COMPLETED.value
        request.save()
        print(f"Completed processing request {request_id}")
        
    except Exception as e:
        print(f"\n!!! Error processing request {request_id} !!!")
        print(f"Error details: {str(e)}")
        request.analysis_request_status_id = AnalysisRequestStatusEnum.FAILED.value
        request.save()
        raise
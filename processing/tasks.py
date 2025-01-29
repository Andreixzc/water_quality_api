import uuid
import os
import time
import shutil
from api.models.analysis_request import AnalysisRequest
from api.models.machine_learning_model import MachineLearningModel
from api.models.analysis import Analysis
from api.models.analysis_machine_learning_model import AnalysisMachineLearningModel
from api.enums.analysis_request_status_enum import AnalysisRequestStatusEnum
from .services.satellite import SatelliteImageExtractor
from .services.drive import DriveService
from .services.ml_processor import WaterQualityPredictor
from django.db.models import Count
from django.conf import settings


def check_for_new_requests():
    """
    Check for new analysis requests in QUEUED status and process them
    """
    print("Checking for new requests...")
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

        # Create Analysis record
        analysis = Analysis.objects.create(
            reservoir=reservoir,
            identifier_code=uuid.uuid4(),
            analysis_date=request.start_date
        )
        print(f"Created analysis record with ID: {analysis.id}")
        
        folder_name = f"analysis_{analysis.identifier_code}"
        
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
        time.sleep(60)  # Wait for 1 minute for tasks to complete
        
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

        # Process each model
        print("\n=== Starting ML Processing ===")
        for index, model in enumerate(models, 1):
            print(f"Processing with model {index}/{len(models)} (ID: {model.id})")
            
            # Create relative and full paths
            relative_dir = os.path.join('processed_images', 
                                      f"analysis_{analysis.identifier_code}", 
                                      f"model_{model.id}")
            output_dir = os.path.join(settings.MEDIA_ROOT, relative_dir)
            os.makedirs(output_dir, exist_ok=True)

            # Initialize predictor with model from database
            predictor = WaterQualityPredictor(model.model_file, model.scaler_file)

            processed_files = []
            # Process each downloaded image
            for image_path in downloaded_files:
                try:
                    output_path = predictor.process_image(image_path, output_dir)
                    # Convert to relative path
                    relative_path = os.path.relpath(output_path, settings.MEDIA_ROOT)
                    processed_files.append(relative_path)
                    print(f"Successfully processed {image_path}")
                except Exception as e:
                    print(f"Error processing {image_path}: {str(e)}")

            # Create AnalysisMachineLearningModel record with relative paths
            analysis_ml_model = AnalysisMachineLearningModel.objects.create(
                analysis=analysis,
                machine_learning_model=model,
                raster_path=','.join(processed_files),  # Storing relative paths now
                intensity_map=""  # TODO: Generate intensity map
            )
            print(f"Created AnalysisMachineLearningModel record: {analysis_ml_model.id}")

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
import uuid
import os
import time
import shutil
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
from django.db.models import Count
from api.models.unprocessed_satellite_image import UnprocessedSatelliteImage
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
            raise TimeoutError(
                "Export tasks did not complete within the maximum wait time"
            )

        # Check status of all tasks
        all_completed = True
        for task_info in tasks_info:
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
            f"Tasks still running, checking again in {check_interval} seconds..."  # noqa
        )
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
        model_ids = request.properties.get("model_ids", [])
        models = MachineLearningModel.objects.filter(id__in=model_ids)

        # Validate all models are from the same reservoir
        distinct_reservoirs = models.values("reservoir").distinct()
        if distinct_reservoirs.count() > 1:
            raise ValueError("All models must be from the same reservoir")

        # Check for duplicate parameters
        parameter_counts = models.values("parameter").annotate(count=Count("parameter"))
        duplicate_parameters = [p["parameter"] for p in parameter_counts if p["count"] > 1]

        if duplicate_parameters:
            raise ValueError(f"Multiple models found for the same parameter(s): {duplicate_parameters}")

        # Get the reservoir (now we know all models have the same reservoir)
        reservoir = models.first().reservoir
        print(f"Using reservoir: {reservoir.name}")

        # Create AnalysisGroup first
        analysis_group = AnalysisGroup.objects.create(
            reservoir=reservoir,
            identifier_code=uuid.uuid4(),
            start_date=request.start_date,
            end_date=request.end_date,
        )
        request.analysis_group = analysis_group
        print(f"Created AnalysisGroup with ID: {analysis_group.id}")

        request.analysis_request_status_id = AnalysisRequestStatusEnum.DOWNLOADING_IMAGES.value
        request.save()

        # Check for existing unprocessed images
        existing_images = UnprocessedSatelliteImage.objects.filter(
            reservoir=reservoir,
            image_date__range=(request.start_date, request.end_date)
        )
        existing_dates = set(img.image_date for img in existing_images)
        all_dates = set(date for date in daterange(request.start_date, request.end_date))
        dates_to_download = all_dates - existing_dates

        print("-------------------------------------------")
        print(f"Existing unprocessed images: {(existing_images)}")
        print(f"Dates to download: {(dates_to_download)}")
        print(f"Existing dates: {existing_dates}")
        print("-------------------------------------------")
        folder_name = f"unprocessed_images_{reservoir.id}"
        local_folder = os.path.join(settings.MEDIA_ROOT, "unprocessed_satellite_images", folder_name)

        if dates_to_download:
            # Create export tasks only for missing dates
            print("Creating Earth Engine export tasks for missing dates...")
            extractor = SatelliteImageExtractor()
            tasks_info = extractor.create_export_tasks(
                coordinates=reservoir.coordinates,
                start_date=min(dates_to_download).isoformat(),
                end_date=max(dates_to_download).isoformat(),
                folder_name=folder_name,
            )

            # Store task information in properties
            request.properties["tasks"] = tasks_info
            request.save()
            print(f"Created {len(tasks_info)} export tasks")

            # Wait for tasks to complete
            print("Waiting for export tasks to complete...")
            wait_for_export_tasks(tasks_info)

            # Download new images
            print("Downloading new images from Drive...")
            drive_service = DriveService()
            os.makedirs(local_folder, exist_ok=True)
            downloaded_files = drive_service.download_folder_contents(folder_name, local_folder)

            # Save new UnprocessedSatelliteImage records
            for file_path in downloaded_files:
                image_date = extract_date_from_filename(file_path)
                UnprocessedSatelliteImage.objects.get_or_create(
                    reservoir=reservoir,
                    image_date=image_date,
                    defaults={'file_path': file_path}
                )

        # Get all relevant unprocessed image paths
        all_unprocessed_images = UnprocessedSatelliteImage.objects.filter(
            reservoir=reservoir,
            image_date__range=(request.start_date, request.end_date)
        )
        all_image_paths = [img.file_path for img in all_unprocessed_images]

        # Update request properties with all file paths
        request.properties["unprocessed_files"] = all_image_paths
        request.save()
        print(f"Total unprocessed images to process: {len(all_image_paths)}")

        # Update status to start processing
        request.analysis_request_status_id = AnalysisRequestStatusEnum.PROCESSING_IMAGES.value
        request.save()

        # Create Analysis records for each image
        analysis_records = {}
        for image_path in all_image_paths:
            image_date = extract_date_from_filename(image_path)
            analysis = Analysis.objects.create(
                analysis_group=analysis_group,
                identifier_code=uuid.uuid4(),
                analysis_date=image_date,
            )
            analysis_records[image_path] = analysis
            print(f"Created analysis record for {image_date} with ID: {analysis.id}")

        # Process each model
        print("\n=== Starting ML Processing ===")
        for index, model in enumerate(models, 1):
            print(f"Processing with model {index}/{len(models)} (ID: {model.id})")

            output_folder = f"analysis_{analysis_group.id}"
            output_dir = os.path.join(settings.MEDIA_ROOT, output_folder)
            os.makedirs(output_dir, exist_ok=True)

            predictor = WaterQualityPredictor(model.model_file, model.scaler_file)

            for image_path in all_image_paths:
                try:
                    output_path = predictor.process_image(image_path, output_dir)
                    relative_path = os.path.relpath(output_path, settings.MEDIA_ROOT)

                    analysis = analysis_records[image_path]
                    map_generator = MapGenerator(output_path, analysis.analysis_date)

                    try:
                        html_map = map_generator.create_interactive_map()
                        if not html_map.strip():
                            html_map = None
                        static_map = map_generator.create_static_map()
                        print(f"Successfully generated maps for {output_path}")
                    except Exception as e:
                        print(f"Error generating maps: {str(e)}")
                        html_map = None
                        static_map = None

                    analysis_ml_model = AnalysisMachineLearningModel.objects.create(
                        analysis=analysis,
                        machine_learning_model=model,
                        raster_path=relative_path,
                        intensity_map=html_map,
                        static_map=static_map,
                    )
                    print(f"Created AnalysisMachineLearningModel record: {analysis_ml_model.id}")

                except Exception as e:
                    print(f"Error processing {image_path}: {str(e)}")
                    raise

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

def extract_date_from_filename(filename):
    import re
    match = re.search(r'\d{4}-\d{2}-\d{2}', os.path.basename(filename))
    if match:
        return datetime.strptime(match.group(), '%Y-%m-%d').date()
    raise ValueError(f"Could not extract date from filename: {filename}")

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)


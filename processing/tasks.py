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
from django.db.models import Count
from api.models.unprocessed_satellite_image import UnprocessedSatelliteImage
from django.conf import settings


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
            
            drive_service = DriveService()
            downloaded_files = drive_service.download_folder_contents(folder_name, tasks_info)
            
            for file_content, file_name, cloud_percentage in downloaded_files:
                image_date = extract_date_from_filename(file_name)
                #print(f"Saving image for {image_date} with cloud percentage: {cloud_percentage}")
                
                unprocessed_image = UnprocessedSatelliteImage.objects.create(
                    reservoir=reservoir,
                    image_date=image_date,
                    image_file=file_content,
                    cloud_percentage=cloud_percentage
                )
                #print(f"Created UnprocessedSatelliteImage with id: {unprocessed_image.id}, cloud_percentage: {unprocessed_image.cloud_percentage}")
        else:
            print("No new images to download")

        all_images = UnprocessedSatelliteImage.objects.filter(
            reservoir=reservoir,
            image_date__range=(request.start_date, request.end_date)
        )

        request.analysis_request_status_id = AnalysisRequestStatusEnum.PROCESSING_IMAGES.value
        request.save()

        #print("\n=== Starting ML Processing ===")
        for index, model in enumerate(models, 1):
            #print(f"Processing with model {index}/{len(models)} (ID: {model.id})")

            predictor = WaterQualityPredictor(model.model_file, model.scaler_file)

            for image in all_images:
                try:
                    with BytesIO(image.image_file) as input_file, BytesIO() as output_file:
                        predictor.process_image(input_file, output_file)
                        output_file.seek(0)
                        processed_image = output_file.getvalue()
                    
                    analysis = Analysis.objects.create(
                        analysis_group=analysis_group,
                        identifier_code=uuid.uuid4(),
                        analysis_date=image.image_date,
                        cloud_percentage=image.cloud_percentage
                    )

                    map_generator = MapGenerator(processed_image, analysis.analysis_date)

                    try:
                        html_map = map_generator.create_interactive_map()
                        if not html_map.strip():
                            html_map = None
                        static_map = map_generator.create_static_map()
                        #print(f"Successfully generated maps for image dated {image.image_date}")
                    except Exception as e:
                        #print(f"Error generating maps: {str(e)}")
                        html_map = None
                        static_map = None

                    analysis_ml_model = AnalysisMachineLearningModel.objects.create(
                        analysis=analysis,
                        machine_learning_model=model,
                        raster_file=processed_image,
                        intensity_map=html_map,
                        static_map=static_map,
                    )
                    #print(f"Created AnalysisMachineLearningModel record: {analysis_ml_model.id}")

                except Exception as e:
                    print(f"Error processing image for date {image.image_date}: {str(e)}")
                    raise

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
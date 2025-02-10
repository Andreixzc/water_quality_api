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
from api.models.analysis_machine_learning_model import AnalysisMachineLearningModel
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
    Aguarda a conclusão das tarefas de exportação do Google Earth Engine.
    
    Monitora periodicamente o estado das tarefas de exportação até que todas
    sejam concluídas ou até que o tempo máximo seja atingido.
    
    Args:
        tasks_info (List[Dict]): Lista de informações das tarefas
        max_wait_time (int): Tempo máximo de espera em segundos (default: 6000000)
        check_interval (int): Intervalo entre verificações em segundos (default: 30)
        
    Raises:
        TimeoutError: Se o tempo máximo de espera for excedido
        Exception: Se uma tarefa falhar ou for cancelada
        
    Example:
        >>> tasks_info = [{"task_id": "123", "filename": "image_2024-01-01"}]
        >>> wait_for_export_tasks(tasks_info, max_wait_time=3600)
    """
    import ee
    start_time = time.time()

    while True:
        if time.time() - start_time > max_wait_time:
            raise TimeoutError("Export tasks did not complete within the maximum wait time")

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

        print(f"Tasks still running, checking again in {check_interval} seconds...")
        time.sleep(check_interval)


def check_for_new_requests():
    """
    Verifica periodicamente por novas solicitações de análise.
    
    Busca requisições com status QUEUED e as encaminha para processamento.
    Este método é normalmente chamado por um agendador de tarefas.
    
    Example:
        >>> check_for_new_requests()  # Processa todas as requisições pendentes
    """
    new_requests = AnalysisRequest.objects.filter(
        analysis_request_status_id=AnalysisRequestStatusEnum.QUEUED.value
    )
    for request in new_requests:
        process_request(request.id)


def process_request(request_id):
    """
    Processa uma solicitação de análise completa.
    
    Este é o método principal que coordena todo o pipeline de processamento:
    1. Validação de modelos e parâmetros
    2. Download de imagens de satélite
    3. Processamento ML
    4. Geração de visualizações
    
    Args:
        request_id (int): ID da solicitação de análise
        
    Raises:
        ValueError: Se houver incompatibilidade nos modelos ou parâmetros
        Exception: Para outros erros de processamento
        
    Notes:
        O processamento passa pelos seguintes estados:
        - QUEUED -> DOWNLOADING_IMAGES -> PROCESSING_IMAGES -> COMPLETED
        Em caso de erro, o estado muda para FAILED
    """
    request = AnalysisRequest.objects.get(id=request_id)
    try:
        print(f"Processing request {request_id}")
        
        # Validação de modelos
        model_ids = request.properties.get("model_ids", [])
        models = MachineLearningModel.objects.filter(id__in=model_ids)

        # Verifica se todos os modelos são do mesmo reservatório
        distinct_reservoirs = models.values("reservoir").distinct()
        if distinct_reservoirs.count() > 1:
            raise ValueError("All models must be from the same reservoir")

        # Verifica parâmetros duplicados
        parameter_counts = models.values("parameter").annotate(count=Count("parameter"))
        duplicate_parameters = [p["parameter"] for p in parameter_counts if p["count"] > 1]
        if duplicate_parameters:
            raise ValueError(f"Multiple models found for the same parameter(s): {duplicate_parameters}")

        reservoir = models.first().reservoir

        # Cria grupo de análise
        analysis_group = AnalysisGroup.objects.create(
            reservoir=reservoir,
            identifier_code=uuid.uuid4(),
            start_date=request.start_date,
            end_date=request.end_date,
        )
        request.analysis_group = analysis_group
        request.analysis_request_status_id = AnalysisRequestStatusEnum.DOWNLOADING_IMAGES.value
        request.save()

        # Verifica imagens existentes
        marked_images = UnprocessedSatelliteImage.objects.filter(
            reservoir=reservoir,
            image_date__range=(request.start_date, request.end_date)
        )
        
        # Determina período para download de novas imagens
        last_marked_date = marked_images.aggregate(Max('image_date'))['image_date__max']
        new_start_date, new_end_date = calculate_download_period(
            last_marked_date, request.start_date, request.end_date
        )

        # Download de novas imagens se necessário
        if new_start_date and new_end_date:
            download_new_images(
                reservoir, new_start_date, new_end_date
            )

        # Recupera todas as imagens do período
        all_images = UnprocessedSatelliteImage.objects.filter(
            reservoir=reservoir,
            image_date__range=(request.start_date, request.end_date)
        )

        # Atualiza status e inicia processamento
        request.analysis_request_status_id = AnalysisRequestStatusEnum.PROCESSING_IMAGES.value
        request.save()

        # Processa cada modelo
        for model in models:
            process_model(model, all_images, analysis_group)

        # Finaliza processamento com sucesso
        request.analysis_request_status_id = AnalysisRequestStatusEnum.COMPLETED.value
        request.save()

    except Exception as e:
        request.analysis_request_status_id = AnalysisRequestStatusEnum.FAILED.value
        request.save()
        raise


def calculate_download_period(last_marked_date, request_start, request_end):
    """
    Calcula o período necessário para download de novas imagens.
    
    Args:
        last_marked_date (date): Data da última imagem existente
        request_start (date): Data inicial solicitada
        request_end (date): Data final solicitada
        
    Returns:
        tuple: (new_start_date, new_end_date) ou (None, None) se não necessário
    """
    if last_marked_date and last_marked_date < request_end:
        new_start_date = last_marked_date + timedelta(days=1)
        new_end_date = request_end
    elif not last_marked_date:
        new_start_date = request_start
        new_end_date = request_end
    else:
        return None, None

    if new_start_date and new_end_date and new_start_date == new_end_date:
        new_end_date += timedelta(days=1)
        
    return new_start_date, new_end_date


def download_new_images(reservoir, start_date, end_date):
    """
    Realiza o download de novas imagens de satélite.
    
    Args:
        reservoir: Objeto do reservatório
        start_date (date): Data inicial
        end_date (date): Data final
        
    Returns:
        List[UnprocessedSatelliteImage]: Lista de imagens baixadas
    """
    folder_name = f"unprocessed_images_{reservoir.id}"
    
    extractor = SatelliteImageExtractor()
    tasks_info = extractor.create_export_tasks(
        coordinates=reservoir.coordinates,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        folder_name=folder_name,
    )
    
    wait_for_export_tasks(tasks_info)
    
    drive_service = DriveService()
    downloaded_files = drive_service.download_folder_contents(folder_name, tasks_info)
    
    saved_images = []
    for file_content, file_name, cloud_percentage in downloaded_files:
        image_date = extract_date_from_filename(file_name)
        unprocessed_image = UnprocessedSatelliteImage.objects.create(
            reservoir=reservoir,
            image_date=image_date,
            image_file=file_content,
            cloud_percentage=cloud_percentage
        )
        saved_images.append(unprocessed_image)
    
    return saved_images


def process_model(model, images, analysis_group):
    """
    Processa um modelo ML para todas as imagens.
    
    Args:
        model (MachineLearningModel): Modelo a ser usado
        images (QuerySet): Imagens a serem processadas
        analysis_group (AnalysisGroup): Grupo de análise
    """
    predictor = WaterQualityPredictor(model.model_file, model.scaler_file)

    for image in images:
        try:
            # Processa imagem
            with BytesIO(image.image_file) as input_file, BytesIO() as output_file:
                predictor.process_image(input_file, output_file)
                output_file.seek(0)
                processed_image = output_file.getvalue()
            
            # Cria registro de análise
            analysis = Analysis.objects.create(
                analysis_group=analysis_group,
                identifier_code=uuid.uuid4(),
                analysis_date=image.image_date,
                cloud_percentage=image.cloud_percentage
            )

            # Gera visualizações
            map_generator = MapGenerator(processed_image, analysis.analysis_date)
            html_map = map_generator.create_interactive_map()
            if not html_map.strip():
                html_map = None
            static_map = map_generator.create_static_map()

            # Salva resultados
            AnalysisMachineLearningModel.objects.create(
                analysis=analysis,
                machine_learning_model=model,
                raster_file=processed_image,
                intensity_map=html_map,
                static_map=static_map,
            )

        except Exception as e:
            print(f"Error processing image for date {image.image_date}: {str(e)}")
            raise


def extract_date_from_filename(filename):
    """
    Extrai a data de um nome de arquivo.
    
    Args:
        filename (str): Nome do arquivo contendo data no formato YYYY-MM-DD
        
    Returns:
        date: Data extraída
        
    Raises:
        ValueError: Se não for possível extrair a data
    """
    import re
    match = re.search(r'\d{4}-\d{2}-\d{2}', os.path.basename(filename))
    if match:
        return datetime.strptime(match.group(), '%Y-%m-%d').date()
    raise ValueError(f"Could not extract date from filename: {filename}")


def daterange(start_date, end_date):
    """
    Gera um range de datas.
    
    Args:
        start_date (date): Data inicial
        end_date (date): Data final
        
    Yields:
        date: Próxima data no range
    """
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)
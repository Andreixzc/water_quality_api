import uuid
from api.models.analysis_request import AnalysisRequest
from api.models.machine_learning_model import MachineLearningModel
from api.enums.analysis_request_status_enum import AnalysisRequestStatusEnum
from .services.satellite import SatelliteImageExtractor
from api.models.analysis import Analysis
from django.db.models import Count





def check_for_new_requests():
    """
    Check for new analysis requests in QUEUED status and process them
    """
    new_requests = AnalysisRequest.objects.filter(
        analysis_request_status_id=AnalysisRequestStatusEnum.QUEUED.value
    )
    for request in new_requests:
        process_request(request.id)

# Acho que eu estou validando se todos os modelos são do mesmo reservatório, e se eu não tenho parametro repetido, checar isso depois.
def process_request(request_id):
    request = AnalysisRequest.objects.get(id=request_id)
    try:
        # Get models
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
        
        # Update status to DOWNLOADING_IMAGES
        request.analysis_request_status_id = AnalysisRequestStatusEnum.DOWNLOADING_IMAGES.value
        request.save()
        # Create Analysis record
        analysis = Analysis.objects.create(
            reservoir=reservoir,
            identifier_code=uuid.uuid4(),
            analysis_date=request.start_date
        )
        
        # Create export tasks
        extractor = SatelliteImageExtractor()
        tasks_info = extractor.create_export_tasks(
            coordinates=reservoir.coordinates,
            start_date=request.start_date.isoformat(),
            end_date=request.end_date.isoformat(),
            folder_name=f"analysis_{analysis.identifier_code}"
        )
        
        # Store task information in properties
        request.properties['tasks'] = tasks_info
        request.save()
        
    except Exception as e:
        print(f"Error processing request {request_id}: {str(e)}")
        request.analysis_request_status_id = AnalysisRequestStatusEnum.FAILED.value
        request.save()
        raise  # Re-raise the exception to handle it at a higher level if needed
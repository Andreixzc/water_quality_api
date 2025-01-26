from api.models.analysis_request import AnalysisRequest
from api.enums.analysis_request_status_enum import AnalysisRequestStatusEnum


def check_for_new_requests():
    new_requests = AnalysisRequest.objects.filter(
        analysis_request_status_id=AnalysisRequestStatusEnum.QUEUED.value
    )
    for request in new_requests:
        process_request(request.id)


def process_request(request_id):
    request = AnalysisRequest.objects.get(id=request_id)
    try:
        # Atualiza o status para DOWNLOADING_IMAGES
        request.analysis_request_status_id = AnalysisRequestStatusEnum.DOWNLOADING_IMAGES.value
        request.save()
        print(f"Processing request {request_id}")
        print(f"Downloaded images for request {request_id}")
        
        # Atualiza o status para PROCESSING_IMAGES
        print(f"Processing images for request {request_id}")
        request.analysis_request_status_id = AnalysisRequestStatusEnum.PROCESSING_IMAGES.value
        request.save()
        
        print(f"Completed processing for request {request_id}")
        # Atualiza o status para COMPLETED
        request.analysis_request_status_id = AnalysisRequestStatusEnum.COMPLETED.value
        request.save()
    except Exception as e:
        print(f"Error processing request {request_id}: {str(e)}")
        request.analysis_request_status_id = AnalysisRequestStatusEnum.FAILED.value
        request.save()

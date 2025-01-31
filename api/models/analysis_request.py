from django.db import models
from api.models.analysis import AnalysisGroup
from api.models.analysis_request_status import AnalysisRequestStatus
from api.models.user import User
from api.enums.analysis_request_status_enum import AnalysisRequestStatusEnum


class AnalysisRequest(models.Model):
    analysis_group = models.ForeignKey(
        AnalysisGroup, on_delete=models.CASCADE, null=True, blank=True
    )
    analysis_request_status = models.ForeignKey(
        AnalysisRequestStatus,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        default=AnalysisRequestStatusEnum.QUEUED.value,
    )
    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=False, blank=False)
    properties = models.JSONField(blank=False, null=False, default=dict)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analysis_request"

    def __str__(self):
        return f"{self.id}"

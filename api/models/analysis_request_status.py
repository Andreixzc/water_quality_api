from django.db import models


class AnalysisRequestStatus(models.Model):
    name = models.CharField(max_length=255, blank=False, null=False)
    description = models.CharField(max_length=255, blank=True, null=True)
    icon = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "analysis_request_status"

    def __str__(self):
        return f"{self.id}"

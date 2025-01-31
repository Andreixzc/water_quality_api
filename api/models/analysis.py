from django.db import models
from api.models.reservoir import Reservoir


class AnalysisGroup(models.Model):
    reservoir = models.ForeignKey(Reservoir, on_delete=models.CASCADE)
    identifier_code = models.UUIDField(unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analysis_group"


class Analysis(models.Model):
    analysis_group = models.ForeignKey(AnalysisGroup, on_delete=models.CASCADE)
    identifier_code = models.UUIDField(unique=True)
    cloud_percentage = models.DecimalField(
        max_digits=6, decimal_places=5, blank=True, null=True
    )
    analysis_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "analysis"

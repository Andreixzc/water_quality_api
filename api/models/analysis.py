from django.db import models
from api.models.reservoir import Reservoir


class Analysis(models.Model):
    reservoir = models.ForeignKey(
        Reservoir, on_delete=models.CASCADE, blank=False, null=False
    )
    identifier_code = models.UUIDField(unique=True)
    cloud_percentage = models.DecimalField(
        max_digits=6, decimal_places=5, blank=True, null=True
    )
    analysis_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analysis"

    def __str__(self):
        return f"{self.id}"

from django.db import models
from api.models.machine_learning_model import MachineLearningModel
from api.models.analysis import Analysis


class AnalysisMachineLearningModel(models.Model):
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    machine_learning_model = models.ForeignKey(
        MachineLearningModel, on_delete=models.CASCADE, blank=False, null=False
    )
    raster_path = models.TextField()  # Changed from CharField to TextField
    intensity_map = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analysis_machine_learning_model"

    def __str__(self):
        return f"{self.id}"
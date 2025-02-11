from django.db import models
from api.models.machine_learning_model import MachineLearningModel
from api.models.analysis import Analysis
from django.db import models

class AnalysisMachineLearningModel(models.Model):
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    machine_learning_model = models.ForeignKey(MachineLearningModel, on_delete=models.CASCADE)
    raster_file = models.BinaryField()  # Novo campo
    intensity_map = models.TextField(null=True, blank=True)
    static_map = models.BinaryField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analysis_machine_learning_model"

    def __str__(self):
        return f"{self.id}"
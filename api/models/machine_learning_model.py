from django.db import models
from api.models.reservoir import Reservoir
from api.models.parameter import Parameter


class MachineLearningModel(models.Model):
    reservoir = models.ForeignKey(
        Reservoir, on_delete=models.CASCADE, blank=False, null=False
    )
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    model_file = models.BinaryField()
    scaler_file = models.BinaryField()
    model_file_hash = models.CharField(max_length=64)
    scaler_file_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "machine_learning_model"
        constraints = [
            models.UniqueConstraint(
                fields=["model_file_hash"], name="unique_file_hashes"
            )
        ]

    def __str__(self):
        return f"{self.id}"

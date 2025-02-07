from django.db import models
from api.models.reservoir import Reservoir

class UnprocessedSatelliteImage(models.Model):
    reservoir = models.ForeignKey('Reservoir', on_delete=models.CASCADE)
    image_date = models.DateField()
    image_file = models.BinaryField()
    cloud_percentage = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['reservoir', 'image_date']
        
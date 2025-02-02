from django.db import models
from api.models.reservoir import Reservoir

class UnprocessedSatelliteImage(models.Model):
    reservoir = models.ForeignKey(Reservoir, on_delete=models.CASCADE)
    file_path = models.CharField(max_length=255)
    image_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "unprocessed_satellite_image"
        unique_together = ['reservoir', 'image_date']

    def __str__(self):
        return f"{self.reservoir.name} - {self.image_date}"
from django.db import models

class User(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    cpf = models.CharField(max_length=14, unique=True)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Reservoir(models.Model):
    name = models.CharField(max_length=255, unique=True)
    coordinates = models.TextField()
    users = models.ManyToManyField(User, related_name='reservoirs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class WaterQualityAnalysis(models.Model):
    # PARAMETER_CHOICES = [
    #     ('chlorophyll', 'Chlorophyll'),
    #     ('turbidity', 'Turbidity'),
    #     # Adicionar futuros parametros.
    # ]
    # parameter = models.CharField(max_length=50, choices=PARAMETER_CHOICES)
    reservoir = models.ForeignKey(Reservoir, on_delete=models.CASCADE, related_name='analyses')
    parameter = models.CharField(max_length=50)
    analysis_start_date = models.DateField()
    analysis_end_date = models.DateField()
    min_value = models.FloatField()
    max_value = models.FloatField()
    raster_path = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.hashers import make_password
from django.core.validators import FileExtensionValidator
import os
from django.conf import settings
class User(AbstractUser):
    email = models.EmailField(unique=True)
    company = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    cpf = models.CharField(max_length=14, unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "cpf"]

    def __str__(self):
        return self.email

class Reservoir(models.Model):
    name = models.CharField(max_length=255, unique=True)
    coordinates = models.JSONField()  # This will store the array structure directly
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    def __str__(self):
        return self.name

class ReservoirUsers(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservoir_accesses')
    reservoir = models.ForeignKey(Reservoir, on_delete=models.CASCADE, related_name='user_accesses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'reservoir']

    def __str__(self):
        return f"{self.user.email} - {self.reservoir.name}"

class WaterQualityAnalysis(models.Model):
    reservoir = models.ForeignKey(Reservoir, on_delete=models.CASCADE, related_name='analyses')
    identifier_code = models.UUIDField(unique=True)
    analysis_start_date = models.DateField()
    analysis_end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.reservoir.name} - {self.analysis_start_date}"

class Parameter(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class WaterQualityAnalysisParameters(models.Model):
    water_quality_analysis = models.ForeignKey(
        WaterQualityAnalysis, 
        on_delete=models.CASCADE,
        related_name='parameters'
    )
    parameter = models.ForeignKey(
        Parameter, 
        on_delete=models.CASCADE,
        related_name='analysis_results'
    )
    min_value = models.FloatField()
    max_value = models.FloatField()
    raster_path = models.CharField(max_length=255)
    intensity_map_path = models.CharField(max_length=255, null=True, blank=True)  # New field
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['water_quality_analysis', 'parameter']

    def __str__(self):
        return f"{self.water_quality_analysis.reservoir.name} - {self.parameter.name}"
    


class ReservoirParameterModel(models.Model):
    reservoir = models.ForeignKey('Reservoir', on_delete=models.CASCADE, related_name='parameter_models')
    parameter = models.ForeignKey('Parameter', on_delete=models.CASCADE, related_name='reservoir_models')
    model_filename = models.CharField(max_length=255)
    scaler_filename = models.CharField(max_length=255)
    model_path = models.CharField(max_length=512)
    scaler_path = models.CharField(max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['reservoir', 'parameter']

    def __str__(self):
        return f"{self.reservoir.name} - {self.parameter.name} Model"
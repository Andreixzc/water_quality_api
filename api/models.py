from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.hashers import make_password

class User(AbstractUser):
    email = models.EmailField(unique=True)
    company = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    cpf = models.CharField(max_length=14, unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'cpf']

    def __str__(self):
        return self.email

class Reservoir(models.Model):
    name = models.CharField(max_length=255, unique=True)
    coordinates = models.TextField()
    users = models.ManyToManyField(User, related_name='reservoirs')
    created_at = models.DateTimeField(auto_now_add=True)                
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class WaterQualityAnalysis(models.Model):
    reservoir = models.ForeignKey(Reservoir, on_delete=models.CASCADE, related_name='analyses')
    parameter = models.CharField(max_length=50)
    analysis_start_date = models.DateField()
    analysis_end_date = models.DateField()
    min_value = models.FloatField()
    max_value = models.FloatField()
    raster_path = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reservoir.name} - {self.parameter} - {self.analysis_start_date}"
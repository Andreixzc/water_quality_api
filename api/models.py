from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    company = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=15, blank=True)

    # aplicar regex para remover pontos, traços, dashs e etc
    # validar também o cpf se é valido
    cpf = models.CharField(max_length=11, unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "cpf"]

    class Meta:
        db_table = "user"

    def __str__(self):
        return self.email


class Reservoir(models.Model):
    name = models.CharField(max_length=255, unique=True)
    coordinates = (
        models.JSONField()
    )  # This will store the array structure directly
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True
    )

    class Meta:
        db_table = "reservoir"

    def __str__(self):
        return self.name


class ReservoirUser(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reservoir_accesses"
    )
    reservoir = models.ForeignKey(
        Reservoir, on_delete=models.CASCADE, related_name="user_accesses"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "reservoir"]
        db_table = "reservoir_user"

    def __str__(self):
        return f"{self.user.email} - {self.reservoir.name}"


class Parameter(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True
    )

    class Meta:
        db_table = "parameter"

    def __str__(self):
        return self.name


class ReservoirParameterModelScaler(models.Model):
    reservoir = models.ForeignKey(
        "Reservoir", on_delete=models.CASCADE, related_name="parameter_models"
    )
    parameter = models.ForeignKey(
        "Parameter", on_delete=models.CASCADE, related_name="reservoir_models"
    )
    model_filename = models.CharField(max_length=255)
    scaler_filename = models.CharField(max_length=255)
    model_path = models.CharField(max_length=512)
    scaler_path = models.CharField(max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["reservoir", "parameter"]
        db_table = "reservoir_parameter_model_scaler"

    def __str__(self):
        return f"{self.reservoir.name} - {self.parameter.name} Model"


class WaterQualityAnalysis(models.Model):
    reservoir = models.ForeignKey(
        Reservoir, on_delete=models.CASCADE, related_name="analyses"
    )
    identifier_code = models.UUIDField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    analysis_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "water_quality_analysis"

    def __str__(self):
        return f"{self.identifier_code} - {self.reservoir.name}"


class WaterQualityAnalysisParameter(models.Model):
    water_quality_analysis = models.ForeignKey(
        WaterQualityAnalysis,
        on_delete=models.CASCADE,
        related_name="parameters",
    )
    parameter = models.ForeignKey(
        Parameter, on_delete=models.CASCADE, related_name="analysis_results"
    )
    min_value = models.FloatField()
    max_value = models.FloatField()
    raster_path = models.CharField(max_length=255)
    intensity_map = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["water_quality_analysis", "parameter"]
        db_table = "water_quality_analysis_parameter"

    def __str__(self):
        return (
            f"{self.water_quality_analysis.reservoir.name}"
            + f" - {self.parameter.name}"
        )

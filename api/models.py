from django.contrib.auth.models import AbstractUser
from django.db import models

from api.enums.enums import WaterQualityAnalysisRequestStatusEnum


class User(AbstractUser):
    email = models.EmailField(unique=True)
    company = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    cpf = models.CharField(max_length=11, unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "cpf"]

    class Meta:
        db_table = "user"

    def __str__(self):
        return f"{self.id}"


class Reservoir(models.Model):
    name = models.CharField(max_length=255, unique=True)
    coordinates = models.JSONField()
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reservoir"

    def __str__(self):
        return f"{self.id}"


class ReservoirUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reservoir = models.ForeignKey(
        Reservoir, on_delete=models.CASCADE, blank=False, null=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reservoir_user"
        unique_together = ["user", "reservoir"]

    def __str__(self):
        return f"{self.id}"


class Parameter(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "parameter"

    def __str__(self):
        return f"{self.id}"


class MLModel(models.Model):
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
        db_table = "ml_model"
        constraints = [
            models.UniqueConstraint(
                fields=["model_file_hash"], name="unique_file_hashes"
            )
        ]

    def __str__(self):
        return f"{self.id}"


class WaterQualityAnalysis(models.Model):
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
        db_table = "water_quality_analysis"

    def __str__(self):
        return f"{self.id}"


class WaterQualityAnalysisMLModel(models.Model):
    water_quality_analysis = models.ForeignKey(
        WaterQualityAnalysis, on_delete=models.CASCADE
    )
    ml_model = models.ForeignKey(
        MLModel, on_delete=models.CASCADE, blank=False, null=False
    )
    raster_path = models.CharField(max_length=255)
    intensity_map = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "water_quality_analysis_ml_model"

    def __str__(self):
        return f"{self.id}"


class WaterQualityAnalysisRequestStatus(models.Model):
    name = models.CharField(max_length=255, blank=False, null=False)
    description = models.CharField(max_length=255, blank=True, null=True)
    icon = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "water_quality_analysis_request_status"

    def __str__(self):
        return f"{self.id}"


class WaterQualityAnalysisRequest(models.Model):
    water_quality_analysis = models.ForeignKey(
        WaterQualityAnalysis, on_delete=models.CASCADE, null=True, blank=True
    )
    water_quality_analysis_request_status = models.ForeignKey(
        WaterQualityAnalysisRequestStatus,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        default=WaterQualityAnalysisRequestStatusEnum.QUEUED.value,
    )
    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=False, blank=False)
    properties = models.JSONField(blank=False, null=False, default=dict)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "water_quality_analysis_request"

    def __str__(self):
        return f"{self.id}"

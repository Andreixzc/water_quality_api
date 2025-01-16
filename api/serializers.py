from rest_framework import serializers
import os
from django.core.validators import FileExtensionValidator
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils.safestring import mark_safe
from .models import (
    ReservoirParameterModel,
    User,
    Reservoir,
    WaterQualityAnalysis,
    Parameter,
    ReservoirUsers,
    WaterQualityAnalysisParameters,
)
from django.contrib.auth.password_validation import validate_password


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "password",
            "cpf",
            "company",
            "phone",
            "is_staff",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
            "is_staff": {"read_only": True},
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        if "password" in validated_data:
            password = validated_data.pop("password")
            instance.set_password(password)
        return super().update(instance, validated_data)


class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = ["id", "name", "created_at", "created_by"]


class WaterQualityAnalysisParametersSerializer(serializers.ModelSerializer):
    parameter_name = serializers.CharField(
        source="parameter.name", read_only=True
    )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation.get('intensity_map'):
            # Normalize line endings and mark as safe
            normalized_html = representation['intensity_map'].replace('\r\n', '\n')
            representation['intensity_map'] = mark_safe(normalized_html)
        return representation

    class Meta:
        model = WaterQualityAnalysisParameters
        fields = [
            "id",
            "water_quality_analysis",
            "parameter",
            "parameter_name",
            "min_value",
            "max_value",
            "intensity_map",
            "analysis_date",
            "raster_path",
            "created_at",
        ]


class WaterQualityAnalysisSerializer(serializers.ModelSerializer):
    parameters = WaterQualityAnalysisParametersSerializer(
        many=True, read_only=True
    )
    reservoir_name = serializers.CharField(
        source="reservoir.name", read_only=True
    )

    class Meta:
        model = WaterQualityAnalysis
        fields = [
            "id",
            "reservoir",
            "reservoir_name",
            "identifier_code",
            "analysis_start_date",
            "analysis_end_date",
            "created_at",
            "created_by",
            "parameters",
        ]


class ReservoirUsersSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    reservoir_name = serializers.CharField(
        source="reservoir.name", read_only=True
    )

    class Meta:
        model = ReservoirUsers
        fields = [
            "id",
            "user",
            "user_email",
            "reservoir",
            "reservoir_name",
            "created_at",
        ]


class ReservoirSerializer(serializers.ModelSerializer):
    user_accesses = ReservoirUsersSerializer(many=True, read_only=True)
    analyses = WaterQualityAnalysisSerializer(many=True, read_only=True)
    created_by_email = serializers.CharField(
        source="created_by.email", read_only=True
    )

    class Meta:
        model = Reservoir
        fields = [
            "id",
            "name",
            "coordinates",
            "created_at",
            "created_by",
            "created_by_email",
            "user_accesses",
            "analyses",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class ReservoirParameterModelSerializer(serializers.ModelSerializer):
    model_file = serializers.FileField(
        write_only=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["pkl", "joblib"])
        ],
    )
    scaler_file = serializers.FileField(
        write_only=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["pkl", "joblib"])
        ],
    )

    class Meta:
        model = ReservoirParameterModel
        fields = [
            "id",
            "reservoir",
            "parameter",
            "model_file",
            "scaler_file",
            "model_filename",
            "scaler_filename",
            "model_path",
            "scaler_path",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "model_filename",
            "scaler_filename",
            "model_path",
            "scaler_path",
        ]

    def create(self, validated_data):
        model_file = validated_data.pop("model_file")
        scaler_file = validated_data.pop("scaler_file")

        instance = ReservoirParameterModel.objects.create(**validated_data)

        # Save model file
        model_ext = os.path.splitext(model_file.name)[1]
        model_filename = (
            f"model_{instance.reservoir.id}_{instance.parameter.id}{model_ext}"
        )
        model_path = os.path.join(settings.MODELS_DIR, model_filename)
        with default_storage.open(model_path, "wb+") as destination:
            for chunk in model_file.chunks():
                destination.write(chunk)
        instance.model_filename = model_filename
        instance.model_path = model_path

        # Save scaler file
        scaler_ext = os.path.splitext(scaler_file.name)[1]
        scaler_filename = f"scaler_{instance.reservoir.id}_{instance.parameter.id}{scaler_ext}"
        scaler_path = os.path.join(settings.SCALERS_DIR, scaler_filename)
        with default_storage.open(scaler_path, "wb+") as destination:
            for chunk in scaler_file.chunks():
                destination.write(chunk)
        instance.scaler_filename = scaler_filename
        instance.scaler_path = scaler_path

        instance.save()
        return instance
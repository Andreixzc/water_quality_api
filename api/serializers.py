from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.utils.safestring import mark_safe
from .models import (
    User,
    Reservoir,
    Parameter,
    ReservoirUser,
    WaterQualityAnalysisMLModel,
    MLModel,
    WaterQualityAnalysisRequest,
)
from .utils import compute_file_hash


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


class WaterQualityAnalysisMLModelSerializer(serializers.ModelSerializer):
    parameter_name = serializers.CharField(
        source="parameter.name", read_only=True
    )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation.get("intensity_map"):
            normalized_html = representation["intensity_map"].replace(
                "\r\n", "\n"
            )
            representation["intensity_map"] = mark_safe(normalized_html)
        return representation

    class Meta:
        model = WaterQualityAnalysisMLModel
        fields = [
            "id",
            "water_quality_analysis",
            "parameter",
            "parameter_name",
            "intensity_map",
            "raster_path",
            "created_at",
        ]


class ReservoirUserSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    reservoir_name = serializers.CharField(
        source="reservoir.name", read_only=True
    )

    class Meta:
        model = ReservoirUser
        fields = [
            "id",
            "user",
            "user_email",
            "reservoir",
            "reservoir_name",
            "created_at",
        ]


class ReservoirSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservoir
        fields = [
            "id",
            "name",
            "coordinates",
            "created_at",
            "created_by",
        ]


class WaterQualityAnalysisRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterQualityAnalysisRequest
        fields = [
            "id",
            "water_quality_analysis",
            "water_quality_analysis_request_status",
            "start_date",
            "end_date",
            "properties",
            "created_by",
            "created_at",
            "updated_at",
        ]


class MLModelSerializer(serializers.ModelSerializer):
    model_file = serializers.FileField()
    scaler_file = serializers.FileField()

    class Meta:
        model = MLModel
        fields = [
            "id",
            "reservoir",
            "parameter",
            "model_file",
            "scaler_file",
            "model_file_hash",
            "scaler_file_hash",
            "created_at",
        ]
        read_only_fields = ["model_file_hash", "scaler_file_hash"]

    def validate(self, data):
        model_file = data.get("model_file")
        scaler_file = data.get("scaler_file")

        if model_file:
            model_file_hash = compute_file_hash(model_file)
            if MLModel.objects.filter(
                model_file_hash=model_file_hash
            ).exists():
                raise serializers.ValidationError(
                    "This model file has already been uploaded."
                )
            data["model_file_hash"] = model_file_hash
            data["model_file"] = model_file.read()

        if scaler_file:
            scaler_file_hash = compute_file_hash(scaler_file)
            if MLModel.objects.filter(
                scaler_file_hash=scaler_file_hash
            ).exists():
                raise serializers.ValidationError(
                    "This scaler file has already been uploaded."
                )
            data["scaler_file_hash"] = scaler_file_hash
            data["scaler_file"] = scaler_file.read()

        return data

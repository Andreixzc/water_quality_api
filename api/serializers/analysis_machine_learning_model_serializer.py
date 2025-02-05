from django.utils.safestring import mark_safe
import base64
from rest_framework import serializers
from api.models.analysis_machine_learning_model import AnalysisMachineLearningModel

class AnalysisMachineLearningModelSerializer(serializers.ModelSerializer):
    parameter_name = serializers.CharField(
        source="machine_learning_model.parameter.name", read_only=True
    )
    static_map_base64 = serializers.SerializerMethodField()
    raster_file_base64 = serializers.SerializerMethodField()

    def get_static_map_base64(self, obj):
        """Convert binary static_map to base64 string for frontend display"""
        if obj.static_map:
            return base64.b64encode(obj.static_map).decode("utf-8")
        return None

    def get_raster_file_base64(self, obj):
        """Convert binary raster_file to base64 string for frontend display"""
        if obj.raster_file:
            return base64.b64encode(obj.raster_file).decode("utf-8")
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Handle interactive map HTML
        if representation.get("intensity_map"):
            normalized_html = representation["intensity_map"].replace("\r\n", "\n")
            representation["intensity_map"] = mark_safe(normalized_html)
        return representation

    class Meta:
        model = AnalysisMachineLearningModel
        fields = [
            "id",
            "analysis",
            "machine_learning_model",
            "parameter_name",
            "intensity_map",
            "static_map_base64",
            "raster_file_base64",
            "created_at",
        ]
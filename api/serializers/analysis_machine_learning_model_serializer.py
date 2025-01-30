from django.utils.safestring import mark_safe
import base64
from rest_framework import serializers
from api.models.analysis_machine_learning_model import AnalysisMachineLearningModel

class AnalysisMachineLearningModelSerializer(serializers.ModelSerializer):
    parameter_name = serializers.CharField(
        source="machine_learning_model.parameter.name", read_only=True
    )
    static_map_base64 = serializers.SerializerMethodField()

    def get_static_map_base64(self, obj):
        """Convert binary static_map to base64 string for frontend display"""
        if obj.static_map:
            return base64.b64encode(obj.static_map).decode('utf-8')
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Handle interactive map HTML
        if representation.get("intensity_map"):
            normalized_html = representation["intensity_map"].replace(
                "\r\n", "\n"
            )
            representation["intensity_map"] = mark_safe(normalized_html)
        return representation

    class Meta:
        model = AnalysisMachineLearningModel
        fields = [
            "id",
            "analysis",
            "machine_learning_model",  # Include the foreign key
            "parameter_name",  # Use the correct source for parameter name
            "intensity_map",
            "static_map_base64",
            "raster_path",
            "created_at",
        ]
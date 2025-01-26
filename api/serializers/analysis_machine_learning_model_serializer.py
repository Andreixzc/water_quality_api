from django.utils.safestring import mark_safe
from rest_framework import serializers
from api.models.analysis_machine_learning_model import (
    AnalysisMachineLearningModel,
)


class AnalysisMachineLearningModelSerializer(serializers.ModelSerializer):
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
        model = AnalysisMachineLearningModel
        fields = [
            "id",
            "analysis",
            "parameter",
            "parameter_name",
            "intensity_map",
            "raster_path",
            "created_at",
        ]

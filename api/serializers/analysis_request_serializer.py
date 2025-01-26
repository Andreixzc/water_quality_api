from rest_framework import serializers
from api.models.analysis_request import AnalysisRequest


class AnalysisRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisRequest
        fields = "__all__"

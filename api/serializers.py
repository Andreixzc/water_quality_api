from rest_framework import serializers
from .models import User, Reservoir, WaterQualityAnalysis

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class ReservoirSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservoir
        fields = '__all__'

class WaterQualityAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterQualityAnalysis
        fields = '__all__'
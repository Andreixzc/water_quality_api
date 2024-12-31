from rest_framework import serializers
from .models import (
    User, 
    Reservoir, 
    WaterQualityAnalysis, 
    Parameter,
    ReservoirUsers,
    WaterQualityAnalysisParameters
)
from django.contrib.auth.password_validation import validate_password

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password', 'cpf', 'company', 'phone', 'is_staff']
        extra_kwargs = {
            'password': {'write_only': True},
            'is_staff': {'read_only': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            password = validated_data.pop('password')
            instance.set_password(password)
        return super().update(instance, validated_data)

class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = ['id', 'name', 'created_at', 'created_by']

class WaterQualityAnalysisParametersSerializer(serializers.ModelSerializer):
    parameter_name = serializers.CharField(source='parameter.name', read_only=True)
    
    class Meta:
        model = WaterQualityAnalysisParameters
        fields = ['id', 'water_quality_analysis', 'parameter', 'parameter_name', 'min_value', 'max_value', 'raster_path', 'created_at']

class WaterQualityAnalysisSerializer(serializers.ModelSerializer):
    parameters = WaterQualityAnalysisParametersSerializer(many=True, read_only=True)
    reservoir_name = serializers.CharField(source='reservoir.name', read_only=True)

    class Meta:
        model = WaterQualityAnalysis
        fields = ['id', 'reservoir', 'reservoir_name', 'identifier_code', 
                 'analysis_start_date', 'analysis_end_date', 'created_at', 
                 'created_by', 'parameters']

class ReservoirUsersSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    reservoir_name = serializers.CharField(source='reservoir.name', read_only=True)

    class Meta:
        model = ReservoirUsers
        fields = ['id', 'user', 'user_email', 'reservoir', 'reservoir_name', 'created_at']

class ReservoirSerializer(serializers.ModelSerializer):
    user_accesses = ReservoirUsersSerializer(many=True, read_only=True)
    analyses = WaterQualityAnalysisSerializer(many=True, read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)

    class Meta: 
        model = Reservoir
        fields = ['id', 'name', 'coordinates', 'created_at', 'created_by', 
                 'created_by_email', 'user_accesses', 'analyses']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)
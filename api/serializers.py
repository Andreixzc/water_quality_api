from rest_framework import serializers
from .models import User, Reservoir, WaterQualityAnalysis
from django.contrib.auth.password_validation import validate_password

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password', 'cpf', 'company', 'phone', 'is_staff']  # Changed is_admin to is_staff
        extra_kwargs = {
            'password': {'write_only': True},
            'is_staff': {'read_only': True}  # Added this to prevent setting is_staff via API
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            password = validated_data.pop('password')
            instance.set_password(password)
        return super().update(instance, validated_data)

class ReservoirSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservoir
        fields = '__all__'

class WaterQualityAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterQualityAnalysis
        fields = '__all__'
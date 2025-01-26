from rest_framework import serializers
from api.models.parameter import Parameter


class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = "__all__"

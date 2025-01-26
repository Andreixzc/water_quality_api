from rest_framework import serializers
from api.models.reservoir import Reservoir


class ReservoirSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservoir
        fields = "__all__"

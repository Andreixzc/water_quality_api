from rest_framework import serializers
from api.models.reservoir_user import ReservoirUser


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

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from api.models.reservoir_user import ReservoirUser
from api.serializers.reservoir_user_serializer import ReservoirUserSerializer
from rest_framework import viewsets
from rest_framework import generics, mixins, views, viewsets


class ReservoirUserViewSet(viewsets.ModelViewSet):
    queryset = ReservoirUser.objects.all()
    serializer_class = ReservoirUserSerializer
    permission_classes = [IsAuthenticated]

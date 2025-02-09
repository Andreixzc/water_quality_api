from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from api.models.reservoir import Reservoir
from api.serializers.reservoir_serializer import ReservoirSerializer
from rest_framework import viewsets
from rest_framework import viewsets
from rest_framework import generics, mixins, views, viewsets
from rest_framework import viewsets
from rest_framework import generics, mixins, views, viewsets


class ReservoirViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = Reservoir.objects.all()
    serializer_class = ReservoirSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied("User not authenticated.")
        serializer.save(created_by=self.request.user)

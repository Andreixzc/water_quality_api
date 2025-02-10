from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from api.models.parameter import Parameter
from api.serializers.parameter_serializer import ParameterSerializer
from rest_framework import viewsets
from rest_framework import generics, mixins, views, viewsets


class ParameterViewSet(mixins.CreateModelMixin,
                       mixins.ListModelMixin,  
                       mixins.RetrieveModelMixin, 
                       viewsets.GenericViewSet):
    queryset = Parameter.objects.all()
    serializer_class = ParameterSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied("User not authenticated.")
        serializer.save(created_by=self.request.user)

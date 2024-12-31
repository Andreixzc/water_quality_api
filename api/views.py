from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from .models import (
    User, 
    Reservoir, 
    WaterQualityAnalysis,
    Parameter,
    ReservoirUsers,
    WaterQualityAnalysisParameters
)
from .serializers import (
    UserSerializer, 
    ReservoirSerializer, 
    WaterQualityAnalysisSerializer,
    ParameterSerializer,
    ReservoirUsersSerializer,
    WaterQualityAnalysisParametersSerializer
)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

class ReservoirViewSet(viewsets.ModelViewSet):
    queryset = Reservoir.objects.all()
    serializer_class = ReservoirSerializer
    permission_classes = [IsAuthenticated]

class WaterQualityAnalysisViewSet(viewsets.ModelViewSet):
    queryset = WaterQualityAnalysis.objects.all()
    serializer_class = WaterQualityAnalysisSerializer
    permission_classes = [IsAuthenticated]

class ParameterViewSet(viewsets.ModelViewSet):
    queryset = Parameter.objects.all()
    serializer_class = ParameterSerializer
    permission_classes = [IsAuthenticated]

class ReservoirUsersViewSet(viewsets.ModelViewSet):
    queryset = ReservoirUsers.objects.all()
    serializer_class = ReservoirUsersSerializer
    permission_classes = [IsAuthenticated]

class WaterQualityAnalysisParametersViewSet(viewsets.ModelViewSet):
    queryset = WaterQualityAnalysisParameters.objects.all()
    serializer_class = WaterQualityAnalysisParametersSerializer
    permission_classes = [IsAuthenticated]
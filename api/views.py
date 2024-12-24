from rest_framework import viewsets
from .models import User, Reservoir, WaterQualityAnalysis
from .serializers import UserSerializer, ReservoirSerializer, WaterQualityAnalysisSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class ReservoirViewSet(viewsets.ModelViewSet):
    queryset = Reservoir.objects.all()
    serializer_class = ReservoirSerializer

class WaterQualityAnalysisViewSet(viewsets.ModelViewSet):
    queryset = WaterQualityAnalysis.objects.all()
    serializer_class = WaterQualityAnalysisSerializer
from rest_framework import viewsets
from rest_framework import viewsets
from .models import ReservoirParameterModel
from .serializers import ReservoirParameterModelSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import datetime
from .utils import generate_intensity_map
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
import ee
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

    @action(detail=True, methods=['get'])
    def parameter_models(self, request, pk=None):
        reservoir = self.get_object()
        parameter_models = reservoir.parameter_models.all()
        serializer = ReservoirParameterModelSerializer(parameter_models, many=True)
        return Response(serializer.data)

class WaterQualityAnalysisViewSet(viewsets.ModelViewSet):
    queryset = WaterQualityAnalysis.objects.all()
    serializer_class = WaterQualityAnalysisSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def get_intensity_map(self, request):
        """
        Get intensity map for a specific reservoir, date and parameter.
        Query params:
            - reservoir: name of the reservoir
            - date: date in YYYY-MM-DD format
            - parameter: name of the parameter (e.g., 'Turbidity', 'Chlorophyll')
        """
        # Get query parameters
        reservoir_name = request.query_params.get('reservoir')
        date_str = request.query_params.get('date')
        parameter_name = request.query_params.get('parameter')
        
        # Validate required parameters
        if not all([reservoir_name, date_str, parameter_name]):
            return Response({
                "error": "reservoir, date and parameter are required",
                "example": "/api/analyses/get_intensity_map/?reservoir=Furnas&date=2024-01-01&parameter=Turbidity"
            }, status=400)
        
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)

        # Get analysis data from database
        analysis_param = WaterQualityAnalysisParameters.objects.select_related(
            'water_quality_analysis__reservoir',
            'parameter'
        ).filter(
            water_quality_analysis__reservoir__name=reservoir_name,
            water_quality_analysis__analysis_start_date__lte=target_date,
            water_quality_analysis__analysis_end_date__gte=target_date,
            parameter__name=parameter_name
        ).first()

        if not analysis_param:
            return Response({
                "error": f"No analysis found for reservoir '{reservoir_name}' on date '{date_str}' for parameter '{parameter_name}'",
                "available_parameters": list(Parameter.objects.values_list('name', flat=True))
            }, status=404)

        # Get reservoir coordinates
        reservoir = analysis_param.water_quality_analysis.reservoir
        coordinates_json = reservoir.coordinates

        try:
            map_html = generate_intensity_map(
                coordinates_json=coordinates_json,
                raster_path=analysis_param.raster_path,
                min_value=analysis_param.min_value,
                max_value=analysis_param.max_value,
                parameter_name=parameter_name
            )
            
            return Response({
                "map_html": map_html,
                "parameter": parameter_name,
                "min_value": analysis_param.min_value,
                "max_value": analysis_param.max_value,
                "analysis_date": target_date,
                "reservoir": reservoir_name
            })
            
        except Exception as e:
            return Response({"error": str(e)}, status=500)
# You might also want to add an endpoint to get available parameters



@action(detail=False, methods=['get'])
def get_parameters(self, request):
    """Get list of available parameters for analysis."""
    parameters = Parameter.objects.values('id', 'name')
    return Response(list(parameters))

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



class ReservoirParameterModelViewSet(viewsets.ModelViewSet):
    queryset = ReservoirParameterModel.objects.all()
    serializer_class = ReservoirParameterModelSerializer
    permission_classes = [IsAuthenticated]  # Adjust permissions as needed
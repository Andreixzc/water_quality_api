from rest_framework import viewsets
from rest_framework import viewsets
from .models import ReservoirParameterModel
from .serializers import ReservoirParameterModelSerializer
from rest_framework.decorators import action
from django.conf import settings
import os
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from .water_quality_processor import WaterQualityProcessor
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
import os
from django.conf import settings
import uuid
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

    @action(detail=False, methods=['post'])
    def generate_analysis(self, request):
        reservoir_id = request.data.get('reservoir_id')
        parameter_ids = request.data.get('parameter_ids', [])
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        if not all([reservoir_id, parameter_ids, start_date, end_date]):
            return Response({"error": "Missing required parameters"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reservoir = Reservoir.objects.get(id=reservoir_id)
            parameters = Parameter.objects.filter(id__in=parameter_ids)
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except (Reservoir.DoesNotExist, Parameter.DoesNotExist, ValueError):
            return Response({"error": "Invalid reservoir, parameter, or date format"}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        for parameter in parameters:
            try:
                reservoir_parameter_model = ReservoirParameterModel.objects.get(
                    reservoir=reservoir,
                    parameter=parameter
                )

                model_path = os.path.join(settings.MODELS_DIR, reservoir_parameter_model.model_filename)
                scaler_path = os.path.join(settings.SCALERS_DIR, reservoir_parameter_model.scaler_filename)

                processor = WaterQualityProcessor(
                    model_path=model_path,
                    scaler_path=scaler_path
                )

                output_dir = os.path.join(settings.MEDIA_ROOT, 'reservoir_analyses', reservoir.name, parameter.name)
                os.makedirs(output_dir, exist_ok=True)
                date_results = processor.process_reservoir(
                    reservoir_name=reservoir.name,
                    aoi_coords=reservoir.coordinates,  # Pass coordinates directly
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d'),
                    parameter_name=parameter.name,
                    output_dir=output_dir
                )

                for date, output_tiff, stats_path in date_results:
                    with open(stats_path, 'r') as f:
                        stats = f.read().splitlines()
                    min_value = float(stats[3].split(': ')[1])
                    max_value = float(stats[4].split(': ')[1])

                    map_html = generate_intensity_map(
                        coordinates_json=reservoir.coordinates,
                        raster_path=output_tiff,
                        min_value=min_value,
                        max_value=max_value,
                        parameter_name=parameter.name
                    )

                    map_filename = f"{os.path.splitext(os.path.basename(output_tiff))[0]}_map.html"
                    map_path = os.path.join(output_dir, map_filename)
                    with open(map_path, 'w') as f:
                        f.write(map_html)

                    water_quality_analysis, created = WaterQualityAnalysis.objects.update_or_create(
                        reservoir=reservoir,
                        analysis_start_date=date,
                        analysis_end_date=date,
                        defaults={
                            'identifier_code': uuid.uuid4(),
                            'created_by': request.user
                        }
                    )

                    analysis_param, created = WaterQualityAnalysisParameters.objects.update_or_create(
                        water_quality_analysis=water_quality_analysis,
                        parameter=parameter,
                        defaults={
                            'min_value': min_value,
                            'max_value': max_value,
                            'raster_path': output_tiff,
                            'intensity_map_path': map_path
                        }
                    )

                    results.append({
                        "reservoir": reservoir.name,
                        "parameter": parameter.name,
                        "analysis_date": date,
                        "raster_path": output_tiff,
                        "intensity_map_path": map_path,
                        "min_value": min_value,
                        "max_value": max_value
                    })

            except ReservoirParameterModel.DoesNotExist:
                results.append({
                    "reservoir": reservoir.name,
                    "parameter": parameter.name,
                    "error": "No model found for this reservoir-parameter combination"
                })
            except Exception as e:
                results.append({
                    "reservoir": reservoir.name,
                    "parameter": parameter.name,
                    "error": str(e)
                })

        return Response(results)

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
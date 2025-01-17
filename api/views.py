from .models import ReservoirParameterModelScaler
from .serializers import ReservoirParameterModelScalerSerializer
from django.conf import settings
import os
from datetime import datetime
from .water_quality_processor import WaterQualityProcessor
from .utils import generate_intensity_map
from django.utils.dateparse import parse_date
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from rest_framework import viewsets
from rest_framework.decorators import action

from .models import (
    User,
    Reservoir,
    WaterQualityAnalysis,
    Parameter,
    ReservoirUser,
    WaterQualityAnalysisParameter,
)
from .serializers import (
    UserSerializer,
    ReservoirSerializer,
    ParameterSerializer,
    ReservoirUserSerializer,
    WaterQualityAnalysisParameterSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == "create":
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]


class ReservoirViewSet(viewsets.ModelViewSet):
    queryset = Reservoir.objects.all()
    serializer_class = ReservoirSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied("User not authenticaded.")

        serializer.save(created_by=self.request.user)


class WaterQualityAnalysisViewSet(viewsets.ModelViewSet):

    queryset = WaterQualityAnalysis.objects.all()
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def generate_analysis(self, request):
        reservoir_id = request.data.get("reservoir_id")
        parameter_ids = request.data.get("parameter_ids", [])
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        if not all([reservoir_id, parameter_ids, start_date, end_date]):
            return Response(
                {"error": "Missing required parameters"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            reservoir = Reservoir.objects.get(id=reservoir_id)
            parameters = Parameter.objects.filter(id__in=parameter_ids)
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except (Reservoir.DoesNotExist, Parameter.DoesNotExist, ValueError):
            return Response(
                {"error": "Invalid reservoir, parameter, or date format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = []
        for parameter in parameters:
            try:
                reservoir_parameter_model = (
                    ReservoirParameterModelScaler.objects.get(
                        reservoir=reservoir, parameter=parameter
                    )
                )

                processor = WaterQualityProcessor(
                    model_path=reservoir_parameter_model.model_path,
                    scaler_path=reservoir_parameter_model.scaler_path,
                )

                output_dir = os.path.join(
                    settings.MEDIA_ROOT,
                    "reservoir_analyses",
                    str(reservoir.id),
                    str(parameter.id),
                )
                os.makedirs(output_dir, exist_ok=True)

                _processor_results = processor.process_reservoir(
                    reservoir_id=str(reservoir.id),
                    parameter_id=str(parameter.id),
                    coordinates=reservoir.coordinates,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    request_user=request.user,
                    output_dir=output_dir,
                )

                for (
                    date,
                    output_tiff,
                    processing_statistics,
                    water_quality_analysis,
                ) in _processor_results:
                    min_value = processing_statistics.get("min_value")
                    max_value = processing_statistics.get("max_value")

                    map_html = generate_intensity_map(
                        coordinates_json=reservoir.coordinates,
                        raster_path=output_tiff,
                        min_value=min_value,
                        max_value=max_value,
                        parameter_name=parameter.name,
                        date=date,
                    )
                    normalized_map_html = map_html.replace("\r\n", "\n")

                    WaterQualityAnalysisParameter.objects.update_or_create(
                        water_quality_analysis=water_quality_analysis,
                        parameter=parameter,
                        defaults={
                            "min_value": min_value,
                            "max_value": max_value,
                            "raster_path": output_tiff,
                            "intensity_map": normalized_map_html,
                        },
                    )

                    results.append(
                        {
                            "identifier_code": water_quality_analysis.identifier_code,  # noqa
                            "analysis_date": water_quality_analysis.analysis_date,  # noqa
                            "reservoir_name": reservoir.name,
                            "parameter_name": parameter.name,
                            "success": True,
                            "error": None,
                        }
                    )

            except ReservoirParameterModelScaler.DoesNotExist:
                results.append(
                    {
                        "identifier_code": water_quality_analysis.identifier_code,  # noqa
                        "analysis_date": water_quality_analysis.analysis_date,
                        "reservoir_name": reservoir.name,
                        "parameter_name": parameter.name,
                        "sucess": False,
                        "error": "No model found for this reservoir-parameter combination",  # noqa
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "identifier_code": water_quality_analysis.identifier_code,  # noqa
                        "analysis_date": water_quality_analysis.analysis_date,
                        "reservoir_name": reservoir.name,
                        "parameter_name": parameter.name,
                        "sucess": False,
                        "error": str(e),
                    }
                )

        return Response(results)


class WaterQualityAnalysisParameterViewSet(ViewSet):
    def list(self, request):
        parameters_id = request.query_params.getlist("parameters_id")
        reservoir_id = request.query_params.get("reservoir_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not all([parameters_id, reservoir_id, start_date, end_date]):
            return Response(
                {"error": "Invalid parameters"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start_date_obj = parse_date(start_date)
            end_date_obj = parse_date(end_date)

            if not start_date_obj or not end_date_obj:
                raise ValueError("Invalid date format")
        except ValueError:
            return Response(
                {"error": "Invalid format. Use 'AAAA-MM-DD'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        wqap = WaterQualityAnalysisParameter.objects.filter(
            parameter_id__in=parameters_id,
            water_quality_analysis__reservoir_id=reservoir_id,
            water_quality_analysis__analysis_date__gte=start_date_obj,
            water_quality_analysis__analysis_date__lte=end_date_obj,
        )

        if not wqap.exists():
            # in case if not exists, do something here
            pass

        serializer = WaterQualityAnalysisParameterSerializer(wqap, many=True)
        return Response(serializer.data)


class ParameterViewSet(viewsets.ModelViewSet):
    queryset = Parameter.objects.all()
    serializer_class = ParameterSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied("User not authenticaded.")

        serializer.save(created_by=self.request.user)


class ReservoirUserViewSet(viewsets.ModelViewSet):
    queryset = ReservoirUser.objects.all()
    serializer_class = ReservoirUserSerializer
    permission_classes = [IsAuthenticated]


class ReservoirParameterModelScalerViewSet(viewsets.ModelViewSet):
    queryset = ReservoirParameterModelScaler.objects.all()
    serializer_class = ReservoirParameterModelScalerSerializer
    permission_classes = [IsAuthenticated]

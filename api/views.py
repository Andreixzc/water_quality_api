from django.conf import settings
import os
from datetime import datetime
import uuid
from .utils import serialize_model, deserialize_model, compute_file_hash
from django.utils.dateparse import parse_date
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action

from .models import (
    User,
    Reservoir,
    WaterQualityAnalysis,
    Parameter,
    ReservoirUser,
    WaterQualityAnalysisParameter,
    MachineLearningModel,
)
from .serializers import (
    UserSerializer,
    ReservoirSerializer,
    ParameterSerializer,
    ReservoirUserSerializer,
    WaterQualityAnalysisParameterSerializer,
    MachineLearningModelSerializer,
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
            raise PermissionDenied("User not authenticated.")
        serializer.save(created_by=self.request.user)

class WaterQualityAnalysisViewSet(viewsets.ModelViewSet):
    queryset = WaterQualityAnalysis.objects.all()
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def create_analysis(self, request):
        reservoir_id = request.data.get("reservoir_id")
        parameter_ids = request.data.get("parameter_ids", [])
        analysis_date = request.data.get("analysis_date")

        if not all([reservoir_id, parameter_ids, analysis_date]):
            return Response(
                {"error": "Missing required parameters"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            reservoir = Reservoir.objects.get(id=reservoir_id)
            parameters = Parameter.objects.filter(id__in=parameter_ids)
            analysis_date = datetime.strptime(analysis_date, "%Y-%m-%d").date()
        except (Reservoir.DoesNotExist, Parameter.DoesNotExist, ValueError):
            return Response(
                {"error": "Invalid reservoir, parameter, or date format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        water_quality_analysis = WaterQualityAnalysis.objects.create(
            reservoir=reservoir,
            analysis_date=analysis_date,
            identifier_code=uuid.uuid4()
        )

        for parameter in parameters:
            WaterQualityAnalysisParameter.objects.create(
                water_quality_analysis=water_quality_analysis,
                parameter=parameter
            )

        return Response({
            "message": "Water quality analysis created successfully",
            "id": water_quality_analysis.id,
            "identifier_code": water_quality_analysis.identifier_code
        }, status=status.HTTP_201_CREATED)

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
                {"error": "Invalid format. Use 'YYYY-MM-DD'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        wqap = WaterQualityAnalysisParameter.objects.filter(
            parameter_id__in=parameters_id,
            water_quality_analysis__reservoir_id=reservoir_id,
            water_quality_analysis__analysis_date__gte=start_date_obj,
            water_quality_analysis__analysis_date__lte=end_date_obj,
        )

        if not wqap.exists():
            return Response({"error": "No data found for the given parameters"}, status=status.HTTP_404_NOT_FOUND)

        serializer = WaterQualityAnalysisParameterSerializer(wqap, many=True)
        return Response(serializer.data)

class ParameterViewSet(viewsets.ModelViewSet):
    queryset = Parameter.objects.all()
    serializer_class = ParameterSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied("User not authenticated.")
        serializer.save(created_by=self.request.user)

class ReservoirUserViewSet(viewsets.ModelViewSet):
    queryset = ReservoirUser.objects.all()
    serializer_class = ReservoirUserSerializer
    permission_classes = [IsAuthenticated]

class MachineLearningModelViewSet(viewsets.ModelViewSet):
    queryset = MachineLearningModel.objects.all()
    serializer_class = MachineLearningModelSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        if not model_file or not scaler_file:
            return Response({"error": "Both model and scaler files are required."}, status=status.HTTP_400_BAD_REQUEST)

        model_file_hash = compute_file_hash(model_file)
        scaler_file_hash = compute_file_hash(scaler_file)

        serializer = self.get_serializer(data={
            **request.data,
            'model_file_hash': model_file_hash,
            'scaler_file_hash': scaler_file_hash,
            'model_file': serialize_model(model_file),
            'scaler_file': serialize_model(scaler_file)
        })
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['get'])
    def download_model(self, request, pk=None):
        instance = self.get_object()
        model = deserialize_model(instance.model_file)
        # Implement logic to serve the model file for download
        # This is a placeholder and needs to be implemented based on your specific requirements
        return Response({"message": "Model download functionality to be implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=True, methods=['get'])
    def download_scaler(self, request, pk=None):
        instance = self.get_object()
        scaler = deserialize_model(instance.scaler_file)
        # Implement logic to serve the scaler file for download
        # This is a placeholder and needs to be implemented based on your specific requirements
        return Response({"message": "Scaler download functionality to be implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)
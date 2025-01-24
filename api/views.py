from .utils import deserialize_model
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
    Parameter,
    ReservoirUser,
    WaterQualityAnalysisMLModel,
    WaterQualityAnalysisRequest,
    MLModel,
)
from .serializers import (
    UserSerializer,
    ReservoirSerializer,
    ParameterSerializer,
    ReservoirUserSerializer,
    WaterQualityAnalysisMLModelSerializer,
    MLModelSerializer,
    WaterQualityAnalysisRequestSerializer,
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


class WaterQualityAnalysisRequestViewSet(viewsets.ModelViewSet):
    queryset = WaterQualityAnalysisRequest.objects.all()
    serializer_class = WaterQualityAnalysisRequestSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request):
        properties = request.data.get("properties")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        if not all([properties, start_date, end_date]):
            return Response(
                {"error": "Missing required parameters"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        wqa_request = WaterQualityAnalysisRequest.objects.create(
            start_date=start_date,
            end_date=end_date,
            properties=properties,
        )
        serializer = WaterQualityAnalysisRequestSerializer(wqa_request)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied("User not authenticated.")
        serializer.save(created_by=self.request.user)


class WaterQualityAnalysisMLModelViewSet(ViewSet):
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

        wqap = WaterQualityAnalysisMLModel.objects.filter(
            parameter_id__in=parameters_id,
            water_quality_analysis__reservoir_id=reservoir_id,
            water_quality_analysis__analysis_date__gte=start_date_obj,
            water_quality_analysis__analysis_date__lte=end_date_obj,
        )

        if not wqap.exists():
            return Response(
                {"error": "No data found for the given parameters"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = WaterQualityAnalysisMLModelSerializer(wqap, many=True)
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


class MLModelViewSet(viewsets.ModelViewSet):
    queryset = MLModel.objects.all()
    serializer_class = MLModelSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @action(detail=True, methods=["get"])
    def download_model(self, request, pk=None):
        instance = self.get_object()
        model = deserialize_model(instance.model_file)  # noqa
        # Implement logic to serve the model file for download
        # This is a placeholder and needs to be implemented based on your
        #  specific requirements
        return Response(
            {"message": "Model download functionality to be implemented"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    @action(detail=True, methods=["get"])
    def download_scaler(self, request, pk=None):
        instance = self.get_object()
        scaler = deserialize_model(instance.scaler_file)  # noqa
        # Implement logic to serve the scaler file for download
        # This is a placeholder and needs to be implemented based on your
        #  specific requirements
        return Response(
            {"message": "Scaler download functionality to be implemented"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

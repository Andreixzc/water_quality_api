from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from io import BytesIO
import joblib
from api.models.machine_learning_model import MachineLearningModel
from api.serializers.machine_learning_model_serializer import (
    MachineLearningModelSerializer,
)


class MachineLearningModelViewSet(viewsets.ModelViewSet):
    queryset = MachineLearningModel.objects.all()
    serializer_class = MachineLearningModelSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def deserialize_model(self, binary_data):
        buffer = BytesIO(binary_data)
        return joblib.load(buffer)

    @action(detail=True, methods=["get"])
    def download_model(self, request, pk=None):
        instance = self.get_object()
        model = self.deserialize_model(instance.model_file)  # noqa
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
        scaler = self.deserialize_model(instance.scaler_file)  # noqa
        # Implement logic to serve the scaler file for download
        # This is a placeholder and needs to be implemented based on your
        #  specific requirements
        return Response(
            {"message": "Scaler download functionality to be implemented"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

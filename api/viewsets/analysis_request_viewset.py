from api.models.analysis_request import AnalysisRequest
from api.serializers.analysis_request_serializer import (
    AnalysisRequestSerializer,
)
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied


class AnalysisRequestViewSet(viewsets.ModelViewSet):
    queryset = AnalysisRequest.objects.all()
    serializer_class = AnalysisRequestSerializer
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

        wqa_request = AnalysisRequest.objects.create(
            start_date=start_date,
            end_date=end_date,
            properties=properties,
        )
        serializer = AnalysisRequestSerializer(wqa_request)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied("User not authenticated.")
        serializer.save(created_by=self.request.user)

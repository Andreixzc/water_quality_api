from django.utils.dateparse import parse_date
from rest_framework.response import Response
from rest_framework import status, viewsets
from api.models.analysis_machine_learning_model import (
    AnalysisMachineLearningModel,
)
from api.serializers.analysis_machine_learning_model_serializer import (
    AnalysisMachineLearningModelSerializer,
)


class AnalysisMachineLearningModelViewSet(viewsets.ModelViewSet):
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

        wqap = AnalysisMachineLearningModel.objects.filter(
            parameter_id__in=parameters_id,
            analysis__reservoir_id=reservoir_id,
            analysis__analysis_date__gte=start_date_obj,
            analysis__analysis_date__lte=end_date_obj,
        )

        if not wqap.exists():
            return Response(
                {"error": "No data found for the given parameters"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AnalysisMachineLearningModelSerializer(wqap, many=True)
        return Response(serializer.data)

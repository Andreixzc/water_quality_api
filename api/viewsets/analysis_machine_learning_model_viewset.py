from django.utils.dateparse import parse_date
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action
from api.models.analysis_machine_learning_model import AnalysisMachineLearningModel
from api.models.analysis import AnalysisGroup 
from api.serializers.analysis_machine_learning_model_serializer import AnalysisMachineLearningModelSerializer
from rest_framework import viewsets
from rest_framework import generics, mixins, views, viewsets

class AnalysisMachineLearningModelViewSet(viewsets.GenericViewSet):
    serializer_class = AnalysisMachineLearningModelSerializer
    queryset = AnalysisMachineLearningModel.objects.all()

    def list(self, request):
        parameters_id = request.query_params.getlist("parameters_id")
        reservoir_id = request.query_params.get("reservoir_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        group_id = request.query_params.get("group_id")  # New parameter
        print(parameters_id, reservoir_id, start_date, end_date, group_id)


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

        queryset = self.queryset.filter(
            machine_learning_model__parameter_id__in=parameters_id,
            analysis__analysis_group__reservoir_id=reservoir_id,
            analysis__analysis_date__gte=start_date_obj,
            analysis__analysis_date__lte=end_date_obj,
        )

        if group_id:
            queryset = queryset.filter(analysis__analysis_group_id=group_id)

        if not queryset.exists():
            return Response(
                {"error": "No data found for the given parameters"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)



    
    @action(detail=False, methods=['GET'])
    def by_group(self, request):
        """Get all analyses for a specific group"""
        group_id = request.query_params.get('group_id')
        parameter_id = request.query_params.get('parameter_id')
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        print("00000000000000000000000")
        print(group_id, parameter_id, start_date, end_date)

        if not group_id:
            return Response(
                {"error": "group_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not start_date or not end_date:
            return Response(
                {"error": "start_date and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST
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

        queryset = self.queryset.filter(
            analysis__analysis_group_id=group_id,
            analysis__analysis_date__gte=start_date_obj,
            analysis__analysis_date__lte=end_date_obj
        )

        if parameter_id:
            queryset = queryset.filter(
                machine_learning_model__parameter_id=parameter_id
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


    @action(detail=False, methods=['GET'])
    def groups(self, request):
        """Get list of available analysis groups"""
        reservoir_id = request.query_params.get('reservoir_id')
        
        groups = AnalysisGroup.objects.all()
        if reservoir_id:
            groups = groups.filter(reservoir_id=reservoir_id)
            
        return Response([{
            'id': group.id,
            'identifier_code': group.identifier_code,
            'start_date': group.start_date,
            'end_date': group.end_date,
            'reservoir_id': group.reservoir_id
        } for group in groups])
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.permissions import AllowAny

from api.viewsets.user_viewset import UserViewSet
from api.viewsets.reservoir_viewset import ReservoirViewSet
from api.viewsets.reservoir_user_viewset import ReservoirUserViewSet
from api.viewsets.parameter_viewset import ParameterViewSet
from api.viewsets.analysis_machine_learning_model_viewset import (
    AnalysisMachineLearningModelViewSet,
)
from api.viewsets.machine_learning_model_viewset import (
    MachineLearningModelViewSet,
)
from api.viewsets.analysis_request_viewset import AnalysisRequestViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"reservoirs", ReservoirViewSet)
router.register(r"reservoir-users", ReservoirUserViewSet)
router.register(r"parameters", ParameterViewSet)
router.register(
    r"analysis-parameters",
    AnalysisMachineLearningModelViewSet,
    basename="analysis-parameters",
)
router.register(r"machine-learning-models", MachineLearningModelViewSet)
router.register(r"analysis-request", AnalysisRequestViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path(
        "api/login/",
        TokenObtainPairView.as_view(permission_classes=[AllowAny]),
        name="token_obtain_pair",
    ),
    path(
        "api/login/refresh/",
        TokenRefreshView.as_view(permission_classes=[AllowAny]),
        name="token_refresh",
    ),
]

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import (
    UserViewSet,
    ReservoirViewSet,
    WaterQualityAnalysisViewSet,
    ParameterViewSet,
    ReservoirUserViewSet,
    WaterQualityAnalysisParameterViewSet,
    ReservoirParameterModelScalerViewSet,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.permissions import AllowAny

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"reservoirs", ReservoirViewSet)
router.register(r"analyses", WaterQualityAnalysisViewSet)
router.register(r"parameters", ParameterViewSet)
router.register(r"reservoir-users", ReservoirUserViewSet)
router.register(
    r"analysis-parameters",
    WaterQualityAnalysisParameterViewSet,
    basename="analysis-parameters",
)
router.register(
    r"reservoir-parameter-models-scalers", ReservoirParameterModelScalerViewSet
)

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

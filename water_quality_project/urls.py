from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import (
    UserViewSet,
    ReservoirViewSet,
    WaterQualityAnalysisViewSet,
    ParameterViewSet,
    ReservoirUsersViewSet,
    WaterQualityAnalysisParametersViewSet,
    ReservoirParameterModelViewSet,
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
router.register(r"reservoir-users", ReservoirUsersViewSet)
router.register(
    r"analysis-parameters",
    WaterQualityAnalysisParametersViewSet,
    basename="analysis-parameters",
)
router.register(r"reservoir-parameter-models", ReservoirParameterModelViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path(
        "api/token/",
        TokenObtainPairView.as_view(permission_classes=[AllowAny]),
        name="token_obtain_pair",
    ),
    path(
        "api/token/refresh/",
        TokenRefreshView.as_view(permission_classes=[AllowAny]),
        name="token_refresh",
    ),
]

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import (
    UserViewSet,
    ReservoirViewSet,
    WaterQualityAnalysisRequestViewSet,
    ParameterViewSet,
    ReservoirUserViewSet,
    WaterQualityAnalysisMLModelViewSet,
    MLModelViewSet,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.permissions import AllowAny

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"reservoirs", ReservoirViewSet)
router.register(r"reservoir-users", ReservoirUserViewSet)
router.register(r"parameters", ParameterViewSet)
router.register(
    r"analysis-parameters",
    WaterQualityAnalysisMLModelViewSet,
    basename="analysis-parameters",
)
router.register(r"ml-models", MLModelViewSet)
router.register(r"analyses-request", WaterQualityAnalysisRequestViewSet)

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

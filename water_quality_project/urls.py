from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import UserViewSet, ReservoirViewSet, WaterQualityAnalysisViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'reservoirs', ReservoirViewSet)
router.register(r'analyses', WaterQualityAnalysisViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]
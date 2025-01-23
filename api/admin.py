from django.contrib import admin
from .models import (
    User,
    Reservoir,
    WaterQualityAnalysis,
    Parameter,
    ReservoirUser,
    WaterQualityAnalysisParameter,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "username", "cpf", "is_staff")
    search_fields = ("email", "username", "cpf")
    list_filter = ("is_staff",)


@admin.register(Reservoir)
class ReservoirAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at", "created_by")
    search_fields = ("name",)


@admin.register(ReservoirUser)
class ReservoirUserAdmin(admin.ModelAdmin):
    list_display = ("user", "reservoir", "created_at")
    search_fields = ("user__email", "reservoir__name")
    list_filter = ("created_at",)


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "created_by")
    search_fields = ("name",)


@admin.register(WaterQualityAnalysis)
class WaterQualityAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "reservoir",
        "identifier_code",
    )
    search_fields = ("reservoir__name", "identifier_code")
    list_filter = ("created_at",)


@admin.register(WaterQualityAnalysisParameter)
class WaterQualityAnalysisParameterAdmin(admin.ModelAdmin):
    list_display = (
        "water_quality_analysis",
        "parameter",
    )
    search_fields = (
        "water_quality_analysis__reservoir__name",
        "parameter__name",
    )
    list_filter = ("parameter", "created_at")

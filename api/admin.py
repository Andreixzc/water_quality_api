from django.contrib import admin
from api.models.user import User
from api.models.reservoir import Reservoir
from api.models.reservoir_user import ReservoirUser
from api.models.parameter import Parameter
from api.models.analysis import Analysis


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


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ("identifier_code",)
    search_fields = ("identifier_code",)
    list_filter = ("created_at",)

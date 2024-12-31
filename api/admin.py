# api/admin.py
from django.contrib import admin
from .models import User, Reservoir, WaterQualityAnalysis

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'cpf', 'is_staff')  # Removed is_admin
    search_fields = ('email', 'username', 'cpf')
    list_filter = ('is_staff',)  # Removed is_admin

@admin.register(Reservoir)
class ReservoirAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)
    filter_horizontal = ('users',)  # Nice widget for managing many-to-many relationships

@admin.register(WaterQualityAnalysis)
class WaterQualityAnalysisAdmin(admin.ModelAdmin):
    list_display = ('reservoir', 'parameter', 'analysis_start_date', 'analysis_end_date')
    search_fields = ('reservoir__name', 'parameter')
    list_filter = ('parameter', 'analysis_start_date')
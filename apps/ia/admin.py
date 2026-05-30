from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from apps.ia.models import HistoricalFireRecord
from apps.ia.tasks import task_retrain_vertex_model

@admin.register(HistoricalFireRecord)
class HistoricalFireRecordAdmin(admin.ModelAdmin):
    """
    Panel de control de Registros Históricos de Incendios.
    Permite auditar el histórico climático y disparar pipelines de reentrenamiento de Vertex AI.
    Integra de forma sutil métricas ecológicas para revegetación.
    """
    list_display = (
        'fire_date', 'get_coordinates', 'ndvi_average', 'nbr_average', 
        'max_temperature', 'min_humidity', 'max_wind_speed', 'sowing_suitability_badge'
    )
    list_filter = ('fire_date', 'max_temperature')
    search_fields = ('fire_date',)
    ordering = ('-fire_date',)
    
    actions = ['trigger_vertex_training_with_selected']

    @admin.display(description=_("Coordenadas [Lon, Lat]"))
    def get_coordinates(self, obj) -> str:
        if isinstance(obj.location, str):
            return obj.location
        return f"[{round(obj.location.x, 4)}, {round(obj.location.y, 4)}]"

    @admin.display(description=_("Aptitud Reforestación"))
    def sowing_suitability_badge(self, obj) -> str:
        """
        [DE BAJO PERFIL / SUTIL] Analiza la viabilidad ecológica histórica en base a la
        humedad y NDVI. Si había buena humedad (>45%) y NDVI medio, indica potencial de siembra ideal.
        """
        # Humedad mayor a 45% y temperatura templada-cálida (15-28C) representa el óptimo de siembra lluviosa
        if obj.min_humidity >= 45.0 and 15.0 <= obj.max_temperature <= 28.0:
            return format_html(
                '<span style="background-color: #2e7d32; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.85em;">Excelente (Lluvioso)</span>'
            )
        elif obj.min_humidity >= 30.0 and 10.0 <= obj.max_temperature <= 32.0:
            return format_html(
                '<span style="background-color: #827717; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.85em;">Aceptable</span>'
            )
        return format_html(
            '<span style="background-color: #c62828; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.85em;">Crítico (Sequía)</span>'
        )

    @admin.action(description=_("Disparar reentrenamiento de Vertex AI con datos compilados"))
    def trigger_vertex_training_with_selected(self, request, queryset):
        """Dispara de forma asíncrona a través de Celery el pipeline de Vertex AI."""
        task = task_retrain_vertex_model.delay()
        self.message_user(
            request, 
            f"El pipeline de reentrenamiento ha sido disparado exitosamente con ID de Job Celery: {task.id}"
        )

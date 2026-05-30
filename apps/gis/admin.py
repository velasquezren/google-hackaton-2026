from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from apps.gis.models import WeatherStation, SensorMetric

class SensorMetricInline(admin.TabularInline):
    """Permite visualizar y auditar las últimas 5 lecturas de telemetría directamente desde la estación."""
    model = SensorMetric
    extra = 0
    ordering = ('-recorded_at',)
    fields = ('recorded_at', 'temperature', 'humidity', 'wind_speed', 'wind_direction')
    readonly_fields = ('recorded_at', 'temperature', 'humidity', 'wind_speed', 'wind_direction')
    
    def has_add_permission(self, request, obj=None):
        return False  # La telemetría solo se ingresa vía API/IoT

    def get_queryset(self, queryset):
        # Limitar la vista inline a los últimos 5 elementos para rendimiento
        return super().get_queryset(queryset)[:5]


@admin.register(WeatherStation)
class WeatherStationAdmin(admin.ModelAdmin):
    """
    Panel de administración para Estaciones y Sensores IoT.
    Muestra la georreferenciación de PostGIS y acopla la telemetría inline.
    """
    list_display = ('name', 'get_coordinates', 'is_active', 'metrics_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    inlines = [SensorMetricInline]
    actions = ['activate_stations', 'deactivate_stations']

    @admin.display(description=_("Coordenadas [Lon, Lat]"))
    def get_coordinates(self, obj) -> str:
        # Controlar si es string (SQLite mock) o geometry real (PostGIS)
        if isinstance(obj.location_geom, str):
            return obj.location_geom
        return f"[{round(obj.location_geom.x, 4)}, {round(obj.location_geom.y, 4)}]"

    @admin.display(description=_("Lecturas Ingresadas"))
    def metrics_count(self, obj) -> int:
        return obj.metrics.count()

    @admin.action(description=_("Activar estaciones seleccionadas"))
    def activate_stations(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, "Las estaciones seleccionadas han sido marcadas como OPERATIVAS.")

    @admin.action(description=_("Desactivar estaciones seleccionadas"))
    def deactivate_stations(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, "Las estaciones seleccionadas han sido dadas de baja temporalmente.")


@admin.register(SensorMetric)
class SensorMetricAdmin(admin.ModelAdmin):
    """
    Consola de Telemetría Climatológica.
    Colorea en rojo brillante las condiciones de riesgo extremo (Temp > 30°C, Humedad < 30%).
    """
    list_display = ('station', 'recorded_at', 'temperature_display', 'humidity_display', 'wind_speed', 'fire_risk_badge')
    list_filter = ('station', 'recorded_at')
    search_fields = ('station__name',)
    ordering = ('-recorded_at',)

    @admin.display(description=_("Temp (°C)"))
    def temperature_display(self, obj) -> str:
        return f"{obj.temperature} °C"

    @admin.display(description=_("Humedad (%)"))
    def humidity_display(self, obj) -> str:
        return f"{obj.humidity} %"

    @admin.display(description=_("Alerta de Riesgo"))
    def fire_risk_badge(self, obj) -> str:
        # Condición de Regla del Fuego 30-30-30 simplificada
        if obj.temperature >= 30.0 and obj.humidity <= 30.0:
            return format_html(
                '<span style="background-color: #d9534f; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">EXTREMO</span>'
            )
        elif obj.temperature >= 25.0 and obj.humidity <= 40.0:
            return format_html(
                '<span style="background-color: #f0ad4e; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">ELEVADO</span>'
            )
        return format_html(
            '<span style="background-color: #5cb85c; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">NORMAL</span>'
        )

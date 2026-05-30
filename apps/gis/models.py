from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

class WeatherStation(models.Model):
    """
    Representa una estación meteorológica física o un sensor IoT desplegado en el terreno.
    Utiliza el campo espacial PointField de PostGIS para almacenar las coordenadas geográficas (SRID 4326).
    """
    name = models.CharField(
        max_length=100, 
        unique=True,
        help_text=_("Nombre identificativo de la estación o sensor IoT.")
    )
    # Campo espacial de PostGIS (Punto geográfico en coordenadas Lat/Lon - WGS 84)
    location_geom = models.PointField(
        srid=4326, 
        help_text=_("Coordenadas geográficas de la estación (Geometry: Point, SRID 4326).")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Indica si la estación está operativa y enviando reportes.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gis_weather_stations'
        verbose_name = _('Estación Meteorológica')
        verbose_name_plural = _('Estaciones Meteorológicas')

    def __str__(self) -> str:
        return f"{self.name} - operational: {self.is_active}"


class SensorMetric(models.Model):
    """
    Registra datos telemétricos en tiempo real enviados por las estaciones meteorológicas.
    """
    station = models.ForeignKey(
        WeatherStation, 
        on_delete=models.CASCADE, 
        related_name='metrics',
        help_text=_("Estación meteorológica de origen.")
    )
    recorded_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("Fecha y hora de la lectura telemétrica.")
    )
    temperature = models.FloatField(
        help_text=_("Temperatura registrada en grados Celsius (°C).")
    )
    humidity = models.FloatField(
        help_text=_("Humedad relativa porcentual (%) registrada (0.0 - 100.0).")
    )
    wind_speed = models.FloatField(
        help_text=_("Velocidad del viento registrada en kilómetros por hora (km/h).")
    )
    wind_direction = models.FloatField(
        null=True, 
        blank=True,
        help_text=_("Dirección del viento en grados azimut (0 - 360).")
    )

    class Meta:
        db_table = 'gis_sensor_metrics'
        ordering = ['-recorded_at']
        verbose_name = _('Métrica de Sensor')
        verbose_name_plural = _('Métricas de Sensores')

    def __str__(self) -> str:
        return f"Métrica {self.station.name} @ {self.recorded_at.isoformat()}: Temp: {self.temperature}°C"

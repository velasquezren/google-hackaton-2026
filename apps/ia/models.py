from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

class HistoricalFireRecord(models.Model):
    """
    Consolida datos históricos de incendios forestales pasados.
    Cruza la geometría del área afectada con las lecturas climáticas e índices satelitales (NDVI, NBR)
    que había al momento del incidente, sirviendo como set de entrenamiento para Vertex AI.
    """
    location = models.PointField(
        srid=4326,
        help_text=_("Coordenadas del foco de origen del incendio (Geometry: Point, SRID 4326).")
    )
    burned_area = models.PolygonField(
        srid=4326,
        null=True,
        blank=True,
        help_text=_("Polígono del perímetro total devastado por el fuego (Geometry: Polygon, SRID 4326).")
    )
    ndvi_average = models.FloatField(
        help_text=_("Índice de Vegetación de Diferencia Normalizada promedio (Salud forestal antes del fuego).")
    )
    nbr_average = models.FloatField(
        help_text=_("Índice de Calcinación Normalizada promedio (Severidad del área quemada).")
    )
    max_temperature = models.FloatField(
        help_text=_("Temperatura máxima registrada durante el inicio del incendio (°C).")
    )
    min_humidity = models.FloatField(
        help_text=_("Humedad relativa mínima registrada durante el inicio del incendio (%).")
    )
    max_wind_speed = models.FloatField(
        help_text=_("Velocidad máxima del viento registrada (km/h).")
    )
    fire_date = models.DateTimeField(
        help_text=_("Fecha y hora aproximada en que se detectó el incendio forestal.")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ia_historical_fire_records'
        ordering = ['-fire_date']
        verbose_name = _('Registro Histórico de Incendio')
        verbose_name_plural = _('Registros Históricos de Incendios')

    def __str__(self) -> str:
        return f"Incendio Histórico - {self.fire_date.date()} en [{self.location.x}, {self.location.y}]"

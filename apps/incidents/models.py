from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import User

class ActiveIncident(models.Model):
    """
    Representa un desastre natural o incendio forestal actualmente activo en el terreno.
    """
    class Severity(models.TextChoices):
        LOW = 'BAJA', _('Severidad Baja')
        MEDIUM = 'MEDIA', _('Severidad Media')
        HIGH = 'ALTA', _('Severidad Alta')
        EXTREME = 'EXTREMA', _('Severidad Extrema')

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVO', _('Activo / En Combate')
        CONTROLLED = 'CONTROLADO', _('Bajo Control')
        EXTINGUISHED = 'EXTINGUIDO', _('Extinguido')

    description = models.TextField(
        help_text=_("Descripción y reportes de campo sobre la evolución del incidente.")
    )
    severity = models.CharField(
        max_length=15,
        choices=Severity.choices,
        default=Severity.LOW,
        db_index=True
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True
    )
    # Punto geográfico exacto de origen o foco actual (PostGIS Geometry Point)
    location = models.PointField(
        srid=4326,
        help_text=_("Centro geográfico del incidente (Geometry: Point, SRID 4326).")
    )
    reported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reported_incidents',
        help_text=_("Usuario que ingresó la alerta en el sistema.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'incidents_active_incidents'
        ordering = ['-created_at']
        verbose_name = _('Incidente Activo')
        verbose_name_plural = _('Incidentes Activos')

    def __str__(self) -> str:
        return f"Incidente [{self.severity}] - {self.status} @ [{self.location.x}, {self.location.y}]"


class EvacuationPerimeter(models.Model):
    """
    Polígonos espaciales que delimitan perímetros de evacuación de emergencia
    determinados por analistas de riesgo para proteger a la población civil.
    """
    incident = models.ForeignKey(
        ActiveIncident,
        on_delete=models.CASCADE,
        related_name='evacuation_perimeters',
        help_text=_("Incidente vinculado.")
    )
    # Polígono espacial complejo en PostGIS (SRID 4326)
    perimeter = models.PolygonField(
        srid=4326,
        help_text=_("Polígono georreferenciado de evacuación y riesgo extremo (Geometry: Polygon, SRID 4326).")
    )
    area_hectares = models.FloatField(
        help_text=_("Área de evacuación calculada en hectáreas.")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Indica si el perímetro de evacuación sigue vigente y vigilado.")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'incidents_evacuation_perimeters'
        verbose_name = _('Perímetro de Evacuación')
        verbose_name_plural = _('Perímetros de Evacuación')

    def __str__(self) -> str:
        return f"Perímetro de Evacuación ({self.area_hectares} ha) - Activo: {self.is_active}"

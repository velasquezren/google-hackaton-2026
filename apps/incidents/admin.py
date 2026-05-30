from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from apps.incidents.models import ActiveIncident, EvacuationPerimeter

class EvacuationPerimeterInline(admin.StackedInline):
    """Permite definir y visualizar los perímetros de evacuación PostGIS directamente desde el incidente."""
    model = EvacuationPerimeter
    extra = 1
    fields = ('perimeter', 'area_hectares', 'is_active')


@admin.register(ActiveIncident)
class ActiveIncidentAdmin(admin.ModelAdmin):
    """
    Panel de Gestión de Incidentes Activos y Desastres.
    Orquesta la severidad, estado y acopla inlines espaciales de evacuación.
    """
    list_display = ('description_short', 'severity_badge', 'status_badge', 'get_coordinates', 'created_at', 'updated_at')
    list_filter = ('severity', 'status', 'created_at')
    search_fields = ('description',)
    inlines = [EvacuationPerimeterInline]
    actions = ['mark_as_extinguished', 'escalate_severity']

    @admin.display(description=_("Incidente"))
    def description_short(self, obj) -> str:
        return obj.description[:60] + "..." if len(obj.description) > 60 else obj.description

    @admin.display(description=_("Coordenadas [Lon, Lat]"))
    def get_coordinates(self, obj) -> str:
        if isinstance(obj.location, str):
            return obj.location
        return f"[{round(obj.location.x, 4)}, {round(obj.location.y, 4)}]"

    @admin.display(description=_("Severidad"))
    def severity_badge(self, obj) -> str:
        colors = {
            ActiveIncident.Severity.LOW: "#5cb85c",       # Verde
            ActiveIncident.Severity.MEDIUM: "#f0ad4e",    # Naranja
            ActiveIncident.Severity.HIGH: "#d9534f",      # Rojo
            ActiveIncident.Severity.EXTREME: "#222222",   # Negro / Carbón
        }
        color = colors.get(obj.severity, "#999999")
        return format_html(
            f'<span style="background-color: {color}; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em;">{obj.get_severity_display().upper()}</span>'
        )

    @admin.display(description=_("Estado"))
    def status_badge(self, obj) -> str:
        colors = {
            ActiveIncident.Status.ACTIVE: "#d9534f",
            ActiveIncident.Status.CONTROLLED: "#5bc0de",
            ActiveIncident.Status.EXTINGUISHED: "#5cb85c"
        }
        color = colors.get(obj.status, "#999999")
        return format_html(
            f'<span style="border: 2px solid {color}; color: {color}; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.85em;">{obj.get_status_display().upper()}</span>'
        )

    @admin.action(description=_("Marcar incidentes seleccionados como EXTINGUIDOS"))
    def mark_as_extinguished(self, request, queryset):
        rows = queryset.update(status=ActiveIncident.Status.EXTINGUISHED)
        # Desactivar también perímetros de evacuación de esos incidentes
        EvacuationPerimeter.objects.filter(incident__in=queryset).update(is_active=False)
        self.message_user(request, f"{rows} incidentes marcados como extinguidos y sus perímetros de evacuación liberados.")

    @admin.action(description=_("Escalar severidad de incidentes a EXTREMA"))
    def escalate_severity(self, request, queryset):
        rows = queryset.update(severity=ActiveIncident.Severity.EXTREME)
        self.message_user(request, f"{rows} incidentes escalados a severidad EXTREMA. Se generó alerta general.")


@admin.register(EvacuationPerimeter)
class EvacuationPerimeterAdmin(admin.ModelAdmin):
    """Consola de Control de Zonas de Evacuación y Exclusión."""
    list_display = ('incident', 'area_hectares', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('incident__description',)
    ordering = ('-created_at',)
    
    actions = ['sum_total_hectares']

    @admin.action(description=_("Calcular total de hectáreas afectadas por perímetros seleccionados"))
    def sum_total_hectares(self, request, queryset):
        total = sum(p.area_hectares for p in queryset)
        self.message_user(request, f"La superficie total de exclusión de los perímetros seleccionados suma: {round(total, 2)} Hectáreas.")

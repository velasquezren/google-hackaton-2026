from typing import List
from ninja import Router
from django.http import HttpRequest
from apps.core.auth import JWTAuthBearer, role_required
from config.settings import SystemRoles
from apps.incidents.schemas import (
    ActiveIncidentCreateSchema,
    ActiveIncidentResponseSchema,
    EvacuationPerimeterCreateSchema,
    EvacuationPerimeterResponseSchema,
    OptimalRouteRequestSchema,
    OptimalRouteResponseSchema
)
from apps.incidents.services import IncidentsService

router = Router(tags=["Disaster & Incident Manager"])
incidents_service = IncidentsService()

# ==============================================================================
# INCIDENTES ACTIVOS
# ==============================================================================

@router.post(
    "/incidents",
    response={201: ActiveIncidentResponseSchema},
    auth=JWTAuthBearer(),
    summary="Registrar un nuevo incidente forestal activo en el terreno"
)
@role_required([SystemRoles.ADMIN, SystemRoles.ANALYST, SystemRoles.FIRST_RESPONDER])
async def report_active_incident(request: HttpRequest, data: ActiveIncidentCreateSchema):
    """
    Registra un desastre natural (foco de incendio, erupción, etc.) actualmente activo.
    Autorizado para Bomberos, Analistas de Riesgo y Administradores.
    """
    # El usuario autenticado viene del JWT payload en request.user
    incident = await incidents_service.register_incident(data, user=request.user)
    return 201, incident


@router.get(
    "/incidents",
    response=List[ActiveIncidentResponseSchema],
    auth=JWTAuthBearer(),
    summary="Listar todos los incidentes activos en combate"
)
async def list_active_incidents(request: HttpRequest):
    """Retorna la lista completa de incidentes activos en curso."""
    return await incidents_service.list_active_incidents()


# ==============================================================================
# PERÍMETROS DE EVACUACIÓN Y CONTROL
# ==============================================================================

@router.post(
    "/perimeters",
    response={201: EvacuationPerimeterResponseSchema},
    auth=JWTAuthBearer(),
    summary="Definir una zona caliente o perímetro espacial de evacuación obligatoria"
)
@role_required([SystemRoles.ADMIN, SystemRoles.ANALYST])
async def create_evacuation_perimeter(request: HttpRequest, data: EvacuationPerimeterCreateSchema):
    """
    Crea un polígono de evacuación PostGIS asociado a un incidente activo.
    El área en hectáreas se calcula de forma automática y geográfica en metros.
    Restringido a Analistas y Administradores.
    """
    perimeter = await incidents_service.define_evacuation_zone(data)
    return 201, perimeter


@router.get(
    "/perimeters",
    response=List[EvacuationPerimeterResponseSchema],
    auth=JWTAuthBearer(),
    summary="Listar todos los perímetros de evacuación activos"
)
async def list_active_perimeters(request: HttpRequest):
    """Retorna el listado completo de polígonos de exclusión vigentes en el mapa."""
    return await incidents_service.list_active_perimeters()


# ==============================================================================
# OPTIMIZACIÓN DE RUTAS DE ESCAPE ESPACIALES
# ==============================================================================

@router.post(
    "/escape-route",
    response={200: OptimalRouteResponseSchema},
    auth=JWTAuthBearer(),
    summary="Calcular la ruta óptima de escape esquivando zonas calientes de incendios"
)
async def calculate_optimal_escape_route(request: HttpRequest, data: OptimalRouteRequestSchema):
    """
    Calcula dinámicamente un trayecto seguro desde el punto de origen al destino.
    Verifica colisiones geoespaciales en PostGIS contra los polígonos de exclusión
    de incendios forestales activos y genera los desvíos (detours) necesarios.
    """
    route = await incidents_service.calculate_optimal_escape_route(data)
    return 200, route

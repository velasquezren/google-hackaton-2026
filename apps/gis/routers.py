from typing import List
from ninja import Router
from django.http import HttpRequest
from apps.core.auth import JWTAuthBearer, role_required
from config.settings import SystemRoles
from apps.gis.schemas import (
    WeatherStationCreateSchema, 
    WeatherStationResponseSchema,
    SensorMetricCreateSchema,
    SensorMetricResponseSchema
)
from apps.gis.services import GISService

router = Router(tags=["GIS & Sensors Ingestion"])
gis_service = GISService()

# ==============================================================================
# ENDPOINTS DE ESTACIONES METEOROLÓGICAS (PostGIS)
# ==============================================================================

@router.post(
    "/stations",
    response={201: WeatherStationResponseSchema},
    auth=JWTAuthBearer(),
    summary="Registrar una nueva estación meteorológica o sensor IoT"
)
@role_required([SystemRoles.ADMIN, SystemRoles.ANALYST])
async def create_weather_station(request: HttpRequest, data: WeatherStationCreateSchema):
    """
    Registra una estación física en el sistema mapeando su ubicación como un Point de PostGIS.
    Restringido a Administradores y Analistas de Riesgo.
    """
    station = await gis_service.register_station(data)
    return 201, station


@router.get(
    "/stations",
    response=List[WeatherStationResponseSchema],
    auth=JWTAuthBearer(),
    summary="Listar todas las estaciones activas"
)
async def list_stations(request: HttpRequest):
    """
    Obtiene las coordenadas y metadatos de todas las estaciones climáticas activas.
    Accesible para cualquier usuario autenticado.
    """
    stations = await gis_service.list_active_stations()
    return stations


@router.get(
    "/stations/{station_id}",
    response=WeatherStationResponseSchema,
    auth=JWTAuthBearer(),
    summary="Obtener detalle de una estación meteorológica específica"
)
async def get_station_details(request: HttpRequest, station_id: int):
    """Retorna la ficha y ubicación espacial exacta de una estación."""
    station = await gis_service.get_station(station_id)
    return station


# ==============================================================================
# INGESTA EN TIEMPO REAL (IoT y Sensores)
# ==============================================================================

@router.post(
    "/telemetry",
    response={201: SensorMetricResponseSchema},
    summary="Ingestar métricas telemétricas en tiempo real (IoT / Campaña)"
)
async def ingest_sensor_metric(request: HttpRequest, data: SensorMetricCreateSchema):
    """
    Endpoint público de alta velocidad para la ingesta masiva de lecturas telemétricas.
    Recibe temperatura, humedad y viento desde microcontroladores IoT o estaciones de terreno.
    """
    metric = await gis_service.ingest_telemetry(data)
    return 201, metric

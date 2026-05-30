from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Tuple
from datetime import datetime
from apps.gis.schemas import GeoJSONPointSchema

class GeoJSONPolygonSchema(BaseModel):
    """
    Validador estricto para geometrías de tipo Polígono en estándar GeoJSON.
    Valida que los anillos espaciales estén cerrados (primer punto igual a último punto).
    Estructura: [ [ [lon, lat], [lon, lat], ... ] ]
    """
    type: str = Field("Polygon", pattern="^Polygon$")
    coordinates: List[List[List[float]]] = Field(
        ..., 
        description="Conjunto de anillos de coordenadas [[Longitud, Latitud]] que definen el polígono."
    )

    @field_validator('coordinates')
    @classmethod
    def validate_polygon_geometry(cls, coords: List[List[List[float]]]) -> List[List[List[float]]]:
        if not coords or len(coords[0]) < 4:
            raise ValueError("Un polígono válido requiere al menos 4 coordenadas (3 vértices + punto de cierre).")
        
        # Validar anillo exterior (el primer elemento)
        outer_ring = coords[0]
        if outer_ring[0] != outer_ring[-1]:
            raise ValueError(
                f"El anillo exterior del polígono debe estar cerrado. "
                f"El primer punto {outer_ring[0]} no coincide con el último {outer_ring[-1]}."
            )
            
        # Validar límites de coordenadas
        for ring in coords:
            for point in ring:
                if len(point) != 2:
                    raise ValueError("Cada punto geográfico debe ser un par de dos elementos [Longitud, Latitud].")
                lon, lat = point
                if not (-180.0 <= lon <= 180.0) or not (-90.0 <= lat <= 90.0):
                    raise ValueError(f"Coordenadas fuera de rango válido: {point}")
                    
        return coords


class ActiveIncidentCreateSchema(BaseModel):
    """Esquema de entrada para registrar un nuevo desastre natural activo."""
    description: str = Field(..., min_length=10)
    severity: str = Field("BAJA", pattern="^(BAJA|MEDIA|ALTA|EXTREMA)$")
    location: GeoJSONPointSchema


class ActiveIncidentResponseSchema(BaseModel):
    """Esquema de salida con metadatos completos del incidente activo."""
    id: int
    description: str
    severity: str
    status: str
    location: GeoJSONPointSchema
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EvacuationPerimeterCreateSchema(BaseModel):
    """Esquema de entrada para definir un perímetro de exclusión / evacuación civil."""
    incident_id: int
    perimeter: GeoJSONPolygonSchema
    is_active: bool = Field(default=True)


class EvacuationPerimeterResponseSchema(BaseModel):
    """Esquema de salida para un perímetro de evacuación PostGIS."""
    id: int
    incident_id: int
    perimeter: GeoJSONPolygonSchema
    area_hectares: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OptimalRouteRequestSchema(BaseModel):
    """Solicitud para calcular la ruta de evacuación óptima."""
    origin: GeoJSONPointSchema = Field(..., description="Ubicación inicial de los civiles o equipos de rescate.")
    destination: GeoJSONPointSchema = Field(..., description="Punto de encuentro o refugio seguro de destino.")


class OptimalRouteResponseSchema(BaseModel):
    """Representa la ruta de escape óptima evitando polígonos de incendios activos."""
    route_geometry: GeoJSONPolygonSchema = Field(..., description="Ruta de escape en formato LineString (representado como polígono/coordenadas para renderizado).")
    total_distance_km: float = Field(..., description="Distancia total a recorrer.")
    estimated_time_minutes: float = Field(..., description="Tiempo estimado de tránsito.")
    incidents_avoided: List[int] = Field(..., description="IDs de incidentes activos cuyo perímetro de riesgo se evitó.")

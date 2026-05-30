from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime

class GeoJSONPointSchema(BaseModel):
    """
    Validador estricto para geometrías de tipo Punto en estándar GeoJSON.
    Almacena coordenadas en formato [Longitud, Latitud].
    """
    type: str = Field("Point", pattern="^Point$")
    coordinates: List[float] = Field(
        ..., 
        min_length=2, 
        max_length=2,
        description="Coordenadas geográficas especificadas como [Longitud, Latitud] bajo WGS84."
    )

    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, coords: List[float]) -> List[float]:
        lon, lat = coords
        if not (-180.0 <= lon <= 180.0):
            raise ValueError("La longitud debe estar contenida entre -180.0 y 180.0 grados.")
        if not (-90.0 <= lat <= 90.0):
            raise ValueError("La latitud debe estar contenida entre -90.0 y 90.0 grados.")
        return coords


class WeatherStationCreateSchema(BaseModel):
    """Esquema de entrada para registrar una nueva estación meteorológica."""
    name: str = Field(..., max_length=100, min_length=3)
    location: GeoJSONPointSchema
    is_active: bool = Field(default=True)


class WeatherStationResponseSchema(BaseModel):
    """Esquema de salida para una estación meteorológica."""
    id: int
    name: str
    location: GeoJSONPointSchema
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SensorMetricCreateSchema(BaseModel):
    """Esquema para recibir alertas en tiempo real / telemetría de sensores IoT y ciudadanos."""
    station_id: int
    temperature: float = Field(..., ge=-50.0, le=70.0, description="Temperatura en grados Celsius.")
    humidity: float = Field(..., ge=0.0, le=100.0, description="Humedad relativa porcentual (0 - 100).")
    wind_speed: float = Field(..., ge=0.0, le=250.0, description="Velocidad del viento en km/h.")
    wind_direction: Optional[float] = Field(default=None, ge=0.0, le=360.0, description="Dirección en azimut (0 - 360).")


class SensorMetricResponseSchema(BaseModel):
    """Esquema de salida para una métrica de sensor."""
    id: int
    station_id: int
    recorded_at: datetime
    temperature: float
    humidity: float
    wind_speed: float
    wind_direction: Optional[float]

    class Config:
        from_attributes = True

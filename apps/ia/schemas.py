from pydantic import BaseModel, Field
from typing import List, Optional
from apps.gis.schemas import GeoJSONPointSchema

class PredictionRequestSchema(BaseModel):
    """
    Parámetros de entrada para evaluar el riesgo de incendio en tiempo real.
    Si no se especifican las variables climáticas locales, el sistema las resolverá 
    buscando automáticamente la estación IoT/Meteorológica PostGIS más cercana.
    """
    location: GeoJSONPointSchema
    current_temperature: Optional[float] = Field(None, ge=-50.0, le=70.0, description="°C. Opcional si hay sensores cercanos.")
    current_humidity: Optional[float] = Field(None, ge=0.0, le=100.0, description="%. Opcional si hay sensores cercanos.")
    current_wind_speed: Optional[float] = Field(None, ge=0.0, le=250.0, description="km/h. Opcional si hay sensores cercanos.")
    current_wind_direction: Optional[float] = Field(None, ge=0.0, le=360.0, description="Grados. Opcional si hay sensores cercanos.")


class PropagationVectorSchema(BaseModel):
    """Representa la velocidad y dirección de avance estimado del frente de fuego."""
    direction_deg: float = Field(..., description="Dirección del avance del fuego en grados azimut (0 - 360).")
    speed_kmh: float = Field(..., description="Velocidad lineal de avance del fuego en km/h.")


class PredictionResponseSchema(BaseModel):
    """Respuesta unificada del endpoint predictivo de IA."""
    coordinates: List[float] = Field(..., description="[Longitud, Latitud]")
    ignition_probability: float = Field(..., description="Probabilidad matemática de ignición (0.0 a 1.0).")
    ndvi_value: float = Field(..., description="Índice NDVI capturado en tiempo real por Sentinel-2.")
    nbr_value: float = Field(..., description="Índice NBR capturado en tiempo real por Sentinel-2.")
    propagation_vector: PropagationVectorSchema
    weather_data_source: str = Field(..., description="Indica si los datos climatológicos son manuales o de una estación IoT cercana.")
    closest_station_name: Optional[str] = Field(None, description="Nombre de la estación meteorológica PostGIS vinculada.")
    closest_station_distance_meters: Optional[float] = Field(None, description="Distancia real al sensor de climatología.")
    
    # Métricas ecológicas integradas de forma sutil
    sowing_viability_score: float = Field(..., description="Índice de viabilidad de siembra/reforestación (0.0 a 1.0) basado en humedad actual y NDVI.")
    sowing_recommendation: str = Field(..., description="Recomendación ecológica sutil sobre la idoneidad y ventanas de siembra según la pluviosidad.")


class RetrainTriggerSchema(BaseModel):
    """Parámetros para disparar el reentrenamiento del modelo en la nube."""
    custom_dataset_uri: Optional[str] = Field(
        None, 
        description="Ruta URI personalizada de GCS para el dataset de entrenamiento (e.g. gs://bucket/data.csv). Si no se especifica, se compilará un dataset fresco de la BD automáticamente."
    )


class RetrainResponseSchema(BaseModel):
    """Detalle del Job de entrenamiento disparado en Vertex AI Pipelines."""
    job_id: str
    status: str
    message: str

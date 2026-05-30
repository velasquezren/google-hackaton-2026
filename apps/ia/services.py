from typing import Optional, Dict, Any
from datetime import datetime
from apps.ia.earth_engine import EarthEngineClient
from apps.ia.vertex_ai import VertexAIClient
from apps.ia.repositories import IASensorRepository
from apps.gis.services import GISService
from apps.ia.schemas import (
    PredictionRequestSchema, 
    PredictionResponseSchema, 
    PropagationVectorSchema,
    RetrainTriggerSchema, 
    RetrainResponseSchema
)
from config.api import BaseAppException

class IAPredictiveService:
    """
    Servicio de Inteligencia Artificial que orquesta el cruce de datos espaciales (PostGIS),
    lectura satelital (Google Earth Engine) e inferencias climáticas (Vertex AI).
    Desacopla por completo la capa de enrutamiento del API Ninja.
    """
    def __init__(
        self,
        sensor_repo: IASensorRepository = None,
        gis_service: GISService = None,
        ee_client: EarthEngineClient = None,
        vertex_client: VertexAIClient = None
    ) -> None:
        self.sensor_repo = sensor_repo or IASensorRepository()
        self.gis_service = gis_service or GISService()
        self.ee_client = ee_client or EarthEngineClient()
        self.vertex_client = vertex_client or VertexAIClient()

    async def evaluate_ignition_and_propagation(self, data: PredictionRequestSchema) -> PredictionResponseSchema:
        """
        Evalúa el riesgo de incendio en coordenadas dadas.
        1. Consulta índices satelitales NDVI y NBR en tiempo real en Earth Engine.
        2. Si no se proveen datos climáticos, busca el sensor IoT PostGIS más cercano para obtenerlos.
        3. Invoca la inferencia en Vertex AI.
        """
        lon, lat = data.location.coordinates
        
        # 1. Obtener Índices Espectrales Satelitales (NDVI y NBR)
        # Se envuelve la llamada de GEE de manera síncrona/segura
        import asyncio
        from asgiref.sync import sync_to_async
        
        ndvi, nbr = await sync_to_async(self.ee_client.get_vegetation_indices)(lon, lat)
        
        # 2. Obtener datos climatológicos (Manuales vs Sensores Cercanos)
        temperature = data.current_temperature
        humidity = data.current_humidity
        wind_speed = data.current_wind_speed
        wind_direction = data.current_wind_direction
        
        weather_source = "Manual Entry"
        closest_station_name = None
        closest_station_dist = None

        if any(v is None for v in [temperature, humidity, wind_speed, wind_direction]):
            # Buscar el sensor más cercano registrado en PostGIS
            metric, distance = await self.gis_service.get_nearest_telemetry(lon, lat)
            if metric:
                # Cargar variables faltantes de forma dinámica
                temperature = temperature if temperature is not None else metric.temperature
                humidity = humidity if humidity is not None else metric.humidity
                wind_speed = wind_speed if wind_speed is not None else metric.wind_speed
                wind_direction = wind_direction if wind_direction is not None else metric.wind_direction
                
                weather_source = "IoT Network"
                closest_station_name = metric.station.name
                closest_station_dist = distance
            else:
                # Si no hay estación cercana ni parámetros completos, lanzar error semántico
                raise BaseAppException(
                    message="Datos climáticos incompletos y no se encontraron estaciones IoT activas en un radio de 50km.",
                    status_code=400
                )

        # 3. Consolidar vector de características para Vertex AI
        features = {
            "longitude": lon,
            "latitude": lat,
            "ndvi_average": ndvi,
            "nbr_average": nbr,
            "temperature": temperature,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction
        }

        # 4. Invocar el Endpoint de Predicciones en línea en Vertex AI
        prediction = await self.vertex_client.predict_ignition_and_propagation(features)

        # 5. [DE BAJO PERFIL] Cálculo analítico de viabilidad de siembra ecológica
        # Humedad alta representa temporada de lluvias (excelente para siembra).
        # Temperatura templada (18°C-28°C) y NDVI moderado (0.3-0.6) representa espacio óptimo para rebrote.
        hum_factor = humidity / 100.0
        
        if 18.0 <= temperature <= 28.0:
            temp_factor = 1.0
        elif temperature < 10.0 or temperature > 38.0:
            temp_factor = 0.2
        else:
            temp_factor = 0.6
            
        if 0.3 <= ndvi <= 0.6:
            ndvi_factor = 1.0
        else:
            ndvi_factor = 0.5
            
        sowing_score = round((hum_factor * 0.5) + (temp_factor * 0.3) + (ndvi_factor * 0.2), 2)
        
        # Generar recomendaciones sutiles según la viabilidad hídrica/térmica
        if sowing_score >= 0.75 and humidity >= 55.0:
            recommendation = "Temporada de lluvias activa detectada. Condiciones hídricas óptimas para siembra y reforestación forestal inmediata."
        elif sowing_score >= 0.55:
            recommendation = "Ventana húmeda aceptable. Recomendado para siembra de especies nativas resistentes y de rápido enraizamiento."
        elif humidity < 35.0:
            recommendation = "Déficit hídrico severo detectado (Temporada Seca). No se aconseja la siembra directa. Postergar hasta inicio de lluvias o asegurar riego permanente."
        else:
            recommendation = "Condiciones climáticas subóptimas. Se sugiere monitorear el aumento progresivo de la humedad relativa del suelo."

        # 6. Mapear y retornar respuesta estructurada
        return PredictionResponseSchema(
            coordinates=[lon, lat],
            ignition_probability=prediction["ignition_probability"],
            ndvi_value=ndvi,
            nbr_value=nbr,
            propagation_vector=PropagationVectorSchema(
                direction_deg=prediction["propagation_vector"]["direction_deg"],
                speed_kmh=prediction["propagation_vector"]["speed_kmh"]
            ),
            weather_data_source=weather_source,
            closest_station_name=closest_station_name,
            closest_station_distance_meters=closest_station_dist,
            sowing_viability_score=sowing_score,
            sowing_recommendation=recommendation
        )

    async def trigger_model_retraining(self, data: RetrainTriggerSchema) -> RetrainResponseSchema:
        """
        Genera un dataset de entrenamiento a partir del histórico y lanza
        un Job de entrenamiento en segundo plano utilizando Vertex AI Pipelines.
        """
        # Resolver dataset URI
        gcs_uri = data.custom_dataset_uri
        if not gcs_uri:
            # Compilar dataset en tiempo real a partir del histórico en PostGIS
            gcs_uri = await self.sensor_repo.compile_historical_dataset()

        # Disparar pipeline en Vertex AI
        job_id = await sync_to_async(self.vertex_client.trigger_pipeline_retraining)(gcs_uri)

        return RetrainResponseSchema(
            job_id=job_id,
            status="PENDING",
            message="El pipeline de reentrenamiento de Vertex AI fue encolado e iniciado de forma asíncrona."
        )

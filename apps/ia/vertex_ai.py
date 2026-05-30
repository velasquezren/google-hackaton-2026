import logging
from typing import Dict, Any, List
from django.conf import settings
from apps.core.exceptions import GoogleAPIException


logger = logging.getLogger(__name__)

# Intentar importar la librería de Google Cloud Vertex AI
try:
    from google.cloud import aiplatform
    HAS_VERTEX = True
except ImportError:
    HAS_VERTEX = False
    logger.warning("Librería 'google-cloud-aiplatform' no está instalada.")

class VertexAIClient:
    """
    Cliente para interactuar con Google Vertex AI.
    Permite invocar endpoints en línea (Online Predictions) para predecir el riesgo 
    y propagación, y disparar ejecuciones de Vertex AI Pipelines para reentrenamiento en GCP.
    """
    def __init__(self) -> None:
        self.initialized = False
        if HAS_VERTEX:
            self._initialize_vertex()

    def _initialize_vertex(self) -> None:
        """Inicializa el SDK de Vertex AI con el proyecto y región de GCP."""
        try:
            if settings.GOOGLE_APPLICATION_CREDENTIALS:
                aiplatform.init(
                    project=settings.GCP_PROJECT_ID,
                    location=settings.GCP_REGION
                )
                self.initialized = True
                logger.info(f"Vertex AI SDK inicializado exitosamente en {settings.GCP_REGION} para el proyecto {settings.GCP_PROJECT_ID}.")
            else:
                logger.warning(
                    "Credenciales de GCP no especificadas. "
                    "Vertex AI Client funcionará en modo simulado (Desarrollo)."
                )
        except Exception as e:
            logger.error(f"Fallo al inicializar SDK de Vertex AI: {str(e)}")
            self.initialized = False

    async def predict_ignition_and_propagation(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoca el Endpoint de Predicción en Línea en Vertex AI.
        Pasa el vector de características consolidado (clima actual + datos satelitales NDVI/NBR + topografía).
        """
        if not self.initialized:
            # Modo simulado: Generar lógica física realista de ignición y propagación
            logger.info("Modo simulado Vertex AI invocado.")
            import random
            import math
            
            # Lógica física básica de viento
            wind_speed = features.get('wind_speed', 0.0)
            wind_direction = features.get('wind_direction', 0.0) or 0.0
            humidity = features.get('humidity', 50.0)
            temperature = features.get('temperature', 20.0)
            ndvi = features.get('ndvi_average', 0.5)
            
            # Calcular probabilidad de ignición basada en variables climáticas e índices satelitales
            # Humedad baja, temp alta y NDVI alto (mucha biomasa seca) aumentan el riesgo
            dryness_factor = (100.0 - humidity) / 100.0
            heat_factor = max(0.0, temperature - 10) / 40.0
            biomass_factor = ndvi
            
            ignition_prob = min(0.99, max(0.01, (dryness_factor * 0.4 + heat_factor * 0.4 + biomass_factor * 0.2)))
            
            # Vector de propagación estimado (Fórmula de Rothermel simplificada)
            # La dirección del viento empuja la dirección del fuego.
            # La velocidad del fuego (rate of spread) es proporcional al viento y la temperatura, e inversa a la humedad.
            base_spread_rate = (wind_speed * 0.15) + (temperature * 0.05) - (humidity * 0.02)
            spread_rate = max(0.5, base_spread_rate) # km/h
            
            # El vector apunta en la dirección en la que sopla el viento (wind_direction)
            return {
                "ignition_probability": round(ignition_prob, 4),
                "propagation_vector": {
                    "direction_deg": round(wind_direction, 2),
                    "speed_kmh": round(spread_rate, 2)
                },
                "simulated": True
            }

        try:
            # Instanciar el endpoint desplegado en GCP
            endpoint_path = f"projects/{settings.GCP_PROJECT_ID}/locations/{settings.GCP_REGION}/endpoints/{settings.VERTEX_AI_ENDPOINT_ID}"
            endpoint = aiplatform.Endpoint(endpoint_name=endpoint_path)
            
            # Las instancias deben ser pasadas como lista de diccionarios
            instances = [features]
            
            # Ejecutar llamada síncrona/bloqueante en hilo (envuelta si es llamada desde controlador async)
            # Para producción, se puede usar sync_to_async o ejecutar en Celery si toma tiempo
            response = endpoint.predict(instances=instances)
            
            predictions = response.predictions
            if not predictions:
                raise GoogleAPIException("El endpoint de Vertex AI retornó una respuesta vacía.")
                
            # Asumiendo que el modelo retorna un diccionario con 'ignition_probability' y 'propagation_params'
            prediction_result = predictions[0]
            
            return {
                "ignition_probability": prediction_result.get("ignition_probability", 0.0),
                "propagation_vector": {
                    "direction_deg": prediction_result.get("direction_deg", features.get("wind_direction", 0.0)),
                    "speed_kmh": prediction_result.get("speed_kmh", 0.0)
                },
                "simulated": False
            }
            
        except Exception as e:
            logger.exception("Fallo al consumir predicción en línea de Vertex AI.")
            raise GoogleAPIException(
                message="Error en el Endpoint de predicción de Vertex AI",
                details={"original_error": str(e), "features": features}
            )

    def trigger_pipeline_retraining(self, gcs_dataset_uri: str) -> str:
        """
        Ejecuta un Pipeline de entrenamiento (Vertex AI Pipelines) en segundo plano en GCP.
        Pasa el dataset con el histórico compilado para reentrenar el modelo de propagación.
        """
        if not self.initialized:
            logger.info(f"Modo simulado Vertex AI Pipelines: Pipeline disparado exitosamente con dataset {gcs_dataset_uri}.")
            return "simulated-vertex-pipeline-job-12345"

        try:
            # Ubicación de la plantilla precompilada del pipeline en GCS (.json o .yaml de KFP)
            template_path = f"{settings.VERTEX_AI_PIPELINE_ROOT}/fire_propagation_training_pipeline.json"
            
            # Definición del Job
            job = aiplatform.PipelineJob(
                display_name="retrain-fire-propagation-model",
                template_path=template_path,
                pipeline_root=settings.VERTEX_AI_PIPELINE_ROOT,
                parameter_values={
                    "dataset_uri": gcs_dataset_uri,
                    "model_id": settings.VERTEX_AI_MODEL_ID,
                    "epochs": 50,
                    "learning_rate": 0.001
                }
            )
            
            # Ejecutar de forma asíncrona en GCP (no bloquea el worker de Celery)
            job.run(sync=False)
            
            logger.info(f"Vertex AI Pipeline Job disparado exitosamente. Resource ID: {job.resource_name}")
            return job.resource_name
            
        except Exception as e:
            logger.exception("Fallo al disparar el pipeline de reentrenamiento en Vertex AI.")
            raise GoogleAPIException(
                message="Error al iniciar el Pipeline de entrenamiento en Vertex AI",
                details={"original_error": str(e), "dataset_uri": gcs_dataset_uri}
            )

from typing import List, Dict, Any
from ninja import Router
from django.http import HttpRequest, JsonResponse
from apps.core.auth import JWTAuthBearer, role_required
from config.settings import SystemRoles
from apps.ia.schemas import (
    PredictionRequestSchema, 
    PredictionResponseSchema,
    RetrainTriggerSchema,
    RetrainResponseSchema
)
from apps.ia.services import IAPredictiveService
from apps.ia.tasks import task_retrain_vertex_model, task_ingest_satellite_historical_record

router = Router(tags=["Artificial Intelligence & ML Predictor"])
ia_service = IAPredictiveService()

# ==============================================================================
# ENDPOINT PREDICITIVO DE RIESGO E IGNICIÓN
# ==============================================================================

@router.post(
    "/predict",
    response={200: PredictionResponseSchema},
    auth=JWTAuthBearer(),
    summary="Evaluar probabilidad de ignición y vector de propagación de incendios"
)
async def evaluate_fire_risk(request: HttpRequest, data: PredictionRequestSchema):
    """
    Evalúa la vulnerabilidad de un foco geográfico.
    Extrae NDVI/NBR satelitales vía Google Earth Engine e infiere el vector de propagación
    y la probabilidad de ignición en base al viento y humedad a través de Google Vertex AI.
    """
    prediction = await ia_service.evaluate_ignition_and_propagation(data)
    return 200, prediction


# ==============================================================================
# ENDPOINT PARA GESTIONAR EL REENTRENAMIENTO (Vertex AI Pipelines)
# ==============================================================================

@router.post(
    "/retrain",
    response={202: RetrainResponseSchema},
    auth=JWTAuthBearer(),
    summary="Disparar el reentrenamiento del modelo de Machine Learning"
)
@role_required([SystemRoles.ADMIN, SystemRoles.ANALYST])
async def trigger_model_retraining(request: HttpRequest, data: RetrainTriggerSchema):
    """
    Dispara la compilación del dataset y el reentrenamiento de Vertex AI.
    Para garantizar alta escalabilidad, delega la tarea pesada a un Worker de Celery
    y retorna inmediatamente un HTTP 202 Accepted.
    """
    # Encolar la tarea asíncrona en Celery/Redis
    task = task_retrain_vertex_model.delay(data.custom_dataset_uri)
    
    return 202, RetrainResponseSchema(
        job_id=task.id,
        status="QUEUED",
        message="La solicitud de reentrenamiento fue encolada y procesada por Celery de forma asíncrona."
    )


# ==============================================================================
# ENDPOINT DE RECOPILACIÓN HISTÓRICA
# ==============================================================================

@router.post(
    "/historical-records",
    auth=JWTAuthBearer(),
    summary="Ingestar un registro histórico de incendios cruzado con datos satelitales"
)
@role_required([SystemRoles.ADMIN, SystemRoles.ANALYST])
async def ingest_historical_record(request: HttpRequest, payload: Dict[str, Any]):
    """
    Recibe un punto geográfico de un incendio pasado y sus variables climáticas.
    Encola una tarea de Celery para consultar Earth Engine y compilar el NDVI histórico de ese día,
    guardando finalmente el registro en PostGIS.
    """
    coords = payload.get("coordinates", [])
    if len(coords) != 2:
        return JsonResponse({"error": "Formato de coordenadas inválido. Debe ser [lon, lat]"}, status=400)
        
    # Encolar tarea asíncrona
    task_ingest_satellite_historical_record.delay(
        lon=float(coords[0]),
        lat=float(coords[1]),
        temp=float(payload.get("temperature", 20)),
        hum=float(payload.get("humidity", 50)),
        wind_sp=float(payload.get("wind_speed", 10)),
        fire_date_str=payload.get("fire_date", "2026-05-30T00:00:00")
    )
    
    return JsonResponse({
        "success": True,
        "message": "Tarea de compilación de registro histórico encolada en Celery exitosamente."
    }, status=202)

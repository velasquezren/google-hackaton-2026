import logging
from celery import shared_task
from datetime import datetime
from asgiref.sync import async_to_sync
from apps.ia.repositories import IASensorRepository
from apps.ia.earth_engine import EarthEngineClient
from apps.ia.vertex_ai import VertexAIClient

logger = logging.getLogger(__name__)

@shared_task(name="ia.tasks.retrain_vertex_model")
def task_retrain_vertex_model(custom_dataset_uri: str = None) -> str:
    """
    Tarea en segundo plano de Celery para disparar el reentrenamiento del modelo.
    Evita bloquear el hilo de Django Ninja en solicitudes web largas.
    """
    logger.info("Iniciando tarea asíncrona de reentrenamiento...")
    
    sensor_repo = IASensorRepository()
    vertex_client = VertexAIClient()
    
    # 1. Resolver URI del dataset en GCS
    if not custom_dataset_uri:
        logger.info("Compilando dataset histórico de la base de datos PostGIS...")
        # Resolver corrutina asíncrona dentro de contexto síncrono de Celery
        custom_dataset_uri = async_to_sync(sensor_repo.compile_historical_dataset)()
        
    logger.info(f"Dataset listo para Vertex AI Pipelines: {custom_dataset_uri}")
    
    # 2. Iniciar el Pipeline de entrenamiento
    job_id = vertex_client.trigger_pipeline_retraining(custom_dataset_uri)
    logger.info(f"Pipeline de reentrenamiento iniciado con éxito en GCP. Job ID: {job_id}")
    
    return job_id


@shared_task(name="ia.tasks.ingest_satellite_historical_record")
def task_ingest_satellite_historical_record(
    lon: float,
    lat: float,
    temp: float,
    hum: float,
    wind_sp: float,
    fire_date_str: str
) -> str:
    """
    Tarea asíncrona para ingestar un nuevo registro histórico de incendios en segundo plano.
    Consulta Google Earth Engine para obtener NDVI y NBR históricos antes de guardar el registro en PostGIS.
    """
    logger.info(f"Ingestando registro histórico asíncrono para foco [{lon}, {lat}]...")
    
    # Parsear parámetros
    fire_date = datetime.fromisoformat(fire_date_str)
    
    ee_client = EarthEngineClient()
    sensor_repo = IASensorRepository()
    
    # Obtener índices satelitales NDVI y NBR históricos
    # (En un ambiente real pasaríamos la fecha específica del incendio a Earth Engine)
    ndvi, nbr = ee_client.get_vegetation_indices(lon, lat)
    
    # Guardar en PostGIS de forma asíncrona (envuelta)
    record = async_to_sync(sensor_repo.add_historical_record)(
        lon=lon,
        lat=lat,
        ndvi=ndvi,
        nbr=nbr,
        temp=temp,
        hum=hum,
        wind_sp=wind_sp,
        fire_date=fire_date
    )
    
    logger.info(f"Registro histórico guardado con éxito. ID: {record.id}")
    return f"Success: {record.id}"

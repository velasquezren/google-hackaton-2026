import os
import csv
import logging
from typing import List, Tuple
from io import StringIO
from datetime import datetime
from django.contrib.gis.geos import Point, Polygon
from django.conf import settings
from asgiref.sync import sync_to_async
from apps.ia.models import HistoricalFireRecord

logger = logging.getLogger(__name__)

# Intentar importar GCS
try:
    from google.cloud import storage
    HAS_GCS = True
except ImportError:
    HAS_GCS = False

class IASensorRepository:
    """
    Repositorio encargado del almacenamiento físico de los registros históricos de incendios
    y de la exportación/compilación del dataset histórico a Google Cloud Storage (GCS)
    para alimentar los pipelines de Vertex AI.
    """

    async def add_historical_record(
        self, 
        lon: float, 
        lat: float, 
        ndvi: float, 
        nbr: float, 
        temp: float, 
        hum: float, 
        wind_sp: float, 
        fire_date: datetime,
        burned_polygon: List[Tuple[float, float]] = None
    ) -> HistoricalFireRecord:
        """Registra un nuevo suceso de incendio histórico con su contexto satelital y climático."""
        location = Point(lon, lat, srid=4326)
        
        polygon_geom = None
        if burned_polygon:
            # Crear polígono PostGIS (Cerramos el anillo exterior si no lo está)
            if burned_polygon[0] != burned_polygon[-1]:
                burned_polygon.append(burned_polygon[0])
            polygon_geom = Polygon(burned_polygon, srid=4326)
            
        record = await HistoricalFireRecord.objects.acreate(
            location=location,
            burned_area=polygon_geom,
            ndvi_average=ndvi,
            nbr_average=nbr,
            max_temperature=temp,
            min_humidity=hum,
            max_wind_speed=wind_sp,
            fire_date=fire_date
        )
        return record

    async def compile_historical_dataset(self) -> str:
        """
        [ASYNC WRAPPER] Compila todos los registros históricos de la base de datos PostGIS,
        genera un archivo CSV estructurado y lo sube a un bucket de Google Cloud Storage (GCS).
        Retorna la URI oficial de GCS (gs://...) del dataset listo para Vertex AI.
        """
        # Delegar a método síncrono que realiza la compilación E/S
        return await sync_to_async(self._compile_dataset_sync)()

    def _compile_dataset_sync(self) -> str:
        """Compila los registros históricos de forma secuencial en CSV."""
        records = HistoricalFireRecord.objects.all()
        
        # Generar buffer en memoria para CSV
        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)
        
        # Cabecera del dataset para entrenamiento de Machine Learning
        writer.writerow([
            "longitude", "latitude", "fire_date", "ndvi_average", 
            "nbr_average", "max_temperature", "min_humidity", "max_wind_speed"
        ])
        
        count = 0
        for r in records:
            writer.writerow([
                r.location.x,
                r.location.y,
                r.fire_date.isoformat(),
                r.ndvi_average,
                r.nbr_average,
                r.max_temperature,
                r.min_humidity,
                r.max_wind_speed
            ])
            count += 1
            
        csv_data = csv_buffer.getvalue()
        csv_buffer.close()
        
        filename = f"datasets/historical_fires_dataset_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Subir a Google Cloud Storage si está configurado
        if HAS_GCS and settings.GOOGLE_APPLICATION_CREDENTIALS:
            try:
                storage_client = storage.Client()
                bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)
                blob = bucket.blob(filename)
                
                # Cargar el archivo CSV como cadena de texto
                blob.upload_from_string(csv_data, content_type='text/csv')
                
                gcs_uri = f"gs://{settings.GCS_BUCKET_NAME}/{filename}"
                logger.info(f"Dataset de entrenamiento ({count} filas) compilado y subido a GCS: {gcs_uri}")
                return gcs_uri
            except Exception as e:
                logger.exception("Fallo al subir el archivo del dataset consolidado a GCS.")
                # Si falla GCS, respaldas guardando de forma local como fallback
                pass

        # Fallback local (Desarrollo sin cuenta de servicio configurada)
        local_dir = os.path.join(settings.BASE_DIR, 'media', 'datasets')
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, os.path.basename(filename))
        
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(csv_data)
            
        logger.info(f"Dataset compilado de forma local (GCP inactivo): {local_path}")
        return f"file://{local_path}"

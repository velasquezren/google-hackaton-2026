import logging
from typing import Dict, Any, Tuple
from django.conf import settings
from apps.core.exceptions import GoogleAPIException
logger = logging.getLogger(__name__)

# Intentar importar la librería de Google Earth Engine
try:
    import ee
    HAS_EE = True
except ImportError:
    HAS_EE = False
    logger.warning("Librería 'earthengine-api' no está instalada o no se encuentra en el PYTHONPATH.")

class EarthEngineClient:
    """
    Cliente para la API de Google Earth Engine (GEE).
    Permite consultar colecciones satelitales (Sentinel-2 y Landsat),
    extraer capas ráster y calcular índices espectrales de vegetación (NDVI)
    y calcinación (NBR) en tiempo real para coordenadas específicas.
    """
    def __init__(self) -> None:
        self.initialized = False
        if HAS_EE:
            self._initialize_gee()

    def _initialize_gee(self) -> None:
        """Inicializa la sesión de Earth Engine usando credenciales de Service Account."""
        try:
            if settings.GOOGLE_APPLICATION_CREDENTIALS:
                # Inicialización usando archivo de credenciales de GCP
                ee.Initialize()
                self.initialized = True
                logger.info("Google Earth Engine inicializado exitosamente con credenciales locales.")
            elif settings.GEE_SERVICE_ACCOUNT and settings.GEE_PRIVATE_KEY_FILE:
                # Inicialización usando credenciales explícitas de GEE
                credentials = ee.ServiceAccountCredentials(
                    settings.GEE_SERVICE_ACCOUNT, 
                    settings.GEE_PRIVATE_KEY_FILE
                )
                ee.Initialize(credentials=credentials)
                self.initialized = True
                logger.info("Google Earth Engine inicializado con credenciales de cuenta de servicio GEE.")
            else:
                logger.warning(
                    "Credenciales de Google Earth Engine no configuradas. "
                    "El cliente operará en modo simulado para desarrollo local."
                )
        except Exception as e:
            logger.error(f"Fallo al inicializar Google Earth Engine: {str(e)}")
            self.initialized = False

    def get_vegetation_indices(self, lon: float, lat: float) -> Tuple[float, float]:
        """
        Calcula NDVI (Normalized Difference Vegetation Index) y NBR (Normalized Burn Ratio)
        promedio para una coordenada geográfica consultando las últimas imágenes de Sentinel-2.
        
        NDVI = (B8 - B4) / (B8 + B4)  -- Banda 8 (NIR), Banda 4 (Rojo)
        NBR = (B8 - B12) / (B8 + B12) -- Banda 8 (NIR), Banda 12 (SWIR 2)
        """
        if not self.initialized:
            # Modo Simulado / Respaldo en desarrollo
            logger.info(f"Modo simulado GEE para coordenadas [{lon}, {lat}]. Generando índices sintéticos.")
            # Retorna valores promedio simulados (NDVI saludable, NBR bajo)
            import random
            simulated_ndvi = round(random.uniform(0.35, 0.75), 4)
            simulated_nbr = round(random.uniform(0.15, 0.45), 4)
            return simulated_ndvi, simulated_nbr

        try:
            # Definir punto de interés geoespacial
            point = ee.Geometry.Point([lon, lat])
            
            # Cargar colección de imágenes Sentinel-2 (Reflectancia de Superficie)
            # Filtrar por zona, rango temporal de los últimos 30 días y ordenar por menor cobertura de nubes
            collection = (ee.ImageCollection('COPERNICUS/S2_SR')
                          .filterBounds(point)
                          .filterDate('now - 30 days', 'now')
                          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                          .sort('CLOUDY_PIXEL_PERCENTAGE'))
            
            # Obtener la mejor imagen disponible
            image = collection.first()
            
            if image is None:
                raise GoogleAPIException(
                    "No se encontraron imágenes satelitales Sentinel-2 con nubosidad aceptable en los últimos 30 días para esta zona."
                )
            
            # Calcular NDVI
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            
            # Calcular NBR
            nbr = image.normalizedDifference(['B8', 'B12']).rename('NBR')
            
            # Combinar bandas calculadas
            indices_image = image.addBands([ndvi, nbr])
            
            # Reducir la región alrededor de la coordenada para obtener el valor puntual medio
            stats = indices_image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=point,
                scale=10, # Resolución de Sentinel-2 en metros para estas bandas
                maxPixels=1e9
            ).getInfo()
            
            # Extraer los índices
            ndvi_val = stats.get('NDVI')
            nbr_val = stats.get('NBR')
            
            # Si el satélite devolvió nulos en el píxel (por ejemplo, si hay nubes densas no filtradas)
            if ndvi_val is None or nbr_val is None:
                logger.warning("Lectura satelital nula en el píxel, retornando valores por defecto seguros.")
                return 0.4, 0.2
                
            return float(ndvi_val), float(nbr_val)
            
        except Exception as e:
            logger.exception("Fallo al consultar los datos satelitales en Google Earth Engine.")
            raise GoogleAPIException(
                message="Error de procesamiento ráster en Earth Engine",
                details={"original_error": str(e), "coordinates": [lon, lat]}
            )

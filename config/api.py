from typing import Any
from django.http import JsonResponse
from ninja import NinjaAPI
from pydantic import ValidationError

# Definición de excepciones del negocio y del sistema
class BaseAppException(Exception):
    def __init__(self, message: str, status_code: int = 400, details: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class GoogleAPIException(BaseAppException):
    """Lanzada cuando fallan integraciones con GEE, Vertex AI o GCS."""
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, status_code=502, details=details) # Bad Gateway

class EntityNotFoundException(BaseAppException):
    """Lanzada cuando un recurso solicitado no existe."""
    def __init__(self, message: str):
        super().__init__(message, status_code=404)

class AccessDeniedException(BaseAppException):
    """Lanzada cuando hay fallos de autorización o rol insuficiente."""
    def __init__(self, message: str = "No tiene permisos para realizar esta acción"):
        super().__init__(message, status_code=403)


# Inicialización de Django Ninja API
api = NinjaAPI(
    title="Forest Fire & Natural Disasters API",
    version="1.0.0",
    description="Backend asíncrono de alto rendimiento para el análisis, predicción y seguimiento de incendios y desastres naturales.",
    urls_namespace="api-v1",
)

# ==============================================================================
# MANEJADORES GLOBALES DE EXCEPCIONES
# ==============================================================================

@api.exception_handler(BaseAppException)
def app_exception_handler(request: Any, exc: BaseAppException) -> JsonResponse:
    """Manejador genérico para excepciones del dominio."""
    return JsonResponse(
        {
            "success": False,
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details
        },
        status=exc.status_code
    )

@api.exception_handler(GoogleAPIException)
def google_api_exception_handler(request: Any, exc: GoogleAPIException) -> JsonResponse:
    """Manejador especializado para fallos en APIs de Google (GEE, Vertex AI, GCS)."""
    return JsonResponse(
        {
            "success": False,
            "error": "GoogleCloudIntegrationError",
            "message": f"Error de comunicación con los servicios de Google Cloud: {exc.message}",
            "details": exc.details
        },
        status=502
    )

@api.exception_handler(ValidationError)
def pydantic_validation_exception_handler(request: Any, exc: ValidationError) -> JsonResponse:
    """Captura errores de validación de Pydantic v2 y devuelve HTTP 422 Unprocessable Entity."""
    errors = exc.errors(include_url=False, include_context=False)
    return JsonResponse(
        {
            "success": False,
            "error": "ValidationError",
            "message": "Los datos proporcionados no cumplen con los esquemas de validación.",
            "details": errors
        },
        status=422
    )

@api.exception_handler(Exception)
def global_exception_handler(request: Any, exc: Exception) -> JsonResponse:
    """Manejador de último recurso para errores no controlados (HTTP 500)."""
    import logging
    logger = logging.getLogger(__name__)
    logger.exception("Error interno no controlado en la API")
    return JsonResponse(
        {
            "success": False,
            "error": "InternalServerError",
            "message": "Ocurrió un error inesperado en el servidor.",
            "details": str(exc) if api.debug else {}
        },
        status=500
    )


# ==============================================================================
# MONTAJE DE ROUTERS MODULARES
# ==============================================================================
from apps.gis.routers import router as gis_router
from apps.ia.routers import router as ia_router
from apps.incidents.routers import router as incidents_router

api.add_router("/gis", gis_router)
api.add_router("/ia", ia_router)
api.add_router("/incidents", incidents_router)


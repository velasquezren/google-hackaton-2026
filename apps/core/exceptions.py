from typing import Any

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

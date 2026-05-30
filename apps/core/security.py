import datetime
from typing import Dict, Any, Optional
import jwt
from django.conf import settings
from config.api import AccessDeniedException

def generate_jwt_token(user_id: int, username: str, role: str) -> str:
    """Genera un token JWT firmado de acceso para el usuario especificado."""
    payload = {
        'sub': str(user_id),
        'username': username,
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.JWT_ACCESS_TOKEN_LIFETIME_MINUTES),
        'iat': datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decodifica y valida un token JWT.
    Lanza AccessDeniedException si está expirado o es inválido.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AccessDeniedException("El token JWT ha expirado. Por favor, inicie sesión nuevamente.")
    except jwt.InvalidTokenError:
        raise AccessDeniedException("Token JWT inválido.")

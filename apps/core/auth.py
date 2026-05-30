from typing import Any, Optional
from django.http import HttpRequest
from ninja.security import HttpBearer
from apps.core.models import User
from apps.core.security import decode_jwt_token
from config.api import AccessDeniedException

class JWTAuthBearer(HttpBearer):
    """
    Clase de seguridad asíncrona para Django Ninja que intercepta las peticiones HTTP,
    lee la cabecera 'Authorization: Bearer <token>' y valida el token JWT contra la base de datos
    usando las capacidades asíncronas de Django 5.0 (aget).
    """
    async def authenticate(self, request: HttpRequest, token: str) -> Optional[User]:
        try:
            # Decodificar el token JWT de manera segura
            payload = decode_jwt_token(token)
            user_id = payload.get('sub')
            
            if not user_id:
                return None
            
            # Obtener el usuario de manera asíncrona usando aget de Django 5.0+
            user = await User.objects.aget(id=user_id)
            
            # Guardar datos de rol y usuario en el request para accesos en los routers
            request.user = user
            request.auth = {
                'user_id': user.id,
                'username': user.username,
                'role': user.role
            }
            return user
        except Exception:
            return None

def role_required(allowed_roles: list[str]):
    """
    Decorador o ayudante de verificación de roles para endpoints.
    Lanza AccessDeniedException si el rol del usuario autenticado no está en la lista.
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Obtener la request (suele ser el primer o segundo argumento según el endpoint)
            request = None
            for arg in args:
                if isinstance(arg, HttpRequest) or (hasattr(arg, 'user') and hasattr(arg, 'auth')):
                    request = arg
                    break
            
            if not request:
                # Buscar en kwargs
                request = kwargs.get('request')
            
            if not request or not hasattr(request, 'auth') or not request.auth:
                raise AccessDeniedException("No autenticado o credenciales inválidas.")
            
            user_role = request.auth.get('role')
            if user_role not in allowed_roles:
                raise AccessDeniedException(f"Permiso denegado. Se requiere uno de los siguientes roles: {allowed_roles}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

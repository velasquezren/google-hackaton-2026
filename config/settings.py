"""
Django settings for forest_fire_backend project.
Generated for production-ready, clean-architecture system.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-prod-forest-fires-2026-key')

DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',')

# Configuración de Aplicaciones de Django
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Aplicación GIS nativa de Django (GeoDjango)
    'django.contrib.gis',
    'corsheaders',
    # Aplicaciones del Proyecto organizadas bajo apps/
    'apps.core',
    'apps.gis.apps.GisConfig',
    'apps.ia',
    'apps.incidents',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Servir archivos estáticos de producción
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ==============================================================================
# CONFIGURACIÓN DE BASE DE DATOS GEOSPATIAL (PostGIS / Spatialite Fallback)
# ==============================================================================
import socket

def is_postgres_available(host: str, port: str) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect((host, int(port)))
        s.close()
        return True
    except Exception:
        return False

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

# Si Postgres está inactivo o si se fuerza por variable de entorno, usar SQLite estándar con mocks
if os.getenv('USE_SQLITE', 'False') == 'True' or not is_postgres_available(DB_HOST, DB_PORT):
    DATABASES = {
        'default': {
            # Motor SQLite estándar para desarrollo ágil sin librerías complejas
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            # Motor PostgreSQL con la extensión PostGIS para GeoDjango
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': os.getenv('DB_NAME', 'forest_fires_db'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
            'HOST': DB_HOST,
            'PORT': DB_PORT,
        }
    }


# Configuración de librerías GIS si es necesario (Linux/Docker por defecto las encuentra)
# GDAL_LIBRARY_PATH = os.getenv('GDAL_LIBRARY_PATH')
# GEOS_LIBRARY_PATH = os.getenv('GEOS_LIBRARY_PATH')

# ==============================================================================
# AUTENTICACIÓN Y ROLES
# ==============================================================================
AUTH_USER_MODEL = 'core.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Roles del sistema
class SystemRoles:
    ADMIN = 'ADMIN'
    ANALYST = 'ANALYST'
    FIRST_RESPONDER = 'FIRST_RESPONDER'
    CITIZEN = 'CITIZEN'

    CHOICES = [
        (ADMIN, 'Administrador del Sistema'),
        (ANALYST, 'Analista de Riesgo'),
        (FIRST_RESPONDER, 'Bomberos / Rescatistas'),
        (CITIZEN, 'Ciudadano'),
    ]

# Configuración de JWT
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_LIFETIME_MINUTES = int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME', '60'))

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Configuración nativa de almacenamiento de archivos estáticos de Django 5.0 con WhiteNoise
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# SEGURIDAD DE ORIGEN (CORS & CSRF)
# ==============================================================================
CORS_ALLOW_ALL_ORIGINS = True

# Orígenes confiables para validación CSRF en Google Cloud Run
CSRF_TRUSTED_ORIGINS = [
    'https://*.run.app',
    'https://*.app.run',
    'https://backend-hackaton-698520637534.us-central1.run.app'
]

# ==============================================================================
# PROCESAMIENTO ASÍNCRONO (Celery & Redis)
# ==============================================================================
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# ==============================================================================
# CONFIGURACIÓN INTEGRACIÓN CON GOOGLE CLOUD PLATFORM (GCP)
# ==============================================================================
# Ubicación del archivo de credenciales de Google Service Account
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')

# Google Cloud Storage Bucket
GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'forest-fires-rasters-bucket')

# Google Vertex AI
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'forest-fires-gcp-project')
GCP_REGION = os.getenv('GCP_REGION', 'us-central1')
VERTEX_AI_PIPELINE_ROOT = os.getenv('VERTEX_AI_PIPELINE_ROOT', f'gs://{GCS_BUCKET_NAME}/vertex-pipelines')
VERTEX_AI_ENDPOINT_ID = os.getenv('VERTEX_AI_ENDPOINT_ID', 'vertex-online-prediction-endpoint-id')
VERTEX_AI_MODEL_ID = os.getenv('VERTEX_AI_MODEL_ID', 'forest_fire_propagation_model')

# Google Earth Engine (GEE)
GEE_SERVICE_ACCOUNT = os.getenv('GEE_SERVICE_ACCOUNT', '')
GEE_PRIVATE_KEY_FILE = os.getenv('GEE_PRIVATE_KEY_FILE', '')

# ==============================================================================
# GIS MOCKING FOR STANDARD SQLITE DEV ENVIRONMENT
# ==============================================================================
if DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    import sys
    from types import ModuleType
    
    # 1. Crear un mock del módulo django.contrib.gis.db.models
    gis_db_models = ModuleType('django.contrib.gis.db.models')
    
    # Heredar todo de django.db.models
    import django.db.models as normal_models
    for attr in dir(normal_models):
        setattr(gis_db_models, attr, getattr(normal_models, attr))
        
    # Definir mocks de campos espaciales
    class MockPointField(normal_models.TextField):
        def __init__(self, *args, **kwargs):
            kwargs.pop('srid', None)
            kwargs.pop('spatial_index', None)
            super().__init__(*args, **kwargs)
        def deconstruct(self):
            name, path, args, kwargs = super().deconstruct()
            return name, 'django.db.models.TextField', args, kwargs
            
    class MockPolygonField(normal_models.TextField):
        def __init__(self, *args, **kwargs):
            kwargs.pop('srid', None)
            kwargs.pop('spatial_index', None)
            super().__init__(*args, **kwargs)
        def deconstruct(self):
            name, path, args, kwargs = super().deconstruct()
            return name, 'django.db.models.TextField', args, kwargs
            
    gis_db_models.PointField = MockPointField
    gis_db_models.PolygonField = MockPolygonField
    gis_db_models.models = gis_db_models  # Permite importar "models" desde sí mismo de forma reflexiva
    
    # Inyectar en sys.modules para que todos los "from django.contrib.gis.db import models" lo obtengan
    sys.modules['django.contrib.gis.db.models'] = gis_db_models
    sys.modules['django.contrib.gis.db'] = gis_db_models
    
    # 2. Mockear el modulo django.contrib.gis.geos
    gis_geos = ModuleType('django.contrib.gis.geos')
    
    class MockPoint:
        def __init__(self, x=0.0, y=0.0, *a, **k):
            self.x = float(x)
            self.y = float(y)
        @property
        def coords(self): return [self.x, self.y]
        
    class MockPolygon:
        def __init__(self, *args, **kwargs):
            self.centroid = type('MockCentroid', (object,), {'x': 0.0, 'y': 0.0})()
            self.coords = [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]]]
            self.area = 1.0
        def clone(self): return self
        def transform(self, *a, **k): pass
        
    class MockLineString:
        def __init__(self, *args, **kwargs):
            self.length = 1.0
            self.coords = [[0.0, 0.0], [1.0, 1.0]]
        def clone(self): return self
        def transform(self, *a, **k): pass
        def buffer(self, *a, **k): return MockPolygon()
        
    gis_geos.Point = MockPoint
    gis_geos.Polygon = MockPolygon
    gis_geos.LineString = MockLineString
    gis_geos.GEOSException = type('GEOSException', (Exception,), {})
    gis_geos.GEOSGeometry = type('GEOSGeometry', (object,), {
        '__init__': lambda *a, **k: None,
        'clone': lambda s: s,
        'transform': lambda *a, **k: None,
    })
    sys.modules['django.contrib.gis.geos'] = gis_geos
    
    # 3. Mockear el modulo django.contrib.gis.db.models.functions
    gis_db_functions = ModuleType('django.contrib.gis.db.models.functions')
    gis_db_functions.Distance = type('MockDistance', (object,), {})
    gis_db_functions.Area = type('MockArea', (object,), {})
    sys.modules['django.contrib.gis.db.models.functions'] = gis_db_functions
    
    # 4. Mockear el modulo django.contrib.gis.measure
    gis_measure = ModuleType('django.contrib.gis.measure')
    gis_measure.D = lambda *a, **k: type('MockD', (object,), {})()
    sys.modules['django.contrib.gis.measure'] = gis_measure




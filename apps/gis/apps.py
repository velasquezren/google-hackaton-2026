from django.apps import AppConfig

class GisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.gis'
    label = 'project_gis'  # Resuelve el conflicto de nombres con 'django.contrib.gis'

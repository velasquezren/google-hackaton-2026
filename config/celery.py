import os
from celery import Celery

# Establecer las configuraciones predeterminadas de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('forest_fire_backend')

# Usar las configuraciones de Django que inicien con el prefijo CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Cargar automáticamente las tareas registradas en cada aplicación de Django
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

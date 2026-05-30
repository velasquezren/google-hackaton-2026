from django.contrib import admin
from django.urls import path
from config.api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    # Montaje de todos los routers de Django Ninja bajo la ruta /api/v1/
    path('api/v1/', api.urls),
]

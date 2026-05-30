#!/bin/bash
set -e

# ==============================================================================
# ENTRYPOINT SCRIPT PARA AUTOGESTIÓN DE MIGRACIONES EN GOOGLE CLOUD RUN
# ==============================================================================

# Si no estamos en modo SQLite de desarrollo, correr migraciones en la DB de producción
if [ "$USE_SQLITE" != "True" ]; then
    echo "⚙️ Detectado entorno de producción. Iniciando migraciones de base de datos..."
    python manage.py migrate --noinput
    echo "✅ Migraciones de base de datos aplicadas exitosamente."
else
    echo "💻 Detectado entorno de desarrollo local (SQLite). Saltando migraciones automáticas en contenedor."
fi

# Iniciar el servidor web asíncrono Uvicorn heredando los procesos (exec)
echo "🚀 Iniciando servidor web asíncrono Uvicorn ASGI..."
exec uvicorn config.asgi:application --host 0.0.0.0 --port 8080


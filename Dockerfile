# ==============================================================================
# DOCKERFILE MULTI-STAGE OPTIMIZADO PARA GEODJANGO (GIS) EN GOOGLE CLOUD RUN
# ==============================================================================

# --- Etapa 1: Compilación de Dependencias (Builder) ---
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar herramientas de compilación y cabeceras de base de datos
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y compilar wheels para acelerar la instalación posterior
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# --- Etapa 2: Imagen de Ejecución Ligera (Final) ---
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# INSTALAR LIBRERÍAS DE GEODJANGO/POSTGIS CRÍTICAS
# GDAL, GEOS, PROJ y cabeceras PostgreSQL requeridos por GeoDjango en el contenedor
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    libpq-dev \
    libsqlite3-mod-spatialite \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar y ejecutar la instalación de las ruedas compiladas de la etapa 1
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/* \
    && pip install --no-cache uvicorn gunicorn

# Copiar el código fuente completo del backend
COPY . .

# Configurar variables de entorno nativas de GDAL/GEOS para Linux en Docker
ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so
ENV GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so

# Exponer el puerto por defecto de Google Cloud Run
EXPOSE 8080

# Crear un usuario sin privilegios root por razones estrictas de seguridad (Container Hardening)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Levantar el servidor web usando Uvicorn ASGI para exprimir el rendimiento asíncrono
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]

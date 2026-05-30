# 🌲 Backend de Análisis, Predicción y Seguimiento de Incendios Forestales y Desastres Naturales

Este es el backend de nivel de producción desarrollado bajo principios de **Clean Architecture** (Arquitectura Limpia) utilizando **Django Ninja** asíncrono, **PostgreSQL + PostGIS** (GeoDjango) y servicios en la nube de **Google Cloud Platform** (**Vertex AI** y **Google Earth Engine**).

---

## 🚀 Arquitectura y Patrones de Diseño

El sistema está diseñado para ser altamente escalable y desacoplado:
1. **Patrón Service/Repository**: Abstrae por completo las llamadas al ORM de GeoDjango y la comunicación externa con APIs de Google, encapsulando la lógica de negocio pura en servicios independientes de la entrega HTTP.
2. **Esquemas Pydantic v2**: Proveen validación ultrarrápida y de tipado estricto en la entrada y salida, incluyendo esquemas GeoJSON específicos para geometrías poligonales cerradas.
3. **Manejadores Globales de Excepciones**: Capturan y transforman errores inesperados o fallos de conexión de Vertex AI/Earth Engine en respuestas semánticas amigables e informativas (HTTP 502, 422, etc.).
4. **Procesamiento de Tareas Asíncronas**: Configurado con **Celery** y **Redis** para derivar el reentrenamiento y el procesamiento ráster pesado a hilos secundarios, garantizando respuestas en milisegundos en los endpoints de la API.

---

## 📂 Estructura del Código Fuente

El proyecto está organizado en módulos independientes dentro de la carpeta `apps/`:

```text
/home/httpreen/Google/
├── config/
│   ├── settings.py         # Configuración del proyecto, PostGIS y variables de GCP
│   ├── celery.py           # Configuración base de Celery Worker
│   ├── api.py              # Instancia global de Django Ninja y manejador de excepciones
│   └── urls.py             # Rutas generales de Django
├── apps/
│   ├── core/               # Módulo de Autenticación, JWT asíncrono y roles del sistema
│   ├── gis/                # Ingesta de sensores IoT, estaciones y consultas espaciales
│   ├── ia/                 # Algoritmo de predicción, Vertex AI, Earth Engine y tareas Celery
│   └── incidents/          # Incendios activos, polígonos de evacuación y ruteo seguro
├── manage.py
└── requirements.txt
```

---

## 🛠️ Tecnologías Clave Utilizadas

- **Django >= 5.0** (Uso nativo de `async/await` y consultas asíncronas con `aget`, `acreate`, etc.).
- **Django Ninja** (Endpoints asíncronos nativos con soporte directo para Pydantic v2).
- **PostGIS & GeoDjango** (Manejo espacial nativo para puntos georreferenciados y polígonos).
- **Google Earth Engine API** (Ingesta y procesamiento satelital de Sentinel-2 para el cálculo de índices NDVI y NBR en tiempo real).
- **Google Cloud Vertex AI** (Online Predictions para evaluación de riesgo y Vertex AI Pipelines para entrenamiento distribuido).
- **Celery & Redis** (Gestión de colas de tareas asíncronas para optimizar recursos).

---

## 📦 Instrucciones de Instalación y Configuración

### 1. Requisitos Previos (En Linux / Debian)
Asegúrate de contar con las librerías espaciales del sistema instaladas:
```bash
sudo apt-get update
sudo apt-get install binutils libproj-dev gdal-bin python3-gdal
```

### 2. Configurar la Base de Datos PostgreSQL + PostGIS
Instala PostgreSQL y crea una base de datos activando la extensión espacial:
```sql
CREATE DATABASE forest_fires_db;
\c forest_fires_db;
CREATE EXTENSION postgis;
```

### 3. Instalación de Dependencias Python
```bash
pip install -r requirements.txt
```

### 4. Variables de Entorno (`.env`)
Crea un archivo `.env` en la raíz del proyecto con la configuración de tu entorno:
```env
DJANGO_SECRET_KEY=clave_secreta_de_produccion_2026
DJANGO_DEBUG=True
DB_NAME=forest_fires_db
DB_USER=postgres
DB_PASSWORD=tu_contraseña
DB_HOST=localhost
DB_PORT=5432

# Integración GCP (Opcional, en su ausencia el sistema operará en modo simulado para desarrollo)
GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/tu/gcp-service-account-key.json
GCS_BUCKET_NAME=tu-bucket-de-rasters
GCP_PROJECT_ID=tu-gcp-project-id
GCP_REGION=us-central1
VERTEX_AI_ENDPOINT_ID=tu-endpoint-id

# Celery & Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 5. Aplicar Migraciones
```bash
python manage.py migrate
```

---

## ⚡ Ejecución del Servidor y Tareas

### Servidor de Desarrollo Asíncrono (Uvicorn / ASGI)
Para aprovechar al máximo las capacidades `async` de Django Ninja, se recomienda correr el servidor con un servidor ASGI:
```bash
pip install uvicorn
uvicorn config.asgi:application --reload --port 8000
```

### Iniciar el Worker de Celery
```bash
celery -A config worker --loglevel=info
```

---

## 🔌 API Endpoints Destacados

### 1. Módulo GIS & Sensores
- `POST /api/v1/gis/stations`: Registra una nueva estación meteorológica con su punto de coordenadas PostGIS. (Requiere rol `ADMIN` o `ANALYST`).
- `POST /api/v1/gis/telemetry`: Ingesta masiva y pública en tiempo real de telemetría IoT (temperatura, humedad, viento).

### 2. Módulo Predictivo de Inteligencia Artificial (ML)
- `POST /api/v1/ia/predict`: Ingiere coordenadas geográficas e infiere en tiempo real el riesgo de incendio devolviendo:
  - **Probabilidad de Ignición** (evaluada con Vertex AI).
  - **Vector de Propagación** (dirección y velocidad del fuego).
  - **Índices NDVI / NBR satelitales** de Sentinel-2 (calculados en caliente vía Google Earth Engine).
  - Si la entrada no contiene datos meteorológicos, el servicio busca de forma espacial la estación PostGIS más cercana en un radio de 50km.
- `POST /api/v1/ia/retrain`: Compila automáticamente los registros históricos y dispara un Pipeline de entrenamiento en Vertex AI Pipelines de forma asíncrona usando Celery.

### 3. Módulo de Desastres/Alertas
- `POST /api/v1/incidents/incidents`: Reporta un incendio forestal activo en terreno.
- `POST /api/v1/incidents/perimeters`: Registra una zona caliente de evacuación obligatoria. PostGIS calcula en metros de forma exacta la superficie total en Hectáreas.
- `POST /api/v1/incidents/escape-route`: Calcula el trayecto óptimo entre dos puntos geográficos, colisionando espacialmente la trayectoria teórica contra los polígonos activos de incendios y calculando un vector de desvío de seguridad para esquivar el peligro.

from typing import List, Tuple, Optional
from asgiref.sync import sync_to_async
from apps.gis.repositories import GISRepository
from apps.gis.schemas import (
    WeatherStationCreateSchema, 
    WeatherStationResponseSchema,
    SensorMetricCreateSchema,
    SensorMetricResponseSchema,
    GeoJSONPointSchema
)
from apps.gis.models import WeatherStation, SensorMetric

class GISService:
    """
    Servicio que implementa la lógica de negocio para la gestión de sensores espaciales y telemetría.
    Desacopla la capa de persistencia de los esquemas Pydantic expuestos en la API.
    """
    def __init__(self, repository: GISRepository = None):
        self.repository = repository or GISRepository()

    async def register_station(self, data: WeatherStationCreateSchema) -> WeatherStationResponseSchema:
        """Valida y registra una nueva estación en la red GIS."""
        lon, lat = data.location.coordinates
        
        station = await self.repository.create_station(
            name=data.name,
            lon=lon,
            lat=lat,
            is_active=data.is_active
        )
        return self._map_station_to_response(station)

    async def ingest_telemetry(self, data: SensorMetricCreateSchema) -> SensorMetricResponseSchema:
        """Procesa e ingesta telemetría proveniente de dispositivos IoT o reportes de campo."""
        station = await self.repository.get_station_by_id(data.station_id)
        
        metric = await self.repository.save_metric(
            station=station,
            temp=data.temperature,
            hum=data.humidity,
            wind_sp=data.wind_speed,
            wind_dir=data.wind_direction
        )
        return self._map_metric_to_response(metric)

    async def get_station(self, station_id: int) -> WeatherStationResponseSchema:
        """Obtiene la ficha técnica de una estación meteorológica."""
        station = await self.repository.get_station_by_id(station_id)
        return self._map_station_to_response(station)

    async def list_active_stations(self) -> List[WeatherStationResponseSchema]:
        """Retorna el listado completo de estaciones activas."""
        stations = await self.repository.list_active_stations()
        return [self._map_station_to_response(s) for s in stations]

    async def get_nearest_telemetry(self, lon: float, lat: float, max_dist_km: float = 50.0) -> Tuple[Optional[SensorMetric], Optional[float]]:
        """
        [ASYNC WRAPPER] Ejecuta de forma asíncrona la búsqueda geoespacial 
        del sensor meteorológico más cercano.
        """
        # Ejecutar de forma segura en un hilo alterno dado que Django ORM no soporta
        # operaciones geoespaciales complejas de forma asíncrona nativa aún (dwithin/annotate)
        metric, distance = await sync_to_async(self.repository.get_nearest_weather_data)(lon, lat, max_dist_km)
        return metric, distance

    def _map_station_to_response(self, station: WeatherStation) -> WeatherStationResponseSchema:
        """Mapea una entidad Django GeoSQL a un esquema Pydantic de salida."""
        if isinstance(station.location_geom, str):
            import ast
            try:
                if station.location_geom.startswith("POINT"):
                    pts = station.location_geom.replace("POINT (", "").replace(")", "").split()
                    coords = [float(pts[0]), float(pts[1])]
                else:
                    coords = ast.literal_eval(station.location_geom)
            except Exception:
                coords = [0.0, 0.0]
        else:
            coords = [station.location_geom.x, station.location_geom.y]

        return WeatherStationResponseSchema(
            id=station.id,
            name=station.name,
            location=GeoJSONPointSchema(
                type="Point",
                coordinates=coords
            ),
            is_active=station.is_active,
            created_at=station.created_at
        )

    def _map_metric_to_response(self, metric: SensorMetric) -> SensorMetricResponseSchema:
        """Mapea un modelo de lectura a su esquema de salida."""
        return SensorMetricResponseSchema(
            id=metric.id,
            station_id=metric.station.id,
            recorded_at=metric.recorded_at,
            temperature=metric.temperature,
            humidity=metric.humidity,
            wind_speed=metric.wind_speed,
            wind_direction=metric.wind_direction
        )

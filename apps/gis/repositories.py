from typing import List, Optional, Tuple
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from apps.gis.models import WeatherStation, SensorMetric
from config.api import EntityNotFoundException

class GISRepository:
    """
    Capa de persistencia especializada para operaciones espaciales (PostGIS) y lectura/escritura de sensores.
    Utiliza consultas GeoDjango optimizadas.
    """
    
    async def create_station(self, name: str, lon: float, lat: float, is_active: bool = True) -> WeatherStation:
        """Crea una estación con geometría Point en PostGIS (SRID 4326)."""
        location = Point(lon, lat, srid=4326)
        station = await WeatherStation.objects.acreate(
            name=name,
            location_geom=location,
            is_active=is_active
        )
        return station

    async def get_station_by_id(self, station_id: int) -> WeatherStation:
        """Obtiene una estación por su ID de manera asíncrona."""
        try:
            return await WeatherStation.objects.aget(id=station_id)
        except WeatherStation.DoesNotExist:
            raise EntityNotFoundException(f"La estación con ID {station_id} no existe.")

    async def list_active_stations(self) -> List[WeatherStation]:
        """Obtiene todas las estaciones activas del mapa."""
        # Django 5.0 soporta la conversión de QuerySets asíncronos mediante a list comprehensions o async for
        stations = []
        async for station in WeatherStation.objects.filter(is_active=True):
            stations.append(station)
        return stations

    async def save_metric(self, station: WeatherStation, temp: float, hum: float, wind_sp: float, wind_dir: Optional[float] = None) -> SensorMetric:
        """Registra una lectura telemétrica en la base de datos."""
        return await SensorMetric.objects.acreate(
            station=station,
            temperature=temp,
            humidity=hum,
            wind_speed=wind_sp,
            wind_direction=wind_dir
        )

    def get_nearest_weather_data(self, lon: float, lat: float, max_distance_km: float = 50.0) -> Tuple[Optional[SensorMetric], Optional[float]]:
        """
        [SÍNCRONO/HÍBRIDO] Busca la estación activa más cercana dentro de un radio en kilómetros
        y devuelve la métrica de sensor más reciente, junto con la distancia en metros.
        Utiliza funciones nativas de distancia PostGIS (o simulador SQLite).
        """
        from django.conf import settings
        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
            # Fallback simple de simulación en SQLite
            station = WeatherStation.objects.filter(is_active=True).first()
            if not station:
                return None, None
            latest_metric = SensorMetric.objects.filter(station=station).order_by('-recorded_at').first()
            return latest_metric, 1200.0 # 1.2km simulados
            
        ref_point = Point(lon, lat, srid=4326)
        
        # Anotar distancia espacial y filtrar
        nearby_stations = WeatherStation.objects.filter(
            is_active=True,
            location_geom__distance_lte=(ref_point, D(km=max_distance_km))
        ).annotate(
            distance=Distance('location_geom', ref_point)
        ).order_by('distance')
        
        station = nearby_stations.first()
        if not station:
            return None, None
            
        # Obtener última métrica registrada
        latest_metric = SensorMetric.objects.filter(station=station).order_by('-recorded_at').first()
        distance_meters = station.distance.m if hasattr(station, 'distance') else None
        
        return latest_metric, distance_meters

import json
import logging
from typing import Dict, List, Optional, Tuple
from src.database.database import ISAZone, get_db
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class GeofencingService:
    """Geofencing service with proper geometric calculations"""
    
    def __init__(self):
        self.zones_cache: Dict[str, Dict] = {}
        self._load_zones()
    
    def _load_zones(self):
        """Load zones from database"""
        try:
            db = next(get_db())
            zones = db.query(ISAZone).filter(ISAZone.is_active == True).all()
            
            for zone in zones:
                try:
                    geojson = json.loads(zone.geojson_data)
                    self.zones_cache[zone.zone_id] = {
                        'zone_id': zone.zone_id,
                        'zone_name': zone.zone_name,
                        'zone_type': zone.zone_type,
                        'max_duration_hours': zone.max_duration_hours,
                        'geojson_data': zone.geojson_data,
                        'geometry': geojson.get('geometry', {})
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid GeoJSON for zone {zone.zone_id}: {e}")
                    continue
            
            logger.info(f"Loaded {len(zones)} zones from database")
        except Exception as e:
            logger.error(f"Error loading zones: {e}")
    
    def check_position(self, latitude: float, longitude: float, depth: float = 0) -> List[Dict]:
        """
        Check if a position is within any zones using proper geometric calculations
        """
        matching_zones = []
        
        for zone_id, zone_data in self.zones_cache.items():
            if self._is_point_in_geometry(longitude, latitude, zone_data['geometry']):
                matching_zones.append({
                    'zone_id': zone_data['zone_id'],
                    'zone_name': zone_data['zone_name'],
                    'zone_type': zone_data['zone_type'],
                    'max_duration_hours': zone_data['max_duration_hours']
                })
        
        return matching_zones
    
    def _is_point_in_geometry(self, x: float, y: float, geometry: Dict) -> bool:
        """
        Check if a point is inside a geometry (Polygon or MultiPolygon)
        """
        geom_type = geometry.get('type', '').lower()
        
        if geom_type == 'polygon':
            return self._is_point_in_polygon(x, y, geometry['coordinates'])
        elif geom_type == 'multipolygon':
            return self._is_point_in_multipolygon(x, y, geometry['coordinates'])
        else:
            logger.warning(f"Unsupported geometry type: {geom_type}")
            return False
    
    def _is_point_in_polygon(self, x: float, y: float, coordinates: List) -> bool:
        """
        Ray casting algorithm for point-in-polygon test
        """
        if not coordinates or len(coordinates) == 0:
            return False
        
        # Handle the first ring (exterior boundary)
        polygon = coordinates[0]
        inside = self._ray_casting_algorithm(x, y, polygon)
        
        # Check holes (interior rings)
        for hole in coordinates[1:]:
            if self._ray_casting_algorithm(x, y, hole):
                inside = False
                break
        
        return inside
    
    def _is_point_in_multipolygon(self, x: float, y: float, coordinates: List) -> bool:
        """
        Check if point is in any polygon of the multipolygon
        """
        for polygon_coords in coordinates:
            if self._is_point_in_polygon(x, y, polygon_coords):
                return True
        return False
    
    def _ray_casting_algorithm(self, x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
        """
        Ray casting algorithm implementation
        """
        n = len(polygon)
        if n < 3:
            return False
        
        inside = False
        j = n - 1
        
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        
        return inside
    
    def get_zone_by_id(self, zone_id: str) -> Optional[Dict]:
        """Get zone by ID"""
        return self.zones_cache.get(zone_id)
    
    def get_all_zones(self) -> List[Dict]:
        """Get all zones"""
        return list(self.zones_cache.values())
    
    def refresh_zones(self):
        """Refresh zones from database"""
        self._load_zones()
    
    def add_zone(self, zone_id: str, zone_name: str, zone_type: str, 
                 max_duration_hours: float, geojson_data: str):
        """Add a new zone to the cache"""
        try:
            geojson = json.loads(geojson_data)
            self.zones_cache[zone_id] = {
                'zone_id': zone_id,
                'zone_name': zone_name,
                'zone_type': zone_type,
                'max_duration_hours': max_duration_hours,
                'geojson_data': geojson_data,
                'geometry': geojson.get('geometry', {})
            }
            logger.info(f"Added zone {zone_id} to cache")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid GeoJSON for zone {zone_id}: {e}")
    
    def reload_zones(self):
        """Reload all zones from database"""
        self.zones_cache.clear()
        self._load_zones() 
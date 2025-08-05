import json
import logging
from typing import Dict, List, Optional
from src.database.database import ISAZone, get_db

logger = logging.getLogger(__name__)

class GeofencingService:
    """Simplified geofencing service without Shapely dependency"""
    
    def __init__(self):
        self.zones_cache: Dict[str, Dict] = {}
        self._load_zones()
    
    def _load_zones(self):
        """Load zones from database"""
        try:
            db = next(get_db())
            zones = db.query(ISAZone).filter(ISAZone.is_active == True).all()
            
            for zone in zones:
                self.zones_cache[zone.zone_id] = {
                    'zone_id': zone.zone_id,
                    'zone_name': zone.zone_name,
                    'zone_type': zone.zone_type,
                    'max_duration_hours': zone.max_duration_hours,
                    'geojson_data': zone.geojson_data
                }
            
            logger.info(f"Loaded {len(zones)} zones from database")
        except Exception as e:
            logger.error(f"Error loading zones: {e}")
    
    def check_position(self, latitude: float, longitude: float, depth: float = 0) -> List[Dict]:
        """
        Check if a position is within any zones
        Simplified version that returns all zones for testing
        """
        # For testing purposes, return all zones
        # In a real implementation, this would use proper geometric calculations
        return list(self.zones_cache.values())
    
    def is_point_in_polygon(self, point: tuple, polygon_coords: List[tuple]) -> bool:
        """
        Simple point-in-polygon test using ray casting algorithm
        """
        x, y = point
        n = len(polygon_coords)
        inside = False
        
        p1x, p1y = polygon_coords[0]
        for i in range(n + 1):
            p2x, p2y = polygon_coords[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
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
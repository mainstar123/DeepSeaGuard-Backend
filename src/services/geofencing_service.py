import json
import shapely.geometry as geometry
from shapely.geometry import Point, Polygon
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from database.database import ISAZone, get_db

logger = logging.getLogger(__name__)

class GeofencingService:
    def __init__(self):
        self.zones: Dict[str, Dict] = {}
        self.load_zones()
    
    def load_zones(self):
        """Load ISA zones from database into memory"""
        try:
            db = next(get_db())
            zones = db.query(ISAZone).filter(ISAZone.is_active == True).all()
            
            for zone in zones:
                try:
                    geojson = json.loads(zone.geojson_data)
                    if geojson['type'] == 'Feature':
                        geometry_data = geojson['geometry']
                        if geometry_data['type'] == 'Polygon':
                            polygon = geometry.Polygon(geometry_data['coordinates'][0])
                            self.zones[zone.zone_id] = {
                                'name': zone.zone_name,
                                'type': zone.zone_type,
                                'max_duration_hours': zone.max_duration_hours,
                                'polygon': polygon,
                                'geojson': geojson
                            }
                        elif geometry_data['type'] == 'MultiPolygon':
                            polygons = [geometry.Polygon(coords[0]) for coords in geometry_data['coordinates']]
                            multi_polygon = geometry.MultiPolygon(polygons)
                            self.zones[zone.zone_id] = {
                                'name': zone.zone_name,
                                'type': zone.zone_type,
                                'max_duration_hours': zone.max_duration_hours,
                                'polygon': multi_polygon,
                                'geojson': geojson
                            }
                except Exception as e:
                    logger.error(f"Error loading zone {zone.zone_id}: {e}")
                    continue
            
            logger.info(f"Loaded {len(self.zones)} ISA zones into memory")
            
        except Exception as e:
            logger.error(f"Error loading zones: {e}")
    
    def check_position(self, latitude: float, longitude: float, depth: float) -> List[Dict]:
        """
        Check if a position is inside any ISA zones
        
        Returns:
            List of zones the position is inside, with zone details
        """
        point = Point(longitude, latitude)  # Note: GeoJSON uses [lng, lat] order
        inside_zones = []
        
        for zone_id, zone_data in self.zones.items():
            try:
                if zone_data['polygon'].contains(point):
                    inside_zones.append({
                        'zone_id': zone_id,
                        'zone_name': zone_data['name'],
                        'zone_type': zone_data['type'],
                        'max_duration_hours': zone_data['max_duration_hours'],
                        'depth': depth
                    })
            except Exception as e:
                logger.error(f"Error checking zone {zone_id}: {e}")
                continue
        
        return inside_zones
    
    def is_inside_zone(self, latitude: float, longitude: float, zone_id: str) -> bool:
        """Check if a position is inside a specific zone"""
        if zone_id not in self.zones:
            return False
        
        point = Point(longitude, latitude)
        try:
            return self.zones[zone_id]['polygon'].contains(point)
        except Exception as e:
            logger.error(f"Error checking if inside zone {zone_id}: {e}")
            return False
    
    def get_zone_info(self, zone_id: str) -> Optional[Dict]:
        """Get information about a specific zone"""
        return self.zones.get(zone_id)
    
    def get_all_zones(self) -> Dict[str, Dict]:
        """Get all loaded zones"""
        return self.zones
    
    def reload_zones(self):
        """Reload zones from database"""
        self.zones.clear()
        self.load_zones()
    
    def add_zone(self, zone_id: str, zone_name: str, zone_type: str, 
                 max_duration_hours: float, geojson_data: str):
        """Add a new zone to the service"""
        try:
            geojson = json.loads(geojson_data)
            if geojson['type'] == 'Feature':
                geometry_data = geojson['geometry']
                if geometry_data['type'] == 'Polygon':
                    polygon = geometry.Polygon(geometry_data['coordinates'][0])
                elif geometry_data['type'] == 'MultiPolygon':
                    polygons = [geometry.Polygon(coords[0]) for coords in geometry_data['coordinates']]
                    polygon = geometry.MultiPolygon(polygons)
                else:
                    raise ValueError(f"Unsupported geometry type: {geometry_data['type']}")
                
                self.zones[zone_id] = {
                    'name': zone_name,
                    'type': zone_type,
                    'max_duration_hours': max_duration_hours,
                    'polygon': polygon,
                    'geojson': geojson
                }
                
                logger.info(f"Added zone {zone_id} to geofencing service")
                
        except Exception as e:
            logger.error(f"Error adding zone {zone_id}: {e}")
            raise 
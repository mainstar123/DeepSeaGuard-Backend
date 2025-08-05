"""
Spatial Index for DeepSeaGuard
Provides fast geometric queries using R-tree indexing
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from shapely.geometry import Point, Polygon, MultiPolygon, box
from shapely.strtree import STRtree
import numpy as np
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class ZoneIndex:
    """Zone data for spatial indexing"""
    zone_id: str
    zone_name: str
    zone_type: str
    max_duration_hours: float
    geometry: Any  # Shapely geometry
    bounds: Tuple[float, float, float, float]  # (minx, miny, maxx, maxy)
    properties: Dict[str, Any]

class SpatialIndex:
    """High-performance spatial index for zone queries"""
    
    def __init__(self):
        self.zones: Dict[str, ZoneIndex] = {}
        self.spatial_tree: Optional[STRtree] = None
        self.bounds_cache: Dict[str, Tuple[float, float, float, float]] = {}
        self.last_rebuild: Optional[datetime] = None
        self.rebuild_interval = timedelta(minutes=5)  # Rebuild every 5 minutes
        
    def add_zone(self, zone_id: str, zone_data: Dict[str, Any]) -> bool:
        """Add a zone to the spatial index"""
        try:
            from shapely.geometry import shape
            
            # Parse geometry
            geometry = shape(zone_data['geometry'])
            
            # Calculate bounds
            bounds = geometry.bounds
            
            # Create zone index entry
            zone_index = ZoneIndex(
                zone_id=zone_id,
                zone_name=zone_data.get('zone_name', ''),
                zone_type=zone_data.get('zone_type', 'sensitive'),
                max_duration_hours=zone_data.get('max_duration_hours', 1.0),
                geometry=geometry,
                bounds=bounds,
                properties=zone_data
            )
            
            self.zones[zone_id] = zone_index
            self.bounds_cache[zone_id] = bounds
            
            # Mark for rebuild
            self._schedule_rebuild()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding zone {zone_id} to spatial index: {e}")
            return False
    
    def remove_zone(self, zone_id: str) -> bool:
        """Remove a zone from the spatial index"""
        try:
            if zone_id in self.zones:
                del self.zones[zone_id]
            if zone_id in self.bounds_cache:
                del self.bounds_cache[zone_id]
            
            self._schedule_rebuild()
            return True
            
        except Exception as e:
            logger.error(f"Error removing zone {zone_id} from spatial index: {e}")
            return False
    
    def _schedule_rebuild(self):
        """Schedule spatial tree rebuild"""
        self.last_rebuild = None  # Force rebuild on next query
    
    def _rebuild_tree(self):
        """Rebuild the spatial R-tree"""
        try:
            if not self.zones:
                self.spatial_tree = None
                return
            
            geometries = []
            zone_ids = []
            
            for zone_id, zone_index in self.zones.items():
                geometries.append(zone_index.geometry)
                zone_ids.append(zone_id)
            
            self.spatial_tree = STRtree(geometries)
            self.last_rebuild = datetime.utcnow()
            
            logger.info(f"Rebuilt spatial index with {len(self.zones)} zones")
            
        except Exception as e:
            logger.error(f"Error rebuilding spatial tree: {e}")
    
    def query_point(self, latitude: float, longitude: float, depth: float = 0) -> List[Dict[str, Any]]:
        """Query zones containing a point"""
        try:
            # Check if rebuild is needed
            if (self.last_rebuild is None or 
                datetime.utcnow() - self.last_rebuild > self.rebuild_interval):
                self._rebuild_tree()
            
            if not self.spatial_tree:
                return []
            
            # Create point geometry
            point = Point(longitude, latitude)
            
            # Query spatial tree
            candidate_indices = self.spatial_tree.query(point)
            
            # Check containment for candidates
            matching_zones = []
            for idx in candidate_indices:
                zone_index = list(self.zones.values())[idx]
                
                # Check if point is inside the zone
                if zone_index.geometry.contains(point):
                    matching_zones.append({
                        'zone_id': zone_index.zone_id,
                        'zone_name': zone_index.zone_name,
                        'zone_type': zone_index.zone_type,
                        'max_duration_hours': zone_index.max_duration_hours,
                        'properties': zone_index.properties
                    })
            
            return matching_zones
            
        except Exception as e:
            logger.error(f"Error querying spatial index: {e}")
            return []
    
    def query_bounds(self, bounds: Tuple[float, float, float, float]) -> List[str]:
        """Query zones intersecting with bounds"""
        try:
            if not self.spatial_tree:
                return []
            
            # Create bounding box
            bbox = box(*bounds)
            
            # Query spatial tree
            candidate_indices = self.spatial_tree.query(bbox)
            
            # Return zone IDs
            zone_ids = []
            for idx in candidate_indices:
                zone_index = list(self.zones.values())[idx]
                zone_ids.append(zone_index.zone_id)
            
            return zone_ids
            
        except Exception as e:
            logger.error(f"Error querying bounds: {e}")
            return []
    
    def get_zone_bounds(self, zone_id: str) -> Optional[Tuple[float, float, float, float]]:
        """Get bounds for a specific zone"""
        return self.bounds_cache.get(zone_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get spatial index statistics"""
        return {
            'total_zones': len(self.zones),
            'spatial_tree_built': self.spatial_tree is not None,
            'last_rebuild': self.last_rebuild.isoformat() if self.last_rebuild else None,
            'bounds_cache_size': len(self.bounds_cache)
        }
    
    def clear(self):
        """Clear all zones from the index"""
        self.zones.clear()
        self.bounds_cache.clear()
        self.spatial_tree = None
        self.last_rebuild = None

# Global spatial index instance
spatial_index = SpatialIndex() 
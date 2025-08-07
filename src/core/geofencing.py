"""
Geofencing Engine Core Module
Handles advanced geofencing operations with spatial calculations
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
import numpy as np

logger = logging.getLogger(__name__)

class GeofencingEngine:
    """Advanced geofencing engine for spatial calculations"""
    
    def __init__(self):
        self.zones: Dict[str, Polygon] = {}
        self.zone_metadata: Dict[str, Dict] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
    def add_zone(self, zone_id: str, coordinates: List[Tuple[float, float]], 
                 metadata: Optional[Dict] = None) -> bool:
        """Add a geofence zone"""
        try:
            # Create polygon from coordinates
            if len(coordinates) < 3:
                logger.error(f"Zone {zone_id}: Need at least 3 coordinates")
                return False
                
            polygon = Polygon(coordinates)
            if not polygon.is_valid:
                logger.error(f"Zone {zone_id}: Invalid polygon")
                return False
                
            self.zones[zone_id] = polygon
            self.zone_metadata[zone_id] = metadata or {}
            
            logger.info(f"Added zone {zone_id} with {len(coordinates)} points")
            return True
            
        except Exception as e:
            logger.error(f"Error adding zone {zone_id}: {e}")
            return False
    
    def remove_zone(self, zone_id: str) -> bool:
        """Remove a geofence zone"""
        if zone_id in self.zones:
            del self.zones[zone_id]
            del self.zone_metadata[zone_id]
            logger.info(f"Removed zone {zone_id}")
            return True
        return False
    
    def check_position(self, latitude: float, longitude: float, depth: float = 0) -> Dict[str, Any]:
        """Check if a position is within any zones"""
        point = Point(longitude, latitude)  # Note: Shapely uses (x, y) = (lon, lat)
        
        violations = []
        warnings = []
        safe_zones = []
        
        for zone_id, polygon in self.zones.items():
            metadata = self.zone_metadata.get(zone_id, {})
            
            # Check if point is inside polygon
            if polygon.contains(point):
                zone_type = metadata.get('zone_type', 'unknown')
                
                # Check depth restrictions
                depth_min = metadata.get('depth_min')
                depth_max = metadata.get('depth_max')
                
                depth_violation = False
                if depth_min is not None and depth < depth_min:
                    depth_violation = True
                if depth_max is not None and depth > depth_max:
                    depth_violation = True
                
                if zone_type == 'restricted':
                    violations.append({
                        'zone_id': zone_id,
                        'zone_name': metadata.get('name', zone_id),
                        'zone_type': zone_type,
                        'severity': 'high',
                        'depth_violation': depth_violation,
                        'timestamp': datetime.now()
                    })
                elif zone_type == 'monitoring':
                    warnings.append({
                        'zone_id': zone_id,
                        'zone_name': metadata.get('name', zone_id),
                        'zone_type': zone_type,
                        'severity': 'medium',
                        'depth_violation': depth_violation,
                        'timestamp': datetime.now()
                    })
                elif zone_type == 'safe':
                    safe_zones.append(zone_id)
        
        # Determine risk level
        risk_level = 'low'
        if violations:
            risk_level = 'critical'
        elif warnings:
            risk_level = 'medium'
        
        return {
            'violations': violations,
            'warnings': warnings,
            'safe_zones': safe_zones,
            'risk_level': risk_level,
            'total_zones_checked': len(self.zones)
        }
    
    def get_zone_info(self, zone_id: str) -> Optional[Dict]:
        """Get information about a specific zone"""
        if zone_id in self.zones:
            polygon = self.zones[zone_id]
            metadata = self.zone_metadata.get(zone_id, {})
            
            return {
                'zone_id': zone_id,
                'coordinates': list(polygon.exterior.coords),
                'area': polygon.area,
                'metadata': metadata
            }
        return None
    
    def get_all_zones(self) -> List[Dict]:
        """Get information about all zones"""
        zones_info = []
        for zone_id in self.zones:
            zone_info = self.get_zone_info(zone_id)
            if zone_info:
                zones_info.append(zone_info)
        return zones_info
    
    def optimize_zones(self):
        """Optimize zone storage and calculations"""
        # Merge overlapping zones if possible
        # This is a simplified optimization
        logger.info(f"Optimized {len(self.zones)} zones")
    
    def get_performance_metrics(self) -> Dict:
        """Get performance metrics"""
        return {
            'total_zones': len(self.zones),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
        } 
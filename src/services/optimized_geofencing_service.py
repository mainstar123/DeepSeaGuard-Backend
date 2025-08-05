"""
Optimized Geofencing Service for DeepSeaGuard
High-performance geofencing with spatial indexing and caching
"""
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import asyncio
from functools import lru_cache

from database.database import ISAZone, get_db
from core.optimization.spatial_index import spatial_index
from core.optimization.cache_manager import cache_manager, cached
from core.optimization.database_optimizer import db_optimizer

logger = logging.getLogger(__name__)

class OptimizedGeofencingService:
    """High-performance geofencing service with spatial indexing and caching"""
    
    def __init__(self):
        self.zones_cache: Dict[str, Dict] = {}
        self.last_cache_update: Optional[datetime] = None
        self.cache_ttl = timedelta(minutes=5)  # Cache zones for 5 minutes
        self._load_zones_async()
    
    async def _load_zones_async(self):
        """Load zones from database asynchronously"""
        try:
            # Check cache first
            cached_zones = await cache_manager.get("zones:all", value_type=dict)
            if cached_zones:
                self.zones_cache = cached_zones
                logger.info(f"Loaded {len(self.zones_cache)} zones from cache")
                return
            
            # Load from database
            session = db_optimizer.get_sync_session()
            try:
                zones = session.query(ISAZone).filter(ISAZone.is_active == True).all()
                
                for zone in zones:
                    try:
                        geojson = json.loads(zone.geojson_data)
                        zone_data = {
                            'zone_id': zone.zone_id,
                            'zone_name': zone.zone_name,
                            'zone_type': zone.zone_type,
                            'max_duration_hours': zone.max_duration_hours,
                            'geojson_data': zone.geojson_data,
                            'geometry': geojson.get('geometry', {}),
                            'properties': geojson.get('properties', {})
                        }
                        
                        self.zones_cache[zone.zone_id] = zone_data
                        
                        # Add to spatial index
                        spatial_index.add_zone(zone.zone_id, zone_data)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid GeoJSON for zone {zone.zone_id}: {e}")
                        continue
                
                # Cache the zones
                await cache_manager.set("zones:all", self.zones_cache, ttl=300)  # 5 minutes
                self.last_cache_update = datetime.utcnow()
                
                logger.info(f"Loaded {len(self.zones_cache)} zones from database")
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error loading zones: {e}")
    
    @cached("geofencing:check_position", ttl=60)  # Cache position checks for 1 minute
    async def check_position(self, latitude: float, longitude: float, depth: float = 0) -> List[Dict]:
        """Check which zones contain the given position (optimized)"""
        try:
            # Use spatial index for fast querying
            matching_zones = spatial_index.query_point(latitude, longitude, depth)
            
            # Add additional metadata
            for zone in matching_zones:
                zone_id = zone['zone_id']
                if zone_id in self.zones_cache:
                    zone.update({
                        'geojson_data': self.zones_cache[zone_id]['geojson_data'],
                        'properties': self.zones_cache[zone_id]['properties']
                    })
            
            return matching_zones
            
        except Exception as e:
            logger.error(f"Error checking position: {e}")
            return []
    
    async def check_position_batch(self, positions: List[Tuple[float, float, float]]) -> List[List[Dict]]:
        """Check multiple positions efficiently"""
        try:
            results = []
            
            # Process in batches for better performance
            batch_size = 100
            for i in range(0, len(positions), batch_size):
                batch = positions[i:i + batch_size]
                
                # Process batch concurrently
                tasks = [
                    self.check_position(lat, lng, depth)
                    for lat, lng, depth in batch
                ]
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                results.extend(batch_results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error checking position batch: {e}")
            return [[] for _ in positions]
    
    async def get_zone_bounds(self, zone_id: str) -> Optional[Tuple[float, float, float, float]]:
        """Get bounds for a specific zone"""
        return spatial_index.get_zone_bounds(zone_id)
    
    async def get_zones_in_bounds(self, bounds: Tuple[float, float, float, float]) -> List[str]:
        """Get all zones intersecting with the given bounds"""
        try:
            return spatial_index.query_bounds(bounds)
        except Exception as e:
            logger.error(f"Error querying bounds: {e}")
            return []
    
    async def add_zone(self, zone_id: str, zone_name: str, zone_type: str, 
                      max_duration_hours: float, geojson_data: str) -> bool:
        """Add a new zone to the system"""
        try:
            # Parse GeoJSON
            geojson = json.loads(geojson_data)
            
            zone_data = {
                'zone_id': zone_id,
                'zone_name': zone_name,
                'zone_type': zone_type,
                'max_duration_hours': max_duration_hours,
                'geojson_data': geojson_data,
                'geometry': geojson.get('geometry', {}),
                'properties': geojson.get('properties', {})
            }
            
            # Add to cache
            self.zones_cache[zone_id] = zone_data
            
            # Add to spatial index
            spatial_index.add_zone(zone_id, zone_data)
            
            # Invalidate cache
            await cache_manager.delete("zones:all")
            
            logger.info(f"Added zone {zone_id} to geofencing service")
            return True
            
        except Exception as e:
            logger.error(f"Error adding zone {zone_id}: {e}")
            return False
    
    async def remove_zone(self, zone_id: str) -> bool:
        """Remove a zone from the system"""
        try:
            # Remove from cache
            if zone_id in self.zones_cache:
                del self.zones_cache[zone_id]
            
            # Remove from spatial index
            spatial_index.remove_zone(zone_id)
            
            # Invalidate cache
            await cache_manager.delete("zones:all")
            
            logger.info(f"Removed zone {zone_id} from geofencing service")
            return True
            
        except Exception as e:
            logger.error(f"Error removing zone {zone_id}: {e}")
            return False
    
    async def reload_zones(self):
        """Reload all zones from database"""
        try:
            # Clear caches
            self.zones_cache.clear()
            spatial_index.clear()
            await cache_manager.delete("zones:all")
            
            # Reload
            await self._load_zones_async()
            
            logger.info("Reloaded all zones")
            
        except Exception as e:
            logger.error(f"Error reloading zones: {e}")
    
    async def get_zone_stats(self) -> Dict[str, Any]:
        """Get statistics about zones and performance"""
        spatial_stats = spatial_index.get_stats()
        cache_stats = cache_manager.get_stats()
        
        return {
            'zones': {
                'total_zones': len(self.zones_cache),
                'last_update': self.last_cache_update.isoformat() if self.last_cache_update else None,
                'cache_ttl_minutes': self.cache_ttl.total_seconds() / 60
            },
            'spatial_index': spatial_stats,
            'cache': cache_stats
        }
    
    @lru_cache(maxsize=1000)
    def _get_zone_by_id(self, zone_id: str) -> Optional[Dict]:
        """Get zone by ID with LRU caching"""
        return self.zones_cache.get(zone_id)
    
    async def validate_zone_geojson(self, geojson_data: str) -> Tuple[bool, str]:
        """Validate GeoJSON data"""
        try:
            geojson = json.loads(geojson_data)
            
            # Check required fields
            if geojson.get('type') != 'Feature':
                return False, "GeoJSON must be a Feature"
            
            geometry = geojson.get('geometry', {})
            if geometry.get('type') not in ['Polygon', 'MultiPolygon']:
                return False, "Geometry must be Polygon or MultiPolygon"
            
            # Validate coordinates
            coordinates = geometry.get('coordinates', [])
            if not coordinates:
                return False, "Geometry must have coordinates"
            
            return True, "Valid GeoJSON"
            
        except json.JSONDecodeError:
            return False, "Invalid JSON format"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

# Global optimized geofencing service instance
optimized_geofencing_service = OptimizedGeofencingService() 
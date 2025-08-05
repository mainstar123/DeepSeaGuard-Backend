from celery import shared_task
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

from src.database.database import get_db, ISAZone, ComplianceEvent
from src.services.geofencing_service import GeofencingService
from src.config.settings import settings

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def reload_zones_async(self):
    """Reload all zones from database into memory"""
    try:
        geofencing_service = GeofencingService()
        geofencing_service.reload_zones()
        
        zones_loaded = len(geofencing_service.get_all_zones())
        
        logger.info(f"Reloaded {zones_loaded} zones into geofencing service")
        return {
            'zones_loaded': zones_loaded,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error reloading zones: {exc}")
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def update_zone_statistics(self):
    """Update zone usage statistics"""
    try:
        db = next(get_db())
        
        # Get all active zones
        zones = db.query(ISAZone).filter(ISAZone.is_active == True).all()
        
        statistics = {}
        
        for zone in zones:
            # Get events for this zone in the last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            events = db.query(ComplianceEvent).filter(
                ComplianceEvent.zone_id == zone.zone_id,
                ComplianceEvent.timestamp >= yesterday
            ).all()
            
            # Calculate statistics
            total_events = len(events)
            violations = len([e for e in events if e.status == 'violation'])
            warnings = len([e for e in events if e.status == 'warning'])
            entries = len([e for e in events if e.event_type == 'entry'])
            exits = len([e for e in events if e.event_type == 'exit'])
            
            # Calculate total time spent in zone
            total_time_minutes = sum([e.duration_minutes or 0 for e in events])
            
            statistics[zone.zone_id] = {
                'zone_name': zone.zone_name,
                'zone_type': zone.zone_type,
                'max_duration_hours': zone.max_duration_hours,
                'total_events_24h': total_events,
                'violations_24h': violations,
                'warnings_24h': warnings,
                'entries_24h': entries,
                'exits_24h': exits,
                'total_time_minutes_24h': total_time_minutes,
                'compliance_rate': ((total_events - violations) / total_events * 100) if total_events > 0 else 100
            }
        
        db.close()
        
        # Cache statistics in Redis (if available)
        try:
            import redis
            redis_client = redis.from_url(settings.REDIS_URL)
            redis_client.setex(
                f"{settings.CACHE_PREFIX}:zone_stats",
                settings.GEO_CACHE_TTL,
                json.dumps(statistics)
            )
        except Exception as e:
            logger.warning(f"Could not cache zone statistics: {e}")
        
        logger.info(f"Updated statistics for {len(statistics)} zones")
        return {
            'zones_updated': len(statistics),
            'statistics': statistics
        }
        
    except Exception as exc:
        logger.error(f"Error updating zone statistics: {exc}")
        raise self.retry(exc=exc, countdown=300)

@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def validate_zone_geojson(self, zone_id: str, geojson_data: str):
    """Validate zone GeoJSON data"""
    try:
        # Parse and validate GeoJSON
        geojson = json.loads(geojson_data)
        
        if geojson.get('type') != 'Feature':
            raise ValueError("GeoJSON must be a Feature")
        
        geometry = geojson.get('geometry', {})
        if geometry.get('type') not in ['Polygon', 'MultiPolygon']:
            raise ValueError("Geometry must be Polygon or MultiPolygon")
        
        # Test if geometry is valid using Shapely
        import shapely.geometry as geometry
        if geometry.get('type') == 'Polygon':
            shapely_geom = geometry.Polygon(geometry['coordinates'][0])
        else:
            polygons = [geometry.Polygon(coords[0]) for coords in geometry['coordinates']]
            shapely_geom = geometry.MultiPolygon(polygons)
        
        if not shapely_geom.is_valid:
            raise ValueError("Invalid geometry")
        
        # Calculate area (optional)
        area_km2 = shapely_geom.area * 111 * 111  # Rough conversion to km²
        
        logger.info(f"Zone {zone_id} GeoJSON validated successfully. Area: {area_km2:.2f} km²")
        return {
            'zone_id': zone_id,
            'valid': True,
            'geometry_type': geometry.get('type'),
            'area_km2': area_km2
        }
        
    except Exception as exc:
        logger.error(f"Error validating zone {zone_id} GeoJSON: {exc}")
        return {
            'zone_id': zone_id,
            'valid': False,
            'error': str(exc)
        }

@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def optimize_zone_cache(self):
    """Optimize zone cache for better performance"""
    try:
        geofencing_service = GeofencingService()
        
        # Get all zones
        zones = geofencing_service.get_all_zones()
        
        # Create spatial index for faster queries
        from shapely.geometry import box
        from shapely.strtree import STRtree
        
        geometries = []
        zone_ids = []
        
        for zone_id, zone_data in zones.items():
            geometries.append(zone_data['polygon'])
            zone_ids.append(zone_id)
        
        # Build spatial index
        spatial_index = STRtree(geometries)
        
        # Cache the index (in a real implementation, you'd store this)
        logger.info(f"Built spatial index for {len(zones)} zones")
        
        return {
            'zones_indexed': len(zones),
            'spatial_index_built': True
        }
        
    except Exception as exc:
        logger.error(f"Error optimizing zone cache: {exc}")
        raise self.retry(exc=exc, countdown=300)

@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def check_zone_overlaps(self):
    """Check for overlapping zones"""
    try:
        geofencing_service = GeofencingService()
        zones = geofencing_service.get_all_zones()
        
        overlaps = []
        zone_list = list(zones.items())
        
        for i, (zone_id1, zone_data1) in enumerate(zone_list):
            for j, (zone_id2, zone_data2) in enumerate(zone_list[i+1:], i+1):
                # Check if zones overlap
                if zone_data1['polygon'].intersects(zone_data2['polygon']):
                    intersection = zone_data1['polygon'].intersection(zone_data2['polygon'])
                    overlap_area = intersection.area
                    
                    if overlap_area > 0:
                        overlaps.append({
                            'zone1_id': zone_id1,
                            'zone1_name': zone_data1['name'],
                            'zone2_id': zone_id2,
                            'zone2_name': zone_data2['name'],
                            'overlap_area': overlap_area,
                            'overlap_percentage': (overlap_area / zone_data1['polygon'].area) * 100
                        })
        
        logger.info(f"Found {len(overlaps)} zone overlaps")
        return {
            'overlaps_found': len(overlaps),
            'overlaps': overlaps
        }
        
    except Exception as exc:
        logger.error(f"Error checking zone overlaps: {exc}")
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def backup_zones_to_file(self, backup_path: str = None):
    """Backup all zones to a file"""
    try:
        if backup_path is None:
            backup_path = f"zones_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        db = next(get_db())
        zones = db.query(ISAZone).filter(ISAZone.is_active == True).all()
        
        backup_data = {
            'backup_timestamp': datetime.utcnow().isoformat(),
            'total_zones': len(zones),
            'zones': []
        }
        
        for zone in zones:
            backup_data['zones'].append({
                'zone_id': zone.zone_id,
                'zone_name': zone.zone_name,
                'zone_type': zone.zone_type,
                'max_duration_hours': zone.max_duration_hours,
                'geojson_data': zone.geojson_data,
                'is_active': zone.is_active
            })
        
        # Write to file
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        db.close()
        
        logger.info(f"Backed up {len(zones)} zones to {backup_path}")
        return {
            'backup_path': backup_path,
            'zones_backed_up': len(zones),
            'backup_size_bytes': len(json.dumps(backup_data))
        }
        
    except Exception as exc:
        logger.error(f"Error backing up zones: {exc}")
        raise self.retry(exc=exc, countdown=300)

@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def restore_zones_from_file(self, backup_path: str):
    """Restore zones from a backup file"""
    try:
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)
        
        db = next(get_db())
        
        restored_count = 0
        for zone_data in backup_data['zones']:
            # Check if zone already exists
            existing_zone = db.query(ISAZone).filter(
                ISAZone.zone_id == zone_data['zone_id']
            ).first()
            
            if existing_zone:
                # Update existing zone
                existing_zone.zone_name = zone_data['zone_name']
                existing_zone.zone_type = zone_data['zone_type']
                existing_zone.max_duration_hours = zone_data['max_duration_hours']
                existing_zone.geojson_data = zone_data['geojson_data']
                existing_zone.is_active = zone_data['is_active']
            else:
                # Create new zone
                new_zone = ISAZone(**zone_data)
                db.add(new_zone)
            
            restored_count += 1
        
        db.commit()
        db.close()
        
        # Reload zones in geofencing service
        geofencing_service = GeofencingService()
        geofencing_service.reload_zones()
        
        logger.info(f"Restored {restored_count} zones from {backup_path}")
        return {
            'zones_restored': restored_count,
            'backup_path': backup_path
        }
        
    except Exception as exc:
        logger.error(f"Error restoring zones: {exc}")
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def analyze_zone_usage_patterns(self, days: int = 30):
    """Analyze zone usage patterns over time"""
    try:
        db = next(get_db())
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all events in the time period
        events = db.query(ComplianceEvent).filter(
            ComplianceEvent.timestamp >= start_date
        ).all()
        
        # Group by zone
        zone_usage = {}
        
        for event in events:
            zone_id = event.zone_id
            if zone_id not in zone_usage:
                zone_usage[zone_id] = {
                    'total_events': 0,
                    'entries': 0,
                    'exits': 0,
                    'violations': 0,
                    'warnings': 0,
                    'total_time_minutes': 0,
                    'unique_auvs': set()
                }
            
            zone_usage[zone_id]['total_events'] += 1
            zone_usage[zone_id]['unique_auvs'].add(event.auv_id)
            
            if event.event_type == 'entry':
                zone_usage[zone_id]['entries'] += 1
            elif event.event_type == 'exit':
                zone_usage[zone_id]['exits'] += 1
            elif event.event_type == 'violation':
                zone_usage[zone_id]['violations'] += 1
            elif event.event_type == 'warning':
                zone_usage[zone_id]['warnings'] += 1
            
            if event.duration_minutes:
                zone_usage[zone_id]['total_time_minutes'] += event.duration_minutes
        
        # Convert sets to counts
        for zone_data in zone_usage.values():
            zone_data['unique_auvs'] = len(zone_data['unique_auvs'])
        
        db.close()
        
        logger.info(f"Analyzed usage patterns for {len(zone_usage)} zones over {days} days")
        return {
            'analysis_period_days': days,
            'zones_analyzed': len(zone_usage),
            'zone_usage': zone_usage
        }
        
    except Exception as exc:
        logger.error(f"Error analyzing zone usage patterns: {exc}")
        raise self.retry(exc=exc, countdown=300) 
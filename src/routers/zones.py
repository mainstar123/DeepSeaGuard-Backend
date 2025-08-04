from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import logging

from database.database import get_db, ISAZone
from models.schemas import ISAZoneCreate, ISAZoneResponse, ZoneType
from services.geofencing_service import GeofencingService

router = APIRouter()
logger = logging.getLogger(__name__)

# This will be injected from main.py
geofencing_service: GeofencingService = None

@router.post("/zones", response_model=ISAZoneResponse)
async def create_zone(
    zone: ISAZoneCreate,
    db: Session = Depends(get_db)
):
    """Create a new ISA zone"""
    try:
        # Validate GeoJSON
        try:
            geojson_data = json.loads(zone.geojson_data)
            if geojson_data.get('type') != 'Feature':
                raise ValueError("GeoJSON must be a Feature")
            
            geometry = geojson_data.get('geometry', {})
            if geometry.get('type') not in ['Polygon', 'MultiPolygon']:
                raise ValueError("Geometry must be Polygon or MultiPolygon")
                
        except json.JSONDecodeError:
            raise ValueError("Invalid GeoJSON format")
        
        # Check if zone already exists
        existing_zone = db.query(ISAZone).filter(ISAZone.zone_id == zone.zone_id).first()
        if existing_zone:
            raise HTTPException(status_code=400, detail="Zone ID already exists")
        
        # Create zone in database
        db_zone = ISAZone(
            zone_id=zone.zone_id,
            zone_name=zone.zone_name,
            zone_type=zone.zone_type,
            max_duration_hours=zone.max_duration_hours,
            geojson_data=zone.geojson_data
        )
        
        db.add(db_zone)
        db.commit()
        db.refresh(db_zone)
        
        # Add to geofencing service
        geofencing_service.add_zone(
            zone.zone_id,
            zone.zone_name,
            zone.zone_type,
            zone.max_duration_hours,
            zone.geojson_data
        )
        
        logger.info(f"Created new ISA zone: {zone.zone_id}")
        return db_zone
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating zone: {e}")
        raise HTTPException(status_code=500, detail="Failed to create zone")

@router.get("/zones", response_model=List[ISAZoneResponse])
async def get_zones(
    zone_type: Optional[ZoneType] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get all ISA zones with optional filtering"""
    try:
        query = db.query(ISAZone)
        
        if active_only:
            query = query.filter(ISAZone.is_active == True)
        
        if zone_type:
            query = query.filter(ISAZone.zone_type == zone_type)
        
        zones = query.all()
        return zones
        
    except Exception as e:
        logger.error(f"Error retrieving zones: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve zones")

@router.get("/zones/{zone_id}", response_model=ISAZoneResponse)
async def get_zone(zone_id: str, db: Session = Depends(get_db)):
    """Get a specific ISA zone by ID"""
    try:
        zone = db.query(ISAZone).filter(ISAZone.zone_id == zone_id).first()
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")
        
        return zone
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving zone {zone_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve zone")

@router.put("/zones/{zone_id}", response_model=ISAZoneResponse)
async def update_zone(
    zone_id: str,
    zone_update: ISAZoneCreate,
    db: Session = Depends(get_db)
):
    """Update an existing ISA zone"""
    try:
        zone = db.query(ISAZone).filter(ISAZone.zone_id == zone_id).first()
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")
        
        # Validate GeoJSON
        try:
            geojson_data = json.loads(zone_update.geojson_data)
            if geojson_data.get('type') != 'Feature':
                raise ValueError("GeoJSON must be a Feature")
        except json.JSONDecodeError:
            raise ValueError("Invalid GeoJSON format")
        
        # Update zone
        zone.zone_name = zone_update.zone_name
        zone.zone_type = zone_update.zone_type
        zone.max_duration_hours = zone_update.max_duration_hours
        zone.geojson_data = zone_update.geojson_data
        
        db.commit()
        db.refresh(zone)
        
        # Reload zones in geofencing service
        geofencing_service.reload_zones()
        
        logger.info(f"Updated ISA zone: {zone_id}")
        return zone
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating zone {zone_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update zone")

@router.delete("/zones/{zone_id}")
async def delete_zone(zone_id: str, db: Session = Depends(get_db)):
    """Delete an ISA zone (soft delete)"""
    try:
        zone = db.query(ISAZone).filter(ISAZone.zone_id == zone_id).first()
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")
        
        # Soft delete
        zone.is_active = False
        db.commit()
        
        # Reload zones in geofencing service
        geofencing_service.reload_zones()
        
        logger.info(f"Deleted ISA zone: {zone_id}")
        return {"message": f"Zone {zone_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting zone {zone_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete zone")

@router.post("/zones/upload")
async def upload_zones_from_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload multiple zones from a GeoJSON file"""
    try:
        if not file.filename.endswith('.geojson'):
            raise HTTPException(status_code=400, detail="File must be a GeoJSON file")
        
        content = await file.read()
        geojson_data = json.loads(content.decode('utf-8'))
        
        if geojson_data.get('type') != 'FeatureCollection':
            raise HTTPException(status_code=400, detail="File must be a FeatureCollection")
        
        features = geojson_data.get('features', [])
        created_zones = []
        
        for feature in features:
            try:
                properties = feature.get('properties', {})
                zone_id = properties.get('zone_id')
                zone_name = properties.get('zone_name', f"Zone {zone_id}")
                zone_type = properties.get('zone_type', 'sensitive')
                max_duration = properties.get('max_duration_hours', 1.0)
                
                if not zone_id:
                    logger.warning("Skipping feature without zone_id")
                    continue
                
                # Check if zone already exists
                existing = db.query(ISAZone).filter(ISAZone.zone_id == zone_id).first()
                if existing:
                    logger.warning(f"Zone {zone_id} already exists, skipping")
                    continue
                
                # Create zone
                db_zone = ISAZone(
                    zone_id=zone_id,
                    zone_name=zone_name,
                    zone_type=zone_type,
                    max_duration_hours=max_duration,
                    geojson_data=json.dumps(feature)
                )
                
                db.add(db_zone)
                created_zones.append(zone_id)
                
            except Exception as e:
                logger.error(f"Error processing feature: {e}")
                continue
        
        db.commit()
        
        # Reload zones in geofencing service
        geofencing_service.reload_zones()
        
        logger.info(f"Uploaded {len(created_zones)} zones from file")
        return {
            "message": f"Successfully uploaded {len(created_zones)} zones",
            "created_zones": created_zones
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"Error uploading zones: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload zones")

@router.get("/zones/geojson")
async def get_all_zones_geojson(db: Session = Depends(get_db)):
    """Get all zones as a GeoJSON FeatureCollection"""
    try:
        zones = db.query(ISAZone).filter(ISAZone.is_active == True).all()
        
        features = []
        for zone in zones:
            try:
                geojson = json.loads(zone.geojson_data)
                # Add zone metadata to properties
                geojson['properties'].update({
                    'zone_id': zone.zone_id,
                    'zone_name': zone.zone_name,
                    'zone_type': zone.zone_type,
                    'max_duration_hours': zone.max_duration_hours
                })
                features.append(geojson)
            except Exception as e:
                logger.error(f"Error processing zone {zone.zone_id}: {e}")
                continue
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
        
    except Exception as e:
        logger.error(f"Error generating GeoJSON: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate GeoJSON") 
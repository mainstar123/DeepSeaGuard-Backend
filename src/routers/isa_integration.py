from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from database.database import get_db
from services.isa_data_service import ISADataService
from services.geofencing_service import GeofencingService

router = APIRouter()
logger = logging.getLogger(__name__)

# This will be injected from main.py
geofencing_service: GeofencingService = None

@router.post("/isa/sync")
async def sync_isa_zones(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Sync ISA zones from ArcGIS services to local database
    This will fetch real ISA data and update the local zones
    """
    try:
        isa_service = ISADataService()
        
        # Run sync in background to avoid timeout
        background_tasks.add_task(run_isa_sync, isa_service, geofencing_service)
        
        return {
            "message": "ISA zone sync started in background",
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error starting ISA sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to start ISA sync")

@router.get("/isa/available-layers")
async def get_available_isa_layers():
    """
    Get list of available ISA ArcGIS layers
    """
    try:
        isa_service = ISADataService()
        layers = isa_service.get_available_layers()
        
        return {
            "layers": layers,
            "total_layers": len(layers)
        }
        
    except Exception as e:
        logger.error(f"Error getting ISA layers: {e}")
        raise HTTPException(status_code=500, detail="Failed to get ISA layers")

@router.get("/isa/ccz-areas")
async def get_ccz_areas():
    """
    Get Clarion Clipperton Zone contract areas from ISA
    """
    try:
        isa_service = ISADataService()
        areas = isa_service.get_ccz_contract_areas()
        
        return {
            "areas": areas,
            "total_areas": len(areas),
            "source": "ISA_ArcGIS"
        }
        
    except Exception as e:
        logger.error(f"Error getting CCZ areas: {e}")
        raise HTTPException(status_code=500, detail="Failed to get CCZ areas")

@router.get("/isa/exploration-areas")
async def get_exploration_areas():
    """
    Get exploration areas from ISA
    """
    try:
        isa_service = ISADataService()
        areas = isa_service.get_exploration_areas()
        
        return {
            "areas": areas,
            "total_areas": len(areas),
            "source": "ISA_ArcGIS"
        }
        
    except Exception as e:
        logger.error(f"Error getting exploration areas: {e}")
        raise HTTPException(status_code=500, detail="Failed to get exploration areas")

@router.get("/isa/protected-areas")
async def get_protected_areas():
    """
    Get protected areas from ISA
    """
    try:
        isa_service = ISADataService()
        areas = isa_service.get_protected_areas()
        
        return {
            "areas": areas,
            "total_areas": len(areas),
            "source": "ISA_ArcGIS"
        }
        
    except Exception as e:
        logger.error(f"Error getting protected areas: {e}")
        raise HTTPException(status_code=500, detail="Failed to get protected areas")

@router.post("/isa/test-connection")
async def test_isa_connection():
    """
    Test connection to ISA ArcGIS services
    """
    try:
        isa_service = ISADataService()
        
        # Test different endpoints
        results = {}
        
        # Test CCZ areas
        try:
            ccz_areas = isa_service.get_ccz_contract_areas()
            results['ccz_areas'] = {
                'status': 'success',
                'count': len(ccz_areas)
            }
        except Exception as e:
            results['ccz_areas'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Test exploration areas
        try:
            exploration_areas = isa_service.get_exploration_areas()
            results['exploration_areas'] = {
                'status': 'success',
                'count': len(exploration_areas)
            }
        except Exception as e:
            results['exploration_areas'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Test protected areas
        try:
            protected_areas = isa_service.get_protected_areas()
            results['protected_areas'] = {
                'status': 'success',
                'count': len(protected_areas)
            }
        except Exception as e:
            results['protected_areas'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Test available layers
        try:
            layers = isa_service.get_available_layers()
            results['available_layers'] = {
                'status': 'success',
                'count': len(layers)
            }
        except Exception as e:
            results['available_layers'] = {
                'status': 'error',
                'error': str(e)
            }
        
        return {
            "connection_test": results,
            "overall_status": "success" if any(r.get('status') == 'success' for r in results.values()) else "error"
        }
        
    except Exception as e:
        logger.error(f"Error testing ISA connection: {e}")
        raise HTTPException(status_code=500, detail="Failed to test ISA connection")

async def run_isa_sync(isa_service: ISADataService, geofencing_service: GeofencingService):
    """
    Run ISA sync in background
    """
    try:
        logger.info("Starting ISA zone sync...")
        result = isa_service.sync_isa_zones_to_database()
        
        # Reload zones in geofencing service
        if geofencing_service:
            geofencing_service.reload_zones()
        
        logger.info(f"ISA sync completed: {result}")
        
    except Exception as e:
        logger.error(f"Error in background ISA sync: {e}") 
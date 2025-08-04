from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
import logging

from database.database import get_db
from models.schemas import TelemetryData, ZoneStatus
from services.compliance_engine import ComplianceEngine
from services.geofencing_service import GeofencingService
from services.websocket_manager import WebSocketManager
from models.schemas import AlertMessage

router = APIRouter()
logger = logging.getLogger(__name__)

# These will be injected from main.py
compliance_engine: ComplianceEngine = None
geofencing_service: GeofencingService = None
websocket_manager: WebSocketManager = None

@router.post("/telemetry/position")
async def process_telemetry(
    telemetry: TelemetryData,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process AUV telemetry and check compliance"""
    try:
        # Check which zones the AUV is currently in
        current_zones = geofencing_service.check_position(
            telemetry.latitude, 
            telemetry.longitude, 
            telemetry.depth
        )
        
        # Process compliance in background
        background_tasks.add_task(
            process_compliance_background,
            telemetry.auv_id,
            telemetry.latitude,
            telemetry.longitude,
            telemetry.depth,
            telemetry.timestamp,
            current_zones
        )
        
        # Send real-time zone status update
        if current_zones:
            zone_status = {
                "auv_id": telemetry.auv_id,
                "current_zones": current_zones,
                "position": {
                    "latitude": telemetry.latitude,
                    "longitude": telemetry.longitude,
                    "depth": telemetry.depth
                },
                "timestamp": telemetry.timestamp
            }
            background_tasks.add_task(
                websocket_manager.send_zone_status_update,
                telemetry.auv_id,
                zone_status
            )
        
        return {
            "message": "Telemetry processed successfully",
            "auv_id": telemetry.auv_id,
            "zones_detected": len(current_zones),
            "timestamp": telemetry.timestamp
        }
        
    except Exception as e:
        logger.error(f"Error processing telemetry: {e}")
        raise HTTPException(status_code=500, detail="Failed to process telemetry")

@router.get("/telemetry/status/{auv_id}")
async def get_auv_status(auv_id: str):
    """Get current status for an AUV"""
    try:
        status = compliance_engine.get_auv_status(auv_id)
        return status
        
    except Exception as e:
        logger.error(f"Error getting AUV status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get AUV status")

@router.get("/telemetry/zones/{auv_id}")
async def get_auv_zones(auv_id: str):
    """Get zones that an AUV is currently in"""
    try:
        status = compliance_engine.get_auv_status(auv_id)
        return {
            "auv_id": auv_id,
            "current_zones": status.get("current_zones", []),
            "total_active_time": status.get("total_active_time", 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting AUV zones: {e}")
        raise HTTPException(status_code=500, detail="Failed to get AUV zones")

@router.post("/telemetry/batch")
async def process_telemetry_batch(
    telemetry_batch: List[TelemetryData],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process multiple telemetry updates at once"""
    try:
        results = []
        
        for telemetry in telemetry_batch:
            # Check zones for each telemetry update
            current_zones = geofencing_service.check_position(
                telemetry.latitude,
                telemetry.longitude,
                telemetry.depth
            )
            
            # Process compliance in background
            background_tasks.add_task(
                process_compliance_background,
                telemetry.auv_id,
                telemetry.latitude,
                telemetry.longitude,
                telemetry.depth,
                telemetry.timestamp,
                current_zones
            )
            
            results.append({
                "auv_id": telemetry.auv_id,
                "zones_detected": len(current_zones),
                "timestamp": telemetry.timestamp
            })
        
        return {
            "message": f"Processed {len(telemetry_batch)} telemetry updates",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error processing telemetry batch: {e}")
        raise HTTPException(status_code=500, detail="Failed to process telemetry batch")

async def process_compliance_background(
    auv_id: str,
    latitude: float,
    longitude: float,
    depth: float,
    timestamp: datetime,
    current_zones: List[Dict]
):
    """Process compliance checks in background"""
    try:
        # Process compliance events
        events = compliance_engine.process_telemetry(
            auv_id, latitude, longitude, depth, timestamp
        )
        
        # Send events via WebSocket
        for event in events:
            await websocket_manager.send_compliance_event(event)
            
            # Create alert for violations and warnings
            if event.get("status") in ["violation", "warning"]:
                alert = AlertMessage(
                    type="compliance_alert",
                    auv_id=auv_id,
                    zone_id=event.get("zone_id"),
                    message=event.get("violation_details", "Compliance alert"),
                    severity=event.get("status"),
                    timestamp=timestamp,
                    data={
                        "event_type": event.get("event_type"),
                        "zone_name": event.get("zone_name"),
                        "duration_minutes": event.get("duration_minutes")
                    }
                )
                await websocket_manager.send_alert(alert)
        
        logger.info(f"Processed {len(events)} compliance events for AUV {auv_id}")
        
    except Exception as e:
        logger.error(f"Error in background compliance processing: {e}")

@router.get("/telemetry/active-auvs")
async def get_active_auvs():
    """Get list of currently active AUVs"""
    try:
        # Get all AUVs that have been tracked recently (last 24 hours)
        active_auvs = list(compliance_engine.auv_tracking.keys())
        
        auv_statuses = []
        for auv_id in active_auvs:
            status = compliance_engine.get_auv_status(auv_id)
            auv_statuses.append({
                "auv_id": auv_id,
                "status": status.get("status"),
                "current_zones": len(status.get("current_zones", [])),
                "total_active_time": status.get("total_active_time", 0)
            })
        
        return {
            "active_auvs": auv_statuses,
            "total_active": len(active_auvs)
        }
        
    except Exception as e:
        logger.error(f"Error getting active AUVs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get active AUVs") 
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from database.database import get_db, ComplianceEvent
from models.schemas import (
    ComplianceEventCreate, 
    ComplianceEventResponse, 
    ComplianceReport,
    Status,
    EventType
)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/compliance/log", response_model=ComplianceEventResponse)
async def log_compliance_event(
    event: ComplianceEventCreate,
    db: Session = Depends(get_db)
):
    """Log a compliance event"""
    try:
        db_event = ComplianceEvent(
            auv_id=event.auv_id,
            zone_id=event.zone_id,
            zone_name=event.zone_name,
            event_type=event.event_type,
            status=event.status,
            latitude=event.latitude,
            longitude=event.longitude,
            depth=event.depth,
            duration_minutes=event.duration_minutes,
            violation_details=event.violation_details
        )
        
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        
        logger.info(f"Compliance event logged: {event.event_type} for AUV {event.auv_id}")
        return db_event
        
    except Exception as e:
        logger.error(f"Error logging compliance event: {e}")
        raise HTTPException(status_code=500, detail="Failed to log compliance event")

@router.get("/compliance/events", response_model=List[ComplianceEventResponse])
async def get_compliance_events(
    auv_id: Optional[str] = Query(None, description="Filter by AUV ID"),
    zone_id: Optional[str] = Query(None, description="Filter by zone ID"),
    event_type: Optional[EventType] = Query(None, description="Filter by event type"),
    status: Optional[Status] = Query(None, description="Filter by status"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    limit: int = Query(100, le=1000, description="Maximum number of events to return"),
    db: Session = Depends(get_db)
):
    """Get compliance events with optional filtering"""
    try:
        query = db.query(ComplianceEvent)
        
        if auv_id:
            query = query.filter(ComplianceEvent.auv_id == auv_id)
        if zone_id:
            query = query.filter(ComplianceEvent.zone_id == zone_id)
        if event_type:
            query = query.filter(ComplianceEvent.event_type == event_type)
        if status:
            query = query.filter(ComplianceEvent.status == status)
        if start_date:
            query = query.filter(ComplianceEvent.timestamp >= start_date)
        if end_date:
            query = query.filter(ComplianceEvent.timestamp <= end_date)
        
        events = query.order_by(ComplianceEvent.timestamp.desc()).limit(limit).all()
        return events
        
    except Exception as e:
        logger.error(f"Error retrieving compliance events: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve compliance events")

@router.get("/compliance/report/{auv_id}", response_model=ComplianceReport)
async def get_compliance_report(
    auv_id: str,
    start_date: Optional[datetime] = Query(None, description="Start date for report"),
    end_date: Optional[datetime] = Query(None, description="End date for report"),
    db: Session = Depends(get_db)
):
    """Generate compliance report for an AUV"""
    try:
        # Default to last 24 hours if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=1)
        if not end_date:
            end_date = datetime.utcnow()
        
        events = db.query(ComplianceEvent).filter(
            ComplianceEvent.auv_id == auv_id,
            ComplianceEvent.timestamp >= start_date,
            ComplianceEvent.timestamp <= end_date
        ).order_by(ComplianceEvent.timestamp).all()
        
        total_violations = len([e for e in events if e.status == Status.VIOLATION])
        total_warnings = len([e for e in events if e.status == Status.WARNING])
        zones_visited = list(set([e.zone_id for e in events]))
        total_time = sum([e.duration_minutes or 0 for e in events])
        
        return ComplianceReport(
            auv_id=auv_id,
            date=start_date.strftime("%Y-%m-%d"),
            total_violations=total_violations,
            total_warnings=total_warnings,
            zones_visited=zones_visited,
            total_time_in_zones=total_time,
            events=events
        )
        
    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate compliance report")

@router.get("/compliance/violations", response_model=List[ComplianceEventResponse])
async def get_violations(
    auv_id: Optional[str] = Query(None, description="Filter by AUV ID"),
    zone_id: Optional[str] = Query(None, description="Filter by zone ID"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    limit: int = Query(100, le=1000, description="Maximum number of violations to return"),
    db: Session = Depends(get_db)
):
    """Get all violations with optional filtering"""
    try:
        query = db.query(ComplianceEvent).filter(ComplianceEvent.status == Status.VIOLATION)
        
        if auv_id:
            query = query.filter(ComplianceEvent.auv_id == auv_id)
        if zone_id:
            query = query.filter(ComplianceEvent.zone_id == zone_id)
        if start_date:
            query = query.filter(ComplianceEvent.timestamp >= start_date)
        if end_date:
            query = query.filter(ComplianceEvent.timestamp <= end_date)
        
        violations = query.order_by(ComplianceEvent.timestamp.desc()).limit(limit).all()
        return violations
        
    except Exception as e:
        logger.error(f"Error retrieving violations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve violations")

@router.get("/compliance/statistics")
async def get_compliance_statistics(
    start_date: Optional[datetime] = Query(None, description="Start date for statistics"),
    end_date: Optional[datetime] = Query(None, description="End date for statistics"),
    db: Session = Depends(get_db)
):
    """Get compliance statistics"""
    try:
        # Default to last 7 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        query = db.query(ComplianceEvent).filter(
            ComplianceEvent.timestamp >= start_date,
            ComplianceEvent.timestamp <= end_date
        )
        
        total_events = query.count()
        violations = query.filter(ComplianceEvent.status == Status.VIOLATION).count()
        warnings = query.filter(ComplianceEvent.status == Status.WARNING).count()
        compliant = query.filter(ComplianceEvent.status == Status.COMPLIANT).count()
        
        # Get unique AUVs and zones
        unique_auvs = db.query(ComplianceEvent.auv_id).distinct().count()
        unique_zones = db.query(ComplianceEvent.zone_id).distinct().count()
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "total_events": total_events,
            "violations": violations,
            "warnings": warnings,
            "compliant": compliant,
            "unique_auvs": unique_auvs,
            "unique_zones": unique_zones,
            "compliance_rate": (compliant / total_events * 100) if total_events > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error generating compliance statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate compliance statistics") 
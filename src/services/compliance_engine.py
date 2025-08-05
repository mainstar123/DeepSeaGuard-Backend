from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from sqlalchemy.orm import Session
from src.database.database import ComplianceEvent, AUVZoneTracking, get_db
from src.models.schemas import Status, EventType
from src.services.geofencing_service import GeofencingService

logger = logging.getLogger(__name__)

class ComplianceEngine:
    def __init__(self, geofencing_service: GeofencingService):
        self.geofencing_service = geofencing_service
        self.auv_tracking: Dict[str, Dict[str, Dict]] = {}  # auv_id -> zone_id -> tracking_data
    
    def process_telemetry(self, auv_id: str, latitude: float, longitude: float, 
                         depth: float, timestamp: datetime) -> List[Dict]:
        """
        Process AUV telemetry and check compliance
        
        Returns:
            List of compliance events generated
        """
        events = []
        
        # Check which zones the AUV is currently in
        current_zones = self.geofencing_service.check_position(latitude, longitude, depth)
        current_zone_ids = {zone['zone_id'] for zone in current_zones}
        
        # Get previous zones for this AUV
        if auv_id not in self.auv_tracking:
            self.auv_tracking[auv_id] = {}
        
        previous_zone_ids = set(self.auv_tracking[auv_id].keys())
        
        # Handle zone entries
        for zone in current_zones:
            zone_id = zone['zone_id']
            if zone_id not in previous_zone_ids:
                # AUV entered this zone
                event = self._handle_zone_entry(auv_id, zone, timestamp)
                if event:
                    events.append(event)
        
        # Handle zone exits
        for zone_id in previous_zone_ids:
            if zone_id not in current_zone_ids:
                # AUV exited this zone
                event = self._handle_zone_exit(auv_id, zone_id, timestamp)
                if event:
                    events.append(event)
        
        # Check for violations in current zones
        for zone in current_zones:
            zone_id = zone['zone_id']
            if zone_id in self.auv_tracking[auv_id]:
                event = self._check_zone_violations(auv_id, zone, timestamp)
                if event:
                    events.append(event)
        
        return events
    
    def _handle_zone_entry(self, auv_id: str, zone: Dict, timestamp: datetime) -> Optional[Dict]:
        """Handle AUV entering a zone"""
        zone_id = zone['zone_id']
        
        # Initialize tracking for this zone
        self.auv_tracking[auv_id][zone_id] = {
            'entry_time': timestamp,
            'zone_name': zone['zone_name'],
            'zone_type': zone['zone_type'],
            'max_duration_hours': zone['max_duration_hours']
        }
        
        # Create entry event
        event = {
            'auv_id': auv_id,
            'zone_id': zone_id,
            'zone_name': zone['zone_name'],
            'event_type': EventType.ENTRY,
            'status': Status.COMPLIANT,
            'timestamp': timestamp,
            'duration_minutes': 0
        }
        
        # Store in database
        self._store_compliance_event(event)
        
        logger.info(f"AUV {auv_id} entered zone {zone_id} ({zone['zone_name']})")
        return event
    
    def _handle_zone_exit(self, auv_id: str, zone_id: str, timestamp: datetime) -> Optional[Dict]:
        """Handle AUV exiting a zone"""
        if auv_id not in self.auv_tracking or zone_id not in self.auv_tracking[auv_id]:
            return None
        
        tracking_data = self.auv_tracking[auv_id][zone_id]
        entry_time = tracking_data['entry_time']
        duration = (timestamp - entry_time).total_seconds() / 60  # minutes
        
        # Create exit event
        event = {
            'auv_id': auv_id,
            'zone_id': zone_id,
            'zone_name': tracking_data['zone_name'],
            'event_type': EventType.EXIT,
            'status': Status.COMPLIANT,
            'timestamp': timestamp,
            'duration_minutes': duration
        }
        
        # Store in database
        self._store_compliance_event(event)
        
        # Remove from tracking
        del self.auv_tracking[auv_id][zone_id]
        
        logger.info(f"AUV {auv_id} exited zone {zone_id} after {duration:.1f} minutes")
        return event
    
    def _check_zone_violations(self, auv_id: str, zone: Dict, timestamp: datetime) -> Optional[Dict]:
        """Check for violations in current zone"""
        zone_id = zone['zone_id']
        tracking_data = self.auv_tracking[auv_id][zone_id]
        
        entry_time = tracking_data['entry_time']
        max_duration_hours = tracking_data['max_duration_hours']
        
        current_duration = (timestamp - entry_time).total_seconds() / 3600  # hours
        current_duration_minutes = current_duration * 60
        
        # Check for violations
        if current_duration >= max_duration_hours:
            # Violation occurred
            event = {
                'auv_id': auv_id,
                'zone_id': zone_id,
                'zone_name': zone['zone_name'],
                'event_type': EventType.VIOLATION,
                'status': Status.VIOLATION,
                'timestamp': timestamp,
                'duration_minutes': current_duration_minutes,
                'violation_details': f"Exceeded maximum duration of {max_duration_hours} hours in {zone['zone_type']} zone"
            }
            
            self._store_compliance_event(event)
            logger.warning(f"VIOLATION: AUV {auv_id} exceeded time limit in zone {zone_id}")
            return event
        
        elif current_duration >= max_duration_hours * 0.8:  # 80% of max duration
            # Warning threshold
            event = {
                'auv_id': auv_id,
                'zone_id': zone_id,
                'zone_name': zone['zone_name'],
                'event_type': EventType.WARNING,
                'status': Status.WARNING,
                'timestamp': timestamp,
                'duration_minutes': current_duration_minutes,
                'violation_details': f"Approaching time limit in {zone['zone_type']} zone"
            }
            
            self._store_compliance_event(event)
            logger.warning(f"WARNING: AUV {auv_id} approaching time limit in zone {zone_id}")
            return event
        
        return None
    
    def _store_compliance_event(self, event: Dict):
        """Store compliance event in database"""
        try:
            db = next(get_db())
            db_event = ComplianceEvent(
                auv_id=event['auv_id'],
                zone_id=event['zone_id'],
                zone_name=event['zone_name'],
                event_type=event['event_type'],
                status=event['status'],
                latitude=0,  # Will be updated with actual position
                longitude=0,
                depth=0,
                timestamp=event['timestamp'],
                duration_minutes=event.get('duration_minutes'),
                violation_details=event.get('violation_details')
            )
            db.add(db_event)
            db.commit()
        except Exception as e:
            logger.error(f"Error storing compliance event: {e}")
    
    def get_auv_status(self, auv_id: str) -> Dict:
        """Get current status for an AUV"""
        if auv_id not in self.auv_tracking:
            return {
                'auv_id': auv_id,
                'current_zones': [],
                'status': Status.COMPLIANT,
                'total_active_time': 0
            }
        
        current_zones = []
        total_active_time = 0
        
        for zone_id, tracking_data in self.auv_tracking[auv_id].items():
            entry_time = tracking_data['entry_time']
            current_duration = (datetime.utcnow() - entry_time).total_seconds() / 60  # minutes
            total_active_time += current_duration
            
            zone_status = {
                'zone_id': zone_id,
                'zone_name': tracking_data['zone_name'],
                'zone_type': tracking_data['zone_type'],
                'entry_time': entry_time,
                'current_duration_minutes': current_duration,
                'max_duration_hours': tracking_data['max_duration_hours'],
                'status': self._get_zone_status(current_duration, tracking_data['max_duration_hours'])
            }
            current_zones.append(zone_status)
        
        overall_status = Status.COMPLIANT
        if any(zone['status'] == Status.VIOLATION for zone in current_zones):
            overall_status = Status.VIOLATION
        elif any(zone['status'] == Status.WARNING for zone in current_zones):
            overall_status = Status.WARNING
        
        return {
            'auv_id': auv_id,
            'current_zones': current_zones,
            'status': overall_status,
            'total_active_time': total_active_time
        }
    
    def _get_zone_status(self, current_duration_minutes: float, max_duration_hours: float) -> Status:
        """Determine status based on current duration vs max duration"""
        current_hours = current_duration_minutes / 60
        
        if current_hours >= max_duration_hours:
            return Status.VIOLATION
        elif current_hours >= max_duration_hours * 0.8:
            return Status.WARNING
        else:
            return Status.COMPLIANT
    
    def get_compliance_report(self, auv_id: str, start_date: datetime, end_date: datetime) -> Dict:
        """Generate compliance report for an AUV"""
        try:
            db = next(get_db())
            events = db.query(ComplianceEvent).filter(
                ComplianceEvent.auv_id == auv_id,
                ComplianceEvent.timestamp >= start_date,
                ComplianceEvent.timestamp <= end_date
            ).order_by(ComplianceEvent.timestamp).all()
            
            total_violations = len([e for e in events if e.status == Status.VIOLATION])
            total_warnings = len([e for e in events if e.status == Status.WARNING])
            zones_visited = list(set([e.zone_id for e in events]))
            total_time = sum([e.duration_minutes or 0 for e in events])
            
            return {
                'auv_id': auv_id,
                'start_date': start_date,
                'end_date': end_date,
                'total_violations': total_violations,
                'total_warnings': total_warnings,
                'zones_visited': zones_visited,
                'total_time_in_zones': total_time,
                'events': events
            }
            
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            return {} 
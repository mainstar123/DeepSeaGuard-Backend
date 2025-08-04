from celery import current_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import logging

from core.celery_app import celery_app
from database.database import get_db, ComplianceEvent, AUVZoneTracking
from models.schemas import Status, EventType
from services.compliance_engine import ComplianceEngine
from services.geofencing_service import GeofencingService
from services.websocket_manager import WebSocketManager
from config.settings import settings

logger = get_task_logger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_telemetry_async(self, auv_id: str, latitude: float, longitude: float, 
                           depth: float, timestamp: str):
    """Process AUV telemetry asynchronously with Celery"""
    try:
        # Convert timestamp string to datetime
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Initialize services
        geofencing_service = GeofencingService()
        compliance_engine = ComplianceEngine(geofencing_service)
        
        # Process compliance
        events = compliance_engine.process_telemetry(
            auv_id, latitude, longitude, depth, timestamp
        )
        
        # Send WebSocket notifications for each event
        for event in events:
            send_compliance_notification.delay(event)
        
        # Update task progress
        current_task.update_state(
            state='SUCCESS',
            meta={
                'auv_id': auv_id,
                'events_processed': len(events),
                'timestamp': timestamp.isoformat()
            }
        )
        
        logger.info(f"Processed telemetry for AUV {auv_id}: {len(events)} events")
        return {
            'auv_id': auv_id,
            'events_processed': len(events),
            'events': events
        }
        
    except Exception as exc:
        logger.error(f"Error processing telemetry for AUV {auv_id}: {exc}")
        # Retry the task
        raise self.retry(exc=exc, countdown=60)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def check_all_auv_compliance(self):
    """Check compliance for all active AUVs"""
    try:
        db = next(get_db())
        
        # Get all active AUV tracking records
        active_tracking = db.query(AUVZoneTracking).filter(
            AUVZoneTracking.is_active == True,
            AUVZoneTracking.exit_time.is_(None)
        ).all()
        
        violations_found = 0
        warnings_found = 0
        
        for tracking in active_tracking:
            # Check if AUV has exceeded time limits
            entry_time = tracking.entry_time
            current_time = datetime.utcnow()
            duration_hours = (current_time - entry_time).total_seconds() / 3600
            
            # Get zone info
            zone = db.query(ISAZone).filter(
                ISAZone.zone_id == tracking.zone_id
            ).first()
            
            if zone:
                max_duration = zone.max_duration_hours
                
                if duration_hours >= max_duration:
                    # Create violation event
                    violation_event = {
                        'auv_id': tracking.auv_id,
                        'zone_id': tracking.zone_id,
                        'zone_name': zone.zone_name,
                        'event_type': EventType.VIOLATION,
                        'status': Status.VIOLATION,
                        'timestamp': current_time,
                        'duration_minutes': duration_hours * 60,
                        'violation_details': f"Exceeded maximum duration of {max_duration} hours in {zone.zone_type} zone"
                    }
                    
                    # Store violation
                    db_event = ComplianceEvent(**violation_event)
                    db.add(db_event)
                    violations_found += 1
                    
                    # Send notification
                    send_compliance_notification.delay(violation_event)
                    
                elif duration_hours >= max_duration * (settings.WARNING_THRESHOLD_PERCENT / 100):
                    # Create warning event
                    warning_event = {
                        'auv_id': tracking.auv_id,
                        'zone_id': tracking.zone_id,
                        'zone_name': zone.zone_name,
                        'event_type': EventType.WARNING,
                        'status': Status.WARNING,
                        'timestamp': current_time,
                        'duration_minutes': duration_hours * 60,
                        'violation_details': f"Approaching time limit in {zone.zone_type} zone"
                    }
                    
                    # Store warning
                    db_event = ComplianceEvent(**warning_event)
                    db.add(db_event)
                    warnings_found += 1
                    
                    # Send notification
                    send_compliance_notification.delay(warning_event)
        
        db.commit()
        db.close()
        
        logger.info(f"Compliance check completed: {violations_found} violations, {warnings_found} warnings")
        return {
            'violations_found': violations_found,
            'warnings_found': warnings_found,
            'total_checked': len(active_tracking)
        }
        
    except Exception as exc:
        logger.error(f"Error in compliance check: {exc}")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def send_compliance_notification(self, event: Dict[str, Any]):
    """Send compliance notification via WebSocket"""
    try:
        # This would integrate with your WebSocket manager
        # For now, we'll just log the notification
        logger.info(f"Compliance notification: {event['event_type']} for AUV {event['auv_id']}")
        
        # In a real implementation, you would:
        # 1. Get the WebSocket manager instance
        # 2. Send the notification to all connected clients
        # 3. Handle any delivery failures
        
        return {
            'notification_sent': True,
            'event_type': event['event_type'],
            'auv_id': event['auv_id']
        }
        
    except Exception as exc:
        logger.error(f"Error sending compliance notification: {exc}")
        raise self.retry(exc=exc, countdown=60)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def generate_daily_compliance_report(self, date: Optional[str] = None):
    """Generate daily compliance report"""
    try:
        if date is None:
            date = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        db = next(get_db())
        
        # Parse date
        start_date = datetime.strptime(date, '%Y-%m-%d')
        end_date = start_date + timedelta(days=1)
        
        # Get all events for the date
        events = db.query(ComplianceEvent).filter(
            ComplianceEvent.timestamp >= start_date,
            ComplianceEvent.timestamp < end_date
        ).all()
        
        # Calculate statistics
        total_events = len(events)
        violations = len([e for e in events if e.status == Status.VIOLATION])
        warnings = len([e for e in events if e.status == Status.WARNING])
        compliant = len([e for e in events if e.status == Status.COMPLIANT])
        
        # Get unique AUVs and zones
        unique_auvs = list(set([e.auv_id for e in events]))
        unique_zones = list(set([e.zone_id for e in events]))
        
        # Generate report
        report = {
            'date': date,
            'total_events': total_events,
            'violations': violations,
            'warnings': warnings,
            'compliant': compliant,
            'unique_auvs': len(unique_auvs),
            'unique_zones': len(unique_zones),
            'compliance_rate': (compliant / total_events * 100) if total_events > 0 else 0,
            'events_by_type': {
                'entry': len([e for e in events if e.event_type == EventType.ENTRY]),
                'exit': len([e for e in events if e.event_type == EventType.EXIT]),
                'violation': len([e for e in events if e.event_type == EventType.VIOLATION]),
                'warning': len([e for e in events if e.event_type == EventType.WARNING])
            }
        }
        
        db.close()
        
        # Store report (you could save to database or file)
        logger.info(f"Daily report generated for {date}: {report}")
        
        return report
        
    except Exception as exc:
        logger.error(f"Error generating daily report: {exc}")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def process_batch_telemetry(self, telemetry_batch: List[Dict[str, Any]]):
    """Process multiple telemetry updates in batch"""
    try:
        results = []
        
        for i, telemetry in enumerate(telemetry_batch):
            # Update progress
            current_task.update_state(
                state='PROGRESS',
                meta={
                    'current': i + 1,
                    'total': len(telemetry_batch),
                    'progress': ((i + 1) / len(telemetry_batch)) * 100
                }
            )
            
            # Process individual telemetry
            result = process_telemetry_async.delay(
                telemetry['auv_id'],
                telemetry['latitude'],
                telemetry['longitude'],
                telemetry['depth'],
                telemetry['timestamp']
            )
            
            results.append({
                'telemetry_index': i,
                'task_id': result.id,
                'auv_id': telemetry['auv_id']
            })
        
        logger.info(f"Batch processing completed: {len(telemetry_batch)} telemetry points")
        return {
            'batch_size': len(telemetry_batch),
            'tasks_created': len(results),
            'results': results
        }
        
    except Exception as exc:
        logger.error(f"Error in batch telemetry processing: {exc}")
        raise self.retry(exc=exc, countdown=60)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def cleanup_old_compliance_events(self, days_to_keep: int = 90):
    """Clean up old compliance events"""
    try:
        db = next(get_db())
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Count events to be deleted
        events_to_delete = db.query(ComplianceEvent).filter(
            ComplianceEvent.timestamp < cutoff_date
        ).count()
        
        # Delete old events
        db.query(ComplianceEvent).filter(
            ComplianceEvent.timestamp < cutoff_date
        ).delete()
        
        db.commit()
        db.close()
        
        logger.info(f"Cleaned up {events_to_delete} old compliance events")
        return {
            'events_deleted': events_to_delete,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up old events: {exc}")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def export_compliance_data(self, start_date: str, end_date: str, format: str = 'json'):
    """Export compliance data for a date range"""
    try:
        db = next(get_db())
        
        # Parse dates
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        
        # Get events
        events = db.query(ComplianceEvent).filter(
            ComplianceEvent.timestamp >= start,
            ComplianceEvent.timestamp < end
        ).all()
        
        # Convert to dict
        event_data = []
        for event in events:
            event_data.append({
                'id': event.id,
                'auv_id': event.auv_id,
                'zone_id': event.zone_id,
                'zone_name': event.zone_name,
                'event_type': event.event_type,
                'status': event.status,
                'latitude': event.latitude,
                'longitude': event.longitude,
                'depth': event.depth,
                'timestamp': event.timestamp.isoformat(),
                'duration_minutes': event.duration_minutes,
                'violation_details': event.violation_details
            })
        
        db.close()
        
        # Export based on format
        if format == 'json':
            return {
                'format': 'json',
                'start_date': start_date,
                'end_date': end_date,
                'total_events': len(event_data),
                'data': event_data
            }
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
    except Exception as exc:
        logger.error(f"Error exporting compliance data: {exc}")
        raise self.retry(exc=exc, countdown=60) 
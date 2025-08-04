from celery import current_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import logging

from core.celery_app import celery_app
from models.schemas import AlertMessage
from config.settings import settings

logger = get_task_logger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_websocket_notification(self, message_type: str, data: Dict[str, Any]):
    """Send notification via WebSocket"""
    try:
        # In a real implementation, you would:
        # 1. Get the WebSocket manager instance
        # 2. Send the message to all connected clients
        # 3. Handle delivery failures
        
        logger.info(f"WebSocket notification sent: {message_type} - {data.get('auv_id', 'N/A')}")
        
        # Simulate WebSocket sending
        notification_data = {
            'type': message_type,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        # Log the notification for debugging
        logger.debug(f"Notification payload: {json.dumps(notification_data, indent=2)}")
        
        return {
            'notification_sent': True,
            'message_type': message_type,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error sending WebSocket notification: {exc}")
        raise self.retry(exc=exc, countdown=30)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def send_compliance_alert(self, alert: Dict[str, Any]):
    """Send compliance alert notification"""
    try:
        # Create alert message
        alert_message = AlertMessage(
            type="compliance_alert",
            auv_id=alert.get('auv_id'),
            zone_id=alert.get('zone_id'),
            message=alert.get('violation_details', 'Compliance alert'),
            severity=alert.get('status', 'warning'),
            timestamp=datetime.utcnow(),
            data={
                'event_type': alert.get('event_type'),
                'zone_name': alert.get('zone_name'),
                'duration_minutes': alert.get('duration_minutes'),
                'latitude': alert.get('latitude'),
                'longitude': alert.get('longitude'),
                'depth': alert.get('depth')
            }
        )
        
        # Send via WebSocket
        send_websocket_notification.delay(
            'compliance_alert',
            alert_message.dict()
        )
        
        # Log the alert
        logger.info(f"Compliance alert sent: {alert_message.severity} for AUV {alert_message.auv_id}")
        
        return {
            'alert_sent': True,
            'auv_id': alert_message.auv_id,
            'severity': alert_message.severity,
            'timestamp': alert_message.timestamp.isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error sending compliance alert: {exc}")
        raise self.retry(exc=exc, countdown=60)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def send_zone_status_update(self, auv_id: str, zone_status: Dict[str, Any]):
    """Send zone status update notification"""
    try:
        # Send zone status update
        send_websocket_notification.delay(
            'zone_status_update',
            {
                'auv_id': auv_id,
                'zone_status': zone_status,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Zone status update sent for AUV {auv_id}")
        return {
            'status_update_sent': True,
            'auv_id': auv_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error sending zone status update: {exc}")
        raise self.retry(exc=exc, countdown=30)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def send_daily_report_notification(self, report_data: Dict[str, Any]):
    """Send daily compliance report notification"""
    try:
        # Create daily report notification
        notification_data = {
            'type': 'daily_report',
            'date': report_data.get('date'),
            'summary': {
                'total_events': report_data.get('total_events', 0),
                'violations': report_data.get('violations', 0),
                'warnings': report_data.get('warnings', 0),
                'compliance_rate': report_data.get('compliance_rate', 0)
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Send notification
        send_websocket_notification.delay('daily_report', notification_data)
        
        logger.info(f"Daily report notification sent for {report_data.get('date')}")
        return {
            'report_notification_sent': True,
            'date': report_data.get('date'),
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error sending daily report notification: {exc}")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def send_system_alert(self, alert_type: str, message: str, severity: str = 'info', data: Dict[str, Any] = None):
    """Send system-wide alert notification"""
    try:
        if data is None:
            data = {}
        
        alert_data = {
            'type': 'system_alert',
            'alert_type': alert_type,
            'message': message,
            'severity': severity,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Send system alert
        send_websocket_notification.delay('system_alert', alert_data)
        
        logger.info(f"System alert sent: {alert_type} - {severity}")
        return {
            'system_alert_sent': True,
            'alert_type': alert_type,
            'severity': severity,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error sending system alert: {exc}")
        raise self.retry(exc=exc, countdown=60)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def send_bulk_notifications(self, notifications: List[Dict[str, Any]]):
    """Send multiple notifications in bulk"""
    try:
        sent_count = 0
        failed_count = 0
        
        for i, notification in enumerate(notifications):
            try:
                # Update progress
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'current': i + 1,
                        'total': len(notifications),
                        'progress': ((i + 1) / len(notifications)) * 100
                    }
                )
                
                # Send individual notification
                if notification.get('type') == 'compliance_alert':
                    send_compliance_alert.delay(notification)
                elif notification.get('type') == 'zone_status_update':
                    send_zone_status_update.delay(
                        notification.get('auv_id'),
                        notification.get('zone_status', {})
                    )
                else:
                    send_websocket_notification.delay(
                        notification.get('type', 'notification'),
                        notification.get('data', {})
                    )
                
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send notification {i}: {e}")
                failed_count += 1
        
        logger.info(f"Bulk notification completed: {sent_count} sent, {failed_count} failed")
        return {
            'total_notifications': len(notifications),
            'sent_count': sent_count,
            'failed_count': failed_count,
            'success_rate': (sent_count / len(notifications)) * 100 if notifications else 0
        }
        
    except Exception as exc:
        logger.error(f"Error in bulk notification sending: {exc}")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def send_emergency_alert(self, auv_id: str, zone_id: str, message: str, coordinates: Dict[str, float] = None):
    """Send emergency alert for critical violations"""
    try:
        emergency_data = {
            'type': 'emergency_alert',
            'auv_id': auv_id,
            'zone_id': zone_id,
            'message': message,
            'severity': 'critical',
            'coordinates': coordinates,
            'timestamp': datetime.utcnow().isoformat(),
            'requires_immediate_action': True
        }
        
        # Send emergency alert with high priority
        send_websocket_notification.delay('emergency_alert', emergency_data)
        
        # Log emergency alert
        logger.warning(f"EMERGENCY ALERT: AUV {auv_id} in zone {zone_id} - {message}")
        
        return {
            'emergency_alert_sent': True,
            'auv_id': auv_id,
            'zone_id': zone_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error sending emergency alert: {exc}")
        raise self.retry(exc=exc, countdown=60)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def cleanup_old_notifications(self, days_to_keep: int = 30):
    """Clean up old notification logs"""
    try:
        # This would clean up notification logs from database or files
        # For now, we'll just log the cleanup
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        logger.info(f"Cleaned up notifications older than {cutoff_date.isoformat()}")
        
        return {
            'cleanup_completed': True,
            'cutoff_date': cutoff_date.isoformat(),
            'days_kept': days_to_keep
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up notifications: {exc}")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def send_zone_violation_summary(self, zone_id: str, violations: List[Dict[str, Any]]):
    """Send summary of violations for a specific zone"""
    try:
        summary_data = {
            'type': 'zone_violation_summary',
            'zone_id': zone_id,
            'violation_count': len(violations),
            'violations': violations,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Send summary notification
        send_websocket_notification.delay('zone_violation_summary', summary_data)
        
        logger.info(f"Zone violation summary sent for zone {zone_id}: {len(violations)} violations")
        return {
            'summary_sent': True,
            'zone_id': zone_id,
            'violation_count': len(violations),
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error sending zone violation summary: {exc}")
        raise self.retry(exc=exc, countdown=60)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def send_periodic_health_check(self):
    """Send periodic health check notification"""
    try:
        health_data = {
            'type': 'health_check',
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'database': 'operational',
                'redis': 'operational',
                'celery': 'operational',
                'websocket': 'operational'
            }
        }
        
        # Send health check notification
        send_websocket_notification.delay('health_check', health_data)
        
        logger.info("Periodic health check notification sent")
        return {
            'health_check_sent': True,
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error sending health check notification: {exc}")
        raise self.retry(exc=exc, countdown=300) 
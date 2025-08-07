"""
Alert Management Microservice
Handles real-time alert generation and distribution across multiple channels
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

import aiohttp
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import text

from src.database.database import get_database
from src.utils.logging_config import setup_logging

# Setup logging
logger = setup_logging(__name__)

app = FastAPI(
    title="DeepSeaGuard Alert Service",
    description="Real-time alert generation and distribution microservice",
    version="2.0.0"
)

class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(str, Enum):
    GEOFENCE_VIOLATION = "geofence_violation"
    COMPLIANCE_VIOLATION = "compliance_violation"
    SYSTEM_ALERT = "system_alert"
    BATTERY_LOW = "battery_low"
    DEPTH_LIMIT = "depth_limit"
    SPEED_LIMIT = "speed_limit"
    MISSION_TIMEOUT = "mission_timeout"
    CUSTOM = "custom"

class AlertChannel(str, Enum):
    WEBSOCKET = "websocket"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"

class Alert(BaseModel):
    alert_id: str
    auv_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    channels: List[AlertChannel]
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

class AlertRequest(BaseModel):
    auv_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    details: Dict[str, Any]
    channels: List[AlertChannel] = [AlertChannel.WEBSOCKET]

class AlertResponse(BaseModel):
    alert_id: str
    status: str
    sent_channels: List[str]
    failed_channels: List[str]
    timestamp: datetime

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_metadata: Dict[WebSocket, Dict] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_metadata[websocket] = {
            "client_id": client_id,
            "connected_at": datetime.now(),
            "last_activity": datetime.now()
        }
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            if websocket in self.connection_metadata:
                del self.connection_metadata[websocket]
        logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")
        
    async def broadcast_alert(self, alert: Alert):
        """Broadcast alert to all connected WebSocket clients"""
        if not self.active_connections:
            return
            
        message = {
            "type": "alert",
            "alert_id": alert.alert_id,
            "auv_id": alert.auv_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "details": alert.details,
            "timestamp": alert.timestamp.isoformat()
        }
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
                self.connection_metadata[connection]["last_activity"] = datetime.now()
            except Exception as e:
                logger.error(f"Error sending alert to WebSocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

class AlertService:
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.websocket_manager = WebSocketManager()
        self.performance_metrics = {
            "total_alerts": 0,
            "alerts_sent": 0,
            "alerts_failed": 0,
            "avg_response_time": 0.0,
            "active_connections": 0
        }
        self.db = None
        self.alert_counter = 0
        
    async def initialize(self):
        """Initialize the alert service"""
        logger.info("Initializing Alert Service")
        
        # Initialize database connection
        self.db = await get_database()
        
        # Start background tasks
        asyncio.create_task(self.cleanup_old_alerts())
        asyncio.create_task(self.update_performance_metrics())
        asyncio.create_task(self.sync_alerts_to_database())
        
        logger.info("Alert Service initialized successfully")
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID"""
        self.alert_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"alert_{timestamp}_{self.alert_counter:06d}"
    
    async def create_alert(self, request: AlertRequest) -> AlertResponse:
        """Create and distribute a new alert"""
        start_time = datetime.now()
        
        try:
            # Generate alert ID
            alert_id = self._generate_alert_id()
            
            # Create alert object
            alert = Alert(
                alert_id=alert_id,
                auv_id=request.auv_id,
                alert_type=request.alert_type,
                severity=request.severity,
                title=request.title,
                message=request.message,
                details=request.details,
                timestamp=datetime.now(),
                channels=request.channels
            )
            
            # Store alert
            self.alerts[alert_id] = alert
            self.alert_history.append(alert)
            
            # Distribute alert to channels
            sent_channels = []
            failed_channels = []
            
            for channel in request.channels:
                try:
                    if channel == AlertChannel.WEBSOCKET:
                        await self.websocket_manager.broadcast_alert(alert)
                        sent_channels.append(channel)
                    elif channel == AlertChannel.EMAIL:
                        await self._send_email_alert(alert)
                        sent_channels.append(channel)
                    elif channel == AlertChannel.SMS:
                        await self._send_sms_alert(alert)
                        sent_channels.append(channel)
                    elif channel == AlertChannel.WEBHOOK:
                        await self._send_webhook_alert(alert)
                        sent_channels.append(channel)
                    elif channel == AlertChannel.SLACK:
                        await self._send_slack_alert(alert)
                        sent_channels.append(channel)
                except Exception as e:
                    logger.error(f"Failed to send alert via {channel}: {e}")
                    failed_channels.append(channel)
            
            # Update performance metrics
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self.performance_metrics["total_alerts"] += 1
            self.performance_metrics["alerts_sent"] += len(sent_channels)
            self.performance_metrics["alerts_failed"] += len(failed_channels)
            self.performance_metrics["avg_response_time"] = (
                (self.performance_metrics["avg_response_time"] * (self.performance_metrics["total_alerts"] - 1) + response_time) 
                / self.performance_metrics["total_alerts"]
            )
            
            # Create response
            response = AlertResponse(
                alert_id=alert_id,
                status="success" if not failed_channels else "partial_success",
                sent_channels=sent_channels,
                failed_channels=failed_channels,
                timestamp=datetime.now()
            )
            
            logger.info(f"Alert {alert_id} created and distributed in {response_time:.2f}ms")
            return response
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            raise HTTPException(status_code=500, detail=f"Alert creation failed: {str(e)}")
    
    async def _send_email_alert(self, alert: Alert):
        """Send alert via email"""
        # In a real implementation, this would use an email service
        # For now, just log the email alert
        logger.info(f"Email alert sent: {alert.title} to AUV {alert.auv_id}")
        await asyncio.sleep(0.1)  # Simulate email sending
    
    async def _send_sms_alert(self, alert: Alert):
        """Send alert via SMS"""
        # In a real implementation, this would use an SMS service
        logger.info(f"SMS alert sent: {alert.title} to AUV {alert.auv_id}")
        await asyncio.sleep(0.1)  # Simulate SMS sending
    
    async def _send_webhook_alert(self, alert: Alert):
        """Send alert via webhook"""
        # In a real implementation, this would send to configured webhooks
        logger.info(f"Webhook alert sent: {alert.title} to AUV {alert.auv_id}")
        await asyncio.sleep(0.1)  # Simulate webhook sending
    
    async def _send_slack_alert(self, alert: Alert):
        """Send alert via Slack"""
        # In a real implementation, this would use Slack API
        logger.info(f"Slack alert sent: {alert.title} to AUV {alert.auv_id}")
        await asyncio.sleep(0.1)  # Simulate Slack sending
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now()
        
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return True
    
    async def get_alerts(self, auv_id: Optional[str] = None, severity: Optional[AlertSeverity] = None, 
                        hours: int = 24) -> List[Alert]:
        """Get alerts with optional filtering"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_alerts = []
        for alert in self.alert_history:
            if alert.timestamp < cutoff_time:
                continue
            if auv_id and alert.auv_id != auv_id:
                continue
            if severity and alert.severity != severity:
                continue
            filtered_alerts.append(alert)
        
        # Sort by timestamp (newest first)
        filtered_alerts.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered_alerts
    
    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get a specific alert by ID"""
        return self.alerts.get(alert_id)
    
    async def get_performance_metrics(self) -> Dict:
        """Get performance metrics"""
        metrics = self.performance_metrics.copy()
        metrics["active_connections"] = len(self.websocket_manager.active_connections)
        return metrics
    
    async def cleanup_old_alerts(self):
        """Clean up old alerts"""
        while True:
            try:
                cutoff_time = datetime.now() - timedelta(days=7)
                
                # Clean up alert history
                self.alert_history = [
                    alert for alert in self.alert_history
                    if alert.timestamp > cutoff_time
                ]
                
                # Clean up active alerts
                old_alert_ids = [
                    alert_id for alert_id, alert in self.alerts.items()
                    if alert.timestamp < cutoff_time
                ]
                for alert_id in old_alert_ids:
                    del self.alerts[alert_id]
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
    
    async def update_performance_metrics(self):
        """Update performance metrics periodically"""
        while True:
            try:
                # Reset counters periodically
                if self.performance_metrics["total_alerts"] > 10000:
                    self.performance_metrics["total_alerts"] = 0
                    self.performance_metrics["alerts_sent"] = 0
                    self.performance_metrics["alerts_failed"] = 0
                    self.performance_metrics["avg_response_time"] = 0.0
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(300)
    
    async def sync_alerts_to_database(self):
        """Sync alerts to database periodically"""
        while True:
            try:
                if self.db:
                    # Sync new alerts to database
                    for alert in self.alert_history:
                        # Insert into alerts table
                        query = text("""
                            INSERT INTO alerts 
                            (alert_id, auv_id, alert_type, severity, title, message, details, timestamp, acknowledged)
                            VALUES (:alert_id, :auv_id, :alert_type, :severity, :title, :message, :details, :timestamp, :acknowledged)
                            ON CONFLICT DO NOTHING
                        """)
                        
                        await self.db.execute(query, {
                            "alert_id": alert.alert_id,
                            "auv_id": alert.auv_id,
                            "alert_type": alert.alert_type,
                            "severity": alert.severity,
                            "title": alert.title,
                            "message": alert.message,
                            "details": json.dumps(alert.details),
                            "timestamp": alert.timestamp,
                            "acknowledged": alert.acknowledged
                        })
                
                await asyncio.sleep(60)  # Run every minute
                
            except Exception as e:
                logger.error(f"Error syncing to database: {e}")
                await asyncio.sleep(60)

# Global service instance
alert_service = AlertService()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    await alert_service.initialize()

@app.post("/alerts", response_model=AlertResponse)
async def create_alert(request: AlertRequest):
    """Create and distribute a new alert"""
    return await alert_service.create_alert(request)

@app.get("/alerts")
async def get_alerts(
    auv_id: Optional[str] = None,
    severity: Optional[AlertSeverity] = None,
    hours: int = 24
):
    """Get alerts with optional filtering"""
    alerts = await alert_service.get_alerts(auv_id, severity, hours)
    return {"alerts": [alert.dict() for alert in alerts]}

@app.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Get a specific alert by ID"""
    alert = await alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, acknowledged_by: str):
    """Acknowledge an alert"""
    success = await alert_service.acknowledge_alert(alert_id, acknowledged_by)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": f"Alert {alert_id} acknowledged successfully"}

@app.get("/metrics")
async def get_metrics():
    """Get performance metrics"""
    return await alert_service.get_performance_metrics()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "alert",
        "active_connections": len(alert_service.websocket_manager.active_connections),
        "total_alerts": alert_service.performance_metrics["total_alerts"],
        "timestamp": datetime.now()
    }

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time alerts"""
    await alert_service.websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            # Could handle client messages here (e.g., acknowledgments)
    except WebSocketDisconnect:
        alert_service.websocket_manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004) 
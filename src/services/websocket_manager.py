from fastapi import WebSocket
from typing import List, Dict, Any
import json
import logging
from datetime import datetime
from src.models.schemas import AlertMessage

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    def _serialize_datetime(self, obj):
        """Helper function to serialize datetime objects for JSON"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._serialize_datetime(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime(item) for item in obj]
        else:
            return obj
    
    async def connect(self, websocket: WebSocket):
        """Connect a new WebSocket client"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket client"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all connected WebSocket clients"""
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_alert(self, alert: AlertMessage):
        """Send an alert message to all connected clients"""
        alert_dict = {
            "type": alert.type,
            "auv_id": alert.auv_id,
            "zone_id": alert.zone_id,
            "message": alert.message,
            "severity": alert.severity,
            "timestamp": alert.timestamp.isoformat(),
            "data": alert.data
        }
        
        message = json.dumps(alert_dict)
        await self.broadcast(message)
        logger.info(f"Alert sent: {alert.message}")
    
    async def send_compliance_event(self, event: Dict):
        """Send a compliance event to all connected clients"""
        event_dict = {
            "type": "compliance_event",
            "auv_id": event.get("auv_id"),
            "zone_id": event.get("zone_id"),
            "zone_name": event.get("zone_name"),
            "event_type": event.get("event_type"),
            "status": event.get("status"),
            "timestamp": event.get("timestamp").isoformat() if event.get("timestamp") else None,
            "duration_minutes": event.get("duration_minutes"),
            "violation_details": event.get("violation_details")
        }
        
        message = json.dumps(event_dict)
        await self.broadcast(message)
        logger.info(f"Compliance event sent: {event.get('event_type')} for AUV {event.get('auv_id')}")
    
    async def send_zone_status_update(self, auv_id: str, zone_status: Dict):
        """Send zone status update to all connected clients"""
        # Serialize the zone_status to handle datetime objects
        serialized_zone_status = self._serialize_datetime(zone_status)
        
        status_dict = {
            "type": "zone_status_update",
            "auv_id": auv_id,
            "zone_status": serialized_zone_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        message = json.dumps(status_dict)
        await self.broadcast(message)
        logger.info(f"Zone status update sent for AUV {auv_id}")
    
    def get_connection_count(self) -> int:
        """Get the number of active WebSocket connections"""
        return len(self.active_connections) 
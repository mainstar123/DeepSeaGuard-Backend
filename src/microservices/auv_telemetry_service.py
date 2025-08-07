"""
AUV Telemetry Microservice
Handles AUV telemetry ingestion and state management
"""
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import pika
import aioredis
from src.core.logging import get_logger, LoggerMixin
from src.core.monitoring import performance_monitor
from src.config.settings import settings

logger = get_logger(__name__)


class TelemetryData(BaseModel):
    """AUV telemetry data model"""
    auv_id: str = Field(..., description="AUV identifier")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    depth: float = Field(..., ge=0, description="Depth in meters")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    speed: Optional[float] = Field(None, ge=0, description="Speed in knots")
    heading: Optional[float] = Field(None, ge=0, le=360, description="Heading in degrees")
    battery_level: Optional[float] = Field(None, ge=0, le=100, description="Battery level percentage")
    status: Optional[str] = Field("active", description="AUV status")


class AUVState(BaseModel):
    """AUV state model"""
    auv_id: str
    position: Dict[str, float]
    last_update: datetime
    status: str
    battery_level: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None


class AUVTelemetryService(LoggerMixin):
    """AUV Telemetry Service with RabbitMQ and Redis integration"""
    
    def __init__(self):
        super().__init__()
        self.redis_client: Optional[aioredis.Redis] = None
        self.rabbitmq_connection: Optional[pika.BlockingConnection] = None
        self.rabbitmq_channel: Optional[pika.channel.Channel] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Redis and RabbitMQ connections"""
        if self._initialized:
            return
        
        try:
            # Initialize Redis
            self.redis_client = aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                password=settings.REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            
            # Initialize RabbitMQ
            self.rabbitmq_connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=settings.REDIS_HOST,  # Using same host for simplicity
                    port=5672,
                    credentials=pika.PlainCredentials('guest', 'guest')
                )
            )
            self.rabbitmq_channel = self.rabbitmq_connection.channel()
            
            # Declare queues
            self.rabbitmq_channel.queue_declare(queue='auv_telemetry', durable=True)
            self.rabbitmq_channel.queue_declare(queue='auv_state_updates', durable=True)
            
            self._initialized = True
            self.logger.info("AUV Telemetry Service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AUV Telemetry Service: {e}")
            raise
    
    async def publish_telemetry(self, telemetry: TelemetryData) -> bool:
        """Publish telemetry to RabbitMQ for processing"""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Publish to telemetry queue
            message = telemetry.dict()
            self.rabbitmq_channel.basic_publish(
                exchange='',
                routing_key='auv_telemetry',
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type='application/json'
                )
            )
            
            # Update AUV state in Redis
            await self.update_auv_state(telemetry)
            
            performance_monitor.record_telemetry_processing(
                telemetry.auv_id, "published", 0.0
            )
            
            self.logger.info("Telemetry published successfully", auv_id=telemetry.auv_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to publish telemetry", error=str(e), auv_id=telemetry.auv_id)
            return False
    
    async def update_auv_state(self, telemetry: TelemetryData):
        """Update AUV state in Redis"""
        try:
            state = AUVState(
                auv_id=telemetry.auv_id,
                position={
                    "latitude": telemetry.latitude,
                    "longitude": telemetry.longitude,
                    "depth": telemetry.depth
                },
                last_update=telemetry.timestamp,
                status=telemetry.status,
                battery_level=telemetry.battery_level,
                speed=telemetry.speed,
                heading=telemetry.heading
            )
            
            # Store in Redis with TTL
            await self.redis_client.setex(
                f"auv_state:{telemetry.auv_id}",
                300,  # 5 minutes TTL
                json.dumps(state.dict())
            )
            
            # Publish state update
            self.rabbitmq_channel.basic_publish(
                exchange='',
                routing_key='auv_state_updates',
                body=json.dumps(state.dict()),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )
            
        except Exception as e:
            self.logger.error("Failed to update AUV state", error=str(e), auv_id=telemetry.auv_id)
    
    async def get_auv_state(self, auv_id: str) -> Optional[AUVState]:
        """Get AUV state from Redis"""
        try:
            if not self._initialized:
                await self.initialize()
            
            state_data = await self.redis_client.get(f"auv_state:{auv_id}")
            if state_data:
                return AUVState(**json.loads(state_data))
            return None
            
        except Exception as e:
            self.logger.error("Failed to get AUV state", error=str(e), auv_id=auv_id)
            return None
    
    async def get_all_auv_states(self) -> List[AUVState]:
        """Get all active AUV states"""
        try:
            if not self._initialized:
                await self.initialize()
            
            states = []
            async for key in self.redis_client.scan_iter("auv_state:*"):
                state_data = await self.redis_client.get(key)
                if state_data:
                    states.append(AUVState(**json.loads(state_data)))
            
            return states
            
            except Exception as e:
            self.logger.error("Failed to get all AUV states", error=str(e))
            return []
        
    async def cleanup_expired_states(self):
        """Clean up expired AUV states"""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Redis automatically handles TTL, but we can add custom cleanup logic here
            self.logger.debug("AUV state cleanup completed")
            
        except Exception as e:
            self.logger.error("Failed to cleanup AUV states", error=str(e))


# Create FastAPI app
app = FastAPI(
    title="AUV Telemetry Service",
    description="Microservice for AUV telemetry ingestion and state management",
    version="1.0.0"
)

# Service instance
telemetry_service = AUVTelemetryService()


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    await telemetry_service.initialize()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if telemetry_service.rabbitmq_connection:
        telemetry_service.rabbitmq_connection.close()


@app.post("/telemetry", response_model=Dict[str, Any])
async def receive_telemetry(telemetry: TelemetryData, background_tasks: BackgroundTasks):
    """Receive AUV telemetry data"""
    try:
        success = await telemetry_service.publish_telemetry(telemetry)
        
        if success:
            return {
                "status": "accepted",
                "auv_id": telemetry.auv_id,
                "timestamp": telemetry.timestamp,
                "message": "Telemetry queued for processing"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to process telemetry")
            
    except Exception as e:
        logger.error("Telemetry reception failed", error=str(e), auv_id=telemetry.auv_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/telemetry/batch", response_model=Dict[str, Any])
async def receive_telemetry_batch(telemetry_batch: List[TelemetryData]):
    """Receive batch AUV telemetry data"""
    try:
        results = []
        for telemetry in telemetry_batch:
            success = await telemetry_service.publish_telemetry(telemetry)
            results.append({
                "auv_id": telemetry.auv_id,
                "success": success
            })
        
        success_count = sum(1 for r in results if r["success"])
        
        return {
            "status": "processed",
            "total": len(telemetry_batch),
            "successful": success_count,
            "failed": len(telemetry_batch) - success_count,
            "results": results
        }
        
    except Exception as e:
        logger.error("Batch telemetry reception failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/status/{auv_id}", response_model=Dict[str, Any])
async def get_auv_status(auv_id: str):
    """Get current status for an AUV"""
    try:
        state = await telemetry_service.get_auv_state(auv_id)
        
        if state:
            return {
                "auv_id": auv_id,
                "status": "active",
                "last_update": state.last_update,
                "position": state.position,
                "battery_level": state.battery_level,
                "speed": state.speed,
                "heading": state.heading
            }
        else:
            return {
                "auv_id": auv_id,
                "status": "unknown",
                "message": "No recent telemetry data"
            }
            
    except Exception as e:
        logger.error("Failed to get AUV status", error=str(e), auv_id=auv_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/status", response_model=Dict[str, Any])
async def get_all_auv_status():
    """Get status for all AUVs"""
    try:
        states = await telemetry_service.get_all_auv_states()
        
        return {
            "total_auvs": len(states),
            "active_auvs": len([s for s in states if s.status == "active"]),
            "auvs": [
                {
                    "auv_id": state.auv_id,
                    "status": state.status,
                    "last_update": state.last_update,
                    "position": state.position
                }
                for state in states
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get all AUV status", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        await telemetry_service.redis_client.ping()
        
        # Check RabbitMQ connection
        if telemetry_service.rabbitmq_connection and not telemetry_service.rabbitmq_connection.is_closed:
            rabbitmq_healthy = True
        else:
            rabbitmq_healthy = False
        
        return {
                "status": "healthy" if rabbitmq_healthy else "degraded",
            "service": "auv_telemetry",
                "redis": "connected",
                "rabbitmq": "connected" if rabbitmq_healthy else "disconnected",
                "timestamp": datetime.now(timezone.utc)
            }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 
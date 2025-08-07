"""
Streaming Manager
Central orchestration for streaming operations across microservice architecture
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

import aiohttp
import aioredis
import pika
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import bytewax
from bytewax.dataflow import Dataflow
from bytewax.inputs import KafkaInput
from bytewax.outputs import KafkaOutput

from src.utils.logging_config import setup_logging

# Setup logging
logger = setup_logging(__name__)

app = FastAPI(
    title="DeepSeaGuard Streaming Manager",
    description="Central streaming orchestration for microservice architecture",
    version="2.0.0"
)

class StreamStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"

class StreamConfig(BaseModel):
    stream_id: str
    name: str
    description: str
    input_topic: str
    output_topic: str
    processor_type: str  # "telemetry", "geofencing", "compliance"
    config: Dict[str, Any]
    enabled: bool = True

class StreamMetrics(BaseModel):
    stream_id: str
    status: StreamStatus
    messages_processed: int
    messages_per_second: float
    error_count: int
    last_error: Optional[str]
    uptime_seconds: int
    memory_usage_mb: float
    cpu_usage_percent: float

class StreamingManager:
    def __init__(self):
        self.streams: Dict[str, StreamConfig] = {}
        self.stream_status: Dict[str, StreamStatus] = {}
        self.stream_metrics: Dict[str, StreamMetrics] = {}
        self.redis_client = None
        self.rabbitmq_connection = None
        self.kafka_producer = None
        self.performance_metrics = {
            "total_streams": 0,
            "active_streams": 0,
            "total_messages_processed": 0,
            "avg_processing_time": 0.0,
            "errors": 0
        }
        
    async def initialize(self):
        """Initialize the streaming manager"""
        logger.info("Initializing Streaming Manager")
        
        # Initialize Redis connection
        try:
            self.redis_client = await aioredis.from_url("redis://localhost:6379", password="redispassword")
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
        
        # Initialize RabbitMQ connection
        try:
            self.rabbitmq_connection = pika.BlockingConnection(
                pika.ConnectionParameters('localhost', 5672, '/', 
                                        pika.PlainCredentials('guest', 'guest'))
            )
            logger.info("RabbitMQ connection established")
        except Exception as e:
            logger.warning(f"RabbitMQ connection failed: {e}")
        
        # Load default stream configurations
        await self._load_default_streams()
        
        # Start background tasks
        asyncio.create_task(self.monitor_streams())
        asyncio.create_task(self.update_metrics())
        asyncio.create_task(self.cleanup_old_data())
        
        logger.info("Streaming Manager initialized successfully")
    
    async def _load_default_streams(self):
        """Load default stream configurations"""
        default_streams = [
            StreamConfig(
                stream_id="telemetry-stream-001",
                name="AUV Telemetry Processing",
                description="Real-time AUV telemetry data processing",
                input_topic="auv-telemetry-raw",
                output_topic="auv-telemetry-processed",
                processor_type="telemetry",
                config={
                    "batch_size": 100,
                    "window_size": 60,
                    "parallelism": 4
                }
            ),
            StreamConfig(
                stream_id="geofencing-stream-001",
                name="Geofencing Analysis",
                description="Real-time geofencing violation detection",
                input_topic="auv-telemetry-processed",
                output_topic="geofencing-violations",
                processor_type="geofencing",
                config={
                    "check_interval": 5,
                    "violation_threshold": 0.1,
                    "parallelism": 2
                }
            ),
            StreamConfig(
                stream_id="compliance-stream-001",
                name="Compliance Monitoring",
                description="Real-time compliance rule evaluation",
                input_topic="auv-telemetry-processed",
                output_topic="compliance-events",
                processor_type="compliance",
                config={
                    "rule_evaluation_interval": 10,
                    "compliance_threshold": 0.8,
                    "parallelism": 3
                }
            )
        ]
        
        for stream in default_streams:
            await self.register_stream(stream)
    
    async def register_stream(self, stream: StreamConfig):
        """Register a new stream"""
        try:
            self.streams[stream.stream_id] = stream
            self.stream_status[stream.stream_id] = StreamStatus.STOPPED
            
            # Initialize metrics
            self.stream_metrics[stream.stream_id] = StreamMetrics(
                stream_id=stream.stream_id,
                status=StreamStatus.STOPPED,
                messages_processed=0,
                messages_per_second=0.0,
                error_count=0,
                last_error=None,
                uptime_seconds=0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0
            )
            
            logger.info(f"Registered stream: {stream.name} ({stream.stream_id})")
            
        except Exception as e:
            logger.error(f"Error registering stream {stream.stream_id}: {e}")
            raise
    
    async def start_stream(self, stream_id: str) -> bool:
        """Start a stream"""
        if stream_id not in self.streams:
            raise HTTPException(status_code=404, detail="Stream not found")
        
        try:
            stream = self.streams[stream_id]
            if not stream.enabled:
                raise HTTPException(status_code=400, detail="Stream is disabled")
            
            # Update status
            self.stream_status[stream_id] = StreamStatus.STARTING
            
            # Start the appropriate processor
            if stream.processor_type == "telemetry":
                await self._start_telemetry_processor(stream)
            elif stream.processor_type == "geofencing":
                await self._start_geofencing_processor(stream)
            elif stream.processor_type == "compliance":
                await self._start_compliance_processor(stream)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown processor type: {stream.processor_type}")
            
            # Update status to running
            self.stream_status[stream_id] = StreamStatus.RUNNING
            self.stream_metrics[stream_id].status = StreamStatus.RUNNING
            self.stream_metrics[stream_id].uptime_seconds = 0
            
            logger.info(f"Started stream: {stream_id}")
            return True
            
        except Exception as e:
            self.stream_status[stream_id] = StreamStatus.ERROR
            self.stream_metrics[stream_id].status = StreamStatus.ERROR
            self.stream_metrics[stream_id].last_error = str(e)
            logger.error(f"Error starting stream {stream_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to start stream: {str(e)}")
    
    async def stop_stream(self, stream_id: str) -> bool:
        """Stop a stream"""
        if stream_id not in self.streams:
            raise HTTPException(status_code=404, detail="Stream not found")
        
        try:
            # Update status
            self.stream_status[stream_id] = StreamStatus.STOPPING
            
            # Stop the stream (in a real implementation, this would stop the actual processor)
            # For now, we'll just update the status
            
            self.stream_status[stream_id] = StreamStatus.STOPPED
            self.stream_metrics[stream_id].status = StreamStatus.STOPPED
            
            logger.info(f"Stopped stream: {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping stream {stream_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to stop stream: {str(e)}")
    
    async def _start_telemetry_processor(self, stream: StreamConfig):
        """Start telemetry processor"""
        # In a real implementation, this would start a Bytewax dataflow
        # For now, we'll simulate the processor
        logger.info(f"Starting telemetry processor for stream: {stream.stream_id}")
        await asyncio.sleep(1)  # Simulate startup time
    
    async def _start_geofencing_processor(self, stream: StreamConfig):
        """Start geofencing processor"""
        logger.info(f"Starting geofencing processor for stream: {stream.stream_id}")
        await asyncio.sleep(1)  # Simulate startup time
    
    async def _start_compliance_processor(self, stream: StreamConfig):
        """Start compliance processor"""
        logger.info(f"Starting compliance processor for stream: {stream.stream_id}")
        await asyncio.sleep(1)  # Simulate startup time
    
    async def get_stream_status(self, stream_id: str) -> Optional[StreamMetrics]:
        """Get status of a specific stream"""
        return self.stream_metrics.get(stream_id)
    
    async def get_all_streams_status(self) -> List[StreamMetrics]:
        """Get status of all streams"""
        return list(self.stream_metrics.values())
    
    async def get_stream_config(self, stream_id: str) -> Optional[StreamConfig]:
        """Get configuration of a specific stream"""
        return self.streams.get(stream_id)
    
    async def update_stream_config(self, stream_id: str, config: Dict[str, Any]) -> bool:
        """Update stream configuration"""
        if stream_id not in self.streams:
            raise HTTPException(status_code=404, detail="Stream not found")
        
        try:
            stream = self.streams[stream_id]
            stream.config.update(config)
            logger.info(f"Updated configuration for stream: {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating stream config {stream_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to update stream config: {str(e)}")
    
    async def monitor_streams(self):
        """Monitor all streams and update metrics"""
        while True:
            try:
                for stream_id, stream in self.streams.items():
                    if self.stream_status[stream_id] == StreamStatus.RUNNING:
                        # Update uptime
                        metrics = self.stream_metrics[stream_id]
                        metrics.uptime_seconds += 30  # Update every 30 seconds
                        
                        # Simulate message processing
                        messages_processed = 100 + (metrics.uptime_seconds // 60) * 50
                        metrics.messages_processed = messages_processed
                        metrics.messages_per_second = messages_processed / max(metrics.uptime_seconds, 1)
                        
                        # Simulate resource usage
                        metrics.memory_usage_mb = 50.0 + (metrics.uptime_seconds % 300) * 0.1
                        metrics.cpu_usage_percent = 20.0 + (metrics.uptime_seconds % 60) * 0.5
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in stream monitoring: {e}")
                await asyncio.sleep(30)
    
    async def update_metrics(self):
        """Update performance metrics"""
        while True:
            try:
                # Calculate aggregate metrics
                active_streams = sum(1 for status in self.stream_status.values() 
                                   if status == StreamStatus.RUNNING)
                total_messages = sum(metrics.messages_processed 
                                   for metrics in self.stream_metrics.values())
                
                self.performance_metrics["total_streams"] = len(self.streams)
                self.performance_metrics["active_streams"] = active_streams
                self.performance_metrics["total_messages_processed"] = total_messages
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(60)
    
    async def cleanup_old_data(self):
        """Clean up old streaming data"""
        while True:
            try:
                # In a real implementation, this would clean up old Kafka topics,
                # Redis keys, and other streaming data
                logger.info("Cleaning up old streaming data")
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
    
    async def get_performance_metrics(self) -> Dict:
        """Get performance metrics"""
        return self.performance_metrics.copy()

# Global streaming manager instance
streaming_manager = StreamingManager()

@app.on_event("startup")
async def startup_event():
    """Initialize streaming manager on startup"""
    await streaming_manager.initialize()

@app.get("/streams")
async def get_streams():
    """Get all streams"""
    streams = []
    for stream_id, stream in streaming_manager.streams.items():
        status = streaming_manager.stream_status.get(stream_id, StreamStatus.STOPPED)
        stream_info = {
            "stream_id": stream_id,
            "name": stream.name,
            "description": stream.description,
            "status": status,
            "enabled": stream.enabled
        }
        streams.append(stream_info)
    return {"streams": streams}

@app.get("/streams/{stream_id}")
async def get_stream(stream_id: str):
    """Get specific stream information"""
    stream = await streaming_manager.get_stream_config(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    status = await streaming_manager.get_stream_status(stream_id)
    return {
        "stream": stream.dict(),
        "status": status.dict() if status else None
    }

@app.post("/streams/{stream_id}/start")
async def start_stream(stream_id: str):
    """Start a stream"""
    success = await streaming_manager.start_stream(stream_id)
    return {"message": f"Stream {stream_id} started successfully"}

@app.post("/streams/{stream_id}/stop")
async def stop_stream(stream_id: str):
    """Stop a stream"""
    success = await streaming_manager.stop_stream(stream_id)
    return {"message": f"Stream {stream_id} stopped successfully"}

@app.put("/streams/{stream_id}/config")
async def update_stream_config(stream_id: str, config: Dict[str, Any]):
    """Update stream configuration"""
    success = await streaming_manager.update_stream_config(stream_id, config)
    return {"message": f"Stream {stream_id} configuration updated successfully"}

@app.get("/streams/{stream_id}/status")
async def get_stream_status(stream_id: str):
    """Get stream status"""
    status = await streaming_manager.get_stream_status(stream_id)
    if not status:
        raise HTTPException(status_code=404, detail="Stream not found")
    return status

@app.get("/status")
async def get_all_status():
    """Get status of all streams"""
    status_list = await streaming_manager.get_all_streams_status()
    return {"streams": [status.dict() for status in status_list]}

@app.get("/metrics")
async def get_metrics():
    """Get performance metrics"""
    return await streaming_manager.get_performance_metrics()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "streaming-manager",
        "total_streams": len(streaming_manager.streams),
        "active_streams": sum(1 for status in streaming_manager.stream_status.values() 
                             if status == StreamStatus.RUNNING),
        "timestamp": datetime.now()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005) 
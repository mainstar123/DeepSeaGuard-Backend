"""
Geofencing Microservice
Handles advanced geofencing operations with real-time processing
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import aiohttp
import numpy as np
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from core.geofencing import GeofencingEngine
from models.telemetry import TelemetryData
from utils.logging_config import setup_logging

# Setup logging
logger = setup_logging(__name__)

app = FastAPI(
    title="DeepSeaGuard Geofencing Service",
    description="Advanced geofencing microservice for AUV position monitoring",
    version="2.0.0"
)

class GeofenceZone(BaseModel):
    zone_id: str
    name: str
    zone_type: str  # "restricted", "monitoring", "safe"
    coordinates: List[Tuple[float, float]]
    depth_min: Optional[float] = None
    depth_max: Optional[float] = None
    time_restrictions: Optional[Dict] = None
    priority: int = 1

class GeofenceRequest(BaseModel):
    auv_id: str
    latitude: float
    longitude: float
    depth: float
    timestamp: datetime
    speed: Optional[float] = None
    heading: Optional[float] = None

class GeofenceResponse(BaseModel):
    auv_id: str
    timestamp: datetime
    violations: List[Dict]
    warnings: List[Dict]
    safe_zones: List[str]
    risk_level: str  # "low", "medium", "high", "critical"
    recommendations: List[str]

class GeofencingService:
    def __init__(self):
        self.geofencing_engine = GeofencingEngine()
        self.active_zones: Dict[str, GeofenceZone] = {}
        self.zone_cache: Dict[str, Polygon] = {}
        self.violation_history: Dict[str, List] = {}
        self.performance_metrics = {
            "total_checks": 0,
            "violations_detected": 0,
            "avg_response_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
    async def initialize(self):
        """Initialize the geofencing service"""
        logger.info("Initializing Geofencing Service")
        
        # Load zones from database or configuration
        await self.load_zones()
        
        # Start background tasks
        asyncio.create_task(self.cleanup_old_violations())
        asyncio.create_task(self.update_performance_metrics())
        
        logger.info("Geofencing Service initialized successfully")
    
    async def load_zones(self):
        """Load geofence zones from database"""
        try:
            # In a real implementation, this would load from database
            # For now, we'll create some sample zones
            sample_zones = [
                GeofenceZone(
                    zone_id="restricted_area_1",
                    name="Marine Protected Area Alpha",
                    zone_type="restricted",
                    coordinates=[(17.7, -77.8), (17.8, -77.8), (17.8, -77.7), (17.7, -77.7)],
                    depth_min=0,
                    depth_max=200,
                    priority=1
                ),
                GeofenceZone(
                    zone_id="monitoring_zone_1",
                    name="Shipping Lane Monitoring",
                    zone_type="monitoring",
                    coordinates=[(17.6, -77.9), (17.9, -77.9), (17.9, -77.6), (17.6, -77.6)],
                    depth_min=0,
                    depth_max=500,
                    priority=2
                )
            ]
            
            for zone in sample_zones:
                await self.add_zone(zone)
                
            logger.info(f"Loaded {len(sample_zones)} geofence zones")
            
        except Exception as e:
            logger.error(f"Error loading zones: {e}")
    
    async def add_zone(self, zone: GeofenceZone):
        """Add a new geofence zone"""
        try:
            # Create polygon from coordinates
            polygon = Polygon(zone.coordinates)
            if not polygon.is_valid:
                raise ValueError(f"Invalid polygon for zone {zone.zone_id}")
            
            self.active_zones[zone.zone_id] = zone
            self.zone_cache[zone.zone_id] = polygon
            
            logger.info(f"Added geofence zone: {zone.name} ({zone.zone_id})")
            
        except Exception as e:
            logger.error(f"Error adding zone {zone.zone_id}: {e}")
            raise
    
    async def check_position(self, request: GeofenceRequest) -> GeofenceResponse:
        """Check AUV position against all geofence zones"""
        start_time = datetime.now()
        
        try:
            violations = []
            warnings = []
            safe_zones = []
            risk_level = "low"
            recommendations = []
            
            # Create point for AUV position
            auv_point = Point(request.longitude, request.latitude)
            
            # Check against each zone
            for zone_id, zone in self.active_zones.items():
                if zone_id in self.zone_cache:
                    polygon = self.zone_cache[zone_id]
                    
                    # Check if AUV is inside zone
                    if polygon.contains(auv_point):
                        # Check depth restrictions
                        depth_violation = False
                        if zone.depth_min is not None and request.depth < zone.depth_min:
                            depth_violation = True
                        if zone.depth_max is not None and request.depth > zone.depth_max:
                            depth_violation = True
                        
                        # Check time restrictions
                        time_violation = False
                        if zone.time_restrictions:
                            current_time = request.timestamp.time()
                            # Simple time check - could be more complex
                            if "start_time" in zone.time_restrictions and "end_time" in zone.time_restrictions:
                                start_time_zone = zone.time_restrictions["start_time"]
                                end_time_zone = zone.time_restrictions["end_time"]
                                if not (start_time_zone <= current_time <= end_time_zone):
                                    time_violation = True
                        
                        # Determine violation type
                        if zone.zone_type == "restricted":
                            violation_info = {
                                "zone_id": zone_id,
                                "zone_name": zone.name,
                                "zone_type": zone.zone_type,
                                "violation_type": "restricted_zone_entry",
                                "severity": "high",
                                "timestamp": request.timestamp,
                                "depth_violation": depth_violation,
                                "time_violation": time_violation
                            }
                            violations.append(violation_info)
                            risk_level = "critical"
                            recommendations.append(f"Immediately exit restricted zone: {zone.name}")
                            
                        elif zone.zone_type == "monitoring":
                            warning_info = {
                                "zone_id": zone_id,
                                "zone_name": zone.name,
                                "zone_type": zone.zone_type,
                                "warning_type": "monitoring_zone_entry",
                                "severity": "medium",
                                "timestamp": request.timestamp,
                                "depth_violation": depth_violation,
                                "time_violation": time_violation
                            }
                            warnings.append(warning_info)
                            if risk_level == "low":
                                risk_level = "medium"
                            recommendations.append(f"Monitor activity in zone: {zone.name}")
                            
                        elif zone.zone_type == "safe":
                            safe_zones.append(zone_id)
                            recommendations.append(f"Currently in safe zone: {zone.name}")
                    
                    # Check proximity to zone boundaries
                    distance_to_boundary = polygon.distance(auv_point)
                    if distance_to_boundary < 0.01:  # Within 1km of boundary
                        proximity_warning = {
                            "zone_id": zone_id,
                            "zone_name": zone.name,
                            "warning_type": "zone_proximity",
                            "distance_km": round(distance_to_boundary * 111, 2),  # Rough conversion
                            "severity": "low"
                        }
                        warnings.append(proximity_warning)
            
            # Update performance metrics
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self.performance_metrics["total_checks"] += 1
            self.performance_metrics["violations_detected"] += len(violations)
            self.performance_metrics["avg_response_time"] = (
                (self.performance_metrics["avg_response_time"] * (self.performance_metrics["total_checks"] - 1) + response_time) 
                / self.performance_metrics["total_checks"]
            )
            
            # Store violation history
            if violations:
                if request.auv_id not in self.violation_history:
                    self.violation_history[request.auv_id] = []
                self.violation_history[request.auv_id].extend(violations)
            
            # Generate response
            response = GeofenceResponse(
                auv_id=request.auv_id,
                timestamp=request.timestamp,
                violations=violations,
                warnings=warnings,
                safe_zones=safe_zones,
                risk_level=risk_level,
                recommendations=recommendations
            )
            
            logger.info(f"Geofence check completed for AUV {request.auv_id} in {response_time:.2f}ms")
            return response
            
        except Exception as e:
            logger.error(f"Error in geofence check: {e}")
            raise HTTPException(status_code=500, detail=f"Geofence check failed: {str(e)}")
    
    async def get_violation_history(self, auv_id: str, hours: int = 24) -> List[Dict]:
        """Get violation history for an AUV"""
        if auv_id not in self.violation_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_violations = [
            v for v in self.violation_history[auv_id]
            if v["timestamp"] > cutoff_time
        ]
        
        return recent_violations
    
    async def get_performance_metrics(self) -> Dict:
        """Get performance metrics"""
        return self.performance_metrics.copy()
    
    async def cleanup_old_violations(self):
        """Clean up old violation history"""
        while True:
            try:
                cutoff_time = datetime.now() - timedelta(days=7)
                for auv_id in list(self.violation_history.keys()):
                    self.violation_history[auv_id] = [
                        v for v in self.violation_history[auv_id]
                        if v["timestamp"] > cutoff_time
                    ]
                    if not self.violation_history[auv_id]:
                        del self.violation_history[auv_id]
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
    
    async def update_performance_metrics(self):
        """Update performance metrics periodically"""
        while True:
            try:
                # Reset counters periodically
                if self.performance_metrics["total_checks"] > 10000:
                    self.performance_metrics["total_checks"] = 0
                    self.performance_metrics["violations_detected"] = 0
                    self.performance_metrics["avg_response_time"] = 0.0
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(300)

# Global service instance
geofencing_service = GeofencingService()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    await geofencing_service.initialize()

@app.post("/check", response_model=GeofenceResponse)
async def check_geofence(request: GeofenceRequest):
    """Check AUV position against geofence zones"""
    return await geofencing_service.check_position(request)

@app.get("/zones")
async def get_zones():
    """Get all active geofence zones"""
    return {
        "zones": [
            {
                "zone_id": zone.zone_id,
                "name": zone.name,
                "zone_type": zone.zone_type,
                "coordinates": zone.coordinates,
                "depth_min": zone.depth_min,
                "depth_max": zone.depth_max,
                "priority": zone.priority
            }
            for zone in geofencing_service.active_zones.values()
        ]
    }

@app.post("/zones")
async def add_zone(zone: GeofenceZone):
    """Add a new geofence zone"""
    await geofencing_service.add_zone(zone)
    return {"message": f"Zone {zone.zone_id} added successfully"}

@app.get("/violations/{auv_id}")
async def get_violations(auv_id: str, hours: int = 24):
    """Get violation history for an AUV"""
    violations = await geofencing_service.get_violation_history(auv_id, hours)
    return {"auv_id": auv_id, "violations": violations}

@app.get("/metrics")
async def get_metrics():
    """Get performance metrics"""
    return await geofencing_service.get_performance_metrics()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "geofencing",
        "active_zones": len(geofencing_service.active_zones),
        "timestamp": datetime.now()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 
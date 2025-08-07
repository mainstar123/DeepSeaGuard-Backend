"""
API Gateway Microservice
Handles service discovery, routing, load balancing, and circuit breakers
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

import aiohttp
import httpx
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
import jwt
from circuitbreaker import circuit

from src.utils.logging_config import setup_logging

# Setup logging
logger = setup_logging(__name__)

app = FastAPI(
    title="DeepSeaGuard API Gateway",
    description="API Gateway for microservice architecture with service discovery and load balancing",
    version="2.0.0"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"

class ServiceInfo(BaseModel):
    service_id: str
    name: str
    version: str
    host: str
    port: int
    health_endpoint: str
    status: ServiceStatus
    last_health_check: datetime
    response_time: float
    load_factor: float = 1.0

class CircuitBreakerConfig(BaseModel):
    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: str = "HTTPException"

class ServiceRegistry:
    def __init__(self):
        self.services: Dict[str, ServiceInfo] = {}
        self.service_instances: Dict[str, List[ServiceInfo]] = {}
        self.load_balancers: Dict[str, int] = {}  # Round-robin counters
        
    async def register_service(self, service: ServiceInfo):
        """Register a new service"""
        self.services[service.service_id] = service
        
        if service.name not in self.service_instances:
            self.service_instances[service.name] = []
        self.service_instances[service.name].append(service)
        
        logger.info(f"Registered service: {service.name} ({service.service_id}) at {service.host}:{service.port}")
    
    async def unregister_service(self, service_id: str):
        """Unregister a service"""
        if service_id in self.services:
            service = self.services[service_id]
            if service.name in self.service_instances:
                self.service_instances[service.name] = [
                    s for s in self.service_instances[service.name] 
                    if s.service_id != service_id
                ]
            del self.services[service_id]
            logger.info(f"Unregistered service: {service_id}")
    
    def get_service_instances(self, service_name: str) -> List[ServiceInfo]:
        """Get all instances of a service"""
        return self.service_instances.get(service_name, [])
    
    def get_next_instance(self, service_name: str) -> Optional[ServiceInfo]:
        """Get next service instance using round-robin load balancing"""
        instances = self.get_service_instances(service_name)
        if not instances:
            return None
        
        # Filter healthy instances
        healthy_instances = [i for i in instances if i.status == ServiceStatus.HEALTHY]
        if not healthy_instances:
            return None
        
        # Round-robin selection
        counter = self.load_balancers.get(service_name, 0)
        instance = healthy_instances[counter % len(healthy_instances)]
        self.load_balancers[service_name] = counter + 1
        
        return instance
    
    async def update_service_health(self, service_id: str, status: ServiceStatus, response_time: float):
        """Update service health status"""
        if service_id in self.services:
            service = self.services[service_id]
            service.status = status
            service.last_health_check = datetime.now()
            service.response_time = response_time

class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if circuit breaker allows execution"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > timedelta(seconds=self.config.recovery_timeout):
                self.state = "HALF_OPEN"
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        return False
    
    def on_success(self):
        """Handle successful execution"""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
        self.failure_count = 0
    
    def on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = "OPEN"

class APIGateway:
    def __init__(self):
        self.service_registry = ServiceRegistry()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.http_client = None
        self.performance_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "circuit_breaker_trips": 0
        }
        
    async def initialize(self):
        """Initialize the API Gateway"""
        logger.info("Initializing API Gateway")
        
        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Register default services
        await self._register_default_services()
        
        # Start background tasks
        asyncio.create_task(self.health_check_services())
        asyncio.create_task(self.update_performance_metrics())
        
        logger.info("API Gateway initialized successfully")
    
    async def _register_default_services(self):
        """Register default microservices"""
        default_services = [
            ServiceInfo(
                service_id="auv-telemetry-001",
                name="auv-telemetry",
                version="2.0.0",
                host="localhost",
                port=8001,
                health_endpoint="/health",
                status=ServiceStatus.HEALTHY,
                last_health_check=datetime.now(),
                response_time=0.0
            ),
            ServiceInfo(
                service_id="geofencing-001",
                name="geofencing",
                version="2.0.0",
                host="localhost",
                port=8002,
                health_endpoint="/health",
                status=ServiceStatus.HEALTHY,
                last_health_check=datetime.now(),
                response_time=0.0
            ),
            ServiceInfo(
                service_id="compliance-001",
                name="compliance",
                version="2.0.0",
                host="localhost",
                port=8003,
                health_endpoint="/health",
                status=ServiceStatus.HEALTHY,
                last_health_check=datetime.now(),
                response_time=0.0
            ),
            ServiceInfo(
                service_id="alert-001",
                name="alert",
                version="2.0.0",
                host="localhost",
                port=8004,
                health_endpoint="/health",
                status=ServiceStatus.HEALTHY,
                last_health_check=datetime.now(),
                response_time=0.0
            )
        ]
        
        for service in default_services:
            await self.service_registry.register_service(service)
            # Initialize circuit breaker for each service
            self.circuit_breakers[service.name] = CircuitBreaker(CircuitBreakerConfig())
    
    async def route_request(self, service_name: str, path: str, method: str, 
                          headers: Dict, body: Optional[bytes] = None) -> Response:
        """Route request to appropriate microservice"""
        start_time = datetime.now()
        
        try:
            # Get service instance
            service_instance = self.service_registry.get_next_instance(service_name)
            if not service_instance:
                raise HTTPException(status_code=503, detail=f"Service {service_name} unavailable")
            
            # Check circuit breaker
            circuit_breaker = self.circuit_breakers.get(service_name)
            if circuit_breaker and not circuit_breaker.can_execute():
                self.performance_metrics["circuit_breaker_trips"] += 1
                raise HTTPException(status_code=503, detail=f"Service {service_name} circuit breaker open")
            
            # Build target URL
            target_url = f"http://{service_instance.host}:{service_instance.port}{path}"
            
            # Forward request
            response = await self._forward_request(target_url, method, headers, body)
            
            # Update circuit breaker
            if circuit_breaker:
                circuit_breaker.on_success()
            
            # Update performance metrics
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self.performance_metrics["total_requests"] += 1
            self.performance_metrics["successful_requests"] += 1
            self.performance_metrics["avg_response_time"] = (
                (self.performance_metrics["avg_response_time"] * (self.performance_metrics["total_requests"] - 1) + response_time) 
                / self.performance_metrics["total_requests"]
            )
            
            return response
            
        except Exception as e:
            # Update circuit breaker on failure
            circuit_breaker = self.circuit_breakers.get(service_name)
            if circuit_breaker:
                circuit_breaker.on_failure()
            
            # Update performance metrics
            self.performance_metrics["total_requests"] += 1
            self.performance_metrics["failed_requests"] += 1
            
            logger.error(f"Error routing request to {service_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Service {service_name} error: {str(e)}")
    
    async def _forward_request(self, target_url: str, method: str, headers: Dict, 
                             body: Optional[bytes] = None) -> Response:
        """Forward request to target service"""
        # Remove host header to avoid conflicts
        headers.pop("host", None)
        
        # Make request
        if method == "GET":
            response = await self.http_client.get(target_url, headers=headers)
        elif method == "POST":
            response = await self.http_client.post(target_url, headers=headers, content=body)
        elif method == "PUT":
            response = await self.http_client.put(target_url, headers=headers, content=body)
        elif method == "DELETE":
            response = await self.http_client.delete(target_url, headers=headers)
        else:
            raise HTTPException(status_code=405, detail="Method not allowed")
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    
    async def health_check_services(self):
        """Periodically check health of all services"""
        while True:
            try:
                for service_name, instances in self.service_registry.service_instances.items():
                    for instance in instances:
                        try:
                            start_time = datetime.now()
                            health_url = f"http://{instance.host}:{instance.port}{instance.health_endpoint}"
                            response = await self.http_client.get(health_url, timeout=5.0)
                            response_time = (datetime.now() - start_time).total_seconds() * 1000
                            
                            if response.status_code == 200:
                                await self.service_registry.update_service_health(
                                    instance.service_id, 
                                    ServiceStatus.HEALTHY, 
                                    response_time
                                )
                            else:
                                await self.service_registry.update_service_health(
                                    instance.service_id, 
                                    ServiceStatus.UNHEALTHY, 
                                    response_time
                                )
                                
                        except Exception as e:
                            logger.warning(f"Health check failed for {instance.service_id}: {e}")
                            await self.service_registry.update_service_health(
                                instance.service_id, 
                                ServiceStatus.UNHEALTHY, 
                                0.0
                            )
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in health check task: {e}")
                await asyncio.sleep(30)
    
    async def update_performance_metrics(self):
        """Update performance metrics periodically"""
        while True:
            try:
                # Reset counters periodically
                if self.performance_metrics["total_requests"] > 10000:
                    self.performance_metrics["total_requests"] = 0
                    self.performance_metrics["successful_requests"] = 0
                    self.performance_metrics["failed_requests"] = 0
                    self.performance_metrics["avg_response_time"] = 0.0
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(300)
    
    async def get_service_status(self) -> Dict:
        """Get status of all services"""
        return {
            "services": [
                {
                    "name": service.name,
                    "version": service.version,
                    "status": service.status,
                    "response_time": service.response_time,
                    "last_health_check": service.last_health_check.isoformat(),
                    "instances": len(self.service_registry.get_service_instances(service.name))
                }
                for service in self.service_registry.services.values()
            ]
        }
    
    async def get_performance_metrics(self) -> Dict:
        """Get performance metrics"""
        return self.performance_metrics.copy()

# Global gateway instance
api_gateway = APIGateway()

@app.on_event("startup")
async def startup_event():
    """Initialize gateway on startup"""
    await api_gateway.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if api_gateway.http_client:
        await api_gateway.http_client.aclose()

# Route definitions for each microservice
@app.api_route("/api/v1/telemetry/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_telemetry(request: Request, path: str):
    """Route telemetry requests to AUV telemetry service"""
    body = await request.body() if request.method in ["POST", "PUT"] else None
    return await api_gateway.route_request(
        "auv-telemetry", 
        f"/api/v1/telemetry/{path}", 
        request.method, 
        dict(request.headers), 
        body
    )

@app.api_route("/api/v1/geofencing/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_geofencing(request: Request, path: str):
    """Route geofencing requests to geofencing service"""
    body = await request.body() if request.method in ["POST", "PUT"] else None
    return await api_gateway.route_request(
        "geofencing", 
        f"/{path}", 
        request.method, 
        dict(request.headers), 
        body
    )

@app.api_route("/api/v1/compliance/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_compliance(request: Request, path: str):
    """Route compliance requests to compliance service"""
    body = await request.body() if request.method in ["POST", "PUT"] else None
    return await api_gateway.route_request(
        "compliance", 
        f"/{path}", 
        request.method, 
        dict(request.headers), 
        body
    )

@app.api_route("/api/v1/alerts/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_alerts(request: Request, path: str):
    """Route alert requests to alert service"""
    body = await request.body() if request.method in ["POST", "PUT"] else None
    return await api_gateway.route_request(
        "alert", 
        f"/{path}", 
        request.method, 
        dict(request.headers), 
        body
    )

@app.get("/services")
async def get_services():
    """Get status of all services"""
    return await api_gateway.get_service_status()

@app.get("/metrics")
async def get_metrics():
    """Get performance metrics"""
    return await api_gateway.get_performance_metrics()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "services_registered": len(api_gateway.service_registry.services),
        "timestamp": datetime.now()
    }

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "DeepSeaGuard API Gateway",
        "version": "2.0.0",
        "description": "API Gateway for microservice architecture",
        "services": list(api_gateway.service_registry.service_instances.keys()),
        "timestamp": datetime.now()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
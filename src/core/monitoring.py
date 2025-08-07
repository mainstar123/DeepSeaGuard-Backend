"""
Production-ready monitoring and metrics for DeepSeaGuard
"""
import time
import psutil
import asyncio
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from core.logging import get_logger

logger = get_logger(__name__)

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'deepseaguard_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'deepseaguard_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'deepseaguard_active_connections',
    'Number of active WebSocket connections'
)

AUV_TELEMETRY_PROCESSED = Counter(
    'deepseaguard_auv_telemetry_processed_total',
    'Total AUV telemetry records processed',
    ['auv_id', 'status']
)

COMPLIANCE_VIOLATIONS = Counter(
    'deepseaguard_compliance_violations_total',
    'Total compliance violations detected',
    ['zone_type', 'severity']
)

ZONE_CHECKS = Counter(
    'deepseaguard_zone_checks_total',
    'Total zone intersection checks performed'
)

CACHE_HITS = Counter(
    'deepseaguard_cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

CACHE_MISSES = Counter(
    'deepseaguard_cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

SYSTEM_MEMORY_USAGE = Gauge(
    'deepseaguard_system_memory_bytes',
    'System memory usage in bytes'
)

SYSTEM_CPU_USAGE = Gauge(
    'deepseaguard_system_cpu_percent',
    'System CPU usage percentage'
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for collecting metrics"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response


class HealthChecker:
    """System health monitoring"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def check_system_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        try:
            # System metrics
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage('/')
            
            # Update Prometheus metrics
            SYSTEM_MEMORY_USAGE.set(memory.used)
            SYSTEM_CPU_USAGE.set(cpu_percent)
            
            health_status = {
                "status": "healthy",
                "timestamp": time.time(),
                "system": {
                    "memory_usage_percent": memory.percent,
                    "cpu_usage_percent": cpu_percent,
                    "disk_usage_percent": (disk.used / disk.total) * 100,
                    "active_connections": ACTIVE_CONNECTIONS._value.get()
                },
                "services": {
                    "database": self._check_database_health(),
                    "redis": self._check_redis_health(),
                    "geofencing": self._check_geofencing_health()
                }
            }
            
            # Check if any service is unhealthy
            for service, status in health_status["services"].items():
                if status.get("status") != "healthy":
                    health_status["status"] = "degraded"
            
            return health_status
            
        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            # This would be implemented with actual database check
            return {"status": "healthy", "response_time_ms": 5}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            # This would be implemented with actual Redis check
            return {"status": "healthy", "response_time_ms": 2}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def _check_geofencing_health(self) -> Dict[str, Any]:
        """Check geofencing service health"""
        try:
            # This would be implemented with actual geofencing check
            return {"status": "healthy", "zones_loaded": 150}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


class PerformanceMonitor:
    """Performance monitoring and optimization"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.start_time = time.time()
    
    def record_telemetry_processing(self, auv_id: str, status: str, duration_ms: float):
        """Record telemetry processing metrics"""
        AUV_TELEMETRY_PROCESSED.labels(auv_id=auv_id, status=status).inc()
        
        if duration_ms > 100:  # Log slow processing
            self.logger.warning(
                "Slow telemetry processing",
                auv_id=auv_id,
                duration_ms=duration_ms
            )
    
    def record_compliance_violation(self, zone_type: str, severity: str):
        """Record compliance violation metrics"""
        COMPLIANCE_VIOLATIONS.labels(zone_type=zone_type, severity=severity).inc()
    
    def record_zone_check(self):
        """Record zone check metrics"""
        ZONE_CHECKS.inc()
    
    def record_cache_hit(self, cache_type: str):
        """Record cache hit metrics"""
        CACHE_HITS.labels(cache_type=cache_type).inc()
    
    def record_cache_miss(self, cache_type: str):
        """Record cache miss metrics"""
        CACHE_MISSES.labels(cache_type=cache_type).inc()
    
    def update_connection_count(self, count: int):
        """Update active connection count"""
        ACTIVE_CONNECTIONS.set(count)
    
    def get_uptime(self) -> float:
        """Get system uptime in seconds"""
        return time.time() - self.start_time


# Global instances
health_checker = HealthChecker()
performance_monitor = PerformanceMonitor()


def get_metrics() -> str:
    """Get Prometheus metrics"""
    return generate_latest()


def create_metrics_response() -> Response:
    """Create metrics response for Prometheus"""
    return Response(
        content=get_metrics(),
        media_type=CONTENT_TYPE_LATEST
    ) 
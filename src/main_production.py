"""
Production-ready DeepSeaGuard application with monitoring and optimization
"""
import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from core.logging import setup_logging, get_logger
from core.monitoring import MetricsMiddleware, health_checker, performance_monitor, create_metrics_response
from core.cache_manager import cache_manager
from database.database import sync_engine, Base
from routers import compliance, telemetry, zones, isa_integration
from services.websocket_manager import WebSocketManager
from services.geofencing_service import GeofencingService
from services.compliance_engine import ComplianceEngine


# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting DeepSeaGuard production server")
    
    # Initialize cache
    await cache_manager.initialize()
    
    # Create database tables (only if they don't exist)
    try:
        Base.metadata.create_all(bind=sync_engine, checkfirst=True)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")
    
    # Initialize services
    app.state.websocket_manager = WebSocketManager()
    app.state.geofencing_service = GeofencingService()
    app.state.compliance_engine = ComplianceEngine(app.state.geofencing_service)
    
    # Inject services into routers
    telemetry.compliance_engine = app.state.compliance_engine
    telemetry.geofencing_service = app.state.geofencing_service
    telemetry.websocket_manager = app.state.websocket_manager
    
    zones.geofencing_service = app.state.geofencing_service
    isa_integration.geofencing_service = app.state.geofencing_service
    
    logger.info("DeepSeaGuard production server started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DeepSeaGuard production server")
    if cache_manager.redis_client:
        await cache_manager.redis_client.close()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Production-ready backend service for AUV telemetry processing and ISA compliance monitoring",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(MetricsMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(compliance.router, prefix="/api/v1", tags=["compliance"])
app.include_router(telemetry.router, prefix="/api/v1", tags=["telemetry"])
app.include_router(zones.router, prefix="/api/v1", tags=["zones"])
app.include_router(isa_integration.router, prefix="/api/v1", tags=["isa-integration"])


# Health check endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    health_data = health_checker.check_system_health()
    status_code = 200 if health_data["status"] == "healthy" else 503
    return JSONResponse(content=health_data, status_code=status_code)


# Metrics endpoint for Prometheus
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return create_metrics_response()


# System status endpoint
@app.get("/status")
async def system_status():
    """System status and statistics"""
    return {
        "status": "running",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": performance_monitor.get_uptime(),
        "cache_stats": await cache_manager.get_cache_stats(),
        "features": [
            "Real-time AUV telemetry processing",
            "ISA compliance monitoring",
            "Real ISA data integration",
            "WebSocket alerts",
            "Advanced geofencing",
            "Production monitoring",
            "Redis caching",
            "Health checks"
        ]
    }


# WebSocket endpoint for real-time alerts
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await app.state.websocket_manager.connect(websocket)
    performance_monitor.update_connection_count(len(app.state.websocket_manager.active_connections))
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        app.state.websocket_manager.disconnect(websocket)
        performance_monitor.update_connection_count(len(app.state.websocket_manager.active_connections))


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": f"{settings.APP_NAME} Production Server",
        "version": settings.APP_VERSION,
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.DEBUG else "disabled in production",
        "health": "/health",
        "metrics": "/metrics",
        "status": "/status"
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        method=request.method
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    uvicorn.run(
        "main_production:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS if settings.ENVIRONMENT == "production" else 1,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    ) 
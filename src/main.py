from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from dotenv import load_dotenv

from database.database import sync_engine, Base
from routers import compliance, telemetry, zones, isa_integration
from services.websocket_manager import WebSocketManager
from services.geofencing_service import GeofencingService
from services.compliance_engine import ComplianceEngine

# Load environment variables
load_dotenv()

# Create database tables
Base.metadata.create_all(bind=sync_engine)

# Initialize FastAPI app
app = FastAPI(
    title="DeepSeaGuard Compliance Engine",
    description="Backend service for AUV telemetry processing and ISA compliance monitoring with real ISA data integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
websocket_manager = WebSocketManager()
geofencing_service = GeofencingService()
compliance_engine = ComplianceEngine(geofencing_service)

# Inject services into routers
telemetry.compliance_engine = compliance_engine
telemetry.geofencing_service = geofencing_service
telemetry.websocket_manager = websocket_manager

zones.geofencing_service = geofencing_service
isa_integration.geofencing_service = geofencing_service

# Include routers
app.include_router(compliance.router, prefix="/api/v1", tags=["compliance"])
app.include_router(telemetry.router, prefix="/api/v1", tags=["telemetry"])
app.include_router(zones.router, prefix="/api/v1", tags=["zones"])
app.include_router(isa_integration.router, prefix="/api/v1", tags=["isa-integration"])

# WebSocket endpoint for real-time alerts
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

@app.get("/")
async def root():
    return {
        "message": "DeepSeaGuard Compliance Engine",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "Real-time AUV telemetry processing",
            "ISA compliance monitoring",
            "Real ISA data integration",
            "WebSocket alerts",
            "Geofencing with proper geometric calculations"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 
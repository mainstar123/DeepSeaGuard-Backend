"""
Telemetry Data Models
Handles AUV telemetry data structures
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

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
    mission_id: Optional[str] = Field(None, description="Mission identifier")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="Additional telemetry data")

class AUVState(BaseModel):
    """AUV state model"""
    auv_id: str
    position: Dict[str, float]
    last_update: datetime
    status: str
    battery_level: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    mission_id: Optional[str] = None

class TelemetryBatch(BaseModel):
    """Batch telemetry data model"""
    batch_id: str
    telemetry_data: list[TelemetryData]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: Optional[str] = Field(None, description="Data source") 
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    ENTRY = "entry"
    EXIT = "exit"
    VIOLATION = "violation"
    WARNING = "warning"

class Status(str, Enum):
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"

class ZoneType(str, Enum):
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"
    PROTECTED = "protected"

class TelemetryData(BaseModel):
    auv_id: str = Field(..., description="Unique identifier for the AUV")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    depth: float = Field(..., ge=0, description="Depth in meters")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the telemetry data")

class ComplianceEventCreate(BaseModel):
    auv_id: str
    zone_id: str
    zone_name: str
    event_type: EventType
    status: Status
    latitude: float
    longitude: float
    depth: float
    duration_minutes: Optional[float] = None
    violation_details: Optional[str] = None

class ComplianceEventResponse(BaseModel):
    id: int
    auv_id: str
    zone_id: str
    zone_name: str
    event_type: EventType
    status: Status
    latitude: float
    longitude: float
    depth: float
    timestamp: datetime
    duration_minutes: Optional[float]
    violation_details: Optional[str]
    
    class Config:
        from_attributes = True

class ISAZoneCreate(BaseModel):
    zone_id: str
    zone_name: str
    zone_type: ZoneType
    max_duration_hours: float
    geojson_data: str

class ISAZoneResponse(BaseModel):
    id: int
    zone_id: str
    zone_name: str
    zone_type: ZoneType
    max_duration_hours: float
    geojson_data: str
    is_active: bool
    
    class Config:
        from_attributes = True

class ZoneStatus(BaseModel):
    auv_id: str
    zone_id: str
    zone_name: str
    zone_type: ZoneType
    status: Status
    current_duration_minutes: float
    max_duration_hours: float
    is_inside: bool
    last_update: datetime

class ComplianceReport(BaseModel):
    auv_id: str
    date: str
    total_violations: int
    total_warnings: int
    zones_visited: List[str]
    total_time_in_zones: float
    events: List[ComplianceEventResponse]

class AlertMessage(BaseModel):
    type: str
    auv_id: str
    zone_id: str
    message: str
    severity: str
    timestamp: datetime
    data: Dict[str, Any] 
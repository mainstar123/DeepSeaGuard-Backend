"""
Compliance Models
Handles compliance and violation data structures
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field

class ViolationType(str, Enum):
    """Types of compliance violations"""
    GEOFENCE_VIOLATION = "geofence_violation"
    SPEED_LIMIT = "speed_limit"
    DEPTH_LIMIT = "depth_limit"
    BATTERY_LOW = "battery_low"
    TIME_RESTRICTION = "time_restriction"
    MISSION_TIMEOUT = "mission_timeout"
    CUSTOM_VIOLATION = "custom_violation"

class ViolationSeverity(str, Enum):
    """Violation severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplianceEvent(BaseModel):
    """Compliance event model"""
    event_id: str
    auv_id: str
    event_type: ViolationType
    severity: ViolationSeverity
    details: Dict[str, Any]
    timestamp: datetime
    location: Optional[Dict[str, float]] = None  # lat, lng, depth
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None

class ComplianceRule(BaseModel):
    """Compliance rule model"""
    rule_id: str
    name: str
    description: str
    rule_type: str  # "geofence", "speed", "depth", "time", "custom"
    conditions: Dict[str, Any]
    severity: ViolationSeverity
    enabled: bool = True
    priority: int = 1
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ComplianceCheck(BaseModel):
    """Compliance check request model"""
    auv_id: str
    timestamp: datetime
    position: Dict[str, float]  # lat, lng, depth
    speed: Optional[float] = None
    heading: Optional[float] = None
    battery_level: Optional[float] = None
    mission_status: Optional[str] = None
    additional_data: Optional[Dict] = None

class ComplianceResult(BaseModel):
    """Compliance check result model"""
    auv_id: str
    timestamp: datetime
    violations: List[Dict]
    warnings: List[Dict]
    compliance_score: float  # 0.0 to 1.0
    risk_level: str  # "low", "medium", "high", "critical"
    recommendations: List[str]
    rules_evaluated: int = 0 
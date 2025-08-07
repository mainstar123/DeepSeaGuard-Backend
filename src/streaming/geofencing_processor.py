"""
Bytewax geofencing processor for advanced spatial-temporal analysis
"""
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple, Optional
import bytewax.operators as op
from bytewax.dataflow import Dataflow
from bytewax.connectors.rabbitmq import RabbitMQInput, RabbitMQOutput
from bytewax.window import SlidingWindowConfig, TumblingWindowConfig
from src.core.logging import get_logger
from src.core.monitoring import performance_monitor

logger = get_logger(__name__)


class ZoneState:
    """State management for zone tracking"""
    
    def __init__(self):
        self.entry_time: Optional[datetime] = None
        self.exit_time: Optional[datetime] = None
        self.total_time_minutes: float = 0.0
        self.entry_count: int = 0
        self.exit_count: int = 0
        self.last_position: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "total_time_minutes": self.total_time_minutes,
            "entry_count": self.entry_count,
            "exit_count": self.exit_count,
            "last_position": self.last_position
        }


def apply_spatial_index(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """Apply spatial indexing for fast geometric queries"""
    try:
        if "error" in telemetry:
            return telemetry
        
        # In a real implementation, this would use R-tree or similar spatial index
        # For now, we'll add spatial metadata
        lat, lon = telemetry["latitude"], telemetry["longitude"]
        
        # Calculate spatial hash for quick lookups
        spatial_hash = f"{int(lat*100)}_{int(lon*100)}"
        
        # Add spatial metadata
        telemetry["spatial_hash"] = spatial_hash
        telemetry["spatial_region"] = get_spatial_region(lat, lon)
        
        logger.debug("Spatial index applied", 
                    auv_id=telemetry["auv_id"], 
                    spatial_hash=spatial_hash)
    
        return telemetry

    except Exception as e:
        logger.error("Spatial indexing failed", error=str(e), auv_id=telemetry.get("auv_id"))
        return telemetry


def get_spatial_region(lat: float, lon: float) -> str:
    """Get spatial region based on coordinates"""
    if 17.0 <= lat <= 18.0 and -78.0 <= lon <= -77.0:
        return "jamaica_basin"
    elif 16.0 <= lat <= 17.0 and -77.0 <= lon <= -76.0:
        return "cayman_trough"
    else:
        return "open_ocean"


def check_zone_intersections(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """Check zone intersections with enhanced spatial analysis"""
    try:
        if "error" in telemetry:
            return telemetry
        
        lat, lon, depth = telemetry["latitude"], telemetry["longitude"], telemetry["depth"]
        zones = []
        
        # Enhanced zone checking with depth consideration
        if 17.5 <= lat <= 18.0 and -78.0 <= lon <= -77.5:
            if depth <= 500:  # Surface to mid-depth
                zones.append({
                    "zone_id": "ISA_ZONE_001",
                    "zone_name": "Jamaica Basin Protected Area",
                    "zone_type": "restricted",
                    "max_duration_hours": 1.0,
                    "depth_range": "surface_to_500m"
                })
            elif depth <= 1000:  # Mid-depth
                zones.append({
                    "zone_id": "ISA_ZONE_001_MID",
                    "zone_name": "Jamaica Basin Protected Area (Mid-Depth)",
                    "zone_type": "sensitive",
                    "max_duration_hours": 2.0,
                    "depth_range": "500m_to_1000m"
                })
        
        if 17.0 <= lat <= 17.5 and -77.5 <= lon <= -77.0:
            zones.append({
                "zone_id": "ISA_ZONE_002",
                "zone_name": "Deep Sea Mining Exploration Zone",
                "zone_type": "sensitive",
                "max_duration_hours": 2.0,
                "depth_range": "all_depths"
            })
        
        # Add boundary proximity analysis
        for zone in zones:
            zone["boundary_distance"] = calculate_boundary_distance(lat, lon, zone["zone_id"])
            zone["is_near_boundary"] = zone["boundary_distance"] < 0.1  # 0.1 degrees
        
        telemetry["zones"] = zones
        telemetry["zone_count"] = len(zones)
        telemetry["spatial_analysis_complete"] = True
        
        performance_monitor.record_zone_check()
        
        logger.debug("Zone intersections checked", 
                    auv_id=telemetry["auv_id"], 
                    zone_count=len(zones))
        
        return telemetry
        
    except Exception as e:
        logger.error("Zone intersection check failed", error=str(e), auv_id=telemetry.get("auv_id"))
        telemetry["zones"] = []
        telemetry["zone_count"] = 0
        return telemetry


def calculate_boundary_distance(lat: float, lon: float, zone_id: str) -> float:
    """Calculate distance to zone boundary (simplified)"""
    # In real implementation, this would use proper geometric calculations
    if zone_id == "ISA_ZONE_001":
        return min(abs(lat - 17.5), abs(lat - 18.0), abs(lon + 78.0), abs(lon + 77.5))
    elif zone_id == "ISA_ZONE_002":
        return min(abs(lat - 17.0), abs(lat - 17.5), abs(lon + 77.5), abs(lon + 77.0))
    return 0.0


def detect_entry_exit(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """Detect zone entry and exit events with state management"""
    try:
        if "error" in telemetry:
            return telemetry
        
        auv_id = telemetry["auv_id"]
        current_zones = {zone["zone_id"] for zone in telemetry.get("zones", [])}
        timestamp = telemetry["timestamp"]
        
        # Get previous state (in real implementation, this would use Bytewax state)
        previous_zones = set()  # Would be retrieved from state
        
        events = []
        
        # Detect entries
        for zone in telemetry.get("zones", []):
            zone_id = zone["zone_id"]
            if zone_id not in previous_zones:
                entry_event = {
                    "event_type": "zone_entry",
                    "auv_id": auv_id,
                    "zone_id": zone_id,
                    "zone_name": zone["zone_name"],
                    "zone_type": zone["zone_type"],
                    "timestamp": timestamp,
                    "position": {
                        "latitude": telemetry["latitude"],
                        "longitude": telemetry["longitude"],
                        "depth": telemetry["depth"]
                    },
                    "boundary_distance": zone.get("boundary_distance", 0),
                    "is_near_boundary": zone.get("is_near_boundary", False)
                }
                events.append(entry_event)
                logger.info("Zone entry detected", 
                           auv_id=auv_id, 
                           zone_id=zone_id, 
                           zone_name=zone["zone_name"])
        
        # Detect exits (simplified - would use actual state)
        for zone_id in previous_zones - current_zones:
            exit_event = {
                "event_type": "zone_exit",
                "auv_id": auv_id,
                "zone_id": zone_id,
                "timestamp": timestamp,
                "position": {
                    "latitude": telemetry["latitude"],
                    "longitude": telemetry["longitude"],
                    "depth": telemetry["depth"]
                }
            }
            events.append(exit_event)
            logger.info("Zone exit detected", auv_id=auv_id, zone_id=zone_id)
        
        telemetry["zone_events"] = events
        telemetry["has_zone_events"] = len(events) > 0
        
        return telemetry
        
    except Exception as e:
        logger.error("Entry/exit detection failed", error=str(e), auv_id=telemetry.get("auv_id"))
        telemetry["zone_events"] = []
        telemetry["has_zone_events"] = False
        return telemetry


def track_zone_duration(telemetry_batch: Tuple[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Track duration in zones using time windows"""
    try:
        auv_id, telemetry_list = telemetry_batch
        
        if not telemetry_list:
            return {"auv_id": auv_id, "error": "No telemetry data"}
        
        # Calculate duration statistics for each zone
        zone_durations = {}
        
        for telemetry in telemetry_list:
            for zone in telemetry.get("zones", []):
                zone_id = zone["zone_id"]
                if zone_id not in zone_durations:
                    zone_durations[zone_id] = {
                        "zone_name": zone["zone_name"],
                        "zone_type": zone["zone_type"],
                        "total_time_minutes": 0,
                        "entry_count": 0,
                        "last_seen": None
                    }
                
                # Simulate time tracking (in real implementation, this would use actual state)
                zone_durations[zone_id]["total_time_minutes"] += 1  # 1 minute per update
                zone_durations[zone_id]["last_seen"] = telemetry["timestamp"]
        
        # Check for violations
        violations = []
        for zone_id, duration_data in zone_durations.items():
            max_duration = 0
            for zone in telemetry_list[-1].get("zones", []):
                if zone["zone_id"] == zone_id:
                    max_duration = zone["max_duration_hours"] * 60
                    break
            
            if duration_data["total_time_minutes"] > max_duration:
                violations.append({
                    "zone_id": zone_id,
                    "zone_name": duration_data["zone_name"],
                    "zone_type": duration_data["zone_type"],
                    "time_spent_minutes": duration_data["total_time_minutes"],
                    "max_allowed_minutes": max_duration,
                    "severity": "critical" if duration_data["zone_type"] == "restricted" else "warning"
                })
        
        result = {
            "auv_id": auv_id,
            "timestamp": datetime.now(timezone.utc),
            "zone_durations": zone_durations,
            "violations": violations,
            "has_violations": len(violations) > 0
        }
        
        logger.info("Zone duration tracking completed", 
                   auv_id=auv_id, 
                   zones_tracked=len(zone_durations),
                   violations=len(violations))
        
        return result
        
    except Exception as e:
        logger.error("Zone duration tracking failed", error=str(e), auv_id=auv_id)
        return {"auv_id": auv_id, "error": str(e)}


def create_geofencing_flow() -> Dataflow:
    """Create Bytewax dataflow for advanced geofencing"""
    flow = Dataflow("geofencing_processor")
    
    # Input: Enriched telemetry from telemetry processor
    telemetry_stream = op.input("geofencing_input", flow, RabbitMQInput(
        queue_name="enriched_telemetry",
        host="localhost",
        port=5672,
        username="guest",
        password="guest"
    ))
    
    # Apply spatial indexing
    indexed_telemetry = op.map("spatial_index", telemetry_stream, apply_spatial_index)
    
    # Check zone intersections
    zone_intersections = op.map("check_zones", indexed_telemetry, check_zone_intersections)
    
    # Detect entry/exit events
    entry_exit_events = op.map("detect_events", zone_intersections, detect_entry_exit)
    
    # Filter events that have zone activity
    zone_activity = op.filter("filter_activity", entry_exit_events, lambda x: x.get('has_zone_events', False))
    
    # Key by AUV ID for stateful processing
    keyed_telemetry = op.map("key_by_auv", zone_activity, lambda x: (x['auv_id'], x))
    
    # Time-window analysis for duration tracking
    time_windows = op.window.collect_window(
        "time_analysis",
        keyed_telemetry,
        window_config=SlidingWindowConfig(
            size=timedelta(minutes=5),
            step=timedelta(minutes=1)
        )
    )
    
    # Track duration in zones
    duration_analysis = op.map("duration_tracking", time_windows, track_zone_duration)
    
    # Filter results with violations
    violations = op.filter("filter_violations", duration_analysis, lambda x: x.get('has_violations', False))
    
    # Output zone events to alert queue
    op.output("zone_events_output", zone_activity, RabbitMQOutput(
        queue_name="zone_events",
        host="localhost",
        port=5672,
        username="guest",
        password="guest"
    ))
    
    # Output duration violations to compliance queue
    op.output("duration_violations_output", violations, RabbitMQOutput(
        queue_name="duration_violations",
        host="localhost",
        port=5672,
        username="guest",
        password="guest"
    ))
    
    # Output all geofencing data to analytics
    op.output("geofencing_analytics_output", duration_analysis, RabbitMQOutput(
        queue_name="geofencing_analytics",
        host="localhost",
        port=5672,
        username="guest",
        password="guest"
    ))
    
    return flow


if __name__ == "__main__":
    # Create and run the dataflow
    flow = create_geofencing_flow()
    
    logger.info("Starting Bytewax geofencing processor")
    
    # Run the dataflow
    from bytewax.run import run_main
    run_main(flow) 
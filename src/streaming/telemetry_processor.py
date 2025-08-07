"""
Bytewax telemetry processor for real-time AUV data processing
"""
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
import bytewax.operators as op
from bytewax.dataflow import Dataflow
from bytewax.connectors.rabbitmq import RabbitMQInput, RabbitMQOutput
from bytewax.connectors.kafka import KafkaOutput
from bytewax.window import SlidingWindowConfig, TumblingWindowConfig
from src.core.logging import get_logger
from src.core.monitoring import performance_monitor

logger = get_logger(__name__)


def parse_telemetry_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse and validate telemetry data"""
    try:
        # Extract telemetry data
        telemetry = {
            "auv_id": data.get("auv_id"),
            "latitude": float(data.get("latitude", 0)),
            "longitude": float(data.get("longitude", 0)),
            "depth": float(data.get("depth", 0)),
            "timestamp": datetime.fromisoformat(data.get("timestamp").replace("Z", "+00:00")),
            "speed": float(data.get("speed", 0)),
            "heading": float(data.get("heading", 0)),
            "battery_level": float(data.get("battery_level", 100)),
            "status": data.get("status", "active")
        }
        
        # Validate required fields
        if not telemetry["auv_id"]:
            raise ValueError("auv_id is required")
        
        if not (-90 <= telemetry["latitude"] <= 90):
            raise ValueError("Invalid latitude")
        
        if not (-180 <= telemetry["longitude"] <= 180):
            raise ValueError("Invalid longitude")
        
        telemetry["processed_at"] = datetime.now(timezone.utc)
        telemetry["processing_id"] = f"{telemetry['auv_id']}_{int(time.time())}"
        
        logger.info("Telemetry parsed successfully", auv_id=telemetry["auv_id"])
        return telemetry
        
    except Exception as e:
        logger.error("Telemetry parsing failed", error=str(e), data=data)
        return {"error": str(e), "raw_data": data}


def enrich_with_zones(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich telemetry with zone information"""
    try:
        if "error" in telemetry:
            return telemetry
        
        # This would integrate with the geofencing service
        # For now, we'll simulate zone checking
        zones = []
        
        # Simulate zone intersection check
        lat, lon = telemetry["latitude"], telemetry["longitude"]
        
        # Example zone checks (in real implementation, this would use spatial index)
        if 17.5 <= lat <= 18.0 and -78.0 <= lon <= -77.5:
            zones.append({
                "zone_id": "ISA_ZONE_001",
                "zone_name": "Jamaica Basin Protected Area",
                "zone_type": "restricted",
                "max_duration_hours": 1.0
            })
        
        if 17.0 <= lat <= 17.5 and -77.5 <= lon <= -77.0:
            zones.append({
                "zone_id": "ISA_ZONE_002", 
                "zone_name": "Deep Sea Mining Exploration Zone",
                "zone_type": "sensitive",
                "max_duration_hours": 2.0
            })
        
        telemetry["zones"] = zones
        telemetry["zone_count"] = len(zones)
        
        performance_monitor.record_zone_check()
        
        logger.debug("Zones enriched", auv_id=telemetry["auv_id"], zone_count=len(zones))
        return telemetry
        
    except Exception as e:
        logger.error("Zone enrichment failed", error=str(e), auv_id=telemetry.get("auv_id"))
        telemetry["zones"] = []
        telemetry["zone_count"] = 0
        return telemetry


def check_compliance_rules(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """Check compliance rules for telemetry data"""
    try:
        if "error" in telemetry:
            return telemetry
        
        violations = []
        warnings = []
        
        # Check zone violations
        for zone in telemetry.get("zones", []):
            zone_id = zone["zone_id"]
            zone_type = zone["zone_type"]
            
            # Simulate time tracking (in real implementation, this would use state management)
            time_in_zone = 30  # minutes - would be calculated from state
            
            if time_in_zone > zone["max_duration_hours"] * 60:
                violation = {
                    "type": "time_limit_exceeded",
                    "zone_id": zone_id,
                    "zone_name": zone["zone_name"],
                    "zone_type": zone_type,
                    "time_in_zone_minutes": time_in_zone,
                    "max_allowed_minutes": zone["max_duration_hours"] * 60,
                    "severity": "critical" if zone_type == "restricted" else "warning"
                }
                
                if violation["severity"] == "critical":
                    violations.append(violation)
                    performance_monitor.record_compliance_violation(zone_type, "critical")
                else:
                    warnings.append(violation)
                    performance_monitor.record_compliance_violation(zone_type, "warning")
        
        # Check depth violations
        if telemetry["depth"] > 1000:  # meters
            violations.append({
                "type": "depth_limit_exceeded",
                "current_depth": telemetry["depth"],
                "max_depth": 1000,
                "severity": "warning"
            })
        
        # Check battery level
        if telemetry["battery_level"] < 20:
            warnings.append({
                "type": "low_battery",
                "battery_level": telemetry["battery_level"],
                "severity": "warning"
            })
        
        telemetry["violations"] = violations
        telemetry["warnings"] = warnings
        telemetry["has_violations"] = len(violations) > 0
        telemetry["has_warnings"] = len(warnings) > 0
        
        logger.info("Compliance check completed", 
                   auv_id=telemetry["auv_id"], 
                   violations=len(violations), 
                   warnings=len(warnings))
        
        return telemetry
        
    except Exception as e:
        logger.error("Compliance check failed", error=str(e), auv_id=telemetry.get("auv_id"))
        telemetry["violations"] = []
        telemetry["warnings"] = []
        telemetry["has_violations"] = False
        telemetry["has_warnings"] = False
        return telemetry


def create_telemetry_flow() -> Dataflow:
    """Create Bytewax dataflow for telemetry processing"""
    flow = Dataflow("telemetry_processor")
    
    # Input: AUV telemetry from RabbitMQ
    telemetry_stream = op.input("telemetry_input", flow, RabbitMQInput(
        queue_name="auv_telemetry",
        host="localhost",
        port=5672,
        username="guest",
        password="guest"
    ))
    
    # Parse and validate telemetry data
    parsed_telemetry = op.map("parse_telemetry", telemetry_stream, parse_telemetry_data)
    
    # Filter out parsing errors
    valid_telemetry = op.filter("filter_valid", parsed_telemetry, lambda x: "error" not in x)
    error_telemetry = op.filter("filter_errors", parsed_telemetry, lambda x: "error" in x)
    
    # Enrich with zone information
    enriched_telemetry = op.map("enrich_zones", valid_telemetry, enrich_with_zones)
    
    # Check compliance rules
    compliance_results = op.map("check_compliance", enriched_telemetry, check_compliance_rules)
    
    # Route results based on outcome
    violations = op.filter("filter_violations", compliance_results, lambda x: x.get('has_violations', False))
    warnings = op.filter("filter_warnings", compliance_results, lambda x: x.get('has_warnings', False) and not x.get('has_violations', False))
    normal_operations = op.filter("filter_normal", compliance_results, lambda x: not x.get('has_violations', False) and not x.get('has_warnings', False))
    
    # Output violations to alert queue
    op.output("violation_output", violations, RabbitMQOutput(
        queue_name="compliance_violations",
        host="localhost",
        port=5672,
        username="guest",
        password="guest"
    ))
    
    # Output warnings to warning queue
    op.output("warning_output", warnings, RabbitMQOutput(
        queue_name="compliance_warnings",
        host="localhost",
        port=5672,
        username="guest",
        password="guest"
    ))
    
    # Output normal operations to analytics
    op.output("analytics_output", normal_operations, KafkaOutput(
        topic="auv_analytics",
        brokers=["localhost:9092"]
    ))
    
    # Output errors to error queue
    op.output("error_output", error_telemetry, RabbitMQOutput(
        queue_name="telemetry_errors",
        host="localhost",
        port=5672,
        username="guest",
        password="guest"
    ))
    
    return flow


if __name__ == "__main__":
    # Create and run the dataflow
    flow = create_telemetry_flow()
    
    logger.info("Starting Bytewax telemetry processor")
    
    # Run the dataflow
    from bytewax.run import run_main
    run_main(flow) 
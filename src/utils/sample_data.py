import json
from datetime import datetime, timedelta
import random
from typing import List, Dict, Any

def create_sample_isa_zones() -> List[Dict[str, Any]]:
    """Create sample ISA zones for testing"""
    
    # Sample sensitive zone (Jamaica)
    sensitive_zone = {
        "zone_id": "JM_SENSITIVE_001",
        "zone_name": "Jamaica Deep Sea Mining Sensitive Zone",
        "zone_type": "sensitive",
        "max_duration_hours": 1.0,
        "geojson_data": json.dumps({
            "type": "Feature",
            "properties": {
                "zone_id": "JM_SENSITIVE_001",
                "zone_name": "Jamaica Deep Sea Mining Sensitive Zone",
                "zone_type": "sensitive",
                "max_duration_hours": 1.0
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-78.0, 17.5],
                    [-77.5, 17.5],
                    [-77.5, 18.0],
                    [-78.0, 18.0],
                    [-78.0, 17.5]
                ]]
            }
        })
    }
    
    # Sample restricted zone
    restricted_zone = {
        "zone_id": "JM_RESTRICTED_001",
        "zone_name": "Jamaica Marine Protected Area",
        "zone_type": "restricted",
        "max_duration_hours": 0.5,
        "geojson_data": json.dumps({
            "type": "Feature",
            "properties": {
                "zone_id": "JM_RESTRICTED_001",
                "zone_name": "Jamaica Marine Protected Area",
                "zone_type": "restricted",
                "max_duration_hours": 0.5
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-77.8, 17.7],
                    [-77.6, 17.7],
                    [-77.6, 17.9],
                    [-77.8, 17.9],
                    [-77.8, 17.7]
                ]]
            }
        })
    }
    
    # Sample protected zone
    protected_zone = {
        "zone_id": "JM_PROTECTED_001",
        "zone_name": "Jamaica Coral Reef Protected Zone",
        "zone_type": "protected",
        "max_duration_hours": 2.0,
        "geojson_data": json.dumps({
            "type": "Feature",
            "properties": {
                "zone_id": "JM_PROTECTED_001",
                "zone_name": "Jamaica Coral Reef Protected Zone",
                "zone_type": "protected",
                "max_duration_hours": 2.0
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-77.9, 17.6],
                    [-77.7, 17.6],
                    [-77.7, 17.8],
                    [-77.9, 17.8],
                    [-77.9, 17.6]
                ]]
            }
        })
    }
    
    return [sensitive_zone, restricted_zone, protected_zone]

def generate_sample_telemetry(
    auv_id: str,
    start_time: datetime = None,
    duration_minutes: int = 60,
    interval_seconds: int = 30
) -> List[Dict[str, Any]]:
    """Generate sample AUV telemetry data"""
    
    if start_time is None:
        start_time = datetime.utcnow() - timedelta(minutes=duration_minutes)
    
    telemetry_data = []
    current_time = start_time
    
    # Start position (outside zones)
    lat = 17.3
    lng = -78.2
    depth = 100
    
    # Movement patterns
    movements = [
        # Move towards sensitive zone
        {"lat_delta": 0.1, "lng_delta": 0.1, "depth_delta": -10},
        # Enter sensitive zone
        {"lat_delta": 0.05, "lng_delta": 0.05, "depth_delta": -5},
        # Stay in zone
        {"lat_delta": 0.01, "lng_delta": 0.01, "depth_delta": 0},
        # Exit zone
        {"lat_delta": -0.05, "lng_delta": -0.05, "depth_delta": 5},
        # Move to restricted zone
        {"lat_delta": 0.2, "lng_delta": 0.1, "depth_delta": -15},
        # Enter restricted zone
        {"lat_delta": 0.02, "lng_delta": 0.02, "depth_delta": -2},
        # Exit restricted zone
        {"lat_delta": -0.1, "lng_delta": -0.1, "depth_delta": 10}
    ]
    
    movement_index = 0
    steps_in_movement = 0
    max_steps_per_movement = 10
    
    while current_time < start_time + timedelta(minutes=duration_minutes):
        # Update position based on movement pattern
        if steps_in_movement >= max_steps_per_movement:
            movement_index = (movement_index + 1) % len(movements)
            steps_in_movement = 0
        
        movement = movements[movement_index]
        lat += movement["lat_delta"] * 0.01  # Scale down movement
        lng += movement["lng_delta"] * 0.01
        depth += movement["depth_delta"]
        
        # Add some randomness
        lat += random.uniform(-0.001, 0.001)
        lng += random.uniform(-0.001, 0.001)
        depth += random.uniform(-1, 1)
        
        # Ensure depth stays reasonable
        depth = max(50, min(500, depth))
        
        telemetry_data.append({
            "auv_id": auv_id,
            "latitude": lat,
            "longitude": lng,
            "depth": depth,
            "timestamp": current_time.isoformat()
        })
        
        current_time += timedelta(seconds=interval_seconds)
        steps_in_movement += 1
    
    return telemetry_data

def create_sample_geojson_file(filename: str = "sample_isa_zones.geojson"):
    """Create a sample GeoJSON file with ISA zones"""
    
    zones = create_sample_isa_zones()
    features = []
    
    for zone in zones:
        geojson = json.loads(zone["geojson_data"])
        features.append(geojson)
    
    geojson_collection = {
        "type": "FeatureCollection",
        "features": features
    }
    
    with open(filename, 'w') as f:
        json.dump(geojson_collection, f, indent=2)
    
    print(f"Created sample GeoJSON file: {filename}")
    return filename

def generate_violation_scenario() -> List[Dict[str, Any]]:
    """Generate telemetry that will trigger violations"""
    
    # Start inside sensitive zone and stay too long
    start_time = datetime.utcnow() - timedelta(hours=2)  # Start 2 hours ago
    
    telemetry_data = []
    current_time = start_time
    
    # Start inside sensitive zone
    lat = 17.75  # Inside sensitive zone
    lng = -77.75
    depth = 150
    
    # Stay in zone for 2 hours (violation)
    while current_time < datetime.utcnow():
        # Small random movement within zone
        lat += random.uniform(-0.01, 0.01)
        lng += random.uniform(-0.01, 0.01)
        depth += random.uniform(-5, 5)
        
        # Keep within zone bounds
        lat = max(17.5, min(18.0, lat))
        lng = max(-78.0, min(-77.5, lng))
        depth = max(100, min(200, depth))
        
        telemetry_data.append({
            "auv_id": "AUV_VIOLATION_TEST",
            "latitude": lat,
            "longitude": lng,
            "depth": depth,
            "timestamp": current_time.isoformat()
        })
        
        current_time += timedelta(minutes=5)  # Update every 5 minutes
    
    return telemetry_data

if __name__ == "__main__":
    # Create sample GeoJSON file
    create_sample_geojson_file()
    
    # Generate sample telemetry
    telemetry = generate_sample_telemetry("AUV_TEST_001", duration_minutes=30)
    print(f"Generated {len(telemetry)} telemetry points")
    
    # Generate violation scenario
    violation_telemetry = generate_violation_scenario()
    print(f"Generated {len(violation_telemetry)} violation scenario points") 
import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json

def generate_sample_telemetry(
    auv_id: str, 
    duration_minutes: int = 30,
    start_position: Tuple[float, float] = None,
    zone_coordinates: List[List[float]] = None
) -> List[Dict]:
    """
    Generate realistic AUV telemetry data for testing
    
    Args:
        auv_id: AUV identifier
        duration_minutes: Duration of telemetry data to generate
        start_position: Starting position (lat, lng) - if None, uses random position
        zone_coordinates: Zone coordinates to simulate movement within
    """
    
    if start_position is None:
        # Default to Jamaica area coordinates
        start_lat = 17.75
        start_lng = -77.75
    else:
        start_lat, start_lng = start_position
    
    # Generate timestamps
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=duration_minutes)
    
    # Calculate number of data points (1 per minute)
    num_points = duration_minutes
    time_interval = duration_minutes / num_points
    
    telemetry_data = []
    
    current_lat = start_lat
    current_lng = start_lng
    current_depth = random.uniform(100, 300)
    
    for i in range(num_points):
        # Calculate timestamp
        timestamp = start_time + timedelta(minutes=i * time_interval)
        
        # Simulate realistic movement
        if zone_coordinates:
            # Move within zone boundaries
            current_lat, current_lng = _move_within_zone(
                current_lat, current_lng, zone_coordinates
            )
        else:
            # Random movement
            current_lat += random.uniform(-0.01, 0.01)
            current_lng += random.uniform(-0.01, 0.01)
        
        # Simulate depth changes
        depth_change = random.uniform(-10, 10)
        current_depth = max(50, min(500, current_depth + depth_change))
        
        telemetry_point = {
            "auv_id": auv_id,
            "latitude": round(current_lat, 6),
            "longitude": round(current_lng, 6),
            "depth": round(current_depth, 2),
            "timestamp": timestamp.isoformat()
        }
        
        telemetry_data.append(telemetry_point)
    
    return telemetry_data

def generate_violation_scenario(
    auv_id: str = "AUV_VIOLATION_TEST",
    zone_coordinates: List[List[float]] = None
) -> List[Dict]:
    """
    Generate telemetry data that will trigger compliance violations
    """
    
    if zone_coordinates is None:
        # Default Jamaica zone coordinates
        zone_coordinates = [
            [-78.0, 17.5],
            [-77.5, 17.5],
            [-77.5, 18.0],
            [-78.0, 18.0],
            [-78.0, 17.5]
        ]
    
    # Generate 2 hours of data (exceeding 1-hour limit for sensitive zones)
    return generate_sample_telemetry(
        auv_id=auv_id,
        duration_minutes=120,
        start_position=(17.75, -77.75),
        zone_coordinates=zone_coordinates
    )

def generate_multi_auv_scenario(
    auv_ids: List[str] = None,
    duration_minutes: int = 60
) -> List[Dict]:
    """
    Generate telemetry data for multiple AUVs
    """
    
    if auv_ids is None:
        auv_ids = ["AUV_001", "AUV_002", "AUV_003"]
    
    all_telemetry = []
    
    for auv_id in auv_ids:
        # Generate different starting positions
        start_lat = 17.5 + random.uniform(0, 0.5)
        start_lng = -77.5 + random.uniform(0, 0.5)
        
        auv_telemetry = generate_sample_telemetry(
            auv_id=auv_id,
            duration_minutes=duration_minutes,
            start_position=(start_lat, start_lng)
        )
        
        all_telemetry.extend(auv_telemetry)
    
    # Sort by timestamp
    all_telemetry.sort(key=lambda x: x['timestamp'])
    
    return all_telemetry

def _move_within_zone(
    current_lat: float, 
    current_lng: float, 
    zone_coordinates: List[List[float]]
) -> Tuple[float, float]:
    """
    Move AUV within zone boundaries
    """
    # Simple boundary checking
    min_lat = min(coord[1] for coord in zone_coordinates)
    max_lat = max(coord[1] for coord in zone_coordinates)
    min_lng = min(coord[0] for coord in zone_coordinates)
    max_lng = max(coord[0] for coord in zone_coordinates)
    
    # Generate new position
    new_lat = current_lat + random.uniform(-0.005, 0.005)
    new_lng = current_lng + random.uniform(-0.005, 0.005)
    
    # Ensure within boundaries
    new_lat = max(min_lat, min(max_lat, new_lat))
    new_lng = max(min_lng, min(max_lng, new_lng))
    
    return new_lat, new_lng

def generate_isa_test_zones() -> List[Dict]:
    """
    Generate test ISA zones for development
    """
    
    zones = [
        {
            "zone_id": "TEST_SENSITIVE_001",
            "zone_name": "Test Sensitive Zone",
            "zone_type": "sensitive",
            "max_duration_hours": 1.0,
            "geojson_data": json.dumps({
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-77.8, 17.6],
                        [-77.6, 17.6],
                        [-77.6, 17.8],
                        [-77.8, 17.8],
                        [-77.8, 17.6]
                    ]]
                }
            })
        },
        {
            "zone_id": "TEST_RESTRICTED_001",
            "zone_name": "Test Restricted Zone",
            "zone_type": "restricted",
            "max_duration_hours": 0.5,
            "geojson_data": json.dumps({
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-77.7, 17.7],
                        [-77.5, 17.7],
                        [-77.5, 17.9],
                        [-77.7, 17.9],
                        [-77.7, 17.7]
                    ]]
                }
            })
        },
        {
            "zone_id": "TEST_PROTECTED_001",
            "zone_name": "Test Protected Zone",
            "zone_type": "protected",
            "max_duration_hours": 2.0,
            "geojson_data": json.dumps({
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-77.9, 17.5],
                        [-77.7, 17.5],
                        [-77.7, 17.7],
                        [-77.9, 17.7],
                        [-77.9, 17.5]
                    ]]
                }
            })
        }
    ]
    
    return zones

def generate_compliance_test_scenarios() -> Dict[str, List[Dict]]:
    """
    Generate various compliance test scenarios
    """
    
    scenarios = {}
    
    # Scenario 1: Normal operation within limits
    scenarios["normal_operation"] = generate_sample_telemetry(
        "AUV_NORMAL_001", 
        duration_minutes=30,
        start_position=(17.75, -77.75)
    )
    
    # Scenario 2: Violation - exceeding time limit
    scenarios["time_violation"] = generate_violation_scenario("AUV_VIOLATION_001")
    
    # Scenario 3: Multiple AUVs
    scenarios["multi_auv"] = generate_multi_auv_scenario(
        ["AUV_MULTI_001", "AUV_MULTI_002", "AUV_MULTI_003"],
        duration_minutes=45
    )
    
    # Scenario 4: Rapid movement (potential suspicious activity)
    scenarios["rapid_movement"] = generate_sample_telemetry(
        "AUV_RAPID_001",
        duration_minutes=60,
        start_position=(17.75, -77.75)
    )
    
    return scenarios

def save_sample_data_to_file(filename: str, data: List[Dict]):
    """
    Save sample data to JSON file for testing
    """
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"Sample data saved to {filename}")

def load_sample_data_from_file(filename: str) -> List[Dict]:
    """
    Load sample data from JSON file
    """
    with open(filename, 'r') as f:
        return json.load(f)

# Example usage functions
def create_test_dataset():
    """
    Create a comprehensive test dataset
    """
    
    # Generate test zones
    zones = generate_isa_test_zones()
    save_sample_data_to_file("test_zones.json", zones)
    
    # Generate test scenarios
    scenarios = generate_compliance_test_scenarios()
    
    for scenario_name, telemetry_data in scenarios.items():
        filename = f"test_telemetry_{scenario_name}.json"
        save_sample_data_to_file(filename, telemetry_data)
    
    print("Test dataset created successfully!")
    print("Files created:")
    print("- test_zones.json")
    for scenario_name in scenarios.keys():
        print(f"- test_telemetry_{scenario_name}.json")

if __name__ == "__main__":
    create_test_dataset() 
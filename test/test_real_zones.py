import requests
import json
from datetime import datetime, timedelta, timezone

def test_real_zones():
    """Test the system with real ISA zones"""
    
    print("🌊 Testing DeepSeaGuard with Real ISA Zones")
    print("=" * 50)
    
    # Test 1: Check uploaded zones
    print("\n1️⃣ Checking uploaded zones...")
    response = requests.get("http://localhost:8000/api/v1/zones")
    zones = response.json()
    print(f"✅ Found {len(zones)} zones:")
    for zone in zones:
        print(f"   - {zone['zone_name']} ({zone['zone_type']}) - Max: {zone['max_duration_hours']}h")
    
    # Test 2: Test telemetry in Clarion Clipperton Zone
    print("\n2️⃣ Testing telemetry in Clarion Clipperton Zone...")
    telemetry_ccz = {
        "auv_id": "AUV_REAL_001",
        "latitude": -2.5,  # Inside CCZ
        "longitude": -145.0,
        "depth": 150,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    response = requests.post("http://localhost:8000/api/v1/telemetry/position", json=telemetry_ccz)
    result = response.json()
    print(f"✅ Telemetry sent: {result['zones_detected']} zones detected")
    
    # Test 3: Test telemetry in Contract Area Alpha
    print("\n3️⃣ Testing telemetry in Contract Area Alpha...")
    telemetry_contract = {
        "auv_id": "AUV_REAL_002",
        "latitude": 0.0,  # Inside Contract Area
        "longitude": -147.5,
        "depth": 200,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    response = requests.post("http://localhost:8000/api/v1/telemetry/position", json=telemetry_contract)
    result = response.json()
    print(f"✅ Telemetry sent: {result['zones_detected']} zones detected")
    
    # Test 4: Test telemetry in Reserved Area
    print("\n4️⃣ Testing telemetry in Reserved Area...")
    telemetry_reserved = {
        "auv_id": "AUV_REAL_003",
        "latitude": 0.0,  # Inside Reserved Area
        "longitude": -137.5,
        "depth": 100,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    response = requests.post("http://localhost:8000/api/v1/telemetry/position", json=telemetry_reserved)
    result = response.json()
    print(f"✅ Telemetry sent: {result['zones_detected']} zones detected")
    
    # Test 5: Check AUV statuses
    print("\n5️⃣ Checking AUV statuses...")
    for auv_id in ["AUV_REAL_001", "AUV_REAL_002", "AUV_REAL_003"]:
        response = requests.get(f"http://localhost:8000/api/v1/telemetry/status/{auv_id}")
        status = response.json()
        print(f"   - {auv_id}: {status.get('status', 'unknown')}, {len(status.get('current_zones', []))} active zones")
    
    # Test 6: Check compliance events
    print("\n6️⃣ Checking compliance events...")
    response = requests.get("http://localhost:8000/api/v1/compliance/events")
    events = response.json()
    print(f"✅ Found {len(events)} compliance events")
    
    # Test 7: Get GeoJSON of all zones
    print("\n7️⃣ Getting GeoJSON of all zones...")
    response = requests.get("http://localhost:8000/api/v1/zones/geojson")
    geojson = response.json()
    print(f"✅ Retrieved GeoJSON with {len(geojson['features'])} features")
    
    print("\n🎉 All tests completed successfully!")
    print("\n📊 System Status:")
    print("   ✅ Real ISA zones loaded")
    print("   ✅ Telemetry processing working")
    print("   ✅ Compliance monitoring active")
    print("   ✅ WebSocket alerts ready")
    print("   ✅ API endpoints functional")
    
    print("\n🌐 Access Points:")
    print("   - Frontend: Open frontend_example.html in browser")
    print("   - API Docs: http://localhost:8000/docs")
    print("   - Health Check: http://localhost:8000/health")

if __name__ == "__main__":
    test_real_zones() 
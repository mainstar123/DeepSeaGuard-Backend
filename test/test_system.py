#!/usr/bin/env python3
"""
Test script for DeepSeaGuard Compliance Engine
Demonstrates the core functionality with sample data
"""

import requests
import json
import time
from datetime import datetime, timedelta
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.sample_data import generate_sample_telemetry, generate_violation_scenario

BASE_URL = "http://localhost:8000"

def test_health():
    """Test if the server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print("❌ Server health check failed")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on localhost:8000")
        return False

def test_zones():
    """Test zone management endpoints"""
    print("\n🗺️ Testing Zone Management...")
    
    # Get all zones
    response = requests.get(f"{BASE_URL}/api/v1/zones")
    if response.status_code == 200:
        zones = response.json()
        print(f"✅ Found {len(zones)} zones:")
        for zone in zones:
            print(f"   - {zone['zone_name']} ({zone['zone_type']}) - Max: {zone['max_duration_hours']}h")
    else:
        print("❌ Failed to get zones")
        return False
    
    # Get zones as GeoJSON
    response = requests.get(f"{BASE_URL}/api/v1/zones/geojson")
    if response.status_code == 200:
        geojson = response.json()
        print(f"✅ GeoJSON contains {len(geojson['features'])} features")
    else:
        print("❌ Failed to get GeoJSON")
        return False
    
    return True

def test_telemetry_processing():
    """Test telemetry processing with sample data"""
    print("\n📡 Testing Telemetry Processing...")
    
    # Generate sample telemetry
    telemetry_data = generate_sample_telemetry("AUV_TEST_001", duration_minutes=5)
    print(f"Generated {len(telemetry_data)} telemetry points")
    
    # Process telemetry
    for i, data in enumerate(telemetry_data[:10]):  # Process first 10 points
        response = requests.post(f"{BASE_URL}/api/v1/telemetry/position", json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Telemetry {i+1}: {result['zones_detected']} zones detected")
        else:
            print(f"❌ Failed to process telemetry {i+1}")
            return False
    
    # Check AUV status
    response = requests.get(f"{BASE_URL}/api/v1/telemetry/status/AUV_TEST_001")
    if response.status_code == 200:
        status = response.json()
        print(f"✅ AUV Status: {status['status']}, {len(status['current_zones'])} active zones")
    else:
        print("❌ Failed to get AUV status")
        return False
    
    return True

def test_violation_scenario():
    """Test violation detection"""
    print("\n⚠️ Testing Violation Detection...")
    
    # Generate violation scenario
    violation_data = generate_violation_scenario()
    print(f"Generated {len(violation_data)} violation scenario points")
    
    # Process violation telemetry
    for i, data in enumerate(violation_data[:5]):  # Process first 5 points
        response = requests.post(f"{BASE_URL}/api/v1/telemetry/position", json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Violation telemetry {i+1}: {result['zones_detected']} zones detected")
        else:
            print(f"❌ Failed to process violation telemetry {i+1}")
            return False
    
    # Check for violations
    response = requests.get(f"{BASE_URL}/api/v1/compliance/violations")
    if response.status_code == 200:
        violations = response.json()
        print(f"✅ Found {len(violations)} violations")
        for violation in violations[:3]:  # Show first 3 violations
            print(f"   - {violation['auv_id']} in {violation['zone_name']}: {violation['violation_details']}")
    else:
        print("❌ Failed to get violations")
        return False
    
    return True

def test_compliance_events():
    """Test compliance event management"""
    print("\n📊 Testing Compliance Events...")
    
    # Get compliance events
    response = requests.get(f"{BASE_URL}/api/v1/compliance/events?limit=10")
    if response.status_code == 200:
        events = response.json()
        print(f"✅ Found {len(events)} compliance events")
        
        # Group by event type
        event_types = {}
        for event in events:
            event_type = event['event_type']
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        for event_type, count in event_types.items():
            print(f"   - {event_type}: {count}")
    else:
        print("❌ Failed to get compliance events")
        return False
    
    # Get compliance statistics
    response = requests.get(f"{BASE_URL}/api/v1/compliance/statistics")
    if response.status_code == 200:
        stats = response.json()
        print(f"✅ Compliance Statistics:")
        print(f"   - Total events: {stats['total_events']}")
        print(f"   - Violations: {stats['violations']}")
        print(f"   - Warnings: {stats['warnings']}")
        print(f"   - Compliant: {stats['compliant']}")
        print(f"   - Compliance rate: {stats['compliance_rate']:.1f}%")
    else:
        print("❌ Failed to get compliance statistics")
        return False
    
    return True

def test_websocket():
    """Test WebSocket connection (basic test)"""
    print("\n🔌 Testing WebSocket Connection...")
    
    try:
        import websocket
        import threading
        
        def on_message(ws, message):
            data = json.loads(message)
            print(f"📡 WebSocket message: {data['type']} - {data.get('message', 'No message')}")
        
        def on_error(ws, error):
            print(f"❌ WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print("🔌 WebSocket connection closed")
        
        def on_open(ws):
            print("✅ WebSocket connected")
            # Send a test message
            ws.send("test")
        
        # Connect to WebSocket
        ws = websocket.WebSocketApp(
            f"ws://localhost:8000/ws/alerts",
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Run WebSocket in a separate thread
        wst = threading.Thread(target=ws.run_forever)
        wst.daemon = True
        wst.start()
        
        # Wait a bit for connection and messages
        time.sleep(3)
        
        # Send some telemetry to trigger WebSocket messages
        test_data = {
            "auv_id": "AUV_WS_TEST",
            "latitude": 17.75,
            "longitude": -77.75,
            "depth": 150,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/telemetry/position", json=test_data)
        if response.status_code == 200:
            print("✅ Sent test telemetry to trigger WebSocket messages")
        
        time.sleep(2)
        ws.close()
        
    except ImportError:
        print("⚠️ WebSocket test skipped (websocket-client not installed)")
        print("   Install with: pip install websocket-client")
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 DeepSeaGuard Compliance Engine - System Test")
    print("=" * 50)
    
    # Check if server is running
    if not test_health():
        return
    
    # Run tests
    tests = [
        test_zones,
        test_telemetry_processing,
        test_violation_scenario,
        test_compliance_events,
        test_websocket
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The system is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    print("\n📖 Next steps:")
    print("1. Visit http://localhost:8000/docs for API documentation")
    print("2. Use the WebSocket endpoint for real-time alerts")
    print("3. Upload your own ISA zones via the zones API")
    print("4. Integrate with your frontend application")

if __name__ == "__main__":
    main() 
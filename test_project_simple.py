#!/usr/bin/env python3
"""
Simple test script for DeepSeaGuard project
"""

import requests
import json
import time
from datetime import datetime

def test_health_endpoint():
    """Test the health endpoint"""
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ Health endpoint working")
            return True
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False

def test_root_endpoint():
    """Test the root endpoint"""
    try:
        response = requests.get("http://localhost:8000/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint working: {data.get('message', 'Unknown')}")
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        return False

def test_zones_endpoint():
    """Test the zones endpoint"""
    try:
        response = requests.get("http://localhost:8000/api/v1/zones")
        if response.status_code == 200:
            zones = response.json()
            print(f"✅ Zones endpoint working: {len(zones)} zones found")
            return True
        else:
            print(f"❌ Zones endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Zones endpoint error: {e}")
        return False

def test_telemetry_endpoint():
    """Test the telemetry endpoint"""
    try:
        # Test with sample telemetry data
        telemetry_data = {
            "auv_id": "test_auv_001",
            "latitude": 18.2208,
            "longitude": -77.5611,
            "depth": 50.0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = requests.post(
            "http://localhost:8000/api/v1/telemetry/position",
            json=telemetry_data
        )
        
        if response.status_code in [200, 201]:
            print("✅ Telemetry endpoint working")
            return True
        else:
            print(f"❌ Telemetry endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Telemetry endpoint error: {e}")
        return False

def test_compliance_endpoint():
    """Test the compliance endpoint"""
    try:
        response = requests.get("http://localhost:8000/api/v1/compliance/events")
        if response.status_code == 200:
            events = response.json()
            print(f"✅ Compliance endpoint working: {len(events)} events found")
            return True
        else:
            print(f"❌ Compliance endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Compliance endpoint error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing DeepSeaGuard Project")
    print("=" * 40)
    
    # Wait a moment for server to be ready
    time.sleep(2)
    
    tests = [
        ("Health Check", test_health_endpoint),
        ("Root Endpoint", test_root_endpoint),
        ("Zones Endpoint", test_zones_endpoint),
        ("Telemetry Endpoint", test_telemetry_endpoint),
        ("Compliance Endpoint", test_compliance_endpoint),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        if test_func():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Project is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the server logs for details.")
    
    print(f"\n🌐 Access your application:")
    print("   Main App: http://localhost:8000")
    print("   API Docs: http://localhost:8000/docs")

if __name__ == "__main__":
    main() 
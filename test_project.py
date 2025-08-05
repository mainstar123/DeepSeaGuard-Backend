#!/usr/bin/env python3
"""
DeepSeaGuard Project Test Script
This script demonstrates all features with sample data
"""

import requests
import json
import time
from datetime import datetime, timedelta
import random

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def test_health_check():
    """Test if the server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Health Check: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health Check Failed: {e}")
        return False

def test_api_documentation():
    """Test API documentation access"""
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"✅ API Docs: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ API Docs Failed: {e}")
        return False

def generate_sample_telemetry(auv_id, base_lat=17.75, base_lon=-77.75):
    """Generate sample AUV telemetry data"""
    # Simulate AUV movement
    lat_offset = random.uniform(-0.1, 0.1)
    lon_offset = random.uniform(-0.1, 0.1)
    depth = random.uniform(100, 200)
    
    return {
        "auv_id": auv_id,
        "latitude": base_lat + lat_offset,
        "longitude": base_lon + lon_offset,
        "depth": depth,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

def test_telemetry_endpoint():
    """Test telemetry processing"""
    print("\n🚢 Testing Telemetry Processing...")
    
    # Generate sample telemetry
    telemetry_data = generate_sample_telemetry("AUV_001")
    
    try:
        response = requests.post(
            f"{API_BASE}/telemetry/position",
            json=telemetry_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Telemetry Processed: {result}")
            return True
        else:
            print(f"❌ Telemetry Failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Telemetry Error: {e}")
        return False

def test_batch_telemetry():
    """Test batch telemetry processing"""
    print("\n📦 Testing Batch Telemetry...")
    
    # Generate multiple telemetry records
    telemetry_batch = []
    for i in range(3):
        telemetry_batch.append(generate_sample_telemetry(f"AUV_00{i+1}"))
    
    try:
        response = requests.post(
            f"{API_BASE}/telemetry/batch",
            json=telemetry_batch,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Batch Telemetry Processed: {result}")
            return True
        else:
            print(f"❌ Batch Telemetry Failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Batch Telemetry Error: {e}")
        return False

def test_compliance_logging():
    """Test compliance event logging"""
    print("\n📋 Testing Compliance Logging...")
    
    compliance_event = {
        "auv_id": "AUV_001",
        "zone_id": "JM_SENSITIVE_001",
        "zone_name": "Jamaica Deep Sea Mining Sensitive Zone",
        "event_type": "entry",
        "status": "compliant",
        "latitude": 17.75,
        "longitude": -77.75,
        "depth": 150
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/compliance/log",
            json=compliance_event,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Compliance Event Logged: {result}")
            return True
        else:
            print(f"❌ Compliance Logging Failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Compliance Logging Error: {e}")
        return False

def test_zone_management():
    """Test zone management endpoints"""
    print("\n🗺️ Testing Zone Management...")
    
    try:
        # Get all zones
        response = requests.get(f"{API_BASE}/zones")
        
        if response.status_code == 200:
            zones = response.json()
            print(f"✅ Zones Retrieved: {len(zones)} zones found")
            return True
        else:
            print(f"❌ Zone Retrieval Failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Zone Management Error: {e}")
        return False

def test_compliance_events():
    """Test compliance events retrieval"""
    print("\n📊 Testing Compliance Events...")
    
    try:
        response = requests.get(f"{API_BASE}/compliance/events")
        
        if response.status_code == 200:
            events = response.json()
            print(f"✅ Compliance Events Retrieved: {len(events)} events found")
            return True
        else:
            print(f"❌ Compliance Events Failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Compliance Events Error: {e}")
        return False

def test_auv_status():
    """Test AUV status endpoint"""
    print("\n📡 Testing AUV Status...")
    
    try:
        response = requests.get(f"{API_BASE}/telemetry/status/AUV_001")
        
        if response.status_code == 200:
            status = response.json()
            print(f"✅ AUV Status Retrieved: {status}")
            return True
        else:
            print(f"❌ AUV Status Failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ AUV Status Error: {e}")
        return False

def run_comprehensive_test():
    """Run all tests"""
    print("🚀 DeepSeaGuard Project Test Suite")
    print("=" * 50)
    
    # Check if server is running
    if not test_health_check():
        print("\n❌ Server is not running. Please start the Docker services first:")
        print("   docker-compose up --build -d")
        return
    
    if not test_api_documentation():
        print("\n❌ API documentation not accessible")
        return
    
    # Run feature tests
    tests = [
        ("Telemetry Processing", test_telemetry_endpoint),
        ("Batch Telemetry", test_batch_telemetry),
        ("Compliance Logging", test_compliance_logging),
        ("Zone Management", test_zone_management),
        ("Compliance Events", test_compliance_events),
        ("AUV Status", test_auv_status),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} Error: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your DeepSeaGuard system is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the logs above for details.")
    
    print(f"\n🌐 Access your application:")
    print(f"   Main App: {BASE_URL}")
    print(f"   API Docs: {BASE_URL}/docs")
    print(f"   Celery Monitor: {BASE_URL.replace('8000', '5555')}")

if __name__ == "__main__":
    run_comprehensive_test() 
#!/usr/bin/env python3
"""
Advanced ISA ArcGIS Connection Test Script

This script tests multiple possible ISA URLs and provides fallback solutions.
"""

import requests
import json
from datetime import datetime
import socket

def test_dns_resolution(hostname):
    """Test DNS resolution for a hostname"""
    try:
        ip = socket.gethostbyname(hostname)
        print(f"✅ DNS Resolution: {hostname} -> {ip}")
        return True
    except socket.gaierror as e:
        print(f"❌ DNS Resolution failed: {hostname} - {e}")
        return False

def test_url_connectivity(url, timeout=10):
    """Test if a URL is accessible"""
    try:
        print(f"🔗 Testing: {url}")
        response = requests.get(url, timeout=timeout)
        print(f"  Status: {response.status_code}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError as e:
        print(f"  ❌ Connection Error: {e}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"  ⏰ Timeout Error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Other Error: {e}")
        return False

def test_isa_urls():
    """Test multiple possible ISA URLs"""
    print("🌐 Testing Multiple ISA URLs...")
    
    # List of possible ISA URLs to test
    test_urls = [
        "https://deepdata.isa.org.jm/server/rest/services",
        "https://www.isa.org.jm/deepdata-database/maps/",
        "https://isa.org.jm/deepdata-database/maps/",
        "https://deepdata.isa.org.jm/",
        "https://www.isa.org.jm/",
        "https://isa.org.jm/"
    ]
    
    working_urls = []
    
    for url in test_urls:
        if test_url_connectivity(url):
            working_urls.append(url)
            print(f"  ✅ {url} is accessible")
        else:
            print(f"  ❌ {url} is not accessible")
    
    return working_urls

def test_alternative_arcgis_services():
    """Test alternative ArcGIS service patterns"""
    print("\n🔍 Testing Alternative ArcGIS Service Patterns...")
    
    # Common ArcGIS service patterns
    base_hosts = [
        "deepdata.isa.org.jm",
        "www.isa.org.jm",
        "isa.org.jm"
    ]
    
    service_patterns = [
        "/server/rest/services",
        "/arcgis/rest/services",
        "/services",
        "/rest/services"
    ]
    
    working_services = []
    
    for host in base_hosts:
        if test_dns_resolution(host):
            for pattern in service_patterns:
                url = f"https://{host}{pattern}"
                if test_url_connectivity(url):
                    working_services.append(url)
                    print(f"  ✅ Found working service: {url}")
    
    return working_services

def create_mock_isa_data():
    """Create mock ISA data for testing when real service is unavailable"""
    print("\n🎭 Creating Mock ISA Data for Testing...")
    
    mock_data = {
        "ccz_contract_areas": [
            {
                "attributes": {
                    "CONTRACTOR": "DEME_CCZ_001",
                    "CONTRACTOR_NAME": "DEME Blue Metals",
                    "CONTRACT_TYPE": "EXPLORATION",
                    "AREA_KM2": 75000,
                    "STATUS": "ACTIVE"
                },
                "geometry": {
                    "type": "polygon",
                    "rings": [[
                        [-140.0, 10.0],
                        [-135.0, 10.0],
                        [-135.0, 15.0],
                        [-140.0, 15.0],
                        [-140.0, 10.0]
                    ]]
                }
            },
            {
                "attributes": {
                    "CONTRACTOR": "GSR_CCZ_002",
                    "CONTRACTOR_NAME": "Global Sea Mineral Resources",
                    "CONTRACT_TYPE": "EXPLORATION",
                    "AREA_KM2": 80000,
                    "STATUS": "ACTIVE"
                },
                "geometry": {
                    "type": "polygon",
                    "rings": [[
                        [-145.0, 8.0],
                        [-140.0, 8.0],
                        [-140.0, 13.0],
                        [-145.0, 13.0],
                        [-145.0, 8.0]
                    ]]
                }
            }
        ],
        "exploration_areas": [
            {
                "attributes": {
                    "AREA_ID": "EXP_001",
                    "AREA_NAME": "Pacific Exploration Zone A",
                    "AREA_TYPE": "EXPLORATION",
                    "MAX_DEPTH": 5000,
                    "STATUS": "ACTIVE"
                },
                "geometry": {
                    "type": "polygon",
                    "rings": [[
                        [-150.0, 5.0],
                        [-145.0, 5.0],
                        [-145.0, 10.0],
                        [-150.0, 10.0],
                        [-150.0, 5.0]
                    ]]
                }
            }
        ],
        "protected_areas": [
            {
                "attributes": {
                    "AREA_ID": "PROT_001",
                    "AREA_NAME": "Marine Protected Area Alpha",
                    "AREA_TYPE": "PROTECTED",
                    "PROTECTION_LEVEL": "HIGH",
                    "STATUS": "ACTIVE"
                },
                "geometry": {
                    "type": "polygon",
                    "rings": [[
                        [-155.0, 0.0],
                        [-150.0, 0.0],
                        [-150.0, 5.0],
                        [-155.0, 5.0],
                        [-155.0, 0.0]
                    ]]
                }
            }
        ]
    }
    
    # Save mock data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mock_isa_data_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(mock_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Mock ISA data saved to: {filename}")
    return mock_data

def test_local_isa_integration():
    """Test the local ISA integration with mock data"""
    print("\n🧪 Testing Local ISA Integration...")
    
    try:
        # Import the ISA service
        from src.services.isa_data_service import ISADataService
        
        # Create mock data
        mock_data = create_mock_isa_data()
        
        # Test the conversion functions
        isa_service = ISADataService()
        
        print("Testing ArcGIS to GeoJSON conversion...")
        for area_type, areas in mock_data.items():
            print(f"  Processing {area_type}: {len(areas)} areas")
            
            for i, area in enumerate(areas):
                geojson = isa_service.convert_arcgis_to_geojson(area)
                if geojson:
                    print(f"    ✅ Area {i+1}: {geojson['properties']['zone_name']}")
                else:
                    print(f"    ❌ Area {i+1}: Conversion failed")
        
        print("✅ Local ISA integration test completed")
        return True
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing local integration: {e}")
        return False

def provide_alternative_solutions():
    """Provide alternative solutions when ISA service is unavailable"""
    print("\n💡 Alternative Solutions:")
    print("=" * 50)
    
    print("1. 📊 Use Mock Data for Development:")
    print("   - The system can work with mock ISA data for development")
    print("   - Mock data has been created with realistic CCZ coordinates")
    print("   - You can test all compliance features locally")
    
    print("\n2. 🌐 Manual Data Import:")
    print("   - Download ISA data manually from their website")
    print("   - Convert to GeoJSON format")
    print("   - Import using the zone upload API")
    
    print("\n3. 🔧 Network Configuration:")
    print("   - Check if you're behind a corporate firewall")
    print("   - Try using a VPN or different network")
    print("   - Contact ISA for API access if needed")
    
    print("\n4. 📋 API Documentation:")
    print("   - ISA might have different API endpoints")
    print("   - Check their official documentation")
    print("   - Look for public datasets they provide")

def main():
    """Main test function"""
    print("🚀 Advanced ISA ArcGIS Connection Test")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Test 1: DNS Resolution
    print("\n🔍 Testing DNS Resolution...")
    test_dns_resolution("deepdata.isa.org.jm")
    test_dns_resolution("www.isa.org.jm")
    test_dns_resolution("isa.org.jm")
    
    # Test 2: URL Connectivity
    working_urls = test_isa_urls()
    
    # Test 3: Alternative ArcGIS Services
    working_services = test_alternative_arcgis_services()
    
    # Test 4: Local Integration
    local_test_success = test_local_isa_integration()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"✅ Working URLs: {len(working_urls)}")
    print(f"✅ Working Services: {len(working_services)}")
    print(f"✅ Local Integration: {'Yes' if local_test_success else 'No'}")
    
    if working_urls or working_services:
        print("\n🎉 ISA service is accessible!")
        print("You can use the real ISA data integration.")
    elif local_test_success:
        print("\n🛠️ Using Mock Data for Development")
        print("The system will work with mock ISA data for testing.")
        provide_alternative_solutions()
    else:
        print("\n❌ No ISA services accessible")
        print("Check network connection and try alternative solutions.")
        provide_alternative_solutions()
    
    # Save test results
    results = {
        "timestamp": datetime.now().isoformat(),
        "working_urls": working_urls,
        "working_services": working_services,
        "local_integration_success": local_test_success,
        "dns_resolution": {
            "deepdata.isa.org.jm": test_dns_resolution("deepdata.isa.org.jm"),
            "www.isa.org.jm": test_dns_resolution("www.isa.org.jm"),
            "isa.org.jm": test_dns_resolution("isa.org.jm")
        }
    }
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"isa_advanced_test_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Detailed results saved to: {filename}")

if __name__ == "__main__":
    main() 
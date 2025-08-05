#!/usr/bin/env python3
"""
ISA ArcGIS Connection Test Script

This script tests the connection to ISA's ArcGIS services and shows what data is available.
"""

import requests
import json
from datetime import datetime

def test_isa_base_url():
    """Test the base ISA ArcGIS URL"""
    print("🔗 Testing ISA Base URL...")
    
    base_url = "https://deepdata.isa.org.jm/server/rest/services"
    
    try:
        response = requests.get(base_url, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Base URL is accessible!")
            print(f"Services available: {len(data.get('services', []))}")
            
            # Show available services
            services = data.get('services', [])
            for i, service in enumerate(services[:10]):  # Show first 10
                print(f"  {i+1}. {service.get('name', 'Unknown')} - {service.get('type', 'Unknown')}")
            
            if len(services) > 10:
                print(f"  ... and {len(services) - 10} more services")
            
            return services
        else:
            print(f"❌ Failed to access base URL: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error accessing base URL: {e}")
        return []

def test_specific_service(service_name):
    """Test a specific ISA service"""
    print(f"\n🔍 Testing service: {service_name}")
    
    base_url = "https://deepdata.isa.org.jm/server/rest/services"
    service_url = f"{base_url}/Hosted/{service_name}/FeatureServer"
    
    try:
        response = requests.get(service_url, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Service {service_name} is accessible!")
            print(f"Layers: {len(data.get('layers', []))}")
            
            layers = data.get('layers', [])
            for layer in layers:
                layer_id = layer.get('id', 'Unknown')
                layer_name = layer.get('name', 'Unknown')
                print(f"  Layer {layer_id}: {layer_name}")
            
            return layers
        else:
            print(f"❌ Failed to access service {service_name}: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error accessing service {service_name}: {e}")
        return []

def test_layer_query(service_name, layer_id=0):
    """Test querying a specific layer"""
    print(f"\n📊 Testing layer query: {service_name} - Layer {layer_id}")
    
    base_url = "https://deepdata.isa.org.jm/server/rest/services"
    query_url = f"{base_url}/Hosted/{service_name}/FeatureServer/{layer_id}/query"
    
    params = {
        'f': 'json',
        'where': '1=1',
        'outFields': '*',
        'returnGeometry': 'true',
        'maxRecordCount': 5  # Limit to 5 records for testing
    }
    
    try:
        response = requests.get(query_url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            print(f"✅ Query successful! Found {len(features)} features")
            
            if features:
                # Show first feature details
                first_feature = features[0]
                attributes = first_feature.get('attributes', {})
                geometry = first_feature.get('geometry', {})
                
                print(f"\n📋 First Feature Details:")
                print(f"  Attributes: {len(attributes)} fields")
                for key, value in list(attributes.items())[:5]:  # Show first 5 attributes
                    print(f"    {key}: {value}")
                
                if len(attributes) > 5:
                    print(f"    ... and {len(attributes) - 5} more attributes")
                
                print(f"  Geometry type: {geometry.get('type', 'Unknown')}")
                if 'rings' in geometry:
                    print(f"  Polygon rings: {len(geometry['rings'])}")
                elif 'paths' in geometry:
                    print(f"  Line paths: {len(geometry['paths'])}")
                elif 'x' in geometry and 'y' in geometry:
                    print(f"  Point: ({geometry['x']}, {geometry['y']})")
            
            return features
        else:
            print(f"❌ Failed to query layer: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return []
            
    except Exception as e:
        print(f"❌ Error querying layer: {e}")
        return []

def test_ccz_contract_areas():
    """Test CCZ Contract Areas specifically"""
    print("\n🌊 Testing CCZ Contract Areas...")
    return test_layer_query("CCZ_Contract_Areas", 0)

def test_exploration_areas():
    """Test Exploration Areas specifically"""
    print("\n🔍 Testing Exploration Areas...")
    return test_layer_query("Exploration_Areas", 0)

def test_protected_areas():
    """Test Protected Areas specifically"""
    print("\n🛡️ Testing Protected Areas...")
    return test_layer_query("Protected_Areas", 0)

def save_test_results(data, filename):
    """Save test results to file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        print(f"✅ Results saved to {filename}")
    except Exception as e:
        print(f"❌ Error saving results: {e}")

def main():
    """Main test function"""
    print("🚀 ISA ArcGIS Connection Test")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Test 1: Base URL
    services = test_isa_base_url()
    
    if not services:
        print("\n❌ No services found. Exiting.")
        return
    
    # Test 2: Test specific services mentioned in the code
    test_services = [
        "CCZ_Contract_Areas",
        "Exploration_Areas", 
        "Protected_Areas"
    ]
    
    results = {}
    
    for service_name in test_services:
        # Check if service exists
        service_exists = any(s.get('name') == service_name for s in services)
        
        if service_exists:
            print(f"\n✅ Service '{service_name}' found in available services")
            layers = test_specific_service(service_name)
            features = test_layer_query(service_name, 0)
            
            results[service_name] = {
                'exists': True,
                'layers': layers,
                'features_count': len(features),
                'sample_features': features[:2] if features else []  # Save first 2 features
            }
        else:
            print(f"\n❌ Service '{service_name}' NOT found in available services")
            results[service_name] = {
                'exists': False,
                'layers': [],
                'features_count': 0,
                'sample_features': []
            }
    
    # Test 3: Try some other common service names
    alternative_services = [
        "Contract_Areas",
        "Mining_Areas",
        "Exploration_Zones",
        "Protected_Zones",
        "Marine_Areas"
    ]
    
    print("\n🔍 Testing alternative service names...")
    for alt_service in alternative_services:
        service_exists = any(s.get('name') == alt_service for s in services)
        if service_exists:
            print(f"  ✅ Found alternative service: {alt_service}")
            results[f"alternative_{alt_service}"] = {
                'exists': True,
                'layers': test_specific_service(alt_service),
                'features_count': len(test_layer_query(alt_service, 0)),
                'sample_features': test_layer_query(alt_service, 0)[:1] if test_layer_query(alt_service, 0) else []
            }
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"isa_test_results_{timestamp}.json"
    save_test_results(results, filename)
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    
    successful_services = [name for name, data in results.items() if data.get('exists', False)]
    total_features = sum(data.get('features_count', 0) for data in results.values())
    
    print(f"✅ Successful services: {len(successful_services)}")
    print(f"📊 Total features found: {total_features}")
    
    for service_name, data in results.items():
        if data.get('exists', False):
            print(f"  📍 {service_name}: {data['features_count']} features")
    
    print(f"\n📄 Detailed results saved to: {filename}")
    
    if successful_services:
        print("\n✅ ISA ArcGIS connection is working!")
        print("You can now use the DeepSeaGuard ISA integration features.")
    else:
        print("\n❌ No ISA services found. Check the service names or network connection.")

if __name__ == "__main__":
    main() 
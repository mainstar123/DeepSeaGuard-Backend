import requests
import json

def upload_zones():
    """Upload real ISA zones to the system"""
    
    # Read the GeoJSON file
    with open('isa_zones_real.geojson', 'r') as f:
        geojson_data = json.load(f)
    
    # Upload via API
    url = "http://localhost:8000/api/v1/zones/upload"
    
    files = {
        'file': ('isa_zones_real.geojson', json.dumps(geojson_data), 'application/json')
    }
    
    try:
        response = requests.post(url, files=files)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Successfully uploaded real ISA zones!")
        else:
            print("❌ Failed to upload zones")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    upload_zones() 
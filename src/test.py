import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime
from shapely.geometry import shape

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ISAArcGISFetcher:
    def __init__(self):
        # ✅ This is a known working FeatureServer used by ISA's public datasets
        self.base_url = (
            "https://services3.arcgis.com/JkZtT1xO2JXnKfMx/ArcGIS/rest/services/"
            "ISA_CZ_Contracts_Public_View/FeatureServer/0/query"
        )
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ISA-Compliance-Client/1.0"
        })

    def fetch_data(self) -> List[Dict]:
        """Fetch contract areas from ISA FeatureServer"""
        params = {
            "where": "1=1",
            "outFields": "*",
            "outSR": 4326,
            "f": "geojson",
            "returnGeometry": "true"
        }

        try:
            logger.info(f"Fetching ISA data from {self.base_url}")
            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            geojson = response.json()
            logger.info(f"Fetched {len(geojson.get('features', []))} features")
            return geojson.get("features", [])
        except Exception as e:
            logger.error(f"Error fetching ISA data: {e}")
            return []

    def convert_to_standard_geojson(self, feature: Dict) -> Dict:
        """Format feature with metadata and default zone handling"""
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})

        zone_id = props.get("Name", "UNKNOWN")
        zone_name = props.get("Contractor", "Unnamed Zone")
        zone_type = self.determine_zone_type(props)
        max_duration = self.default_duration(zone_type)

        return {
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "zone_id": zone_id,
                "zone_name": zone_name,
                "zone_type": zone_type,
                "max_duration_hours": max_duration,
                "source": "ISA_Public",
                "imported_at": datetime.utcnow().isoformat(),
                "original_attributes": props
            }
        }

    def determine_zone_type(self, props: Dict) -> str:
        name = (props.get("Type") or "").lower()
        if "exploration" in name:
            return "sensitive"
        elif "exploitation" in name or "mining" in name:
            return "restricted"
        elif "protected" in name:
            return "protected"
        return "sensitive"

    def default_duration(self, zone_type: str) -> float:
        return {"sensitive": 1.0, "restricted": 0.5, "protected": 2.0}.get(zone_type, 1.0)

    def run(self):
        features = self.fetch_data()
        geojson_features = [self.convert_to_standard_geojson(f) for f in features]

        # Output file for confirmation
        output = {
            "type": "FeatureCollection",
            "features": geojson_features
        }

        with open("isa_public_zones.geojson", "w") as f:
            import json
            json.dump(output, f, indent=2)

        logger.info("Exported GeoJSON to 'isa_public_zones.geojson'")


# Run
if __name__ == "__main__":
    fetcher = ISAArcGISFetcher()
    fetcher.run()
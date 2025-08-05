import requests
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from database.database import ISAZone, get_db

logger = logging.getLogger(__name__)

class ISADataService:
    """Service to integrate with ISA's ArcGIS services and pull real map data"""
    
    def __init__(self):
        self.base_url = "https://deepdata.isa.org.jm/server/rest/services"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DeepSeaGuard/1.0 (Compliance Engine)'
        })
    
    def get_ccz_contract_areas(self) -> List[Dict]:
        """
        Get Clarion Clipperton Zone contract areas from ISA ArcGIS service
        """
        try:
            url = f"{self.base_url}/Hosted/CCZ_Contract_Areas/FeatureServer/0/query"
            params = {
                'f': 'json',
                'where': '1=1',
                'outFields': '*',
                'returnGeometry': 'true'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            logger.info(f"Retrieved {len(features)} CCZ contract areas from ISA")
            return features
            
        except requests.RequestException as e:
            logger.error(f"Error fetching CCZ contract areas: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing CCZ contract areas response: {e}")
            return []
    
    def get_exploration_areas(self) -> List[Dict]:
        """
        Get exploration areas from ISA ArcGIS service
        """
        try:
            url = f"{self.base_url}/Hosted/Exploration_Areas/FeatureServer/0/query"
            params = {
                'f': 'json',
                'where': '1=1',
                'outFields': '*',
                'returnGeometry': 'true'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            logger.info(f"Retrieved {len(features)} exploration areas from ISA")
            return features
            
        except requests.RequestException as e:
            logger.error(f"Error fetching exploration areas: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing exploration areas response: {e}")
            return []
    
    def get_protected_areas(self) -> List[Dict]:
        """
        Get protected areas from ISA ArcGIS service
        """
        try:
            url = f"{self.base_url}/Hosted/Protected_Areas/FeatureServer/0/query"
            params = {
                'f': 'json',
                'where': '1=1',
                'outFields': '*',
                'returnGeometry': 'true'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            logger.info(f"Retrieved {len(features)} protected areas from ISA")
            return features
            
        except requests.RequestException as e:
            logger.error(f"Error fetching protected areas: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing protected areas response: {e}")
            return []
    
    def convert_arcgis_to_geojson(self, arcgis_feature: Dict) -> Dict:
        """
        Convert ArcGIS feature to GeoJSON format
        """
        try:
            attributes = arcgis_feature.get('attributes', {})
            geometry = arcgis_feature.get('geometry', {})
            
            # Extract relevant attributes
            zone_id = attributes.get('CONTRACTOR', attributes.get('ID', f"ISA_{datetime.now().timestamp()}"))
            zone_name = attributes.get('CONTRACTOR_NAME', attributes.get('NAME', f"ISA Zone {zone_id}"))
            
            # Determine zone type based on attributes
            zone_type = self._determine_zone_type(attributes)
            
            # Set default duration based on zone type
            max_duration_hours = self._get_default_duration(zone_type)
            
            # Convert ArcGIS geometry to GeoJSON
            geojson_geometry = self._convert_geometry(geometry)
            
            geojson_feature = {
                "type": "Feature",
                "properties": {
                    "zone_id": zone_id,
                    "zone_name": zone_name,
                    "zone_type": zone_type,
                    "max_duration_hours": max_duration_hours,
                    "source": "ISA_ArcGIS",
                    "imported_at": datetime.utcnow().isoformat(),
                    "original_attributes": attributes
                },
                "geometry": geojson_geometry
            }
            
            return geojson_feature
            
        except Exception as e:
            logger.error(f"Error converting ArcGIS feature to GeoJSON: {e}")
            return None
    
    def _determine_zone_type(self, attributes: Dict) -> str:
        """
        Determine zone type based on ArcGIS attributes
        """
        # Check for specific contract types
        contract_type = attributes.get('CONTRACT_TYPE', '').upper()
        area_type = attributes.get('AREA_TYPE', '').upper()
        
        if 'EXPLORATION' in contract_type or 'EXPLORATION' in area_type:
            return 'sensitive'
        elif 'EXPLOITATION' in contract_type or 'MINING' in contract_type:
            return 'restricted'
        elif 'PROTECTED' in area_type or 'RESERVE' in area_type:
            return 'protected'
        else:
            # Default based on common patterns
            if any(keyword in str(attributes).upper() for keyword in ['SENSITIVE', 'CRITICAL']):
                return 'sensitive'
            elif any(keyword in str(attributes).upper() for keyword in ['RESTRICTED', 'MINING']):
                return 'restricted'
            else:
                return 'sensitive'  # Default to sensitive for safety
    
    def _get_default_duration(self, zone_type: str) -> float:
        """
        Get default duration based on zone type
        """
        durations = {
            'sensitive': 1.0,    # 1 hour for sensitive areas
            'restricted': 0.5,   # 30 minutes for restricted areas
            'protected': 2.0     # 2 hours for protected areas
        }
        return durations.get(zone_type, 1.0)
    
    def _convert_geometry(self, arcgis_geometry: Dict) -> Dict:
        """
        Convert ArcGIS geometry to GeoJSON geometry
        """
        try:
            # Handle different geometry types
            if 'rings' in arcgis_geometry:
                # Polygon geometry
                return {
                    "type": "Polygon",
                    "coordinates": arcgis_geometry['rings']
                }
            elif 'paths' in arcgis_geometry:
                # LineString geometry
                return {
                    "type": "LineString",
                    "coordinates": arcgis_geometry['paths'][0]
                }
            elif 'x' in arcgis_geometry and 'y' in arcgis_geometry:
                # Point geometry
                return {
                    "type": "Point",
                    "coordinates": [arcgis_geometry['x'], arcgis_geometry['y']]
                }
            else:
                logger.warning(f"Unsupported ArcGIS geometry type: {arcgis_geometry}")
                return None
                
        except Exception as e:
            logger.error(f"Error converting ArcGIS geometry: {e}")
            return None
    
    def sync_isa_zones_to_database(self) -> Dict:
        """
        Sync ISA zones from ArcGIS services to local database
        """
        try:
            db = next(get_db())
            
            # Get all ISA data
            ccz_areas = self.get_ccz_contract_areas()
            exploration_areas = self.get_exploration_areas()
            protected_areas = self.get_protected_areas()
            
            all_features = ccz_areas + exploration_areas + protected_areas
            
            imported_count = 0
            updated_count = 0
            errors = []
            
            for feature in all_features:
                try:
                    geojson_feature = self.convert_arcgis_to_geojson(feature)
                    if not geojson_feature:
                        continue
                    
                    zone_id = geojson_feature['properties']['zone_id']
                    zone_name = geojson_feature['properties']['zone_name']
                    zone_type = geojson_feature['properties']['zone_type']
                    max_duration_hours = geojson_feature['properties']['max_duration_hours']
                    geojson_data = json.dumps(geojson_feature)
                    
                    # Check if zone already exists
                    existing_zone = db.query(ISAZone).filter(ISAZone.zone_id == zone_id).first()
                    
                    if existing_zone:
                        # Update existing zone
                        existing_zone.zone_name = zone_name
                        existing_zone.zone_type = zone_type
                        existing_zone.max_duration_hours = max_duration_hours
                        existing_zone.geojson_data = geojson_data
                        existing_zone.is_active = True
                        updated_count += 1
                    else:
                        # Create new zone
                        new_zone = ISAZone(
                            zone_id=zone_id,
                            zone_name=zone_name,
                            zone_type=zone_type,
                            max_duration_hours=max_duration_hours,
                            geojson_data=geojson_data,
                            is_active=True
                        )
                        db.add(new_zone)
                        imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Error processing feature: {e}")
                    continue
            
            db.commit()
            
            result = {
                'imported': imported_count,
                'updated': updated_count,
                'total_processed': len(all_features),
                'errors': errors
            }
            
            logger.info(f"ISA zone sync completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error syncing ISA zones: {e}")
            return {
                'imported': 0,
                'updated': 0,
                'total_processed': 0,
                'errors': [str(e)]
            }
    
    def get_available_layers(self) -> List[Dict]:
        """
        Get list of available ISA ArcGIS layers
        """
        try:
            url = f"{self.base_url}/Hosted"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            services = data.get('services', [])
            
            layers = []
            for service in services:
                service_name = service.get('name', '')
                service_url = f"{self.base_url}/Hosted/{service_name}/FeatureServer"
                
                try:
                    layer_response = self.session.get(service_url, timeout=10)
                    if layer_response.status_code == 200:
                        layer_data = layer_response.json()
                        layers.append({
                            'name': service_name,
                            'url': service_url,
                            'layers': layer_data.get('layers', [])
                        })
                except:
                    continue
            
            return layers
            
        except Exception as e:
            logger.error(f"Error getting available layers: {e}")
            return [] 
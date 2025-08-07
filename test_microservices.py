#!/usr/bin/env python3
"""
DeepSeaGuard Microservice Architecture Testing Script
Comprehensive testing of all microservices and their integration
"""

import asyncio
import json
import sys
import time
import requests
import subprocess
import threading
from datetime import datetime
from typing import Dict, List, Optional

# Add src to path
sys.path.append('src')

class MicroserviceTester:
    def __init__(self):
        self.base_urls = {
            "api-gateway": "http://localhost:8010",
            "auv-telemetry": "http://localhost:8011", 
            "geofencing": "http://localhost:8012",
            "compliance": "http://localhost:8013",
            "alert": "http://localhost:8014",
            "streaming-manager": "http://localhost:8015"
        }
        self.running_services = {}
        self.test_results = {}
        
    def print_header(self, title: str):
        """Print a formatted header"""
        print(f"\n{'='*60}")
        print(f"🧪 {title}")
        print(f"{'='*60}")
        
    def print_success(self, message: str):
        """Print success message"""
        print(f"✅ {message}")
        
    def print_error(self, message: str):
        """Print error message"""
        print(f"❌ {message}")
        
    def print_info(self, message: str):
        """Print info message"""
        print(f"ℹ️  {message}")
        
    def test_service_import(self, service_name: str, module_path: str) -> bool:
        """Test if a service module can be imported"""
        try:
            module = __import__(module_path, fromlist=['app'])
            self.print_success(f"{service_name} module imported successfully")
            return True
        except Exception as e:
            self.print_error(f"{service_name} import failed: {str(e)}")
            return False
            
    def start_service(self, service_name: str, port: int) -> bool:
        """Start a microservice on a specific port"""
        try:
            self.print_info(f"Starting {service_name} on port {port}...")
            
            # Create command to run the service
            cmd = [
                sys.executable, "-m", "uvicorn", 
                f"src.microservices.{service_name.replace('-', '_')}:app", 
                "--host", "0.0.0.0", 
                "--port", str(port),
                "--reload"
            ]
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.running_services[service_name] = {
                "process": process,
                "port": port,
                "start_time": datetime.now()
            }
            
            # Wait a bit for the service to start
            time.sleep(3)
            
            # Test if service is responding
            try:
                response = requests.get(f"http://localhost:{port}/health", timeout=5)
                if response.status_code == 200:
                    self.print_success(f"{service_name} started and responding on port {port}")
                    return True
                else:
                    self.print_error(f"{service_name} started but health check failed")
                    return False
            except requests.exceptions.RequestException:
                self.print_error(f"{service_name} started but not responding on port {port}")
                return False
                
        except Exception as e:
            self.print_error(f"Failed to start {service_name}: {str(e)}")
            return False
            
    def test_api_endpoints(self, service_name: str, base_url: str) -> Dict:
        """Test API endpoints for a service"""
        results = {}
        
        # Common endpoints to test
        endpoints = [
            ("/health", "GET"),
            ("/docs", "GET"),
            ("/openapi.json", "GET")
        ]
        
        for endpoint, method in endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"{base_url}{endpoint}", timeout=5)
                else:
                    response = requests.post(f"{base_url}{endpoint}", timeout=5)
                    
                if response.status_code in [200, 404]:  # 404 is OK for some endpoints
                    results[endpoint] = {
                        "status": "success",
                        "status_code": response.status_code
                    }
                    self.print_success(f"{service_name} {endpoint}: {response.status_code}")
                else:
                    results[endpoint] = {
                        "status": "error",
                        "status_code": response.status_code
                    }
                    self.print_error(f"{service_name} {endpoint}: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                results[endpoint] = {
                    "status": "error",
                    "error": str(e)
                }
                self.print_error(f"{service_name} {endpoint}: Connection failed")
                
        return results
        
    def test_telemetry_processing(self) -> bool:
        """Test AUV telemetry processing"""
        self.print_header("Testing AUV Telemetry Processing")
        
        # Sample telemetry data
        telemetry_data = {
            "auv_id": "AUV_TEST_001",
            "latitude": 17.75,
            "longitude": -77.75,
            "depth": 150,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Test telemetry endpoint
            response = requests.post(
                f"{self.base_urls['auv-telemetry']}/api/v1/telemetry/position",
                json=telemetry_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                self.print_success(f"Telemetry processed: {result.get('status', 'unknown')}")
                return True
            else:
                self.print_error(f"Telemetry processing failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"Telemetry test failed: {str(e)}")
            return False
            
    def test_geofencing(self) -> bool:
        """Test geofencing functionality"""
        self.print_header("Testing Geofencing Service")
        
        # Test zone query
        test_position = {
            "latitude": 17.75,
            "longitude": -77.75
        }
        
        try:
            response = requests.post(
                f"{self.base_urls['geofencing']}/api/v1/zones/check",
                json=test_position,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                zones = result.get('zones', [])
                self.print_success(f"Geofencing check: {len(zones)} zones detected")
                return True
            else:
                self.print_error(f"Geofencing check failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"Geofencing test failed: {str(e)}")
            return False
            
    def test_compliance_monitoring(self) -> bool:
        """Test compliance monitoring"""
        self.print_header("Testing Compliance Monitoring")
        
        # Test compliance check
        compliance_data = {
            "auv_id": "AUV_TEST_001",
            "zone_id": "TEST_ZONE",
            "entry_time": datetime.now().isoformat(),
            "duration_minutes": 30
        }
        
        try:
            response = requests.post(
                f"{self.base_urls['compliance']}/api/v1/compliance/check",
                json=compliance_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                self.print_success(f"Compliance check: {result.get('status', 'unknown')}")
                return True
            else:
                self.print_error(f"Compliance check failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"Compliance test failed: {str(e)}")
            return False
            
    def test_alert_system(self) -> bool:
        """Test alert system"""
        self.print_header("Testing Alert System")
        
        # Test alert creation
        alert_data = {
            "auv_id": "AUV_TEST_001",
            "alert_type": "violation",
            "message": "Test violation alert",
            "severity": "high",
            "zone_id": "TEST_ZONE"
        }
        
        try:
            response = requests.post(
                f"{self.base_urls['alert']}/api/v1/alerts",
                json=alert_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                self.print_success(f"Alert created: {result.get('alert_id', 'unknown')}")
                return True
            else:
                self.print_error(f"Alert creation failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"Alert test failed: {str(e)}")
            return False
            
    def test_integration_workflow(self) -> bool:
        """Test complete integration workflow"""
        self.print_header("Testing Integration Workflow")
        
        # Simulate complete workflow: telemetry -> geofencing -> compliance -> alert
        workflow_data = {
            "auv_id": "AUV_INTEGRATION_TEST",
            "latitude": 17.75,
            "longitude": -77.75,
            "depth": 150,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Step 1: Send telemetry
            response = requests.post(
                f"{self.base_urls['auv-telemetry']}/api/v1/telemetry/position",
                json=workflow_data,
                timeout=10
            )
            
            if response.status_code != 200:
                self.print_error("Integration workflow failed at telemetry step")
                return False
                
            self.print_success("Integration workflow: Telemetry processed")
            
            # Step 2: Check geofencing
            response = requests.post(
                f"{self.base_urls['geofencing']}/api/v1/zones/check",
                json={"latitude": workflow_data["latitude"], "longitude": workflow_data["longitude"]},
                timeout=10
            )
            
            if response.status_code != 200:
                self.print_error("Integration workflow failed at geofencing step")
                return False
                
            self.print_success("Integration workflow: Geofencing checked")
            
            # Step 3: Check compliance
            response = requests.get(
                f"{self.base_urls['compliance']}/api/v1/compliance/status/{workflow_data['auv_id']}",
                timeout=10
            )
            
            if response.status_code != 200:
                self.print_error("Integration workflow failed at compliance step")
                return False
                
            self.print_success("Integration workflow: Compliance status checked")
            
            self.print_success("✅ Complete integration workflow successful!")
            return True
            
        except Exception as e:
            self.print_error(f"Integration workflow failed: {str(e)}")
            return False
            
    def stop_all_services(self):
        """Stop all running services"""
        self.print_header("Stopping All Services")
        
        for service_name, service_info in self.running_services.items():
            try:
                process = service_info["process"]
                process.terminate()
                process.wait(timeout=5)
                self.print_success(f"{service_name} stopped")
            except Exception as e:
                self.print_error(f"Failed to stop {service_name}: {str(e)}")
                
    def run_comprehensive_test(self):
        """Run comprehensive microservice testing"""
        self.print_header("DeepSeaGuard Microservice Architecture Testing")
        
        # Test 1: Module Import Tests
        self.print_header("Module Import Tests")
        import_tests = [
            ("API Gateway", "src.microservices.api_gateway"),
            ("AUV Telemetry", "src.microservices.auv_telemetry_service"),
            ("Geofencing", "src.microservices.geofencing_service"),
            ("Compliance", "src.microservices.compliance_service"),
            ("Alert Service", "src.microservices.alert_service")
        ]
        
        for service_name, module_path in import_tests:
            self.test_service_import(service_name, module_path)
            
        # Test 2: Service Startup Tests
        self.print_header("Service Startup Tests")
        services_to_start = [
            ("api-gateway", 8010),
            ("auv-telemetry", 8011),
            ("geofencing", 8012),
            ("compliance", 8013),
            ("alert", 8014)
        ]
        
        for service_name, port in services_to_start:
            self.start_service(service_name, port)
            
        # Wait for all services to be ready
        time.sleep(5)
        
        # Test 3: API Endpoint Tests
        self.print_header("API Endpoint Tests")
        for service_name, base_url in self.base_urls.items():
            if service_name in self.running_services:
                self.test_api_endpoints(service_name, base_url)
                
        # Test 4: Functional Tests
        self.test_telemetry_processing()
        self.test_geofencing()
        self.test_compliance_monitoring()
        self.test_alert_system()
        
        # Test 5: Integration Test
        self.test_integration_workflow()
        
        # Test 6: Summary
        self.print_header("Test Summary")
        self.print_info(f"Services started: {len(self.running_services)}")
        self.print_info("All tests completed!")
        
        # Keep services running for manual testing
        self.print_info("Services are still running for manual testing.")
        self.print_info("Press Ctrl+C to stop all services.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_all_services()

def main():
    """Main testing function"""
    tester = MicroserviceTester()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
DeepSeaGuard Microservice Architecture Startup Script
Version 2.0 - Advanced Streaming and Microservice System
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from typing import List, Dict

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.logging_config import setup_logging

# Setup logging
logger = setup_logging(__name__)

class MicroserviceManager:
    def __init__(self):
        self.services = {
            "api-gateway": {
                "module": "src.microservices.api_gateway",
                "port": 8000,
                "description": "API Gateway with service discovery and load balancing"
            },
            "auv-telemetry": {
                "module": "src.microservices.auv_telemetry_service",
                "port": 8001,
                "description": "AUV Telemetry Processing Microservice"
            },
            "geofencing": {
                "module": "src.microservices.geofencing_service",
                "port": 8002,
                "description": "Advanced Geofencing Microservice"
            },
            "compliance": {
                "module": "src.microservices.compliance_service",
                "port": 8003,
                "description": "Compliance Monitoring Microservice"
            },
            "alert": {
                "module": "src.microservices.alert_service",
                "port": 8004,
                "description": "Alert Management Microservice"
            },
            "streaming-manager": {
                "module": "src.streaming.streaming_manager",
                "port": 8005,
                "description": "Streaming Orchestration Manager"
            }
        }
        self.running_services = {}
        
    async def start_service(self, service_name: str) -> bool:
        """Start a specific microservice"""
        if service_name not in self.services:
            logger.error(f"Unknown service: {service_name}")
            return False
        
        service_config = self.services[service_name]
        
        try:
            logger.info(f"Starting {service_name} on port {service_config['port']}...")
            
            # Import and start the service
            module_name = service_config["module"]
            module = __import__(module_name, fromlist=['app'])
            
            # Start the service in a separate process
            import subprocess
            import uvicorn
            
            # Create command to run the service
            cmd = [
                sys.executable, "-m", "uvicorn", 
                f"{module_name}:app", 
                "--host", "0.0.0.0", 
                "--port", str(service_config["port"]),
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
                "port": service_config["port"],
                "start_time": datetime.now()
            }
            
            logger.info(f"✅ {service_name} started successfully on port {service_config['port']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start {service_name}: {e}")
            return False
    
    async def start_all_services(self) -> Dict[str, bool]:
        """Start all microservices"""
        logger.info("🚀 Starting DeepSeaGuard Microservice Architecture (Version 2.0)")
        logger.info("=" * 60)
        
        results = {}
        
        # Start services in order (dependencies first)
        service_order = [
            "streaming-manager",  # Start streaming infrastructure first
            "auv-telemetry",
            "geofencing", 
            "compliance",
            "alert",
            "api-gateway"  # Start API gateway last
        ]
        
        for service_name in service_order:
            if service_name in self.services:
                success = await self.start_service(service_name)
                results[service_name] = success
                
                if success:
                    # Wait a bit between services
                    await asyncio.sleep(2)
        
        return results
    
    async def stop_service(self, service_name: str) -> bool:
        """Stop a specific microservice"""
        if service_name not in self.running_services:
            return False
        
        try:
            service_info = self.running_services[service_name]
            process = service_info["process"]
            
            logger.info(f"Stopping {service_name}...")
            process.terminate()
            
            # Wait for graceful shutdown
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            
            del self.running_services[service_name]
            logger.info(f"✅ {service_name} stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop {service_name}: {e}")
            return False
    
    async def stop_all_services(self):
        """Stop all running services"""
        logger.info("🛑 Stopping all microservices...")
        
        for service_name in list(self.running_services.keys()):
            await self.stop_service(service_name)
        
        logger.info("✅ All services stopped")
    
    def get_service_status(self) -> Dict[str, Dict]:
        """Get status of all services"""
        status = {}
        
        for service_name, service_config in self.services.items():
            is_running = service_name in self.running_services
            service_info = {
                "name": service_name,
                "description": service_config["description"],
                "port": service_config["port"],
                "status": "running" if is_running else "stopped",
                "uptime": None
            }
            
            if is_running:
                start_time = self.running_services[service_name]["start_time"]
                uptime = datetime.now() - start_time
                service_info["uptime"] = str(uptime).split('.')[0]  # Remove microseconds
            
            status[service_name] = service_info
        
        return status
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all services"""
        import httpx
        
        health_results = {}
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for service_name, service_config in self.services.items():
                if service_name in self.running_services:
                    try:
                        response = await client.get(f"http://localhost:{service_config['port']}/health")
                        health_results[service_name] = response.status_code == 200
                    except Exception:
                        health_results[service_name] = False
                else:
                    health_results[service_name] = False
        
        return health_results

async def main():
    """Main function"""
    manager = MicroserviceManager()
    
    try:
        # Start all services
        results = await manager.start_all_services()
        
        # Check which services started successfully
        successful_services = [name for name, success in results.items() if success]
        failed_services = [name for name, success in results.items() if not success]
        
        logger.info("=" * 60)
        logger.info("🎯 MICROSERVICE STARTUP SUMMARY")
        logger.info("=" * 60)
        
        if successful_services:
            logger.info("✅ Successfully started services:")
            for service in successful_services:
                config = manager.services[service]
                logger.info(f"   • {service} (Port {config['port']}) - {config['description']}")
        
        if failed_services:
            logger.info("❌ Failed to start services:")
            for service in failed_services:
                logger.info(f"   • {service}")
        
        logger.info("=" * 60)
        logger.info("🌐 SERVICE ENDPOINTS:")
        logger.info("   • API Gateway: http://localhost:8000")
        logger.info("   • AUV Telemetry: http://localhost:8001")
        logger.info("   • Geofencing: http://localhost:8002")
        logger.info("   • Compliance: http://localhost:8003")
        logger.info("   • Alert Management: http://localhost:8004")
        logger.info("   • Streaming Manager: http://localhost:8005")
        logger.info("=" * 60)
        logger.info("📊 MONITORING:")
        logger.info("   • Prometheus: http://localhost:9090")
        logger.info("   • Grafana: http://localhost:3000 (admin/admin)")
        logger.info("   • Jaeger Tracing: http://localhost:16686")
        logger.info("   • RabbitMQ Management: http://localhost:15672 (guest/guest)")
        logger.info("=" * 60)
        logger.info("🎬 Ready for CTO Demo! Press Ctrl+C to stop all services.")
        
        # Keep the services running
        while True:
            await asyncio.sleep(10)
            
            # Periodic health check
            health_results = await manager.health_check()
            unhealthy_services = [name for name, healthy in health_results.items() if not healthy]
            
            if unhealthy_services:
                logger.warning(f"⚠️  Unhealthy services detected: {unhealthy_services}")
    
    except KeyboardInterrupt:
        logger.info("\n🛑 Received shutdown signal...")
        await manager.stop_all_services()
        logger.info("👋 DeepSeaGuard Microservices stopped. Goodbye!")
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        await manager.stop_all_services()
        sys.exit(1)

if __name__ == "__main__":
    # Check if running in the right environment
    if not os.path.exists("src/microservices"):
        logger.error("❌ Microservices directory not found. Please run from the project root.")
        sys.exit(1)
    
    # Run the main function
    asyncio.run(main()) 
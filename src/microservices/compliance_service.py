"""
Compliance Microservice
Handles real-time compliance monitoring and violation detection
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import aiohttp
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import text

from src.database.database import get_database
from src.models.compliance import ComplianceEvent, ViolationType
from src.utils.logging_config import setup_logging

# Setup logging
logger = setup_logging(__name__)

app = FastAPI(
    title="DeepSeaGuard Compliance Service",
    description="Real-time compliance monitoring and violation detection microservice",
    version="2.0.0"
)

class ComplianceRule(BaseModel):
    rule_id: str
    name: str
    description: str
    rule_type: str  # "geofence", "speed", "depth", "time", "custom"
    conditions: Dict[str, Any]
    severity: str  # "low", "medium", "high", "critical"
    enabled: bool = True
    priority: int = 1

class ComplianceCheck(BaseModel):
    auv_id: str
    timestamp: datetime
    position: Dict[str, float]  # lat, lng, depth
    speed: Optional[float] = None
    heading: Optional[float] = None
    battery_level: Optional[float] = None
    mission_status: Optional[str] = None
    additional_data: Optional[Dict] = None

class ComplianceResult(BaseModel):
    auv_id: str
    timestamp: datetime
    violations: List[Dict]
    warnings: List[Dict]
    compliance_score: float  # 0.0 to 1.0
    risk_level: str  # "low", "medium", "high", "critical"
    recommendations: List[str]

class ComplianceService:
    def __init__(self):
        self.active_rules: Dict[str, ComplianceRule] = {}
        self.violation_cache: Dict[str, List] = {}
        self.performance_metrics = {
            "total_checks": 0,
            "violations_detected": 0,
            "avg_response_time": 0.0,
            "rules_evaluated": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        self.db = None
        
    async def initialize(self):
        """Initialize the compliance service"""
        logger.info("Initializing Compliance Service")
        
        # Initialize database connection
        self.db = await get_database()
        
        # Load compliance rules
        await self.load_compliance_rules()
        
        # Start background tasks
        asyncio.create_task(self.cleanup_old_violations())
        asyncio.create_task(self.update_performance_metrics())
        asyncio.create_task(self.sync_violations_to_database())
        
        logger.info("Compliance Service initialized successfully")
    
    async def load_compliance_rules(self):
        """Load compliance rules from database"""
        try:
            # Sample compliance rules
            sample_rules = [
                ComplianceRule(
                    rule_id="speed_limit_001",
                    name="Speed Limit Violation",
                    description="AUV speed exceeds maximum allowed speed",
                    rule_type="speed",
                    conditions={
                        "max_speed": 10.0,  # knots
                        "min_speed": 0.0
                    },
                    severity="medium",
                    priority=1
                ),
                ComplianceRule(
                    rule_id="depth_limit_001",
                    name="Depth Limit Violation",
                    description="AUV operating depth exceeds safety limits",
                    rule_type="depth",
                    conditions={
                        "max_depth": 1000.0,  # meters
                        "min_depth": 0.0
                    },
                    severity="high",
                    priority=2
                ),
                ComplianceRule(
                    rule_id="battery_low_001",
                    name="Low Battery Warning",
                    description="AUV battery level below critical threshold",
                    rule_type="battery",
                    conditions={
                        "min_battery": 0.2,  # 20%
                        "critical_battery": 0.1  # 10%
                    },
                    severity="medium",
                    priority=3
                ),
                ComplianceRule(
                    rule_id="mission_timeout_001",
                    name="Mission Timeout",
                    description="AUV mission duration exceeds maximum allowed time",
                    rule_type="time",
                    conditions={
                        "max_mission_duration": 24.0  # hours
                    },
                    severity="high",
                    priority=4
                )
            ]
            
            for rule in sample_rules:
                self.active_rules[rule.rule_id] = rule
                
            logger.info(f"Loaded {len(sample_rules)} compliance rules")
            
        except Exception as e:
            logger.error(f"Error loading compliance rules: {e}")
    
    async def add_rule(self, rule: ComplianceRule):
        """Add a new compliance rule"""
        try:
            self.active_rules[rule.rule_id] = rule
            logger.info(f"Added compliance rule: {rule.name} ({rule.rule_id})")
        except Exception as e:
            logger.error(f"Error adding rule {rule.rule_id}: {e}")
            raise
    
    async def check_compliance(self, check: ComplianceCheck) -> ComplianceResult:
        """Check AUV compliance against all active rules"""
        start_time = datetime.now()
        
        try:
            violations = []
            warnings = []
            recommendations = []
            compliance_score = 1.0
            risk_level = "low"
            
            # Evaluate each rule
            for rule_id, rule in self.active_rules.items():
                if not rule.enabled:
                    continue
                
                self.performance_metrics["rules_evaluated"] += 1
                
                # Check rule based on type
                if rule.rule_type == "speed":
                    result = await self._check_speed_rule(check, rule)
                elif rule.rule_type == "depth":
                    result = await self._check_depth_rule(check, rule)
                elif rule.rule_type == "battery":
                    result = await self._check_battery_rule(check, rule)
                elif rule.rule_type == "time":
                    result = await self._check_time_rule(check, rule)
                else:
                    result = await self._check_custom_rule(check, rule)
                
                if result:
                    if result["type"] == "violation":
                        violations.append(result["data"])
                        compliance_score -= 0.2  # Reduce compliance score
                        if rule.severity in ["high", "critical"]:
                            risk_level = "high"
                    elif result["type"] == "warning":
                        warnings.append(result["data"])
                        compliance_score -= 0.1  # Reduce compliance score slightly
                        if risk_level == "low" and rule.severity == "medium":
                            risk_level = "medium"
            
            # Ensure compliance score is between 0 and 1
            compliance_score = max(0.0, min(1.0, compliance_score))
            
            # Generate recommendations based on violations
            if violations:
                recommendations.extend(self._generate_violation_recommendations(violations))
            if warnings:
                recommendations.extend(self._generate_warning_recommendations(warnings))
            
            # Update performance metrics
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self.performance_metrics["total_checks"] += 1
            self.performance_metrics["violations_detected"] += len(violations)
            self.performance_metrics["avg_response_time"] = (
                (self.performance_metrics["avg_response_time"] * (self.performance_metrics["total_checks"] - 1) + response_time) 
                / self.performance_metrics["total_checks"]
            )
            
            # Store violations in cache
            if violations:
                if check.auv_id not in self.violation_cache:
                    self.violation_cache[check.auv_id] = []
                self.violation_cache[check.auv_id].extend(violations)
            
            # Create response
            result = ComplianceResult(
                auv_id=check.auv_id,
                timestamp=check.timestamp,
                violations=violations,
                warnings=warnings,
                compliance_score=compliance_score,
                risk_level=risk_level,
                recommendations=recommendations
            )
            
            logger.info(f"Compliance check completed for AUV {check.auv_id} in {response_time:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Error in compliance check: {e}")
            raise HTTPException(status_code=500, detail=f"Compliance check failed: {str(e)}")
    
    async def _check_speed_rule(self, check: ComplianceCheck, rule: ComplianceRule) -> Optional[Dict]:
        """Check speed compliance rule"""
        if check.speed is None:
            return None
        
        max_speed = rule.conditions.get("max_speed", float('inf'))
        min_speed = rule.conditions.get("min_speed", 0.0)
        
        if check.speed > max_speed:
            return {
                "type": "violation",
                "data": {
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "violation_type": "speed_limit_exceeded",
                    "current_value": check.speed,
                    "limit_value": max_speed,
                    "severity": rule.severity,
                    "timestamp": check.timestamp
                }
            }
        elif check.speed < min_speed:
            return {
                "type": "warning",
                "data": {
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "warning_type": "speed_below_minimum",
                    "current_value": check.speed,
                    "limit_value": min_speed,
                    "severity": rule.severity,
                    "timestamp": check.timestamp
                }
            }
        
        return None
    
    async def _check_depth_rule(self, check: ComplianceCheck, rule: ComplianceRule) -> Optional[Dict]:
        """Check depth compliance rule"""
        depth = check.position.get("depth")
        if depth is None:
            return None
        
        max_depth = rule.conditions.get("max_depth", float('inf'))
        min_depth = rule.conditions.get("min_depth", 0.0)
        
        if depth > max_depth:
            return {
                "type": "violation",
                "data": {
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "violation_type": "depth_limit_exceeded",
                    "current_value": depth,
                    "limit_value": max_depth,
                    "severity": rule.severity,
                    "timestamp": check.timestamp
                }
            }
        elif depth < min_depth:
            return {
                "type": "warning",
                "data": {
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "warning_type": "depth_below_minimum",
                    "current_value": depth,
                    "limit_value": min_depth,
                    "severity": rule.severity,
                    "timestamp": check.timestamp
                }
            }
        
        return None
    
    async def _check_battery_rule(self, check: ComplianceCheck, rule: ComplianceRule) -> Optional[Dict]:
        """Check battery compliance rule"""
        if check.battery_level is None:
            return None
        
        min_battery = rule.conditions.get("min_battery", 0.2)
        critical_battery = rule.conditions.get("critical_battery", 0.1)
        
        if check.battery_level < critical_battery:
            return {
                "type": "violation",
                "data": {
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "violation_type": "critical_battery_level",
                    "current_value": check.battery_level,
                    "limit_value": critical_battery,
                    "severity": "critical",
                    "timestamp": check.timestamp
                }
            }
        elif check.battery_level < min_battery:
            return {
                "type": "warning",
                "data": {
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "warning_type": "low_battery_level",
                    "current_value": check.battery_level,
                    "limit_value": min_battery,
                    "severity": rule.severity,
                    "timestamp": check.timestamp
                }
            }
        
        return None
    
    async def _check_time_rule(self, check: ComplianceCheck, rule: ComplianceRule) -> Optional[Dict]:
        """Check time-based compliance rule"""
        # This would check mission duration, time windows, etc.
        # For now, return None as this requires mission tracking
        return None
    
    async def _check_custom_rule(self, check: ComplianceCheck, rule: ComplianceRule) -> Optional[Dict]:
        """Check custom compliance rule"""
        # Custom rule evaluation logic
        return None
    
    def _generate_violation_recommendations(self, violations: List[Dict]) -> List[str]:
        """Generate recommendations based on violations"""
        recommendations = []
        
        for violation in violations:
            violation_type = violation.get("violation_type", "")
            
            if "speed_limit_exceeded" in violation_type:
                recommendations.append("Reduce AUV speed to comply with speed limits")
            elif "depth_limit_exceeded" in violation_type:
                recommendations.append("Ascend to safe operating depth immediately")
            elif "critical_battery_level" in violation_type:
                recommendations.append("Initiate emergency surfacing due to critical battery level")
            else:
                recommendations.append(f"Address violation: {violation.get('rule_name', 'Unknown')}")
        
        return recommendations
    
    def _generate_warning_recommendations(self, warnings: List[Dict]) -> List[str]:
        """Generate recommendations based on warnings"""
        recommendations = []
        
        for warning in warnings:
            warning_type = warning.get("warning_type", "")
            
            if "low_battery_level" in warning_type:
                recommendations.append("Monitor battery level and plan for recharging")
            elif "speed_below_minimum" in warning_type:
                recommendations.append("Consider increasing speed for mission efficiency")
            else:
                recommendations.append(f"Monitor warning: {warning.get('rule_name', 'Unknown')}")
        
        return recommendations
    
    async def get_violation_history(self, auv_id: str, hours: int = 24) -> List[Dict]:
        """Get violation history for an AUV"""
        if auv_id not in self.violation_cache:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_violations = [
            v for v in self.violation_cache[auv_id]
            if v["timestamp"] > cutoff_time
        ]
        
        return recent_violations
    
    async def get_performance_metrics(self) -> Dict:
        """Get performance metrics"""
        return self.performance_metrics.copy()
    
    async def cleanup_old_violations(self):
        """Clean up old violation history"""
        while True:
            try:
                cutoff_time = datetime.now() - timedelta(days=7)
                for auv_id in list(self.violation_cache.keys()):
                    self.violation_cache[auv_id] = [
                        v for v in self.violation_cache[auv_id]
                        if v["timestamp"] > cutoff_time
                    ]
                    if not self.violation_cache[auv_id]:
                        del self.violation_cache[auv_id]
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
    
    async def update_performance_metrics(self):
        """Update performance metrics periodically"""
        while True:
            try:
                # Reset counters periodically
                if self.performance_metrics["total_checks"] > 10000:
                    self.performance_metrics["total_checks"] = 0
                    self.performance_metrics["violations_detected"] = 0
                    self.performance_metrics["avg_response_time"] = 0.0
                    self.performance_metrics["rules_evaluated"] = 0
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(300)
    
    async def sync_violations_to_database(self):
        """Sync violations to database periodically"""
        while True:
            try:
                if self.db:
                    # Sync violation cache to database
                    for auv_id, violations in self.violation_cache.items():
                        for violation in violations:
                            # Insert into compliance_events table
                            query = text("""
                                INSERT INTO compliance_events 
                                (auv_id, event_type, severity, details, timestamp)
                                VALUES (:auv_id, :event_type, :severity, :details, :timestamp)
                                ON CONFLICT DO NOTHING
                            """)
                            
                            await self.db.execute(query, {
                                "auv_id": auv_id,
                                "event_type": violation.get("violation_type", "unknown"),
                                "severity": violation.get("severity", "medium"),
                                "details": json.dumps(violation),
                                "timestamp": violation.get("timestamp", datetime.now())
                            })
                
                await asyncio.sleep(60)  # Run every minute
                
            except Exception as e:
                logger.error(f"Error syncing to database: {e}")
                await asyncio.sleep(60)

# Global service instance
compliance_service = ComplianceService()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    await compliance_service.initialize()

@app.post("/check", response_model=ComplianceResult)
async def check_compliance(check: ComplianceCheck):
    """Check AUV compliance against all rules"""
    return await compliance_service.check_compliance(check)

@app.get("/rules")
async def get_rules():
    """Get all active compliance rules"""
    return {
        "rules": [
            {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "rule_type": rule.rule_type,
                "severity": rule.severity,
                "enabled": rule.enabled,
                "priority": rule.priority
            }
            for rule in compliance_service.active_rules.values()
        ]
    }

@app.post("/rules")
async def add_rule(rule: ComplianceRule):
    """Add a new compliance rule"""
    await compliance_service.add_rule(rule)
    return {"message": f"Rule {rule.rule_id} added successfully"}

@app.get("/violations/{auv_id}")
async def get_violations(auv_id: str, hours: int = 24):
    """Get violation history for an AUV"""
    violations = await compliance_service.get_violation_history(auv_id, hours)
    return {"auv_id": auv_id, "violations": violations}

@app.get("/metrics")
async def get_metrics():
    """Get performance metrics"""
    return await compliance_service.get_performance_metrics()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "compliance",
        "active_rules": len(compliance_service.active_rules),
        "timestamp": datetime.now()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003) 
"""
Bytewax-based compliance processor for complex rule evaluation and alert generation
"""
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import bytewax.operators as op
from bytewax.dataflow import Dataflow
from bytewax.connectors.rabbitmq import RabbitMQInput, RabbitMQOutput
from bytewax.window import SlidingWindowConfig, TumblingWindowConfig
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplianceRule:
    """Compliance rule definition"""
    
    def __init__(self, rule_id: str, rule_type: str, conditions: Dict, actions: List[str]):
        self.rule_id = rule_id
        self.rule_type = rule_type
        self.conditions = conditions
        self.actions = actions
        self.active = True

class ComplianceRuleEngine:
    """Dynamic compliance rule engine"""
    
    def __init__(self):
        self.rules = {}
        self.rule_cache = {}
    
    def add_rule(self, rule: ComplianceRule):
        """Add a compliance rule"""
        self.rules[rule.rule_id] = rule
        self.rule_cache.clear()  # Clear cache when rules change
    
    def remove_rule(self, rule_id: str):
        """Remove a compliance rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            self.rule_cache.clear()
    
    def evaluate_rules(self, telemetry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate all active rules against telemetry"""
        violations = []
        
        for rule_id, rule in self.rules.items():
            if not rule.active:
                continue
            
            if self._evaluate_rule(rule, telemetry):
                violation = {
                    'rule_id': rule_id,
                    'rule_type': rule.rule_type,
                    'auv_id': telemetry.get('auv_id'),
                    'timestamp': telemetry.get('timestamp'),
                    'severity': self._determine_severity(rule, telemetry),
                    'message': self._generate_violation_message(rule, telemetry),
                    'actions': rule.actions
                }
                violations.append(violation)
        
        return violations
    
    def _evaluate_rule(self, rule: ComplianceRule, telemetry: Dict[str, Any]) -> bool:
        """Evaluate a single rule"""
        rule_type = rule.rule_type
        conditions = rule.conditions
        
        if rule_type == 'zone_duration':
            return self._evaluate_zone_duration_rule(conditions, telemetry)
        elif rule_type == 'depth_limit':
            return self._evaluate_depth_rule(conditions, telemetry)
        elif rule_type == 'speed_limit':
            return self._evaluate_speed_rule(conditions, telemetry)
        elif rule_type == 'boundary_violation':
            return self._evaluate_boundary_rule(conditions, telemetry)
        elif rule_type == 'complex_condition':
            return self._evaluate_complex_rule(conditions, telemetry)
        
        return False
    
    def _evaluate_zone_duration_rule(self, conditions: Dict, telemetry: Dict[str, Any]) -> bool:
        """Evaluate zone duration rule"""
        max_duration = conditions.get('max_duration_hours', 0)
        zone_id = conditions.get('zone_id')
        
        if not zone_id:
            return False
        
        # Check if AUV is in the specified zone
        current_zones = telemetry.get('spatial_zones', [])
        in_zone = any(zone['zone_id'] == zone_id for zone in current_zones)
        
        if not in_zone:
            return False
        
        # Check duration (simplified - in real implementation, track actual time)
        # This would integrate with the duration tracking from geofencing processor
        return True  # Placeholder
    
    def _evaluate_depth_rule(self, conditions: Dict, telemetry: Dict[str, Any]) -> bool:
        """Evaluate depth limit rule"""
        max_depth = conditions.get('max_depth', float('inf'))
        min_depth = conditions.get('min_depth', 0)
        
        depth = telemetry.get('depth', 0)
        
        return depth > max_depth or depth < min_depth
    
    def _evaluate_speed_rule(self, conditions: Dict, telemetry: Dict[str, Any]) -> bool:
        """Evaluate speed limit rule"""
        max_speed = conditions.get('max_speed', float('inf'))
        
        # Calculate speed from position changes (simplified)
        speed = telemetry.get('speed', 0)
        
        return speed > max_speed
    
    def _evaluate_boundary_rule(self, conditions: Dict, telemetry: Dict[str, Any]) -> bool:
        """Evaluate boundary violation rule"""
        boundary_polygon = conditions.get('boundary_polygon')
        
        if not boundary_polygon:
            return False
        
        # Check if AUV is outside boundary (simplified)
        lat = telemetry.get('latitude', 0)
        lon = telemetry.get('longitude', 0)
        
        # This would use proper spatial operations
        return False  # Placeholder
    
    def _evaluate_complex_rule(self, conditions: Dict, telemetry: Dict[str, Any]) -> bool:
        """Evaluate complex multi-condition rule"""
        # Complex rule evaluation with multiple conditions
        all_conditions = conditions.get('conditions', [])
        
        for condition in all_conditions:
            if not self._evaluate_rule(ComplianceRule("temp", condition['type'], condition, []), telemetry):
                return False
        
        return True
    
    def _determine_severity(self, rule: ComplianceRule, telemetry: Dict[str, Any]) -> str:
        """Determine violation severity"""
        # Default severity based on rule type
        severity_map = {
            'zone_duration': 'warning',
            'depth_limit': 'critical',
            'speed_limit': 'warning',
            'boundary_violation': 'critical',
            'complex_condition': 'warning'
        }
        
        return severity_map.get(rule.rule_type, 'warning')
    
    def _generate_violation_message(self, rule: ComplianceRule, telemetry: Dict[str, Any]) -> str:
        """Generate violation message"""
        auv_id = telemetry.get('auv_id', 'Unknown')
        
        if rule.rule_type == 'zone_duration':
            return f"AUV {auv_id} exceeded time limit in restricted zone"
        elif rule.rule_type == 'depth_limit':
            return f"AUV {auv_id} operating outside depth limits"
        elif rule.rule_type == 'speed_limit':
            return f"AUV {auv_id} exceeded speed limit"
        elif rule.rule_type == 'boundary_violation':
            return f"AUV {auv_id} operating outside designated boundary"
        else:
            return f"AUV {auv_id} violated compliance rule {rule.rule_id}"

# Global rule engine
rule_engine = ComplianceRuleEngine()

def evaluate_compliance_rules(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate compliance rules for telemetry"""
    if not telemetry:
        return None
    
    # Evaluate rules
    violations = rule_engine.evaluate_rules(telemetry)
    
    # Add violations to telemetry
    telemetry['compliance_violations'] = violations
    telemetry['compliance_status'] = 'violation' if violations else 'compliant'
    telemetry['compliance_evaluated_at'] = datetime.now(timezone.utc)
    
    return telemetry

def classify_violation_severity(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """Classify violations by severity"""
    if not telemetry:
        return None
    
    violations = telemetry.get('compliance_violations', [])
    
    # Group violations by severity
    severity_groups = {
        'critical': [],
        'warning': [],
        'info': []
    }
    
    for violation in violations:
        severity = violation.get('severity', 'warning')
        severity_groups[severity].append(violation)
    
    telemetry['violations_by_severity'] = severity_groups
    telemetry['has_critical_violations'] = len(severity_groups['critical']) > 0
    telemetry['has_warnings'] = len(severity_groups['warning']) > 0
    
    return telemetry

def generate_compliance_alerts(telemetry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate compliance alerts"""
    if not telemetry:
        return []
    
    alerts = []
    violations = telemetry.get('compliance_violations', [])
    
    for violation in violations:
        alert = {
            'alert_id': f"alert_{telemetry['auv_id']}_{violation['rule_id']}_{int(telemetry['timestamp'].timestamp())}",
            'auv_id': telemetry['auv_id'],
            'alert_type': 'compliance_violation',
            'severity': violation['severity'],
            'message': violation['message'],
            'rule_id': violation['rule_id'],
            'timestamp': telemetry['timestamp'],
            'position': {
                'latitude': telemetry['latitude'],
                'longitude': telemetry['longitude'],
                'depth': telemetry['depth']
            },
            'actions': violation.get('actions', []),
            'requires_immediate_action': violation['severity'] == 'critical'
        }
        alerts.append(alert)
    
    return alerts

def create_compliance_flow() -> Dataflow:
    """Create Bytewax dataflow for compliance processing"""
    flow = Dataflow("compliance_processor")
    
    # Input: Enriched telemetry with zone data
    telemetry_stream = op.input("compliance_input", flow, RabbitMQInput(
        queue_name="enriched_telemetry",
        host="localhost",
        port=5672
    ))
    
    # Load dynamic rules (simplified - in real implementation, this would be a separate stream)
    # For now, we'll initialize rules statically
    initialize_rules()
    
    # Evaluate compliance rules
    rule_evaluation = op.map("evaluate_rules", telemetry_stream, evaluate_compliance_rules)
    
    # Classify violations by severity
    classified_violations = op.map("classify_severity", rule_evaluation, classify_violation_severity)
    
    # Generate alerts
    alerts = op.map("generate_alerts", classified_violations, generate_compliance_alerts)
    
    # Flatten alerts list
    flattened_alerts = op.flat_map("flatten_alerts", alerts, lambda x: x)
    
    # Route alerts by severity
    critical_alerts = op.filter("critical_alerts", flattened_alerts, 
                               lambda x: x.get('severity') == 'critical')
    warning_alerts = op.filter("warning_alerts", flattened_alerts, 
                              lambda x: x.get('severity') == 'warning')
    info_alerts = op.filter("info_alerts", flattened_alerts, 
                           lambda x: x.get('severity') == 'info')
    
    # Output critical alerts immediately
    op.output("critical_output", critical_alerts, RabbitMQOutput(
        queue_name="critical_alerts",
        host="localhost",
        port=5672
    ))
    
    # Batch warning alerts
    batched_warnings = op.window.collect_window(
        "batch_warnings",
        warning_alerts,
        window_config=TumblingWindowConfig(size=timedelta(minutes=5))
    )
    
    op.output("warning_output", batched_warnings, RabbitMQOutput(
        queue_name="warning_alerts",
        host="localhost",
        port=5672
    ))
    
    # Batch info alerts
    batched_info = op.window.collect_window(
        "batch_info",
        info_alerts,
        window_config=TumblingWindowConfig(size=timedelta(minutes=10))
    )
    
    op.output("info_output", batched_info, RabbitMQOutput(
        queue_name="info_alerts",
        host="localhost",
        port=5672
    ))
    
    # Output compliance analytics
    op.output("analytics_output", classified_violations, RabbitMQOutput(
        queue_name="compliance_analytics",
        host="localhost",
        port=5672
    ))
    
    return flow

def create_alert_aggregation_flow() -> Dataflow:
    """Create dataflow for alert aggregation and reporting"""
    flow = Dataflow("alert_aggregation")
    
    # Input all alerts
    alert_stream = op.input("alert_input", flow, RabbitMQInput(
        queue_name="critical_alerts"
    ))
    
    # Aggregate alerts by AUV
    keyed_alerts = op.map("key_by_auv", alert_stream, 
                         lambda x: (x['auv_id'], x))
    
    # Aggregate over time windows
    aggregated_alerts = op.window.collect_window(
        "alert_aggregation",
        keyed_alerts,
        window_config=SlidingWindowConfig(
            size=timedelta(minutes=15),
            step=timedelta(minutes=5)
        )
    )
    
    # Generate alert summaries
    alert_summaries = op.map("generate_summaries", aggregated_alerts, generate_alert_summary)
    
    # Output alert summaries
    op.output("summary_output", alert_summaries, RabbitMQOutput(
        queue_name="alert_summaries",
        host="localhost",
        port=5672
    ))
    
    return flow

def generate_alert_summary(alert_batch):
    """Generate alert summary for a batch of alerts"""
    auv_id, alerts = alert_batch
    
    if not alerts:
        return None
    
    # Count alerts by severity
    severity_counts = {
        'critical': 0,
        'warning': 0,
        'info': 0
    }
    
    for alert in alerts:
        severity = alert.get('severity', 'warning')
        severity_counts[severity] += 1
    
    # Get latest position
    latest_alert = max(alerts, key=lambda x: x['timestamp'])
    
    summary = {
        'auv_id': auv_id,
        'timestamp': datetime.now(timezone.utc),
        'alert_count': len(alerts),
        'severity_counts': severity_counts,
        'latest_position': latest_alert.get('position'),
        'latest_alert_type': latest_alert.get('alert_type'),
        'requires_attention': severity_counts['critical'] > 0
    }
    
    return summary

def initialize_rules():
    """Initialize compliance rules"""
    # Zone duration rules
    rule_engine.add_rule(ComplianceRule(
        rule_id="zone_duration_001",
        rule_type="zone_duration",
        conditions={
            'zone_id': 'ISA_JAMAICA_001',
            'max_duration_hours': 1
        },
        actions=['send_alert', 'log_violation']
    ))
    
    # Depth limit rules
    rule_engine.add_rule(ComplianceRule(
        rule_id="depth_limit_001",
        rule_type="depth_limit",
        conditions={
            'max_depth': 1000,
            'min_depth': 0
        },
        actions=['send_alert', 'emergency_stop']
    ))
    
    # Speed limit rules
    rule_engine.add_rule(ComplianceRule(
        rule_id="speed_limit_001",
        rule_type="speed_limit",
        conditions={
            'max_speed': 10.0  # knots
        },
        actions=['send_alert', 'reduce_speed']
    ))

if __name__ == "__main__":
    # Create and run the compliance processing flow
    flow = create_compliance_flow()
    
    # Run the flow
    from bytewax.run import run_main
    run_main(flow) 
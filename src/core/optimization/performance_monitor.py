"""
Performance Monitor for DeepSeaGuard
Comprehensive system monitoring and performance analytics
"""
import logging
import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import psutil
import threading
from functools import wraps

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Performance metric data"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LatencyMetric:
    """Latency measurement"""
    operation: str
    duration_ms: float
    timestamp: datetime
    success: bool
    error: Optional[str] = None

class PerformanceMonitor:
    """Comprehensive performance monitoring system"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetric] = []
        self.latency_metrics: List[LatencyMetric] = []
        self.system_stats = {
            'cpu_usage': deque(maxlen=100),
            'memory_usage': deque(maxlen=100),
            'disk_io': deque(maxlen=100),
            'network_io': deque(maxlen=100)
        }
        self.operation_counters = defaultdict(int)
        self.error_counters = defaultdict(int)
        self.alert_thresholds = {
            'cpu_usage': 80.0,  # Alert if CPU > 80%
            'memory_usage': 85.0,  # Alert if memory > 85%
            'latency_ms': 1000.0,  # Alert if latency > 1 second
            'error_rate': 5.0  # Alert if error rate > 5%
        }
        
        # Start monitoring threads
        self._start_system_monitoring()
        self._start_cleanup_task()
    
    def _start_system_monitoring(self):
        """Start system resource monitoring"""
        def monitor_system():
            while True:
                try:
                    # CPU usage
                    cpu_percent = psutil.cpu_percent(interval=1)
                    self.system_stats['cpu_usage'].append({
                        'value': cpu_percent,
                        'timestamp': datetime.utcnow()
                    })
                    
                    # Memory usage
                    memory = psutil.virtual_memory()
                    self.system_stats['memory_usage'].append({
                        'value': memory.percent,
                        'timestamp': datetime.utcnow()
                    })
                    
                    # Disk I/O
                    disk_io = psutil.disk_io_counters()
                    if disk_io:
                        self.system_stats['disk_io'].append({
                            'read_bytes': disk_io.read_bytes,
                            'write_bytes': disk_io.write_bytes,
                            'timestamp': datetime.utcnow()
                        })
                    
                    # Network I/O
                    net_io = psutil.net_io_counters()
                    if net_io:
                        self.system_stats['network_io'].append({
                            'bytes_sent': net_io.bytes_sent,
                            'bytes_recv': net_io.bytes_recv,
                            'timestamp': datetime.utcnow()
                        })
                    
                    # Check for alerts
                    self._check_alerts()
                    
                    time.sleep(10)  # Monitor every 10 seconds
                    
                except Exception as e:
                    logger.error(f"Error in system monitoring: {e}")
                    time.sleep(30)  # Wait longer on error
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(target=monitor_system, daemon=True)
        monitor_thread.start()
    
    def _start_cleanup_task(self):
        """Start cleanup task for old metrics"""
        def cleanup_old_metrics():
            while True:
                try:
                    cutoff_time = datetime.utcnow() - timedelta(hours=24)
                    
                    # Clean up old metrics
                    self.metrics = [
                        m for m in self.metrics
                        if m.timestamp > cutoff_time
                    ]
                    
                    # Clean up old latency metrics
                    self.latency_metrics = [
                        l for l in self.latency_metrics
                        if l.timestamp > cutoff_time
                    ]
                    
                    time.sleep(3600)  # Clean up every hour
                    
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
                    time.sleep(3600)
        
        cleanup_thread = threading.Thread(target=cleanup_old_metrics, daemon=True)
        cleanup_thread.start()
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None, 
                     metadata: Dict[str, Any] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags or {},
            metadata=metadata or {}
        )
        self.metrics.append(metric)
    
    def record_latency(self, operation: str, duration_ms: float, success: bool = True, 
                      error: str = None):
        """Record latency for an operation"""
        latency = LatencyMetric(
            operation=operation,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow(),
            success=success,
            error=error
        )
        self.latency_metrics.append(latency)
        
        # Update counters
        self.operation_counters[operation] += 1
        if not success:
            self.error_counters[operation] += 1
    
    def monitor_latency(self, operation_name: str = None):
        """Decorator to monitor function latency"""
        def decorator(func: Callable):
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                error = None
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error = str(e)
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    op_name = operation_name or f"{func.__module__}.{func.__name__}"
                    self.record_latency(op_name, duration_ms, success, error)
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                error = None
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error = str(e)
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    op_name = operation_name or f"{func.__module__}.{func.__name__}"
                    self.record_latency(op_name, duration_ms, success, error)
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def _check_alerts(self):
        """Check for performance alerts"""
        try:
            # Check CPU usage
            if self.system_stats['cpu_usage']:
                latest_cpu = self.system_stats['cpu_usage'][-1]['value']
                if latest_cpu > self.alert_thresholds['cpu_usage']:
                    logger.warning(f"High CPU usage detected: {latest_cpu}%")
            
            # Check memory usage
            if self.system_stats['memory_usage']:
                latest_memory = self.system_stats['memory_usage'][-1]['value']
                if latest_memory > self.alert_thresholds['memory_usage']:
                    logger.warning(f"High memory usage detected: {latest_memory}%")
            
            # Check latency
            recent_latency = [
                l for l in self.latency_metrics[-100:]  # Last 100 operations
                if l.duration_ms > self.alert_thresholds['latency_ms']
            ]
            if recent_latency:
                avg_latency = sum(l.duration_ms for l in recent_latency) / len(recent_latency)
                logger.warning(f"High latency detected: {avg_latency:.2f}ms average")
            
            # Check error rate
            for operation, total_count in self.operation_counters.items():
                error_count = self.error_counters.get(operation, 0)
                if total_count > 0:
                    error_rate = (error_count / total_count) * 100
                    if error_rate > self.alert_thresholds['error_rate']:
                        logger.warning(f"High error rate for {operation}: {error_rate:.1f}%")
                        
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        try:
            # Calculate latency statistics
            if self.latency_metrics:
                recent_latency = self.latency_metrics[-1000:]  # Last 1000 operations
                avg_latency = sum(l.duration_ms for l in recent_latency) / len(recent_latency)
                max_latency = max(l.duration_ms for l in recent_latency)
                min_latency = min(l.duration_ms for l in recent_latency)
                
                # Group by operation
                operation_latency = defaultdict(list)
                for l in recent_latency:
                    operation_latency[l.operation].append(l.duration_ms)
                
                operation_stats = {}
                for op, latencies in operation_latency.items():
                    operation_stats[op] = {
                        'avg_latency_ms': sum(latencies) / len(latencies),
                        'max_latency_ms': max(latencies),
                        'min_latency_ms': min(latencies),
                        'count': len(latencies),
                        'error_count': self.error_counters.get(op, 0)
                    }
            else:
                avg_latency = max_latency = min_latency = 0
                operation_stats = {}
            
            # Calculate system statistics
            if self.system_stats['cpu_usage']:
                latest_cpu = self.system_stats['cpu_usage'][-1]['value']
                avg_cpu = sum(s['value'] for s in self.system_stats['cpu_usage']) / len(self.system_stats['cpu_usage'])
            else:
                latest_cpu = avg_cpu = 0
            
            if self.system_stats['memory_usage']:
                latest_memory = self.system_stats['memory_usage'][-1]['value']
                avg_memory = sum(s['value'] for s in self.system_stats['memory_usage']) / len(self.system_stats['memory_usage'])
            else:
                latest_memory = avg_memory = 0
            
            return {
                'latency': {
                    'avg_latency_ms': round(avg_latency, 2),
                    'max_latency_ms': round(max_latency, 2),
                    'min_latency_ms': round(min_latency, 2),
                    'total_operations': len(self.latency_metrics),
                    'operation_stats': operation_stats
                },
                'system': {
                    'cpu_usage': {
                        'current': round(latest_cpu, 2),
                        'average': round(avg_cpu, 2)
                    },
                    'memory_usage': {
                        'current': round(latest_memory, 2),
                        'average': round(avg_memory, 2)
                    },
                    'disk_io': len(self.system_stats['disk_io']),
                    'network_io': len(self.system_stats['network_io'])
                },
                'counters': {
                    'operations': dict(self.operation_counters),
                    'errors': dict(self.error_counters)
                },
                'metrics': {
                    'total_metrics': len(self.metrics),
                    'metric_types': list(set(m.name for m in self.metrics))
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting performance stats: {e}")
            return {}
    
    def get_health_status(self) -> Dict[str, str]:
        """Get system health status"""
        try:
            status = {
                'overall': 'healthy',
                'cpu': 'healthy',
                'memory': 'healthy',
                'latency': 'healthy',
                'errors': 'healthy'
            }
            
            # Check CPU
            if self.system_stats['cpu_usage']:
                latest_cpu = self.system_stats['cpu_usage'][-1]['value']
                if latest_cpu > self.alert_thresholds['cpu_usage']:
                    status['cpu'] = 'warning'
                    status['overall'] = 'warning'
            
            # Check memory
            if self.system_stats['memory_usage']:
                latest_memory = self.system_stats['memory_usage'][-1]['value']
                if latest_memory > self.alert_thresholds['memory_usage']:
                    status['memory'] = 'warning'
                    status['overall'] = 'warning'
            
            # Check latency
            if self.latency_metrics:
                recent_latency = self.latency_metrics[-100:]
                slow_operations = [l for l in recent_latency if l.duration_ms > self.alert_thresholds['latency_ms']]
                if len(slow_operations) > len(recent_latency) * 0.1:  # More than 10% slow
                    status['latency'] = 'warning'
                    status['overall'] = 'warning'
            
            # Check errors
            total_operations = sum(self.operation_counters.values())
            total_errors = sum(self.error_counters.values())
            if total_operations > 0:
                error_rate = (total_errors / total_operations) * 100
                if error_rate > self.alert_thresholds['error_rate']:
                    status['errors'] = 'critical'
                    status['overall'] = 'critical'
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {'overall': 'unknown'}

# Global performance monitor instance
performance_monitor = PerformanceMonitor() 
"""
DeepSeaGuard Optimization Module
High-performance optimization components for scalability and maintainability
"""

from .cache_manager import cache_manager, CacheManager, cached
from .spatial_index import spatial_index, SpatialIndex
from .database_optimizer import db_optimizer, DatabaseOptimizer
from .performance_monitor import performance_monitor, PerformanceMonitor

__all__ = [
    'cache_manager',
    'CacheManager', 
    'cached',
    'spatial_index',
    'SpatialIndex',
    'db_optimizer',
    'DatabaseOptimizer',
    'performance_monitor',
    'PerformanceMonitor'
] 
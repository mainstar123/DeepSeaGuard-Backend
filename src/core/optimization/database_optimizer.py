"""
Database Optimizer for DeepSeaGuard
Provides optimized database operations with connection pooling and query optimization
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from sqlalchemy import text, create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import time
from dataclasses import dataclass
from collections import defaultdict

from config.settings import settings

logger = logging.getLogger(__name__)

@dataclass
class QueryMetrics:
    """Query performance metrics"""
    query: str
    execution_time: float
    timestamp: datetime
    success: bool
    error: Optional[str] = None

class DatabaseOptimizer:
    """Database optimization and monitoring"""
    
    def __init__(self):
        self.query_metrics: List[QueryMetrics] = []
        self.connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'failed_connections': 0,
            'slow_queries': 0
        }
        self.slow_query_threshold = 1.0  # seconds
        
        # Create optimized engines
        self._create_engines()
        self._setup_monitoring()
    
    def _create_engines(self):
        """Create optimized database engines"""
        # Sync engine with connection pooling
        self.sync_engine = create_engine(
            settings.DATABASE_SYNC_URL,
            poolclass=QueuePool,
            pool_size=20,  # Maximum number of connections
            max_overflow=30,  # Additional connections beyond pool_size
            pool_pre_ping=True,  # Validate connections before use
            pool_recycle=3600,  # Recycle connections every hour
            pool_timeout=30,  # Timeout for getting connection from pool
            echo=settings.DEBUG,
            connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_SYNC_URL else {}
        )
        
        # Async engine
        self.async_engine = create_async_engine(
            settings.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_timeout=30,
            echo=settings.DEBUG,
            connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
        )
        
        # Session makers
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.sync_engine
        )
        
        self.AsyncSessionLocal = async_sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    def _setup_monitoring(self):
        """Setup database monitoring"""
        @event.listens_for(self.sync_engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            self.connection_stats['total_connections'] += 1
            self.connection_stats['active_connections'] += 1
        
        @event.listens_for(self.sync_engine, "disconnect")
        def receive_disconnect(dbapi_connection, connection_record):
            self.connection_stats['active_connections'] -= 1
        
        @event.listens_for(self.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            pass
        
        @event.listens_for(self.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            pass
    
    @asynccontextmanager
    async def get_async_session(self):
        """Get async database session with automatic cleanup"""
        session = self.AsyncSessionLocal()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    def get_sync_session(self) -> Session:
        """Get sync database session"""
        return self.SessionLocal()
    
    def monitor_query(self, query_func):
        """Decorator to monitor query performance"""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = query_func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Record metrics
                metrics = QueryMetrics(
                    query=str(query_func.__name__),
                    execution_time=execution_time,
                    timestamp=datetime.utcnow(),
                    success=success
                )
                self.query_metrics.append(metrics)
                
                # Check for slow queries
                if execution_time > self.slow_query_threshold:
                    self.connection_stats['slow_queries'] += 1
                    logger.warning(f"Slow query detected: {query_func.__name__} took {execution_time:.2f}s")
                
                return result
                
            except Exception as e:
                success = False
                error = str(e)
                execution_time = time.time() - start_time
                
                metrics = QueryMetrics(
                    query=str(query_func.__name__),
                    execution_time=execution_time,
                    timestamp=datetime.utcnow(),
                    success=success,
                    error=error
                )
                self.query_metrics.append(metrics)
                
                logger.error(f"Query failed: {query_func.__name__} - {error}")
                raise
        
        return wrapper
    
    async def optimize_tables(self):
        """Optimize database tables"""
        try:
            async with self.get_async_session() as session:
                if 'sqlite' in settings.DATABASE_URL:
                    await session.execute(text("VACUUM"))
                    await session.execute(text("ANALYZE"))
                elif 'postgresql' in settings.DATABASE_URL:
                    await session.execute(text("VACUUM ANALYZE"))
                
                await session.commit()
                logger.info("Database tables optimized")
                
        except Exception as e:
            logger.error(f"Error optimizing tables: {e}")
    
    async def create_indexes(self):
        """Create performance indexes"""
        try:
            async with self.get_async_session() as session:
                # Create indexes for common queries
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_compliance_events_auv_id ON compliance_events(auv_id)",
                    "CREATE INDEX IF NOT EXISTS idx_compliance_events_timestamp ON compliance_events(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_compliance_events_zone_id ON compliance_events(zone_id)",
                    "CREATE INDEX IF NOT EXISTS idx_isa_zones_zone_type ON isa_zones(zone_type)",
                    "CREATE INDEX IF NOT EXISTS idx_isa_zones_active ON isa_zones(is_active)"
                ]
                
                for index_sql in indexes:
                    await session.execute(text(index_sql))
                
                await session.commit()
                logger.info("Database indexes created")
                
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get database performance statistics"""
        # Calculate query statistics
        total_queries = len(self.query_metrics)
        successful_queries = len([q for q in self.query_metrics if q.success])
        failed_queries = total_queries - successful_queries
        
        if total_queries > 0:
            avg_execution_time = sum(q.execution_time for q in self.query_metrics) / total_queries
            max_execution_time = max(q.execution_time for q in self.query_metrics)
            min_execution_time = min(q.execution_time for q in self.query_metrics)
        else:
            avg_execution_time = max_execution_time = min_execution_time = 0
        
        # Get recent slow queries
        recent_slow_queries = [
            q for q in self.query_metrics[-100:]  # Last 100 queries
            if q.execution_time > self.slow_query_threshold
        ]
        
        return {
            'connection_stats': self.connection_stats,
            'query_stats': {
                'total_queries': total_queries,
                'successful_queries': successful_queries,
                'failed_queries': failed_queries,
                'success_rate': (successful_queries / total_queries * 100) if total_queries > 0 else 0,
                'avg_execution_time': round(avg_execution_time, 3),
                'max_execution_time': round(max_execution_time, 3),
                'min_execution_time': round(min_execution_time, 3),
                'slow_queries_count': len(recent_slow_queries)
            },
            'recent_slow_queries': [
                {
                    'query': q.query,
                    'execution_time': round(q.execution_time, 3),
                    'timestamp': q.timestamp.isoformat(),
                    'error': q.error
                }
                for q in recent_slow_queries
            ]
        }
    
    def cleanup_old_metrics(self, days: int = 7):
        """Clean up old query metrics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        self.query_metrics = [
            q for q in self.query_metrics
            if q.timestamp > cutoff_date
        ]
        logger.info(f"Cleaned up query metrics older than {days} days")

# Global database optimizer instance
db_optimizer = DatabaseOptimizer() 
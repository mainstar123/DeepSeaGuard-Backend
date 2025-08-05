"""
Cache Manager for DeepSeaGuard
Provides intelligent caching for zones, telemetry, and compliance data
"""
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import hashlib
from functools import wraps
import asyncio
from concurrent.futures import ThreadPoolExecutor

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from config.settings import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """Intelligent cache manager with Redis and in-memory fallback"""
    
    def __init__(self):
        self.redis_client = None
        self.memory_cache: Dict[str, Dict] = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        self._init_redis()
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    def _init_redis(self):
        """Initialize Redis connection if available"""
        if REDIS_AVAILABLE and hasattr(settings, 'REDIS_URL'):
            try:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Redis not available, using in-memory cache: {e}")
                self.redis_client = None
        else:
            logger.info("Using in-memory cache (Redis not configured)")
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments"""
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            key_parts.append(str(arg))
        
        # Add keyword arguments (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}:{value}")
        
        key_string = ":".join(key_parts)
        return f"{settings.CACHE_PREFIX}:{key_string}"
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for caching"""
        if isinstance(value, (dict, list)):
            return json.dumps(value, default=str)
        return str(value)
    
    def _deserialize_value(self, value: str, value_type: type = str) -> Any:
        """Deserialize cached value"""
        if value_type == dict or value_type == list:
            return json.loads(value)
        return value_type(value)
    
    async def get(self, key: str, default: Any = None, value_type: type = str) -> Any:
        """Get value from cache"""
        try:
            if self.redis_client:
                # Try Redis first
                value = await asyncio.get_event_loop().run_in_executor(
                    self._executor, self.redis_client.get, key
                )
                if value is not None:
                    self.cache_stats['hits'] += 1
                    return self._deserialize_value(value, value_type)
            
            # Fallback to memory cache
            if key in self.memory_cache:
                cache_entry = self.memory_cache[key]
                if cache_entry['expires_at'] > datetime.utcnow():
                    self.cache_stats['hits'] += 1
                    return cache_entry['value']
                else:
                    # Expired, remove it
                    del self.memory_cache[key]
            
            self.cache_stats['misses'] += 1
            return default
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return default
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with TTL"""
        try:
            ttl = ttl or settings.CACHE_TTL
            serialized_value = self._serialize_value(value)
            
            if self.redis_client:
                # Try Redis first
                success = await asyncio.get_event_loop().run_in_executor(
                    self._executor, self.redis_client.setex, key, ttl, serialized_value
                )
                if success:
                    self.cache_stats['sets'] += 1
                    return True
            
            # Fallback to memory cache
            self.memory_cache[key] = {
                'value': value,
                'expires_at': datetime.utcnow() + timedelta(seconds=ttl)
            }
            self.cache_stats['sets'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if self.redis_client:
                await asyncio.get_event_loop().run_in_executor(
                    self._executor, self.redis_client.delete, key
                )
            
            if key in self.memory_cache:
                del self.memory_cache[key]
            
            self.cache_stats['deletes'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        try:
            deleted_count = 0
            
            if self.redis_client:
                keys = await asyncio.get_event_loop().run_in_executor(
                    self._executor, self.redis_client.keys, pattern
                )
                if keys:
                    deleted_count = await asyncio.get_event_loop().run_in_executor(
                        self._executor, self.redis_client.delete, *keys
                    )
            
            # Also clear memory cache keys matching pattern
            memory_keys = [k for k in self.memory_cache.keys() if pattern in k]
            for key in memory_keys:
                del self.memory_cache[key]
                deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache pattern invalidation error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.cache_stats,
            'hit_rate_percent': round(hit_rate, 2),
            'memory_cache_size': len(self.memory_cache),
            'redis_available': self.redis_client is not None
        }
    
    async def clear_all(self) -> bool:
        """Clear all cache data"""
        try:
            if self.redis_client:
                await asyncio.get_event_loop().run_in_executor(
                    self._executor, self.redis_client.flushdb
                )
            
            self.memory_cache.clear()
            return True
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

# Global cache instance
cache_manager = CacheManager()

def cached(prefix: str, ttl: int = None, key_func=None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_manager._generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key, value_type=dict)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator 
"""
Advanced caching system with Redis
"""
import json
import pickle
from typing import Any, Optional, Union
import aioredis
from src.config.settings import settings
from src.core.logging import get_logger
from src.core.monitoring import PerformanceMonitor

logger = get_logger(__name__)

class RedisCache:
    """Redis-based caching system"""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.connected = False
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                password=settings.REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            self.connected = True
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.connected = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.connected or not self.redis:
            PerformanceMonitor.track_cache_miss()
            return None
        
        try:
            value = await self.redis.get(key)
            if value:
                PerformanceMonitor.track_cache_hit()
                return json.loads(value)
            else:
                PerformanceMonitor.track_cache_miss()
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            PerformanceMonitor.track_cache_miss()
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache"""
        if not self.connected or not self.redis:
            return False
        
        try:
            ttl = ttl or settings.CACHE_TTL
            await self.redis.setex(
                key,
                ttl,
                json.dumps(value, default=str)
            )
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.connected or not self.redis:
            return False
        
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.connected or not self.redis:
            return False
        
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key"""
        if not self.connected or not self.redis:
            return False
        
        try:
            return await self.redis.expire(key, ttl)
        except Exception as e:
            logger.error(f"Cache expire error: {e}")
            return False

# Global cache instance
cache = RedisCache()

def cache_key(prefix: str, *args) -> str:
    """Generate cache key"""
    return f"deepseaguard:{prefix}:{':'.join(str(arg) for arg in args)}"

async def get_cached_or_fetch(key: str, fetch_func, ttl: int = None):
    """Get from cache or fetch and cache"""
    # Try cache first
    cached_value = await cache.get(key)
    if cached_value is not None:
        return cached_value
    
    # Fetch and cache
    value = await fetch_func()
    if value is not None:
        await cache.set(key, value, ttl)
    
    return value 
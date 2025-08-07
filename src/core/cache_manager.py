"""
Production-ready cache management for DeepSeaGuard
"""
import json
import pickle
from typing import Any, Optional, Dict, List
from cachetools import TTLCache
import redis.asyncio as aioredis
from config.settings import settings
from core.logging import LoggerMixin
from core.monitoring import performance_monitor


class CacheManager(LoggerMixin):
    """Production-ready cache manager with Redis and in-memory caching"""
    
    def __init__(self):
        super().__init__()
        self.redis_client: Optional[aioredis.Redis] = None
        self.memory_cache = TTLCache(maxsize=1000, ttl=settings.CACHE_TTL)
        self.zone_cache = TTLCache(maxsize=500, ttl=settings.ZONE_CACHE_TTL)
        self._initialized = False
    
    async def initialize(self):
        """Initialize Redis connection"""
        if self._initialized:
            return
        
        try:
            self.redis_client = aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                password=settings.REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            self._initialized = True
            self.logger.info("Redis cache initialized successfully")
            
        except Exception as e:
            self.logger.warning(f"Redis initialization failed, using memory cache only: {e}")
            self.redis_client = None
    
    async def get(self, key: str, cache_type: str = "memory") -> Optional[Any]:
        """Get value from cache"""
        try:
            if cache_type == "redis" and self.redis_client:
                value = await self.redis_client.get(key)
                if value:
                    performance_monitor.record_cache_hit("redis")
                    return json.loads(value)
                else:
                    performance_monitor.record_cache_miss("redis")
                    return None
            
            elif cache_type == "memory":
                cache = self._get_memory_cache(key)
                if key in cache:
                    performance_monitor.record_cache_hit("memory")
                    return cache[key]
                else:
                    performance_monitor.record_cache_miss("memory")
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None, cache_type: str = "memory"):
        """Set value in cache"""
        try:
            if cache_type == "redis" and self.redis_client:
                serialized_value = json.dumps(value)
                if ttl:
                    await self.redis_client.setex(key, ttl, serialized_value)
                else:
                    await self.redis_client.set(key, serialized_value)
            
            elif cache_type == "memory":
                cache = self._get_memory_cache(key)
                cache[key] = value
            
        except Exception as e:
            self.logger.error(f"Cache set error for key {key}: {e}")
    
    async def delete(self, key: str, cache_type: str = "memory"):
        """Delete value from cache"""
        try:
            if cache_type == "redis" and self.redis_client:
                await self.redis_client.delete(key)
            
            elif cache_type == "memory":
                cache = self._get_memory_cache(key)
                if key in cache:
                    del cache[key]
            
        except Exception as e:
            self.logger.error(f"Cache delete error for key {key}: {e}")
    
    async def clear(self, cache_type: str = "memory"):
        """Clear all cache"""
        try:
            if cache_type == "redis" and self.redis_client:
                await self.redis_client.flushdb()
            
            elif cache_type == "memory":
                self.memory_cache.clear()
                self.zone_cache.clear()
            
        except Exception as e:
            self.logger.error(f"Cache clear error: {e}")
    
    def _get_memory_cache(self, key: str) -> TTLCache:
        """Get appropriate memory cache based on key prefix"""
        if key.startswith("zone:"):
            return self.zone_cache
        return self.memory_cache
    
    async def get_auv_state(self, auv_id: str) -> Optional[Dict]:
        """Get AUV state from cache"""
        return await self.get(f"auv_state:{auv_id}", "redis")
    
    async def set_auv_state(self, auv_id: str, state: Dict, ttl: int = 300):
        """Set AUV state in cache"""
        await self.set(f"auv_state:{auv_id}", state, ttl, "redis")
    
    async def get_zone_data(self, zone_id: str) -> Optional[Dict]:
        """Get zone data from cache"""
        return await self.get(f"zone:{zone_id}", "memory")
    
    async def set_zone_data(self, zone_id: str, zone_data: Dict):
        """Set zone data in cache"""
        await self.set(f"zone:{zone_id}", zone_data, cache_type="memory")
    
    async def get_compliance_rules(self) -> Optional[List[Dict]]:
        """Get compliance rules from cache"""
        return await self.get("compliance_rules", "memory")
    
    async def set_compliance_rules(self, rules: List[Dict]):
        """Set compliance rules in cache"""
        await self.set("compliance_rules", rules, cache_type="memory")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "memory_cache_size": len(self.memory_cache),
            "zone_cache_size": len(self.zone_cache),
            "redis_connected": self.redis_client is not None
        }
        
        if self.redis_client:
            try:
                info = await self.redis_client.info()
                stats["redis_info"] = {
                    "used_memory": info.get("used_memory", 0),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0)
                }
            except Exception as e:
                stats["redis_error"] = str(e)
        
        return stats


# Global cache manager instance
cache_manager = CacheManager() 
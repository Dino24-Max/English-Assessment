"""
Redis caching utilities for performance optimization
Provides decorators and utilities for caching database queries
"""

import json
import logging
import functools
from typing import Any, Callable, Optional, Union
from datetime import timedelta
import redis.asyncio as aioredis
from redis.exceptions import RedisError

from core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis cache manager with async support"""
    
    _instance: Optional['CacheManager'] = None
    _redis_client: Optional[aioredis.Redis] = None
    
    def __new__(cls):
        """Singleton pattern to ensure single Redis connection"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self):
        """Initialize Redis connection - gracefully handles Redis unavailability"""
        if self._redis_client is None:
            try:
                self._redis_client = await aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    health_check_interval=30
                )
                await self._redis_client.ping()
                logger.info("✅ Redis cache connected successfully - Caching ENABLED")
            except (RedisError, Exception) as e:
                logger.warning(f"⚠️ Redis not available: {e}")
                logger.warning("⚠️ Application will run WITHOUT caching - Performance may be reduced")
                logger.info("💡 To enable caching: Install and start Redis server")
                self._redis_client = None
    
    async def disconnect(self):
        """Close Redis connection"""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
            logger.info("Redis cache disconnected")
    
    @property
    def redis(self) -> Optional[aioredis.Redis]:
        """Get Redis client instance"""
        return self._redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._redis_client:
            return None
        
        try:
            value = await self._redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """Set value in cache with optional TTL (time to live)"""
        if not self._redis_client:
            return False
        
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                if isinstance(ttl, timedelta):
                    ttl = int(ttl.total_seconds())
                await self._redis_client.setex(key, ttl, serialized)
            else:
                await self._redis_client.set(key, serialized)
            return True
        except (RedisError, TypeError, ValueError) as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self._redis_client:
            return False
        
        try:
            await self._redis_client.delete(key)
            return True
        except RedisError as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self._redis_client:
            return 0
        
        try:
            keys = []
            async for key in self._redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self._redis_client.delete(*keys)
            return 0
        except RedisError as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._redis_client:
            return False
        
        try:
            return await self._redis_client.exists(key) > 0
        except RedisError as e:
            logger.warning(f"Cache exists error for key {key}: {e}")
            return False
    
    async def clear_all(self) -> bool:
        """Clear entire cache (use with caution!)"""
        if not self._redis_client:
            return False
        
        try:
            await self._redis_client.flushdb()
            logger.info("Cache cleared successfully")
            return True
        except RedisError as e:
            logger.error(f"Cache clear error: {e}")
            return False


# Global cache manager instance
cache_manager = CacheManager()


def cache_result(
    ttl: int = 300,  # 5 minutes default
    key_prefix: str = "",
    include_args: bool = True,
    include_kwargs: bool = True
):
    """
    Decorator for caching function results
    
    Args:
        ttl: Time to live in seconds (default 300 = 5 minutes)
        key_prefix: Prefix for cache key
        include_args: Include function args in cache key
        include_kwargs: Include function kwargs in cache key
    
    Example:
        @cache_result(ttl=3600, key_prefix="questions")
        async def get_questions_by_module(module_type, division):
            # ... database query ...
            return questions
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix or func.__name__]
            
            if include_args and args:
                # Skip 'self' or 'cls' argument for methods
                start_idx = 1 if args and hasattr(args[0], '__class__') else 0
                key_parts.extend(str(arg) for arg in args[start_idx:])
            
            if include_kwargs and kwargs:
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # Cache miss - execute function
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache_manager.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(key_pattern: str):
    """
    Decorator for invalidating cache when function is called
    
    Args:
        key_pattern: Pattern of cache keys to invalidate
    
    Example:
        @invalidate_cache("questions:*")
        async def update_question(question_id, new_data):
            # ... update database ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute function first
            result = await func(*args, **kwargs)
            
            # Then invalidate cache
            deleted = await cache_manager.delete_pattern(key_pattern)
            logger.info(f"Invalidated {deleted} cache keys matching {key_pattern}")
            
            return result
        
        return wrapper
    return decorator


# Cache key constants for consistency
class CacheKeys:
    """Standard cache key prefixes"""
    QUESTIONS = "questions"
    QUESTIONS_BY_MODULE = "questions:module"
    QUESTIONS_BY_DIVISION = "questions:division"
    ASSESSMENT = "assessment"
    USER = "user"
    CONFIG = "config"
    STATISTICS = "statistics"


# TTL constants (in seconds)
class CacheTTL:
    """Standard TTL values"""
    SHORT = 60  # 1 minute
    MEDIUM = 300  # 5 minutes
    LONG = 1800  # 30 minutes
    HOUR = 3600  # 1 hour
    DAY = 86400  # 24 hours

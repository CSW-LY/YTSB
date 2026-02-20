"""Cache management for intent recognition results."""

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class CacheManager:
    """Manager for Redis cache operations."""

    def __init__(self):
        self._pool: Optional[Redis] = None

    async def connect(self) -> None:
        """Establish Redis connection pool."""
        if self._pool is None:
            self._pool = redis.from_url(
                settings.redis_url,
                max_connections=settings.redis_pool_size,
                decode_responses=True,
            )
            try:
                await self._pool.ping()
                logger.info("Connected to Redis successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Cache will be disabled.")
                self._pool = None

    async def disconnect(self) -> None:
        """Close Redis connections."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    def _get_key(self, key: str) -> str:
        """Get prefixed cache key."""
        return f"{settings.cache_prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not settings.enable_cache or not self._pool:
            return None

        try:
            value = await self._pool.get(self._get_key(key))
            if value:
                return json.loads(value)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")

        return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        if not settings.enable_cache or not self._pool:
            return False

        ttl = ttl or settings.cache_ttl
        try:
            await self._pool.set(
                self._get_key(key),
                json.dumps(value),
                ex=ttl,
            )
            return True
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not settings.enable_cache or not self._pool:
            return False

        try:
            await self._pool.delete(self._get_key(key))
            return True
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        if not settings.enable_cache or not self._pool:
            return 0

        try:
            keys = await self._pool.keys(f"{settings.cache_prefix}{pattern}")
            if keys:
                return await self._pool.delete(*keys)
        except Exception as e:
            logger.warning(f"Cache invalidate error: {e}")

        return 0


# Global cache manager instance
cache_manager = CacheManager()


async def get_cache() -> CacheManager:
    """Get cache manager instance."""
    if not cache_manager._pool:
        await cache_manager.connect()
    return cache_manager


def generate_cache_key(app_key: str, text: str, context: Optional[dict] = None) -> str:
    """Generate cache key for intent recognition."""
    import hashlib

    # Create a hash of the text and context
    content = f"{app_key}:{text}"
    if context:
        content += f":{json.dumps(context, sort_keys=True)}"

    return hashlib.md5(content.encode()).hexdigest()

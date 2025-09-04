"""
Redis-based caching service for DevCycle.

This module provides a Redis-backed caching service that can be used throughout
the application for improved performance and distributed caching capabilities.
"""

import json
from typing import Any, Dict, Optional

import redis

from ..config import get_config
from ..logging import get_logger

logger = get_logger(__name__)


class RedisCache:
    """Redis-based caching service."""

    def __init__(self, key_prefix: str = "devcycle:cache:") -> None:
        """
        Initialize Redis cache service.

        Args:
            key_prefix: Prefix for all cache keys
        """
        config = get_config()
        self.redis_client = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            password=config.redis.password,
            db=config.redis.db,
            decode_responses=True,
            socket_timeout=config.redis.socket_timeout,
            socket_connect_timeout=config.redis.socket_connect_timeout,
            retry_on_timeout=config.redis.retry_on_timeout,
            max_connections=config.redis.max_connections,
        )
        self.key_prefix = key_prefix
        logger.info("Redis cache service initialized")

    def _get_key(self, key: str) -> str:
        """Get the full Redis key with prefix."""
        return f"{self.key_prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            full_key = self._get_key(key)
            value = self.redis_client.get(full_key)

            if value is None:
                return None

            # Try to deserialize JSON, fallback to string
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"Error getting cache value for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None for no expiration)

        Returns:
            True if successful, False otherwise
        """
        try:
            full_key = self._get_key(key)

            # Serialize value to JSON if it's not a string
            if isinstance(value, str):
                serialized_value = value
            else:
                serialized_value = json.dumps(value)

            redis_result: bool | None
            if ttl is not None:
                redis_result = self.redis_client.setex(full_key, ttl, serialized_value)
            else:
                redis_result = self.redis_client.set(full_key, serialized_value)

            return redis_result is not None and bool(redis_result)

        except Exception as e:
            logger.error(f"Error setting cache value for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        try:
            full_key = self._get_key(key)
            result = self.redis_client.delete(full_key)
            return bool(result)

        except Exception as e:
            logger.error(f"Error deleting cache value for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        try:
            full_key = self._get_key(key)
            return bool(self.redis_client.exists(full_key))

        except Exception as e:
            logger.error(f"Error checking cache existence for key {key}: {e}")
            return False

    def get_ttl(self, key: str) -> int:
        """
        Get the time to live for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        try:
            full_key = self._get_key(key)
            result = self.redis_client.ttl(full_key)
            return int(result) if result is not None else -2

        except Exception as e:
            logger.error(f"Error getting TTL for key {key}: {e}")
            return -2

    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.

        Args:
            pattern: Pattern to match (without prefix)

        Returns:
            Number of keys deleted
        """
        try:
            full_pattern = self._get_key(pattern)
            keys = self.redis_client.keys(full_pattern)

            if not keys:
                return 0

            result = self.redis_client.delete(*keys)
            return int(result) if result is not None else 0

        except Exception as e:
            logger.error(f"Error clearing cache pattern {pattern}: {e}")
            return 0

    def clear_all(self) -> int:
        """
        Clear all cache keys with the current prefix.

        Returns:
            Number of keys deleted
        """
        return int(self.clear_pattern("*"))

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            info = self.redis_client.info()
            keys = self.redis_client.keys(self._get_key("*"))

            return {
                "total_keys": len(keys),
                "redis_connected": True,
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "total_keys": 0,
                "redis_connected": False,
                "error": str(e),
            }

    def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if Redis is accessible, False otherwise
        """
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Global cache instance
_cache_instance: Optional[RedisCache] = None


def get_cache(key_prefix: str = "devcycle:cache:") -> RedisCache:
    """
    Get the global cache instance.

    Args:
        key_prefix: Prefix for cache keys

    Returns:
        RedisCache instance
    """
    global _cache_instance
    import os

    # In test environments, always create a new instance to use the current config
    # This ensures tests can use the correct Redis settings
    if os.getenv("ENVIRONMENT") == "testing":
        _cache_instance = RedisCache(key_prefix)
    else:
        # In non-test environments, use singleton behavior
        # Only create new instance if none exists, ignore key_prefix for singleton behavior
        if _cache_instance is None:
            _cache_instance = RedisCache(key_prefix)

    return _cache_instance

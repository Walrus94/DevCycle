"""
Redis client for DevCycle system.

This module provides Redis connection management, health checks,
and utility functions for Redis operations.
"""

import asyncio
from typing import Any, Optional, Set

from redis.asyncio import ConnectionPool, Redis  # type: ignore[import-not-found]
from redis.exceptions import RedisError  # type: ignore[import-not-found]

from .config import get_config
from .logging import get_logger


class RedisManager:
    """Redis connection manager with connection pooling and health checks."""

    def __init__(self) -> None:
        """Initialize Redis manager."""
        self.config = get_config().redis
        self.logger = get_logger("core.redis")

        # Connection pool
        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[Redis] = None

        # Health check state
        self._healthy = False
        self._last_health_check: float = 0.0
        self._health_check_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize Redis connection pool and client."""
        try:
            # Create connection pool
            self.pool = ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                db=self.config.db,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                decode_responses=True,
            )

            # Create Redis client
            self.client = Redis(connection_pool=self.pool)

            # Test connection
            await self.client.ping()
            self._healthy = True

            self.logger.info(
                f"Redis connection established to {self.config.host}:{self.config.port}"
            )

            # Start health check task
            self._start_health_check()

        except Exception as e:
            self.logger.error(f"Failed to initialize Redis connection: {e}")
            self._healthy = False
            raise

    async def close(self) -> None:
        """Close Redis connections and cleanup."""
        try:
            # Stop health check task
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass

            # Close client
            if self.client:
                await self.client.close()

            # Close pool
            if self.pool:
                await self.pool.disconnect()

            self._healthy = False
            self.logger.info("Redis connections closed")

        except Exception as e:
            self.logger.error(f"Error closing Redis connections: {e}")

    def _start_health_check(self) -> None:
        """Start background health check task."""
        if self._health_check_task and not self._health_check_task.done():
            return

        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._check_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check error: {e}")

    async def _check_health(self) -> None:
        """Check Redis connection health."""
        try:
            if self.client:
                await self.client.ping()
                self._healthy = True
                self._last_health_check = asyncio.get_event_loop().time()
        except Exception as e:
            self._healthy = False
            self.logger.warning(f"Redis health check failed: {e}")

    @property
    def is_healthy(self) -> bool:
        """Check if Redis connection is healthy."""
        return self._healthy

    async def get_client(self) -> Redis:
        """Get Redis client instance."""
        if not self.client or not self._healthy:
            raise RedisError("Redis connection not available")
        return self.client

    async def execute(self, command: str, *args: Any, **kwargs: Any) -> Any:
        """Execute Redis command with error handling."""
        try:
            client = await self.get_client()
            return await client.execute_command(command, *args, **kwargs)
        except RedisError as e:
            self.logger.error(f"Redis connection error: {e}")
            self._healthy = False
            raise
        except RedisError as e:
            self.logger.error(f"Redis command error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected Redis error: {e}")
            raise

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        try:
            client = await self.get_client()
            result = await client.get(key)
            return result if result is None else str(result)
        except Exception as e:
            self.logger.error(f"Redis GET error for key {key}: {e}")
            raise

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis with optional expiration."""
        try:
            client = await self.get_client()
            result = await client.set(key, value, ex=ex)
            return bool(result)
        except Exception as e:
            self.logger.error(f"Redis SET error for key {key}: {e}")
            raise

    async def setex(self, key: str, ex: int, value: str) -> bool:
        """Set value in Redis with expiration."""
        try:
            client = await self.get_client()
            result = await client.setex(key, ex, value)
            return bool(result)
        except Exception as e:
            self.logger.error(f"Redis SETEX error for key {key}: {e}")
            raise

    async def delete(self, key: str) -> int:
        """Delete key from Redis."""
        try:
            client = await self.get_client()
            result = await client.delete(key)
            return int(result)
        except Exception as e:
            self.logger.error(f"Redis DELETE error for key {key}: {e}")
            raise

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        try:
            client = await self.get_client()
            result = await client.exists(key)
            return bool(result)
        except Exception as e:
            self.logger.error(f"Redis EXISTS error for key {key}: {e}")
            raise

    async def expire(self, key: str, ex: int) -> bool:
        """Set expiration for key."""
        try:
            client = await self.get_client()
            result = await client.expire(key, ex)
            return bool(result)
        except Exception as e:
            self.logger.error(f"Redis EXPIRE error for key {key}: {e}")
            raise

    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        try:
            client = await self.get_client()
            result = client.ttl(key)
            if hasattr(result, "__await__"):
                result = await result
            # Ensure result is properly typed before conversion
            if result is None:
                return -1
            return int(str(result))
        except Exception as e:
            self.logger.error(f"Redis TTL error for key {key}: {e}")
            raise

    async def incr(self, key: str) -> int:
        """Increment value in Redis."""
        try:
            client = await self.get_client()
            result = client.incr(key)
            if hasattr(result, "__await__"):
                result = await result
            # Ensure result is properly typed before conversion
            if result is None:
                return 0
            return int(str(result))
        except Exception as e:
            self.logger.error(f"Redis INCR error for key {key}: {e}")
            raise

    async def sadd(self, key: str, *members: str) -> int:
        """Add members to set."""
        try:
            client = await self.get_client()
            result = client.sadd(key, *members)
            if hasattr(result, "__await__"):
                result = await result
            return int(result)
        except Exception as e:
            self.logger.error(f"Redis SADD error for key {key}: {e}")
            raise

    async def srem(self, key: str, *members: str) -> int:
        """Remove members from set."""
        try:
            client = await self.get_client()
            result = client.srem(key, *members)
            if hasattr(result, "__await__"):
                result = await result
            return int(result)
        except Exception as e:
            self.logger.error(f"Redis SREM error for key {key}: {e}")
            raise

    async def smembers(self, key: str) -> Set[str]:
        """Get all members of set."""
        try:
            client = await self.get_client()
            result = client.smembers(key)
            if hasattr(result, "__await__"):
                result = await result
            return set(str(member) for member in result) if result else set()
        except Exception as e:
            self.logger.error(f"Redis SMEMBERS error for key {key}: {e}")
            raise


# Global Redis manager instance
redis_manager = RedisManager()


async def get_redis() -> RedisManager:
    """Get Redis manager instance."""
    return redis_manager


async def initialize_redis() -> None:
    """Initialize Redis connection."""
    await redis_manager.initialize()


async def close_redis() -> None:
    """Close Redis connection."""
    await redis_manager.close()

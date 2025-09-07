"""
Redis connection pool optimization.

This module provides intelligent connection pool management and optimization
for Redis connections to improve performance and resource utilization.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from ...logging import get_logger

logger = get_logger(__name__)


class PoolOptimizationStrategy(Enum):
    """Connection pool optimization strategies."""

    STATIC = "static"
    DYNAMIC = "dynamic"
    ADAPTIVE = "adaptive"


@dataclass
class PoolMetrics:
    """Connection pool metrics."""

    total_connections: int
    active_connections: int
    idle_connections: int
    connection_utilization: float
    average_connection_lifetime: float
    connection_creation_rate: float
    connection_destruction_rate: float
    pool_hit_ratio: float
    average_wait_time_ms: float


@dataclass
class PoolConfiguration:
    """Connection pool configuration."""

    min_connections: int
    max_connections: int
    max_idle_connections: int
    connection_timeout: float
    socket_timeout: float
    socket_keepalive: bool
    socket_keepalive_options: Dict[str, Any]
    retry_on_timeout: bool
    health_check_interval: float


class ConnectionPoolOptimizer:
    """Intelligent Redis connection pool optimizer."""

    def __init__(
        self, redis_url: str, initial_config: Optional[PoolConfiguration] = None
    ):
        """
        Initialize connection pool optimizer.

        Args:
            redis_url: Redis connection URL
            initial_config: Initial pool configuration
        """
        self.redis_url = redis_url
        self.pool: Optional[ConnectionPool] = None
        self.redis_client: Optional[redis.Redis] = None

        # Default configuration
        self.config = initial_config or PoolConfiguration(
            min_connections=5,
            max_connections=20,
            max_idle_connections=10,
            connection_timeout=5.0,
            socket_timeout=5.0,
            socket_keepalive=True,
            socket_keepalive_options={},
            retry_on_timeout=True,
            health_check_interval=30.0,
        )

        # Optimization state
        self.optimization_strategy = PoolOptimizationStrategy.ADAPTIVE
        self.optimization_enabled = True
        self.last_optimization = datetime.now(timezone.utc)
        self.optimization_interval = timedelta(minutes=5)

        # Metrics tracking
        self.metrics_history: List[PoolMetrics] = []
        self.connection_events: List[Tuple[datetime, str, float]] = (
            []
        )  # (timestamp, event_type, duration)
        self.max_history_size = 1000

        # Background task
        self._optimization_task: Optional[asyncio.Task] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the connection pool optimizer."""
        if self._running:
            return

        self._running = True

        # Create initial pool
        await self._create_pool()

        # Start background tasks
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        if self.optimization_enabled:
            self._optimization_task = asyncio.create_task(self._optimization_loop())

        logger.info("Connection pool optimizer started")

    async def stop(self) -> None:
        """Stop the connection pool optimizer."""
        if not self._running:
            return

        self._running = False

        # Stop background tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass

        # Close pool
        if self.pool:
            await self.pool.disconnect()

        logger.info("Connection pool optimizer stopped")

    async def _create_pool(self) -> None:
        """Create Redis connection pool."""
        self.pool = ConnectionPool.from_url(
            self.redis_url,
            max_connections=self.config.max_connections,
            retry_on_timeout=self.config.retry_on_timeout,
            socket_timeout=self.config.socket_timeout,
            socket_keepalive=self.config.socket_keepalive,
            socket_keepalive_options=self.config.socket_keepalive_options,
            health_check_interval=self.config.health_check_interval,
        )

        self.redis_client = redis.Redis(connection_pool=self.pool)

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                await self._collect_pool_metrics()
                await asyncio.sleep(30)  # Collect metrics every 30 seconds
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)

    async def _optimization_loop(self) -> None:
        """Background optimization loop."""
        while self._running:
            try:
                await asyncio.sleep(self.optimization_interval.total_seconds())
                if self.optimization_enabled:
                    await self._run_optimization_cycle()
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(60)

    async def _collect_pool_metrics(self) -> None:
        """Collect connection pool metrics."""
        if not self.pool:
            return

        try:
            # Get pool statistics
            total_connections = self.pool.connection_kwargs.get("max_connections", 0)
            # Use public API to get connection counts
            active_connections = (
                getattr(self.pool, "_in_use_connections", set()).__len__()
                if hasattr(self.pool, "_in_use_connections")
                else 0
            )
            idle_connections = (
                getattr(self.pool, "_available_connections", set()).__len__()
                if hasattr(self.pool, "_available_connections")
                else 0
            )

            # Calculate utilization
            utilization = (
                active_connections / total_connections if total_connections > 0 else 0
            )

            # Calculate average connection lifetime
            now = datetime.now(timezone.utc)
            lifetimes = []
            for event_time, event_type, duration in self.connection_events:
                if event_type == "connection_created":
                    # Find corresponding destruction event
                    for destroy_time, destroy_type, _ in self.connection_events:
                        if (
                            destroy_type == "connection_destroyed"
                            and destroy_time > event_time
                        ):
                            lifetime = (destroy_time - event_time).total_seconds()
                            lifetimes.append(lifetime)
                            break

            avg_lifetime = sum(lifetimes) / len(lifetimes) if lifetimes else 0

            # Calculate rates
            recent_events = [
                event
                for event in self.connection_events
                if now - event[0] < timedelta(minutes=5)
            ]

            creation_events = [e for e in recent_events if e[1] == "connection_created"]
            destruction_events = [
                e for e in recent_events if e[1] == "connection_destroyed"
            ]

            creation_rate = len(creation_events) / 5  # per minute
            destruction_rate = len(destruction_events) / 5  # per minute

            # Calculate pool hit ratio (simplified)
            pool_hit_ratio = 1.0 - (len(creation_events) / max(1, active_connections))

            # Calculate average wait time
            wait_times = [e[2] for e in recent_events if e[1] == "connection_wait"]
            avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0

            metrics = PoolMetrics(
                total_connections=total_connections,
                active_connections=active_connections,
                idle_connections=idle_connections,
                connection_utilization=utilization,
                average_connection_lifetime=avg_lifetime,
                connection_creation_rate=creation_rate,
                connection_destruction_rate=destruction_rate,
                pool_hit_ratio=pool_hit_ratio,
                average_wait_time_ms=avg_wait_time * 1000,
            )

            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history.pop(0)

        except Exception as e:
            logger.error(f"Error collecting pool metrics: {e}")

    async def _run_optimization_cycle(self) -> None:
        """Run a complete optimization cycle."""
        if not self.metrics_history:
            return

        logger.info("Starting connection pool optimization cycle")

        # Analyze recent metrics
        recent_metrics = self.metrics_history[-10:]  # Last 10 measurements
        avg_utilization = sum(m.connection_utilization for m in recent_metrics) / len(
            recent_metrics
        )
        avg_wait_time = sum(m.average_wait_time_ms for m in recent_metrics) / len(
            recent_metrics
        )
        avg_pool_hit_ratio = sum(m.pool_hit_ratio for m in recent_metrics) / len(
            recent_metrics
        )

        # Generate optimization recommendations
        recommendations = self._generate_optimization_recommendations(
            avg_utilization, avg_wait_time, avg_pool_hit_ratio
        )

        # Apply recommendations
        await self._apply_optimization_recommendations(recommendations)

        self.last_optimization = datetime.now(timezone.utc)
        logger.info(
            f"Connection pool optimization cycle completed. "
            f"Applied {len(recommendations)} recommendations"
        )

    def _generate_optimization_recommendations(
        self, utilization: float, wait_time: float, hit_ratio: float
    ) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on metrics."""
        recommendations = []

        # High utilization - increase pool size
        if utilization > 0.8:
            new_max_connections = min(self.config.max_connections * 1.5, 100)
            recommendations.append(
                {
                    "type": "increase_pool_size",
                    "current_value": self.config.max_connections,
                    "recommended_value": int(new_max_connections),
                    "reason": f"High utilization ({utilization:.2%})",
                }
            )

        # Low utilization - decrease pool size
        elif utilization < 0.3 and self.config.max_connections > 10:
            new_max_connections = max(self.config.max_connections * 0.8, 10)
            recommendations.append(
                {
                    "type": "decrease_pool_size",
                    "current_value": self.config.max_connections,
                    "recommended_value": int(new_max_connections),
                    "reason": f"Low utilization ({utilization:.2%})",
                }
            )

        # High wait time - increase pool size or adjust timeouts
        if wait_time > 100:  # 100ms
            if utilization < 0.7:
                new_max_connections = min(self.config.max_connections * 1.2, 100)
                recommendations.append(
                    {
                        "type": "increase_pool_size",
                        "current_value": self.config.max_connections,
                        "recommended_value": int(new_max_connections),
                        "reason": (
                            f"High wait time ({wait_time:.1f}ms) with low utilization"
                        ),
                    }
                )
            else:
                recommendations.append(
                    {
                        "type": "decrease_timeout",
                        "current_value": self.config.connection_timeout,
                        "recommended_value": self.config.connection_timeout * 0.8,
                        "reason": (
                            f"High wait time ({wait_time:.1f}ms) with high utilization"
                        ),
                    }
                )

        # Low pool hit ratio - adjust idle connections
        if hit_ratio < 0.7:
            new_max_idle = max(self.config.max_idle_connections * 1.2, 5)
            recommendations.append(
                {
                    "type": "increase_idle_connections",
                    "current_value": self.config.max_idle_connections,
                    "recommended_value": int(new_max_idle),
                    "reason": f"Low pool hit ratio ({hit_ratio:.2%})",
                }
            )

        return recommendations

    async def _apply_optimization_recommendations(
        self, recommendations: List[Dict[str, Any]]
    ) -> None:
        """Apply optimization recommendations."""
        for rec in recommendations:
            try:
                if rec["type"] == "increase_pool_size":
                    await self._update_pool_size(rec["recommended_value"])
                elif rec["type"] == "decrease_pool_size":
                    await self._update_pool_size(rec["recommended_value"])
                elif rec["type"] == "increase_idle_connections":
                    await self._update_idle_connections(rec["recommended_value"])
                elif rec["type"] == "decrease_timeout":
                    await self._update_connection_timeout(rec["recommended_value"])

                logger.info(
                    f"Applied optimization: {rec['type']} = "
                    f"{rec['recommended_value']} ({rec['reason']})"
                )

            except Exception as e:
                logger.error(f"Failed to apply optimization {rec['type']}: {e}")

    async def _update_pool_size(self, new_max_connections: int) -> None:
        """Update pool size by recreating the pool."""
        if new_max_connections == self.config.max_connections:
            return

        old_pool = self.pool
        self.config.max_connections = new_max_connections

        # Create new pool
        await self._create_pool()

        # Close old pool
        if old_pool:
            await old_pool.disconnect()

    async def _update_idle_connections(self, new_max_idle: int) -> None:
        """Update maximum idle connections."""
        self.config.max_idle_connections = new_max_idle
        # Note: This would require pool recreation in a real implementation

    async def _update_connection_timeout(self, new_timeout: float) -> None:
        """Update connection timeout."""
        self.config.connection_timeout = new_timeout
        # Note: This would require pool recreation in a real implementation

    def record_connection_event(self, event_type: str, duration: float = 0.0) -> None:
        """Record a connection event for metrics."""
        self.connection_events.append(
            (datetime.now(timezone.utc), event_type, duration)
        )

        # Keep only recent events
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        self.connection_events = [
            event for event in self.connection_events if event[0] > cutoff
        ]

    def get_pool_metrics(self) -> Optional[PoolMetrics]:
        """Get current pool metrics."""
        if not self.metrics_history:
            return None
        return self.metrics_history[-1]

    def get_metrics_history(self, hours: int = 1) -> List[PoolMetrics]:
        """Get metrics history for the specified time period."""
        return [
            metrics
            for metrics in self.metrics_history
            if metrics.total_connections > 0  # Filter out empty metrics
        ]

    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get current optimization recommendations."""
        if not self.metrics_history:
            return []

        recent_metrics = self.metrics_history[-5:]
        avg_utilization = sum(m.connection_utilization for m in recent_metrics) / len(
            recent_metrics
        )
        avg_wait_time = sum(m.average_wait_time_ms for m in recent_metrics) / len(
            recent_metrics
        )
        avg_pool_hit_ratio = sum(m.pool_hit_ratio for m in recent_metrics) / len(
            recent_metrics
        )

        return self._generate_optimization_recommendations(
            avg_utilization, avg_wait_time, avg_pool_hit_ratio
        )

    def get_pool_configuration(self) -> Dict[str, Any]:
        """Get current pool configuration."""
        return {
            "min_connections": self.config.min_connections,
            "max_connections": self.config.max_connections,
            "max_idle_connections": self.config.max_idle_connections,
            "connection_timeout": self.config.connection_timeout,
            "socket_timeout": self.config.socket_timeout,
            "socket_keepalive": self.config.socket_keepalive,
            "socket_keepalive_options": self.config.socket_keepalive_options,
            "retry_on_timeout": self.config.retry_on_timeout,
            "health_check_interval": self.config.health_check_interval,
            "optimization_strategy": self.optimization_strategy.value,
            "optimization_enabled": self.optimization_enabled,
        }

    def set_optimization_strategy(self, strategy: PoolOptimizationStrategy) -> None:
        """Set optimization strategy."""
        self.optimization_strategy = strategy
        logger.info(f"Optimization strategy set to {strategy.value}")

    def enable_optimization(self) -> None:
        """Enable pool optimization."""
        self.optimization_enabled = True
        if not self._optimization_task and self._running:
            self._optimization_task = asyncio.create_task(self._optimization_loop())
        logger.info("Pool optimization enabled")

    def disable_optimization(self) -> None:
        """Disable pool optimization."""
        self.optimization_enabled = False
        if self._optimization_task:
            self._optimization_task.cancel()
            self._optimization_task = None
        logger.info("Pool optimization disabled")

    def set_optimization_interval(self, minutes: int) -> None:
        """Set optimization interval in minutes."""
        self.optimization_interval = timedelta(minutes=minutes)
        logger.info(f"Optimization interval set to {minutes} minutes")

    async def get_redis_client(self) -> redis.Redis:
        """Get the optimized Redis client."""
        if not self.redis_client:
            await self._create_pool()
        if self.redis_client is None:
            raise RuntimeError("Failed to create Redis client")
        return self.redis_client

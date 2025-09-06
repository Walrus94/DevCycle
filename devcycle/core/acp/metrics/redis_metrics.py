"""
Redis performance metrics collection.

This module provides detailed metrics collection for Redis operations
including cache hit ratios, operation latencies, memory usage, and more.
"""

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ...cache.redis_cache import RedisCache
from ...logging import get_logger

logger = get_logger(__name__)


@dataclass
class RedisOperationMetrics:
    """Metrics for a single Redis operation."""

    operation: str
    key: str
    duration_ms: float
    success: bool
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    memory_usage: Optional[int] = None


@dataclass
class RedisPerformanceSnapshot:
    """Snapshot of Redis performance metrics."""

    timestamp: datetime
    total_operations: int
    successful_operations: int
    failed_operations: int
    average_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    cache_hit_ratio: float
    memory_usage_bytes: int
    memory_usage_percentage: float
    connected_clients: int
    operations_per_second: float
    key_count: int
    expired_keys: int
    evicted_keys: int


class RedisMetricsCollector:
    """Collects and analyzes Redis performance metrics."""

    def __init__(self, redis_cache: RedisCache, window_size: int = 1000):
        """
        Initialize Redis metrics collector.

        Args:
            redis_cache: Redis cache instance to monitor
            window_size: Number of operations to keep in sliding window
        """
        self.redis = redis_cache.redis_client
        self.window_size = window_size
        self.operation_history: deque = deque(maxlen=window_size)
        self.operation_counts: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.latency_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # Performance tracking
        self.start_time = datetime.now(timezone.utc)
        self.last_snapshot_time = self.start_time

        # Initialize Redis info
        self.redis_info = {
            "memory_usage": 0,
            "memory_peak": 0,
            "connected_clients": 0,
            "total_commands_processed": 0,
            "keyspace_hits": 0,
            "keyspace_misses": 0,
            "expired_keys": 0,
            "evicted_keys": 0,
            "keyspace": {},
            "uptime_seconds": 0,
        }

        # Background task
        self._collection_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the metrics collection background task."""
        if self._running:
            return

        self._running = True
        self._collection_task = asyncio.create_task(self._collect_metrics_loop())
        logger.info("Redis metrics collector started")

    async def stop(self) -> None:
        """Stop the metrics collection background task."""
        if not self._running:
            return

        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Redis metrics collector stopped")

    async def _collect_metrics_loop(self) -> None:
        """Background task to collect Redis metrics."""
        while self._running:
            try:
                await self._collect_redis_info()
                await asyncio.sleep(10)  # Collect every 10 seconds
            except Exception as e:
                logger.error(f"Error collecting Redis metrics: {e}")
                await asyncio.sleep(5)

    async def _collect_redis_info(self) -> None:
        """Collect Redis server information."""
        try:
            info = self.redis.info()

            # Store key metrics
            self.redis_info = {
                "memory_usage": info.get("used_memory", 0),
                "memory_peak": info.get("used_memory_peak", 0),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "expired_keys": info.get("expired_keys", 0),
                "evicted_keys": info.get("evicted_keys", 0),
                "keyspace": info.get("keyspace", {}),
                "uptime_seconds": info.get("uptime_in_seconds", 0),
            }
        except Exception as e:
            logger.error(f"Error collecting Redis info: {e}")

    def record_operation(
        self,
        operation: str,
        key: str,
        duration_ms: float,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Record a Redis operation for metrics collection."""
        metrics = RedisOperationMetrics(
            operation=operation,
            key=key,
            duration_ms=duration_ms,
            success=success,
            error=error,
        )

        # Add to history
        self.operation_history.append(metrics)

        # Update counters
        self.operation_counts[operation] += 1
        if not success and error:
            self.error_counts[error] += 1

        # Update latency history
        self.latency_history[operation].append(duration_ms)

    def get_performance_snapshot(self) -> RedisPerformanceSnapshot:
        """Get current performance snapshot."""
        now = datetime.now(timezone.utc)

        # Calculate basic metrics
        total_ops = len(self.operation_history)
        successful_ops = sum(1 for op in self.operation_history if op.success)
        failed_ops = total_ops - successful_ops

        # Calculate latencies
        all_latencies = [op.duration_ms for op in self.operation_history]
        avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0

        # Calculate percentiles
        sorted_latencies = sorted(all_latencies)
        p95_latency = self._calculate_percentile(sorted_latencies, 95)
        p99_latency = self._calculate_percentile(sorted_latencies, 99)

        # Calculate cache hit ratio
        hits = int(str(self.redis_info.get("keyspace_hits", 0)))
        misses = int(str(self.redis_info.get("keyspace_misses", 0)))
        total_requests = hits + misses
        cache_hit_ratio = (hits / total_requests) if total_requests > 0 else 0

        # Calculate operations per second
        time_diff = (now - self.last_snapshot_time).total_seconds()
        ops_per_second = total_ops / time_diff if time_diff > 0 else 0

        # Calculate key count
        keyspace = self.redis_info.get("keyspace", {})
        if isinstance(keyspace, dict):
            key_count = sum(
                int(db_info.get("keys", 0)) for db_info in keyspace.values()
            )
        else:
            key_count = 0

        # Memory usage
        memory_usage = int(str(self.redis_info.get("memory_usage", 0)))
        memory_peak = int(str(self.redis_info.get("memory_peak", 0)))
        memory_percentage = (memory_usage / memory_peak * 100) if memory_peak > 0 else 0

        snapshot = RedisPerformanceSnapshot(
            timestamp=now,
            total_operations=total_ops,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            average_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            cache_hit_ratio=cache_hit_ratio,
            memory_usage_bytes=memory_usage,
            memory_usage_percentage=memory_percentage,
            connected_clients=int(str(self.redis_info.get("connected_clients", 0))),
            operations_per_second=ops_per_second,
            key_count=key_count,
            expired_keys=int(str(self.redis_info.get("expired_keys", 0))),
            evicted_keys=int(str(self.redis_info.get("evicted_keys", 0))),
        )

        self.last_snapshot_time = now
        return snapshot

    def _calculate_percentile(
        self, sorted_values: List[float], percentile: int
    ) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]

    def get_operation_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get breakdown of operations by type."""
        breakdown = {}

        for operation in self.operation_counts:
            operation_metrics = [
                op for op in self.operation_history if op.operation == operation
            ]

            if operation_metrics:
                latencies = [op.duration_ms for op in operation_metrics]
                successful = sum(1 for op in operation_metrics if op.success)

                breakdown[operation] = {
                    "count": len(operation_metrics),
                    "successful": successful,
                    "failed": len(operation_metrics) - successful,
                    "success_rate": successful / len(operation_metrics),
                    "avg_latency_ms": sum(latencies) / len(latencies),
                    "min_latency_ms": min(latencies),
                    "max_latency_ms": max(latencies),
                    "p95_latency_ms": self._calculate_percentile(sorted(latencies), 95),
                    "p99_latency_ms": self._calculate_percentile(sorted(latencies), 99),
                }

        return breakdown

    def get_error_breakdown(self) -> Dict[str, int]:
        """Get breakdown of errors by type."""
        return dict(self.error_counts)

    def get_top_slow_operations(self, limit: int = 10) -> List[RedisOperationMetrics]:
        """Get top slowest operations."""
        return sorted(
            self.operation_history, key=lambda x: x.duration_ms, reverse=True
        )[:limit]

    def get_recent_errors(self, limit: int = 10) -> List[RedisOperationMetrics]:
        """Get recent failed operations."""
        errors = [op for op in self.operation_history if not op.success]
        return sorted(errors, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_memory_usage_trend(self, hours: int = 24) -> List[Tuple[datetime, int]]:
        """Get memory usage trend over time."""
        # This would require storing historical data
        # For now, return current usage
        return [
            (
                datetime.now(timezone.utc),
                int(str(self.redis_info.get("memory_usage", 0))),
            )
        ]

    def get_operations_per_second_trend(
        self, minutes: int = 60
    ) -> List[Tuple[datetime, float]]:
        """Get operations per second trend over time."""
        # This would require storing historical data
        # For now, return current rate
        snapshot = self.get_performance_snapshot()
        return [(datetime.now(timezone.utc), snapshot.operations_per_second)]

    def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        self.operation_history.clear()
        self.operation_counts.clear()
        self.error_counts.clear()
        for latency_deque in self.latency_history.values():
            latency_deque.clear()
        self.start_time = datetime.now(timezone.utc)
        self.last_snapshot_time = self.start_time
        logger.info("Redis metrics reset")

    def get_health_score(self) -> float:
        """Calculate overall Redis health score (0-100)."""
        snapshot = self.get_performance_snapshot()

        # Factors affecting health score
        success_rate = (
            (snapshot.successful_operations / snapshot.total_operations)
            if snapshot.total_operations > 0
            else 1.0
        )
        cache_hit_ratio = snapshot.cache_hit_ratio
        memory_usage_ratio = 1.0 - (snapshot.memory_usage_percentage / 100)
        latency_score = max(
            0, 1.0 - (snapshot.p95_latency_ms / 1000)
        )  # Penalize > 1s latency

        # Weighted average
        health_score = (
            success_rate * 0.3
            + cache_hit_ratio * 0.25
            + memory_usage_ratio * 0.25
            + latency_score * 0.2
        ) * 100

        return min(100, max(0, health_score))

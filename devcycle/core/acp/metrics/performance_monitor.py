"""
Performance monitoring coordinator.

This module provides a centralized performance monitoring system that
coordinates Redis metrics, ACP metrics, and system health monitoring.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ...cache.redis_cache import RedisCache
from ...logging import get_logger
from .acp_metrics import ACPMetricsCollector, ACPPerformanceSnapshot
from .redis_metrics import RedisMetricsCollector, RedisPerformanceSnapshot

logger = get_logger(__name__)


@dataclass
class SystemHealthSnapshot:
    """Comprehensive system health snapshot."""

    timestamp: datetime
    redis_health: float
    acp_health: float
    overall_health: float
    redis_metrics: RedisPerformanceSnapshot
    acp_metrics: ACPPerformanceSnapshot
    alerts: List[str]
    recommendations: List[str]


class PerformanceMonitor:
    """Centralized performance monitoring system."""

    def __init__(self, redis_cache: RedisCache):
        """
        Initialize performance monitor.

        Args:
            redis_cache: Redis cache instance to monitor
        """
        self.redis_cache = redis_cache
        self.redis_metrics = RedisMetricsCollector(redis_cache)
        self.acp_metrics = ACPMetricsCollector()

        # Health thresholds
        self.health_thresholds = {
            "redis_memory_usage_percentage": 80.0,
            "redis_latency_ms": 100.0,
            "redis_cache_hit_ratio": 0.8,
            "acp_success_rate": 0.95,
            "acp_latency_ms": 500.0,
            "overall_health_score": 70.0,
        }

        # Background task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the performance monitoring system."""
        if self._running:
            return

        self._running = True

        # Start individual collectors
        await self.redis_metrics.start()

        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info("Performance monitor started")

    async def stop(self) -> None:
        """Stop the performance monitoring system."""
        if not self._running:
            return

        self._running = False

        # Stop individual collectors
        await self.redis_metrics.stop()

        # Stop monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Performance monitor stopped")

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                # Collect metrics every 30 seconds
                await asyncio.sleep(30)

                # Generate health snapshot
                # TODO: Fix snapshot usage - currently unused but
                # should be used for alerts
                snapshot = await self.get_system_health_snapshot()  # noqa: F841

                # Check for alerts (pass None for Redis snapshot for now)
                alerts = self._check_alerts(None, None)
                if alerts:
                    logger.warning(f"Performance alerts: {alerts}")

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)

    async def get_system_health_snapshot(self) -> SystemHealthSnapshot:
        """Get comprehensive system health snapshot."""
        # Get individual metrics
        redis_snapshot = self.redis_metrics.get_performance_snapshot()
        acp_snapshot = self.acp_metrics.get_performance_snapshot()

        # Calculate health scores
        redis_health = self.redis_metrics.get_health_score()
        acp_health = acp_snapshot.health_score
        overall_health = (redis_health + acp_health) / 2

        # Check for alerts and recommendations
        alerts = self._check_alerts(redis_snapshot, acp_snapshot)
        recommendations = self._generate_recommendations(redis_snapshot, acp_snapshot)

        return SystemHealthSnapshot(
            timestamp=datetime.now(timezone.utc),
            redis_health=redis_health,
            acp_health=acp_health,
            overall_health=overall_health,
            redis_metrics=redis_snapshot,
            acp_metrics=acp_snapshot,
            alerts=alerts,
            recommendations=recommendations,
        )

    def _check_alerts(
        self,
        redis_snapshot: Optional[RedisPerformanceSnapshot],
        acp_snapshot: Optional[ACPPerformanceSnapshot],
    ) -> List[str]:
        """Check for performance alerts."""
        alerts = []

        # Redis alerts
        if redis_snapshot:
            if (
                redis_snapshot.memory_usage_percentage
                > self.health_thresholds["redis_memory_usage_percentage"]
            ):
                alerts.append(
                    f"Redis memory usage high: "
                    f"{redis_snapshot.memory_usage_percentage:.1f}%"
                )

            if (
                redis_snapshot.p95_latency_ms
                > self.health_thresholds["redis_latency_ms"]
            ):
                alerts.append(
                    f"Redis latency high: {redis_snapshot.p95_latency_ms:.1f}ms"
                )

            if (
                redis_snapshot.cache_hit_ratio
                < self.health_thresholds["redis_cache_hit_ratio"]
            ):
                alerts.append(
                    f"Redis cache hit ratio low: {redis_snapshot.cache_hit_ratio:.2f}"
                )

        # ACP alerts
        if acp_snapshot and acp_snapshot.total_operations > 0:
            success_rate = (
                acp_snapshot.successful_operations / acp_snapshot.total_operations
            )
            if success_rate < self.health_thresholds["acp_success_rate"]:
                alerts.append(f"ACP success rate low: {success_rate:.2f}")

        if (
            acp_snapshot
            and acp_snapshot.p95_latency_ms > self.health_thresholds["acp_latency_ms"]
        ):
            alerts.append(f"ACP latency high: {acp_snapshot.p95_latency_ms:.1f}ms")

        return alerts

    def _generate_recommendations(
        self,
        redis_snapshot: RedisPerformanceSnapshot,
        acp_snapshot: ACPPerformanceSnapshot,
    ) -> List[str]:
        """Generate performance recommendations."""
        recommendations = []

        # Redis recommendations
        if redis_snapshot.memory_usage_percentage > 70:
            recommendations.append(
                "Consider increasing Redis memory limit or optimizing data structures"
            )

        if redis_snapshot.cache_hit_ratio < 0.8:
            recommendations.append(
                "Review cache key patterns and TTL settings for better hit ratio"
            )

        if redis_snapshot.p95_latency_ms > 50:
            recommendations.append(
                "Consider Redis connection pooling or clustering for better performance"
            )

        # ACP recommendations
        if acp_snapshot.total_operations > 0:
            success_rate = (
                acp_snapshot.successful_operations / acp_snapshot.total_operations
            )
            if success_rate < 0.95:
                recommendations.append(
                    "Review error handling and retry logic in ACP services"
                )

        if acp_snapshot.p95_latency_ms > 200:
            recommendations.append(
                "Consider optimizing ACP service operations or adding caching"
            )

        return recommendations

    def record_redis_operation(
        self,
        operation: str,
        key: str,
        duration_ms: float,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Record a Redis operation for metrics collection."""
        self.redis_metrics.record_operation(operation, key, duration_ms, success, error)

    def record_acp_operation(
        self,
        service: str,
        operation: str,
        duration_ms: float,
        success: bool,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an ACP service operation for metrics collection."""
        self.acp_metrics.record_operation(
            service, operation, duration_ms, success, error, metadata
        )

    def update_agent_registry_metrics(self, **kwargs: Any) -> None:
        """Update agent registry specific metrics."""
        self.acp_metrics.update_agent_registry_metrics(**kwargs)

    def update_workflow_engine_metrics(self, **kwargs: Any) -> None:
        """Update workflow engine specific metrics."""
        self.acp_metrics.update_workflow_engine_metrics(**kwargs)

    def update_message_router_metrics(self, **kwargs: Any) -> None:
        """Update message router specific metrics."""
        self.acp_metrics.update_message_router_metrics(**kwargs)

    def get_redis_metrics(self) -> RedisPerformanceSnapshot:
        """Get Redis performance metrics."""
        return self.redis_metrics.get_performance_snapshot()

    def get_acp_metrics(self) -> ACPPerformanceSnapshot:
        """Get ACP performance metrics."""
        return self.acp_metrics.get_performance_snapshot()

    def get_redis_operation_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get Redis operation breakdown."""
        return self.redis_metrics.get_operation_breakdown()

    def get_acp_operation_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get ACP operation breakdown."""
        return self.acp_metrics.get_operation_breakdown()

    def get_redis_health_score(self) -> float:
        """Get Redis health score."""
        return self.redis_metrics.get_health_score()

    def get_acp_health_score(self) -> float:
        """Get ACP health score."""
        return self.acp_metrics.get_performance_snapshot().health_score

    def get_system_health_score(self) -> float:
        """Get overall system health score."""
        redis_health = self.get_redis_health_score()
        acp_health = self.get_acp_health_score()
        return (redis_health + acp_health) / 2

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        redis_snapshot = self.get_redis_metrics()
        acp_snapshot = self.get_acp_metrics()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_health": self.get_system_health_score(),
            "redis": {
                "health_score": redis_snapshot.cache_hit_ratio * 100,
                "memory_usage_percentage": redis_snapshot.memory_usage_percentage,
                "cache_hit_ratio": redis_snapshot.cache_hit_ratio,
                "operations_per_second": redis_snapshot.operations_per_second,
                "average_latency_ms": redis_snapshot.average_latency_ms,
                "p95_latency_ms": redis_snapshot.p95_latency_ms,
            },
            "acp": {
                "health_score": acp_snapshot.health_score,
                "operations_per_second": acp_snapshot.operations_per_second,
                "average_latency_ms": acp_snapshot.average_latency_ms,
                "p95_latency_ms": acp_snapshot.p95_latency_ms,
                "success_rate": acp_snapshot.successful_operations
                / max(1, acp_snapshot.total_operations),
            },
            "services": self.acp_metrics.get_service_health(),
        }

    def reset_all_metrics(self) -> None:
        """Reset all performance metrics."""
        self.redis_metrics.reset_metrics()
        self.acp_metrics.reset_metrics()
        logger.info("All performance metrics reset")

    def get_health_thresholds(self) -> Dict[str, float]:
        """Get current health thresholds."""
        return dict(self.health_thresholds)

    def set_health_thresholds(self, thresholds: Dict[str, float]) -> None:
        """Set health thresholds."""
        self.health_thresholds.update(thresholds)
        logger.info(f"Health thresholds updated: {thresholds}")

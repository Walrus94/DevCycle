"""
Advanced cache optimization strategies.

This module provides intelligent cache optimization including TTL optimization,
cache warming, and adaptive caching strategies.
"""

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ...cache.acp_cache import ACPCache
from ...logging import get_logger

logger = get_logger(__name__)


@dataclass
class CacheAccessPattern:
    """Represents a cache access pattern for analysis."""

    key: str
    access_count: int
    last_access: datetime
    first_access: datetime
    avg_ttl: float
    hit_ratio: float
    access_frequency: float  # accesses per hour


@dataclass
class CacheOptimizationRecommendation:
    """Cache optimization recommendation."""

    key_pattern: str
    recommendation_type: str  # 'ttl_adjustment', 'preload', 'eviction', 'compression'
    current_value: Any
    recommended_value: Any
    expected_improvement: float
    priority: int  # 1-5, 5 being highest


class CacheOptimizer:
    """Advanced cache optimization service."""

    def __init__(self, acp_cache: ACPCache, analysis_window_hours: int = 24):
        """
        Initialize cache optimizer.

        Args:
            acp_cache: ACP cache instance to optimize
            analysis_window_hours: Hours of data to analyze for patterns
        """
        self.acp_cache = acp_cache
        self.analysis_window_hours = analysis_window_hours

        # Access pattern tracking
        self.access_patterns: Dict[str, CacheAccessPattern] = {}
        self.key_access_times: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self.key_ttl_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # Optimization state
        self.optimization_enabled = True
        self.last_optimization = datetime.now(timezone.utc)
        self.optimization_interval = timedelta(hours=1)

        # Background task
        self._optimization_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the cache optimization system."""
        if self._running:
            return

        self._running = True
        self._optimization_task = asyncio.create_task(self._optimization_loop())
        logger.info("Cache optimizer started")

    async def stop(self) -> None:
        """Stop the cache optimization system."""
        if not self._running:
            return

        self._running = False
        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
        logger.info("Cache optimizer stopped")

    async def _optimization_loop(self) -> None:
        """Background optimization loop."""
        while self._running:
            try:
                await asyncio.sleep(self.optimization_interval.total_seconds())

                if self.optimization_enabled:
                    await self._run_optimization_cycle()

            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _run_optimization_cycle(self) -> None:
        """Run a complete optimization cycle."""
        logger.info("Starting cache optimization cycle")

        # Analyze access patterns
        await self._analyze_access_patterns()

        # Generate recommendations
        recommendations = await self._generate_recommendations()

        # Apply high-priority recommendations
        await self._apply_recommendations(recommendations)

        # Update optimization timestamp
        self.last_optimization = datetime.now(timezone.utc)

        applied_count = len([r for r in recommendations if r.priority >= 4])
        logger.info(
            f"Cache optimization cycle completed. "
            f"Applied {applied_count} recommendations"
        )

    async def record_access(self, key: str, ttl: Optional[float] = None) -> None:
        """Record a cache access for pattern analysis."""
        now = datetime.now(timezone.utc)
        self.key_access_times[key].append(now)

        if ttl is not None:
            self.key_ttl_history[key].append(ttl)

        # Update access pattern
        if key in self.access_patterns:
            pattern = self.access_patterns[key]
            pattern.access_count += 1
            pattern.last_access = now
        else:
            self.access_patterns[key] = CacheAccessPattern(
                key=key,
                access_count=1,
                last_access=now,
                first_access=now,
                avg_ttl=ttl or 0,
                hit_ratio=1.0,
                access_frequency=0.0,
            )

    async def _analyze_access_patterns(self) -> None:
        """Analyze cache access patterns to identify optimization opportunities."""
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=self.analysis_window_hours)

        for key, pattern in self.access_patterns.items():
            # Calculate access frequency
            recent_accesses = [
                access_time
                for access_time in self.key_access_times[key]
                if access_time >= cutoff_time
            ]

            hours_analyzed = self.analysis_window_hours
            pattern.access_frequency = len(recent_accesses) / hours_analyzed

            # Calculate average TTL
            if self.key_ttl_history[key]:
                pattern.avg_ttl = sum(self.key_ttl_history[key]) / len(
                    self.key_ttl_history[key]
                )

            # Calculate hit ratio (simplified - would need cache hit/miss tracking)
            # For now, assume high frequency = high hit ratio
            pattern.hit_ratio = min(1.0, pattern.access_frequency / 10.0)

    async def _generate_recommendations(self) -> List[CacheOptimizationRecommendation]:
        """Generate cache optimization recommendations."""
        recommendations = []

        for key, pattern in self.access_patterns.items():
            # TTL optimization recommendations
            if (
                pattern.access_frequency > 5.0 and pattern.avg_ttl < 300
            ):  # High frequency, short TTL
                recommendations.append(
                    CacheOptimizationRecommendation(
                        key_pattern=key,
                        recommendation_type="ttl_adjustment",
                        current_value=pattern.avg_ttl,
                        recommended_value=min(
                            3600, pattern.avg_ttl * 2
                        ),  # Double TTL, max 1 hour
                        expected_improvement=0.15,  # 15% improvement
                        priority=4,
                    )
                )

            elif (
                pattern.access_frequency < 0.1 and pattern.avg_ttl > 1800
            ):  # Low frequency, long TTL
                recommendations.append(
                    CacheOptimizationRecommendation(
                        key_pattern=key,
                        recommendation_type="ttl_adjustment",
                        current_value=pattern.avg_ttl,
                        recommended_value=max(
                            300, pattern.avg_ttl / 2
                        ),  # Halve TTL, min 5 minutes
                        expected_improvement=0.10,  # 10% improvement
                        priority=3,
                    )
                )

            # Preload recommendations for frequently accessed keys
            if pattern.access_frequency > 10.0 and pattern.hit_ratio > 0.8:
                recommendations.append(
                    CacheOptimizationRecommendation(
                        key_pattern=key,
                        recommendation_type="preload",
                        current_value=False,
                        recommended_value=True,
                        expected_improvement=0.20,  # 20% improvement
                        priority=5,
                    )
                )

        return recommendations

    async def _apply_recommendations(
        self, recommendations: List[CacheOptimizationRecommendation]
    ) -> None:
        """Apply optimization recommendations."""
        for rec in recommendations:
            if rec.priority >= 4:  # Apply high-priority recommendations
                try:
                    if rec.recommendation_type == "ttl_adjustment":
                        await self._adjust_key_ttl(
                            rec.key_pattern, rec.recommended_value
                        )
                    elif rec.recommendation_type == "preload":
                        await self._preload_key(rec.key_pattern)

                except Exception as e:
                    logger.error(
                        f"Failed to apply recommendation for {rec.key_pattern}: {e}"
                    )

    async def _adjust_key_ttl(self, key: str, new_ttl: float) -> None:
        """Adjust TTL for a specific key."""
        try:
            # Get current value
            current_value = self.acp_cache.redis.get(key)
            if current_value:
                # Set with new TTL
                self.acp_cache.redis.set(key, current_value, ttl=int(new_ttl))
                logger.info(f"Adjusted TTL for {key} to {new_ttl}s")
        except Exception as e:
            logger.error(f"Failed to adjust TTL for {key}: {e}")

    async def _preload_key(self, key: str) -> None:
        """Preload a key (implementation depends on data source)."""
        # This would typically involve loading data from the original source
        # For now, just log the recommendation
        logger.info(f"Preload recommendation for {key}")

    async def warm_cache(self, key_patterns: List[str]) -> None:
        """Warm the cache with frequently accessed data."""
        logger.info(f"Starting cache warming for {len(key_patterns)} patterns")

        for pattern in key_patterns:
            try:
                # This would typically involve loading data from the original source
                # For now, just log the warming attempt
                logger.info(f"Cache warming for pattern: {pattern}")
            except Exception as e:
                logger.error(f"Failed to warm cache for pattern {pattern}: {e}")

    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats: Dict[str, Any] = {
            "total_keys_tracked": len(self.access_patterns),
            "optimization_enabled": self.optimization_enabled,
            "last_optimization": self.last_optimization.isoformat(),
            "access_patterns": {},
        }

        # Add pattern statistics
        for key, pattern in self.access_patterns.items():
            stats["access_patterns"][key] = {
                "access_count": pattern.access_count,
                "access_frequency": pattern.access_frequency,
                "avg_ttl": pattern.avg_ttl,
                "hit_ratio": pattern.hit_ratio,
                "last_access": pattern.last_access.isoformat(),
            }

        return stats

    async def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get current optimization recommendations."""
        recommendations = await self._generate_recommendations()

        return [
            {
                "key_pattern": rec.key_pattern,
                "type": rec.recommendation_type,
                "current_value": rec.current_value,
                "recommended_value": rec.recommended_value,
                "expected_improvement": rec.expected_improvement,
                "priority": rec.priority,
            }
            for rec in recommendations
        ]

    def enable_optimization(self) -> None:
        """Enable cache optimization."""
        self.optimization_enabled = True
        logger.info("Cache optimization enabled")

    def disable_optimization(self) -> None:
        """Disable cache optimization."""
        self.optimization_enabled = False
        logger.info("Cache optimization disabled")

    def set_optimization_interval(self, hours: int) -> None:
        """Set optimization interval in hours."""
        self.optimization_interval = timedelta(hours=hours)
        logger.info(f"Optimization interval set to {hours} hours")

    async def reset_statistics(self) -> None:
        """Reset all optimization statistics."""
        self.access_patterns.clear()
        for key_times in self.key_access_times.values():
            key_times.clear()
        for key_ttl in self.key_ttl_history.values():
            key_ttl.clear()
        logger.info("Cache optimization statistics reset")

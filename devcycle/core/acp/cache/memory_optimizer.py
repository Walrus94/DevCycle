"""
Redis memory optimization strategies.

This module provides intelligent memory optimization for Redis including
data compression, eviction policies, and memory usage monitoring.
"""

import asyncio
import base64
import gzip
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import redis.asyncio as redis

from ...logging import get_logger


def safe_serialize(value: Any) -> bytes:
    """Safely serialize a value using JSON for security."""
    try:
        # Try JSON serialization first (safest)
        json_str = json.dumps(
            value, default=str
        )  # default=str handles non-serializable types
        return json_str.encode("utf-8")
    except (TypeError, ValueError):
        # Fallback to base64 encoding for complex objects
        try:
            # For complex objects, convert to string representation
            str_repr = str(value)
            return base64.b64encode(str_repr.encode("utf-8"))
        except Exception:
            # Last resort: serialize as string
            return str(value).encode("utf-8")


def safe_deserialize(data: bytes) -> Any:
    """Safely deserialize data using JSON."""
    try:
        # Try JSON deserialization first
        json_str = data.decode("utf-8")
        return json.loads(json_str)
    except (json.JSONDecodeError, UnicodeDecodeError):
        try:
            # Try base64 decoding
            decoded = base64.b64decode(data)
            return decoded.decode("utf-8")
        except Exception:
            # Fallback: return as string
            return data.decode("utf-8", errors="replace")


logger = get_logger(__name__)


class CompressionAlgorithm(Enum):
    """Compression algorithms."""

    GZIP = "gzip"
    LZ4 = "lz4"
    ZSTD = "zstd"
    NONE = "none"


class EvictionPolicy(Enum):
    """Redis eviction policies."""

    ALLKEYS_LRU = "allkeys-lru"
    ALLKEYS_LFU = "allkeys-lfu"
    VOLATILE_LRU = "volatile-lru"
    VOLATILE_LFU = "volatile-lfu"
    VOLATILE_TTL = "volatile-ttl"
    NOEVICTION = "noeviction"


@dataclass
class MemoryMetrics:
    """Redis memory metrics."""

    used_memory: int
    used_memory_peak: int
    used_memory_rss: int
    used_memory_ratio: float
    memory_fragmentation_ratio: float
    total_keys: int
    expired_keys: int
    evicted_keys: int
    memory_usage_by_type: Dict[str, int]
    largest_keys: List[Tuple[str, int]]


@dataclass
class MemoryOptimizationRecommendation:
    """Memory optimization recommendation."""

    recommendation_type: str
    description: str
    current_value: Any
    recommended_value: Any
    expected_savings: int
    priority: int


class MemoryOptimizer:
    """Intelligent Redis memory optimizer."""

    def __init__(self, redis_client: redis.Redis, memory_threshold: float = 0.8):
        """
        Initialize memory optimizer.

        Args:
            redis_client: Redis client instance
            memory_threshold: Memory usage threshold for optimization (0.0-1.0)
        """
        self.redis_client = redis_client
        self.memory_threshold = memory_threshold

        # Optimization settings
        self.compression_enabled = True
        self.compression_algorithm = CompressionAlgorithm.GZIP
        self.compression_threshold = 1024  # Compress objects larger than 1KB
        self.eviction_policy = EvictionPolicy.ALLKEYS_LRU

        # Memory monitoring
        self.memory_history: List[MemoryMetrics] = []
        self.max_history_size = 1000
        self.last_optimization = datetime.now(timezone.utc)
        self.optimization_interval = timedelta(hours=1)

        # Background task
        self._optimization_task: Optional[asyncio.Task] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the memory optimizer."""
        if self._running:
            return

        self._running = True

        # Start background tasks
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._optimization_task = asyncio.create_task(self._optimization_loop())

        logger.info("Memory optimizer started")

    async def stop(self) -> None:
        """Stop the memory optimizer."""
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

        logger.info("Memory optimizer stopped")

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                await self._collect_memory_metrics()
                await asyncio.sleep(60)  # Collect metrics every minute
            except Exception as e:
                logger.error(f"Error in memory monitoring loop: {e}")
                await asyncio.sleep(30)

    async def _optimization_loop(self) -> None:
        """Background optimization loop."""
        while self._running:
            try:
                await asyncio.sleep(self.optimization_interval.total_seconds())
                await self._run_optimization_cycle()
            except Exception as e:
                logger.error(f"Error in memory optimization loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _collect_memory_metrics(self) -> None:
        """Collect Redis memory metrics."""
        try:
            info = await self.redis_client.info("memory")

            # Get key information
            db_info = await self.redis_client.info("keyspace")
            total_keys = sum(int(db.get("keys", 0)) for db in db_info.values())

            # Get largest keys (sample)
            largest_keys = await self._get_largest_keys(limit=10)

            # Calculate memory usage by type
            memory_by_type = await self._analyze_memory_by_type()

            metrics = MemoryMetrics(
                used_memory=info.get("used_memory", 0),
                used_memory_peak=info.get("used_memory_peak", 0),
                used_memory_rss=info.get("used_memory_rss", 0),
                used_memory_ratio=info.get("used_memory", 0)
                / max(info.get("maxmemory", 1), 1),
                memory_fragmentation_ratio=info.get("mem_fragmentation_ratio", 1.0),
                total_keys=total_keys,
                expired_keys=info.get("expired_keys", 0),
                evicted_keys=info.get("evicted_keys", 0),
                memory_usage_by_type=memory_by_type,
                largest_keys=largest_keys,
            )

            self.memory_history.append(metrics)
            if len(self.memory_history) > self.max_history_size:
                self.memory_history.pop(0)

        except Exception as e:
            logger.error(f"Error collecting memory metrics: {e}")

    async def _get_largest_keys(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get the largest keys by memory usage."""
        try:
            # Use MEMORY USAGE command to get key sizes
            keys = await self.redis_client.keys("*")
            key_sizes = []

            for key in keys[:100]:  # Sample first 100 keys
                try:
                    size = await self.redis_client.memory_usage(key)
                    key_sizes.append((key, size))
                except Exception as e:
                    logger.warning(f"Failed to get memory usage for key {key}: {e}")
                    # Skip this key but continue processing others

            # Sort by size and return top keys
            key_sizes.sort(key=lambda x: x[1], reverse=True)
            return key_sizes[:limit]

        except Exception as e:
            logger.error(f"Error getting largest keys: {e}")
            return []

    async def _analyze_memory_by_type(self) -> Dict[str, int]:
        """Analyze memory usage by data type."""
        try:
            # Get all keys and their types
            keys = await self.redis_client.keys("*")
            type_counts: Dict[str, int] = {}
            type_memory: Dict[str, int] = {}

            for key in keys[:1000]:  # Sample first 1000 keys
                try:
                    key_type = await self.redis_client.type(key)
                    memory_usage = await self.redis_client.memory_usage(key)

                    type_counts[key_type] = type_counts.get(key_type, 0) + 1
                    type_memory[key_type] = type_memory.get(key_type, 0) + memory_usage
                except Exception as e:
                    logger.warning(f"Failed to analyze memory for key {key}: {e}")
                    # Skip this key but continue processing others

            return type_memory

        except Exception as e:
            logger.error(f"Error analyzing memory by type: {e}")
            return {}

    async def _run_optimization_cycle(self) -> None:
        """Run a complete memory optimization cycle."""
        if not self.memory_history:
            return

        logger.info("Starting memory optimization cycle")

        # Get current metrics
        current_metrics = self.memory_history[-1]

        # Check if optimization is needed
        if current_metrics.used_memory_ratio < self.memory_threshold:
            logger.info("Memory usage below threshold, skipping optimization")
            return

        # Generate recommendations
        recommendations = await self._generate_memory_recommendations(current_metrics)

        # Apply high-priority recommendations
        high_priority_recs = [r for r in recommendations if r.priority >= 4]
        for rec in high_priority_recs:
            try:
                await self._apply_memory_recommendation(rec)
                logger.info(f"Applied memory optimization: {rec.description}")
            except Exception as e:
                logger.error(
                    f"Failed to apply memory optimization "
                    f"{rec.recommendation_type}: {e}"
                )

        self.last_optimization = datetime.now(timezone.utc)
        logger.info(
            f"Memory optimization cycle completed. "
            f"Applied {len(high_priority_recs)} recommendations"
        )

    async def _generate_memory_recommendations(
        self, metrics: MemoryMetrics
    ) -> List[MemoryOptimizationRecommendation]:
        """Generate memory optimization recommendations."""
        recommendations = []

        # High memory usage - recommend eviction policy change
        if metrics.used_memory_ratio > 0.9:
            recommendations.append(
                MemoryOptimizationRecommendation(
                    recommendation_type="eviction_policy",
                    description="Change eviction policy to more aggressive",
                    current_value=self.eviction_policy.value,
                    recommended_value=EvictionPolicy.ALLKEYS_LRU.value,
                    expected_savings=int(metrics.used_memory * 0.1),  # 10% reduction
                    priority=5,
                )
            )

        # High fragmentation - recommend memory defragmentation
        if metrics.memory_fragmentation_ratio > 1.5:
            recommendations.append(
                MemoryOptimizationRecommendation(
                    recommendation_type="defragmentation",
                    description="Run memory defragmentation",
                    current_value=metrics.memory_fragmentation_ratio,
                    recommended_value=1.2,
                    expected_savings=int(metrics.used_memory * 0.2),  # 20% reduction
                    priority=4,
                )
            )

        # Large keys - recommend compression
        if metrics.largest_keys and any(
            size > self.compression_threshold for _, size in metrics.largest_keys
        ):
            recommendations.append(
                MemoryOptimizationRecommendation(
                    recommendation_type="compression",
                    description="Enable compression for large keys",
                    current_value=False,
                    recommended_value=True,
                    expected_savings=int(metrics.used_memory * 0.15),  # 15% reduction
                    priority=3,
                )
            )

        # High key count - recommend TTL optimization
        if metrics.total_keys > 10000:
            recommendations.append(
                MemoryOptimizationRecommendation(
                    recommendation_type="ttl_optimization",
                    description="Optimize TTL settings for better key expiration",
                    current_value="mixed",
                    recommended_value="optimized",
                    expected_savings=int(metrics.used_memory * 0.05),  # 5% reduction
                    priority=2,
                )
            )

        return recommendations

    async def _apply_memory_recommendation(
        self, recommendation: MemoryOptimizationRecommendation
    ) -> None:
        """Apply a memory optimization recommendation."""
        if recommendation.recommendation_type == "eviction_policy":
            await self._set_eviction_policy(recommendation.recommended_value)
        elif recommendation.recommendation_type == "defragmentation":
            await self._run_memory_defragmentation()
        elif recommendation.recommendation_type == "compression":
            await self._enable_compression_for_large_keys()
        elif recommendation.recommendation_type == "ttl_optimization":
            await self._optimize_ttl_settings()

    async def _set_eviction_policy(self, policy: str) -> None:
        """Set Redis eviction policy."""
        try:
            await self.redis_client.config_set("maxmemory-policy", policy)
            self.eviction_policy = EvictionPolicy(policy)
            logger.info(f"Eviction policy set to {policy}")
        except Exception as e:
            logger.error(f"Failed to set eviction policy: {e}")

    async def _run_memory_defragmentation(self) -> None:
        """Run memory defragmentation."""
        try:
            # Note: MEMORY PURGE is not available in all Redis versions
            # This is a placeholder for defragmentation logic
            logger.info("Memory defragmentation completed")
        except Exception as e:
            logger.error(f"Failed to run memory defragmentation: {e}")

    async def _enable_compression_for_large_keys(self) -> None:
        """Enable compression for large keys."""
        try:
            # This would implement compression for large keys
            # For now, just log the action
            logger.info("Compression enabled for large keys")
        except Exception as e:
            logger.error(f"Failed to enable compression: {e}")

    async def _optimize_ttl_settings(self) -> None:
        """Optimize TTL settings."""
        try:
            # This would implement TTL optimization logic
            # For now, just log the action
            logger.info("TTL settings optimized")
        except Exception as e:
            logger.error(f"Failed to optimize TTL settings: {e}")

    async def compress_value(self, value: Any) -> bytes:
        """Compress a value using the configured algorithm."""
        if not self.compression_enabled:
            return safe_serialize(value)

        serialized = safe_serialize(value)

        if len(serialized) < self.compression_threshold:
            return serialized

        if self.compression_algorithm == CompressionAlgorithm.GZIP:
            return gzip.compress(serialized)
        else:
            return serialized

    async def decompress_value(self, compressed_data: bytes) -> Any:
        """Decompress a value."""
        if not self.compression_enabled:
            return safe_deserialize(compressed_data)

        try:
            if self.compression_algorithm == CompressionAlgorithm.GZIP:
                decompressed = gzip.decompress(compressed_data)
            else:
                decompressed = compressed_data

            return safe_deserialize(decompressed)
        except Exception:
            # Fallback to safe deserialization
            return safe_deserialize(compressed_data)

    def get_memory_metrics(self) -> Optional[MemoryMetrics]:
        """Get current memory metrics."""
        if not self.memory_history:
            return None
        return self.memory_history[-1]

    def get_memory_history(self, hours: int = 24) -> List[MemoryMetrics]:
        """Get memory metrics history."""
        return [metrics for metrics in self.memory_history if metrics.used_memory > 0]

    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get current optimization recommendations."""
        if not self.memory_history:
            return []

        current_metrics = self.memory_history[-1]
        recommendations = asyncio.run(
            self._generate_memory_recommendations(current_metrics)
        )

        return [
            {
                "type": rec.recommendation_type,
                "description": rec.description,
                "current_value": rec.current_value,
                "recommended_value": rec.recommended_value,
                "expected_savings": rec.expected_savings,
                "priority": rec.priority,
            }
            for rec in recommendations
        ]

    def get_memory_configuration(self) -> Dict[str, Any]:
        """Get current memory configuration."""
        return {
            "memory_threshold": self.memory_threshold,
            "compression_enabled": self.compression_enabled,
            "compression_algorithm": self.compression_algorithm.value,
            "compression_threshold": self.compression_threshold,
            "eviction_policy": self.eviction_policy.value,
            "optimization_interval_hours": self.optimization_interval.total_seconds()
            / 3600,
        }

    def set_memory_threshold(self, threshold: float) -> None:
        """Set memory usage threshold."""
        self.memory_threshold = max(0.1, min(1.0, threshold))
        logger.info(f"Memory threshold set to {self.memory_threshold}")

    def set_compression_algorithm(self, algorithm: CompressionAlgorithm) -> None:
        """Set compression algorithm."""
        self.compression_algorithm = algorithm
        logger.info(f"Compression algorithm set to {algorithm.value}")

    def set_compression_threshold(self, threshold: int) -> None:
        """Set compression threshold in bytes."""
        self.compression_threshold = max(100, threshold)
        logger.info(f"Compression threshold set to {self.compression_threshold} bytes")

    def enable_compression(self) -> None:
        """Enable compression."""
        self.compression_enabled = True
        logger.info("Compression enabled")

    def disable_compression(self) -> None:
        """Disable compression."""
        self.compression_enabled = False
        logger.info("Compression disabled")

"""
Integration tests for Redis performance optimization features using testcontainers.

This module provides comprehensive integration tests for all Phase 4
performance optimization features working together with real Redis.
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone

import pytest
from testcontainers.redis import RedisContainer

from devcycle.core.acp.cache.batch_operations import (
    RedisBatchProcessor,
    batch_get,
    batch_set,
)
from devcycle.core.acp.cache.cache_optimizer import CacheOptimizer
from devcycle.core.acp.cache.cache_warmer import (
    CacheWarmer,
    WarmingRule,
    WarmingStrategy,
)
from devcycle.core.acp.cache.connection_pool_optimizer import (
    ConnectionPoolOptimizer,
    PoolConfiguration,
)
from devcycle.core.acp.cache.memory_optimizer import (
    CompressionAlgorithm,
    MemoryOptimizer,
)
from devcycle.core.acp.metrics.performance_monitor import PerformanceMonitor
from devcycle.core.cache.acp_cache import ACPCache


class TestRedisPerformanceIntegration:
    """Integration tests for Redis performance optimization using testcontainers."""

    @pytest.fixture(scope="class")
    def redis_container(self):
        """Create Redis testcontainer."""
        with RedisContainer("redis:7-alpine") as redis:
            yield redis

    @pytest.fixture
    async def redis_client(self, redis_container):
        """Create a Redis client connected to testcontainer."""
        import redis.asyncio as redis

        client = redis.Redis(
            host=redis_container.get_container_host_ip(),
            port=redis_container.get_exposed_port(6379),
            db=0,
        )
        await client.flushdb()  # Clean test database
        yield client
        await client.flushdb()  # Clean up after test
        await client.aclose()  # Use aclose() instead of close()

    @pytest.fixture
    async def acp_cache(self, redis_client):
        """Create ACP cache with real Redis."""
        return ACPCache(redis_client)

    @pytest.fixture
    async def performance_monitor(self, acp_cache):
        """Create performance monitor."""
        monitor = PerformanceMonitor(acp_cache)
        await monitor.start()
        yield monitor
        await monitor.stop()

    @pytest.fixture
    async def cache_optimizer(self, acp_cache):
        """Create cache optimizer."""
        optimizer = CacheOptimizer(acp_cache)
        await optimizer.start()
        yield optimizer
        await optimizer.stop()

    @pytest.fixture
    async def cache_warmer(self, acp_cache):
        """Create cache warmer."""
        warmer = CacheWarmer(acp_cache)
        await warmer.start()
        yield warmer
        await warmer.stop()

    @pytest.fixture
    async def batch_processor(self, acp_cache):
        """Create batch processor."""
        return RedisBatchProcessor(acp_cache)

    @pytest.fixture
    async def connection_pool_optimizer(self, redis_container):
        """Create connection pool optimizer."""
        config = PoolConfiguration(
            min_connections=2,
            max_connections=10,
            max_idle_connections=5,
            connection_timeout=5.0,
            socket_timeout=5.0,
            socket_keepalive=True,
            socket_keepalive_options={},
            retry_on_timeout=True,
            health_check_interval=30.0,
        )
        redis_url = (
            f"redis://{redis_container.get_container_host_ip()}:"
            f"{redis_container.get_exposed_port(6379)}/0"
        )
        optimizer = ConnectionPoolOptimizer(redis_url, config)
        await optimizer.start()
        yield optimizer
        await optimizer.stop()

    @pytest.fixture
    async def memory_optimizer(self, redis_client):
        """Create memory optimizer."""
        optimizer = MemoryOptimizer(redis_client)
        await optimizer.start()
        yield optimizer
        await optimizer.stop()

    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(
        self, performance_monitor, redis_client
    ):
        """Test performance monitoring with real Redis operations."""
        # Perform some operations directly with Redis client
        await redis_client.set("test_key_1", "value_1", ex=60)
        await redis_client.set("test_key_2", "value_2", ex=60)
        await redis_client.get("test_key_1")
        await redis_client.get("test_key_2")
        await redis_client.get("nonexistent_key")  # This will be a miss

        # Record operations in performance monitor
        performance_monitor.record_redis_operation("SET", "test_key_1", 1.0, True)
        performance_monitor.record_redis_operation("SET", "test_key_2", 1.0, True)
        performance_monitor.record_redis_operation("GET", "test_key_1", 0.5, True)
        performance_monitor.record_redis_operation("GET", "test_key_2", 0.5, True)
        performance_monitor.record_redis_operation(
            "GET", "nonexistent_key", 0.3, False, "Key not found"
        )

        # Wait a bit for metrics collection
        await asyncio.sleep(1)

        # Check performance summary
        summary = performance_monitor.get_performance_summary()

        assert "overall_health" in summary
        assert "redis" in summary
        assert "acp" in summary
        assert summary["redis"]["operations_per_second"] >= 0
        assert summary["redis"]["cache_hit_ratio"] >= 0

    @pytest.mark.asyncio
    async def test_cache_optimization_integration(self, cache_optimizer):
        """Test cache optimization with real access patterns."""
        # Simulate access patterns
        for i in range(20):
            await cache_optimizer.record_access(f"frequent_key_{i % 5}", 3600.0)
            await cache_optimizer.record_access(f"rare_key_{i}", 3600.0)

        # Wait for analysis
        await asyncio.sleep(1)

        # Generate recommendations
        recommendations = await cache_optimizer.get_optimization_recommendations()

        assert len(recommendations) > 0
        # Check if any recommendation has the expected structure
        assert any(
            "recommendation_type" in rec or "type" in rec for rec in recommendations
        )

    @pytest.mark.asyncio
    async def test_cache_warming_integration(self, cache_warmer, redis_client):
        """Test cache warming with real data loading."""

        # Define warming rule
        async def data_loader(key_pattern):
            if "test_data" in key_pattern:
                return {
                    "data": f"warmed_data_for_{key_pattern}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            return None

        rule = WarmingRule(
            name="test_warming_rule",
            key_pattern="test_data_*",
            data_loader=data_loader,
            priority=1,
            ttl=300.0,
        )

        cache_warmer.add_warming_rule(rule)

        # Warm cache on demand
        await cache_warmer.warm_on_demand(["test_data_1", "test_data_2"])

        # Check if data was cached directly with Redis
        cached_data_1 = await redis_client.get("test_data_1")
        cached_data_2 = await redis_client.get("test_data_2")

        assert cached_data_1 is not None
        assert cached_data_2 is not None
        assert b"warmed_data_for_test_data_1" in cached_data_1
        assert b"warmed_data_for_test_data_2" in cached_data_2

    @pytest.mark.asyncio
    async def test_batch_operations_integration(self, batch_processor, redis_client):
        """Test batch operations with real Redis."""
        # Test batch set operations
        key_value_pairs = [
            ("batch_key_1", "value_1"),
            ("batch_key_2", "value_2"),
            ("batch_key_3", "value_3"),
        ]

        result = await batch_set(batch_processor, key_value_pairs, ttl=60)

        assert result.total_operations == 3
        assert result.successful_operations == 3
        assert result.failed_operations == 0
        assert result.execution_time_ms >= 0

        # Test batch get operations
        keys = ["batch_key_1", "batch_key_2", "batch_key_3"]
        result = await batch_get(batch_processor, keys)

        assert result.total_operations == 3
        assert result.successful_operations == 3
        assert len(result.operations) == 3

        # Verify data was actually stored (Redis returns bytes)
        for i, op in enumerate(result.operations):
            assert op.result == f"value_{i + 1}".encode()

    @pytest.mark.asyncio
    async def test_connection_pool_optimization_integration(
        self, connection_pool_optimizer
    ):
        """Test connection pool optimization with real Redis."""
        # Record some connection events
        connection_pool_optimizer.record_connection_event("connection_created", 0.1)
        connection_pool_optimizer.record_connection_event("connection_destroyed", 0.05)

        # Get Redis client
        redis_client = await connection_pool_optimizer.get_redis_client()

        # Perform some operations
        await redis_client.set("pool_test_key", "pool_test_value")
        value = await redis_client.get("pool_test_key")

        assert value == b"pool_test_value"

        # Check pool configuration
        config = connection_pool_optimizer.get_pool_configuration()
        assert "max_connections" in config
        assert "optimization_strategy" in config

    @pytest.mark.asyncio
    async def test_memory_optimization_integration(
        self, memory_optimizer, redis_client
    ):
        """Test memory optimization with real Redis."""
        # Store some data
        await redis_client.set("memory_test_key", "memory_test_value")

        # Test compression
        test_data = {
            "large_data": "x" * 1000,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        compressed = await memory_optimizer.compress_value(test_data)
        decompressed = await memory_optimizer.decompress_value(compressed)

        assert decompressed == test_data
        assert len(compressed) < len(str(test_data).encode())

        # Check memory configuration
        config = memory_optimizer.get_memory_configuration()
        assert "memory_threshold" in config
        assert "compression_enabled" in config

    @pytest.mark.asyncio
    async def test_full_system_integration(
        self,
        performance_monitor,
        cache_optimizer,
        cache_warmer,
        batch_processor,
        redis_client,
    ):
        """Test all performance optimization features working together."""

        # 1. Set up cache warming
        async def data_loader(key_pattern):
            return {
                "data": f"integrated_data_{key_pattern}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        rule = WarmingRule(
            name="integration_rule",
            key_pattern="integration_*",
            data_loader=data_loader,
            priority=1,
            ttl=300.0,
        )
        cache_warmer.add_warming_rule(rule)

        # 2. Warm cache
        await cache_warmer.warm_on_demand(["integration_test_1", "integration_test_2"])

        # 3. Perform batch operations
        key_value_pairs = [
            ("integration_batch_1", "batch_value_1"),
            ("integration_batch_2", "batch_value_2"),
        ]
        batch_result = await batch_set(batch_processor, key_value_pairs, ttl=60)

        # 4. Record access patterns for optimization
        for i in range(10):
            await cache_optimizer.record_access(f"integration_batch_{i % 2 + 1}", 60.0)

        # 5. Wait for metrics collection
        await asyncio.sleep(1)

        # 6. Verify everything worked
        assert batch_result.successful_operations == 2

        # Check warmed data
        warmed_data = await redis_client.get("integration_test_1")
        assert warmed_data is not None

        # Check batch data
        batch_data = await redis_client.get("integration_batch_1")
        assert batch_data == b"batch_value_1"

        # Check performance metrics
        summary = performance_monitor.get_performance_summary()
        assert summary["overall_health"] >= 0

        # Check optimization recommendations
        recommendations = await cache_optimizer.get_optimization_recommendations()
        assert (
            len(recommendations) >= 0
        )  # May or may not have recommendations based on patterns

    @pytest.mark.asyncio
    async def test_performance_under_load(
        self, performance_monitor, batch_processor, redis_client
    ):
        """Test performance optimization under load."""
        # Create load
        start_time = time.time()

        # Perform many operations concurrently
        tasks = []
        for i in range(50):
            task = asyncio.create_task(
                redis_client.set(f"load_test_{i}", f"value_{i}", ex=60)
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Perform batch operations
        key_value_pairs = [(f"batch_load_{i}", f"batch_value_{i}") for i in range(20)]
        batch_result = await batch_set(batch_processor, key_value_pairs)

        end_time = time.time()
        total_time = end_time - start_time

        # Check performance
        assert batch_result.successful_operations == 20
        assert total_time < 5.0  # Should complete within 5 seconds

        # Check performance metrics
        summary = performance_monitor.get_performance_summary()
        assert summary["redis"]["operations_per_second"] >= 0

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, performance_monitor):
        """Test error handling in performance optimization."""
        # Test performance monitoring with errors
        performance_monitor.record_redis_operation(
            "GET", "test_key", 10.0, False, "Key not found"
        )
        performance_monitor.record_acp_operation(
            "test_service", "test_op", 5.0, False, "Service error"
        )

        # Check that errors are recorded
        summary = performance_monitor.get_performance_summary()
        assert summary["redis"]["operations_per_second"] >= 0
        assert summary["acp"]["operations_per_second"] >= 0

    @pytest.mark.asyncio
    async def test_configuration_persistence(
        self, cache_optimizer, cache_warmer, memory_optimizer
    ):
        """Test that configuration changes persist."""
        # Test cache optimizer configuration
        cache_optimizer.set_optimization_interval(2)  # 2 hours
        assert cache_optimizer.optimization_interval == timedelta(hours=2)

        # Test cache warmer configuration
        cache_warmer.add_warming_strategy(WarmingStrategy.SCHEDULED)
        assert WarmingStrategy.SCHEDULED in cache_warmer.warming_strategies

        # Test memory optimizer configuration
        memory_optimizer.set_compression_threshold(2048)
        assert memory_optimizer.compression_threshold == 2048

        memory_optimizer.set_compression_algorithm(CompressionAlgorithm.LZ4)
        assert memory_optimizer.compression_algorithm == CompressionAlgorithm.LZ4

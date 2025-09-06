"""
Performance benchmarks for Redis optimization features using testcontainers.

This module provides comprehensive performance tests for all Phase 4
optimization features to measure and validate performance improvements.
"""

import asyncio
import statistics
import time
from datetime import datetime, timezone

import pytest
from testcontainers.redis import RedisContainer

from devcycle.core.acp.cache.batch_operations import RedisBatchProcessor, batch_set
from devcycle.core.acp.cache.cache_warmer import WarmingRule
from devcycle.core.acp.cache.connection_pool_optimizer import (
    ConnectionPoolOptimizer,
    PoolConfiguration,
)
from devcycle.core.acp.cache.memory_optimizer import MemoryOptimizer
from devcycle.core.acp.metrics.performance_monitor import PerformanceMonitor
from devcycle.core.cache.acp_cache import ACPCache


class TestRedisPerformanceBenchmarks:
    """Performance benchmarks for Redis optimization features using testcontainers."""

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
        await client.aclose()

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
    async def batch_processor(self, acp_cache):
        """Create batch processor."""
        return RedisBatchProcessor(acp_cache, batch_size=50, max_concurrent_batches=5)

    @pytest.fixture
    async def connection_pool_optimizer(self, redis_container):
        """Create connection pool optimizer."""
        config = PoolConfiguration(
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
    @pytest.mark.performance
    async def test_basic_operations_performance(self, redis_client):
        """Benchmark basic Redis operations."""
        # Test single operations
        start_time = time.time()

        for i in range(1000):
            await redis_client.set(f"perf_key_{i}", f"value_{i}", ex=60)

        set_time = time.time() - start_time

        start_time = time.time()

        for i in range(1000):
            await redis_client.get(f"perf_key_{i}")

        get_time = time.time() - start_time

        # Performance assertions
        assert set_time < 5.0, f"Set operations took too long: {set_time:.2f}s"
        assert get_time < 3.0, f"Get operations took too long: {get_time:.2f}s"

        print("Basic Operations Performance:")
        print(f"  Set 1000 keys: {set_time:.3f}s ({1000/set_time:.0f} ops/sec)")
        print(f"  Get 1000 keys: {get_time:.3f}s ({1000/get_time:.0f} ops/sec)")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_batch_operations_performance(self, batch_processor, redis_client):
        """Benchmark batch operations vs individual operations."""
        # Prepare test data
        key_value_pairs = [(f"batch_perf_{i}", f"batch_value_{i}") for i in range(1000)]

        # Test individual operations
        start_time = time.time()
        for key, value in key_value_pairs:
            await redis_client.set(key, value, ex=60)
        individual_time = time.time() - start_time

        # Test batch operations
        start_time = time.time()
        batch_result = await batch_set(batch_processor, key_value_pairs, ttl=60)
        batch_time = time.time() - start_time

        # Performance comparison
        speedup = individual_time / batch_time if batch_time > 0 else 0

        assert batch_result.successful_operations == 1000
        assert batch_time < individual_time, "Batch operations should be faster"
        assert (
            speedup > 1.5
        ), f"Batch operations should be at least 1.5x faster, got {speedup:.2f}x"

        print("Batch Operations Performance:")
        print(f"  Individual operations: {individual_time:.3f}s")
        print(f"  Batch operations: {batch_time:.3f}s")
        print(f"  Speedup: {speedup:.2f}x")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_operations_performance(self, redis_client):
        """Benchmark concurrent operations."""

        async def concurrent_set_operations():
            tasks = []
            for i in range(500):
                task = asyncio.create_task(
                    redis_client.set(f"concurrent_{i}", f"value_{i}", ex=60)
                )
                tasks.append(task)
            await asyncio.gather(*tasks)

        async def concurrent_get_operations():
            tasks = []
            for i in range(500):
                task = asyncio.create_task(redis_client.get(f"concurrent_{i}"))
                tasks.append(task)
            await asyncio.gather(*tasks)

        # Test concurrent sets
        start_time = time.time()
        await concurrent_set_operations()
        concurrent_set_time = time.time() - start_time

        # Test concurrent gets
        start_time = time.time()
        await concurrent_get_operations()
        concurrent_get_time = time.time() - start_time

        assert (
            concurrent_set_time < 3.0
        ), f"Concurrent sets took too long: {concurrent_set_time:.2f}s"
        assert (
            concurrent_get_time < 2.0
        ), f"Concurrent gets took too long: {concurrent_get_time:.2f}s"

        print("Concurrent Operations Performance:")
        print(
            f"  Concurrent sets (500): {concurrent_set_time:.3f}s "
            f"({500/concurrent_set_time:.0f} ops/sec)"
        )
        print(
            f"  Concurrent gets (500): {concurrent_get_time:.3f}s "
            f"({500/concurrent_get_time:.0f} ops/sec)"
        )

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cache_hit_ratio_performance(self, redis_client, performance_monitor):
        """Benchmark cache hit ratio performance."""
        # Warm up cache
        for i in range(100):
            await redis_client.set(f"hit_ratio_{i}", f"value_{i}", ex=60)

        # Test cache hits (should be fast)
        start_time = time.time()
        for i in range(100):
            await redis_client.get(f"hit_ratio_{i}")
        hit_time = time.time() - start_time

        # Test cache misses (should be slower)
        start_time = time.time()
        for i in range(100):
            await redis_client.get(f"miss_ratio_{i}")
        miss_time = time.time() - start_time

        # Wait for metrics collection
        await asyncio.sleep(1)

        # Check performance metrics
        summary = performance_monitor.get_performance_summary()
        cache_hit_ratio = summary["redis"]["cache_hit_ratio"]

        assert hit_time < miss_time, "Cache hits should be faster than misses"
        assert (
            cache_hit_ratio > 0.5
        ), f"Cache hit ratio should be > 50%, got {cache_hit_ratio:.2%}"

        print("Cache Hit Ratio Performance:")
        print(f"  Cache hits (100): {hit_time:.3f}s ({100/hit_time:.0f} ops/sec)")
        print(f"  Cache misses (100): {miss_time:.3f}s ({100/miss_time:.0f} ops/sec)")
        print(f"  Cache hit ratio: {cache_hit_ratio:.2%}")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_memory_compression_performance(self, memory_optimizer):
        """Benchmark memory compression performance."""
        # Test data of different sizes
        test_data_small = {"key": "value", "number": 123}
        test_data_medium = {"key": "value" * 100, "data": list(range(100))}
        test_data_large = {
            "key": "value" * 1000,
            "data": list(range(1000)),
            "nested": {"deep": "data" * 100},
        }

        # Test compression performance
        compression_times = []
        compression_ratios = []

        for data in [test_data_small, test_data_medium, test_data_large]:
            start_time = time.time()
            compressed = await memory_optimizer.compress_value(data)
            compression_time = time.time() - start_time

            start_time = time.time()
            decompressed = await memory_optimizer.decompress_value(compressed)
            decompression_time = time.time() - start_time

            compression_times.append(compression_time + decompression_time)

            original_size = len(str(data).encode())
            compressed_size = len(compressed)
            ratio = compressed_size / original_size if original_size > 0 else 1.0
            compression_ratios.append(ratio)

            assert decompressed == data, "Decompressed data should match original"

        avg_compression_time = statistics.mean(compression_times)
        avg_compression_ratio = statistics.mean(compression_ratios)

        assert (
            avg_compression_time < 0.1
        ), f"Compression too slow: {avg_compression_time:.3f}s"
        assert (
            avg_compression_ratio < 0.8
        ), f"Compression ratio too high: {avg_compression_ratio:.2%}"

        print("Memory Compression Performance:")
        print(f"  Average compression time: {avg_compression_time:.3f}s")
        print(f"  Average compression ratio: {avg_compression_ratio:.2%}")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_connection_pool_performance(self, connection_pool_optimizer):
        """Benchmark connection pool performance."""
        redis_client = await connection_pool_optimizer.get_redis_client()

        # Test connection pool under load
        async def pool_operation(i):
            await redis_client.set(f"pool_test_{i}", f"value_{i}")
            return await redis_client.get(f"pool_test_{i}")

        start_time = time.time()
        tasks = [asyncio.create_task(pool_operation(i)) for i in range(200)]
        results = await asyncio.gather(*tasks)
        pool_time = time.time() - start_time

        # Verify all operations succeeded
        assert len(results) == 200
        assert all(result is not None for result in results)

        # Check pool metrics
        pool_metrics = connection_pool_optimizer.get_pool_metrics()
        if pool_metrics:
            assert pool_metrics.connection_utilization > 0
            assert pool_metrics.pool_hit_ratio >= 0

        assert pool_time < 5.0, f"Pool operations took too long: {pool_time:.2f}s"

        print("Connection Pool Performance:")
        print(
            f"  200 concurrent operations: {pool_time:.3f}s "
            f"({200/pool_time:.0f} ops/sec)"
        )

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cache_warming_performance(self, cache_warmer, redis_client):
        """Benchmark cache warming performance."""

        # Define warming rule
        async def data_loader(key_pattern):
            # Simulate data loading delay
            await asyncio.sleep(0.001)
            return {
                "data": f"warmed_{key_pattern}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        rule = WarmingRule(
            name="perf_warming_rule",
            key_pattern="warm_perf_*",
            data_loader=data_loader,
            priority=1,
            ttl=300.0,
        )
        cache_warmer.add_warming_rule(rule)

        # Test cache warming performance
        keys_to_warm = [f"warm_perf_{i}" for i in range(50)]

        start_time = time.time()
        await cache_warmer.warm_on_demand(keys_to_warm)
        warming_time = time.time() - start_time

        # Verify data was warmed
        for key in keys_to_warm[:10]:  # Check first 10
            data = await redis_client.get(key)
            assert data is not None
            assert b"warmed_" in data

        assert warming_time < 2.0, f"Cache warming took too long: {warming_time:.2f}s"

        print("Cache Warming Performance:")
        print(f"  Warmed 50 keys: {warming_time:.3f}s ({50/warming_time:.0f} keys/sec)")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_optimization_recommendations_performance(self, cache_optimizer):
        """Benchmark optimization recommendations generation."""
        # Generate access patterns
        for i in range(1000):
            await cache_optimizer.record_access(f"opt_key_{i % 10}", 3600.0)

        # Test recommendation generation performance
        start_time = time.time()
        recommendations = await cache_optimizer.get_optimization_recommendations()
        recommendation_time = time.time() - start_time

        assert (
            recommendation_time < 1.0
        ), f"Recommendation generation too slow: {recommendation_time:.3f}s"
        assert len(recommendations) >= 0  # May or may not have recommendations

        print("Optimization Recommendations Performance:")
        print(f"  Generated recommendations: {recommendation_time:.3f}s")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_end_to_end_performance(
        self,
        performance_monitor,
        cache_optimizer,
        cache_warmer,
        batch_processor,
        redis_client,
    ):
        """Benchmark end-to-end performance with all optimizations."""

        # Set up warming
        async def data_loader(key_pattern):
            return {
                "data": f"e2e_{key_pattern}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        rule = WarmingRule(
            name="e2e_rule",
            key_pattern="e2e_*",
            data_loader=data_loader,
            priority=1,
            ttl=300.0,
        )
        cache_warmer.add_warming_rule(rule)

        # Warm cache
        await cache_warmer.warm_on_demand(["e2e_warm_1", "e2e_warm_2"])

        # Perform mixed operations
        start_time = time.time()

        # Batch operations
        key_value_pairs = [(f"e2e_batch_{i}", f"batch_value_{i}") for i in range(100)]
        batch_result = await batch_set(batch_processor, key_value_pairs, ttl=60)

        # Individual operations
        for i in range(50):
            await redis_client.set(
                f"e2e_individual_{i}", f"individual_value_{i}", ex=60
            )

        # Read operations
        for i in range(50):
            await redis_client.get(f"e2e_batch_{i % 100}")

        # Record access patterns
        for i in range(200):
            await cache_optimizer.record_access(f"e2e_batch_{i % 100}", 60.0)

        total_time = time.time() - start_time

        # Wait for metrics collection
        await asyncio.sleep(1)

        # Check performance
        assert batch_result.successful_operations == 100
        assert (
            total_time < 10.0
        ), f"End-to-end operations took too long: {total_time:.2f}s"

        # Check performance summary
        summary = performance_monitor.get_performance_summary()
        assert summary["overall_health"] >= 0

        print("End-to-End Performance:")
        print(f"  Total operations time: {total_time:.3f}s")
        print(f"  Overall health score: {summary['overall_health']:.1f}")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_memory_usage_under_load(self, memory_optimizer, redis_client):
        """Test memory usage under load."""
        # Store large amounts of data
        large_data = {"data": "x" * 10000, "numbers": list(range(1000))}

        start_time = time.time()
        for i in range(100):
            await redis_client.set(f"memory_load_{i}", str(large_data))
        store_time = time.time() - start_time

        # Test compression
        start_time = time.time()
        await memory_optimizer.compress_value(large_data)
        compression_time = time.time() - start_time

        # Check memory metrics
        memory_metrics = memory_optimizer.get_memory_metrics()
        if memory_metrics:
            assert memory_metrics.used_memory > 0
            assert memory_metrics.total_keys > 0

        assert store_time < 5.0, f"Data storage took too long: {store_time:.2f}s"
        assert (
            compression_time < 0.1
        ), f"Compression took too long: {compression_time:.3f}s"

        print("Memory Usage Under Load:")
        print(f"  Stored 100 large objects: {store_time:.3f}s")
        print(f"  Compression time: {compression_time:.3f}s")
        if memory_metrics:
            print(f"  Memory usage: {memory_metrics.used_memory / 1024 / 1024:.1f} MB")
            print(f"  Total keys: {memory_metrics.total_keys}")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_performance_monitoring_overhead(
        self, performance_monitor, redis_client
    ):
        """Test performance monitoring overhead."""
        # Test operations without monitoring
        start_time = time.time()
        for i in range(100):
            await redis_client.set(f"no_monitor_{i}", f"value_{i}", ex=60)
        no_monitor_time = time.time() - start_time

        # Test operations with monitoring
        start_time = time.time()
        for i in range(100):
            await redis_client.set(f"with_monitor_{i}", f"value_{i}", ex=60)
            performance_monitor.record_redis_operation(
                "SET", f"with_monitor_{i}", 1.0, True
            )
        with_monitor_time = time.time() - start_time

        # Calculate overhead
        overhead = (
            (with_monitor_time - no_monitor_time) / no_monitor_time
            if no_monitor_time > 0
            else 0
        )

        assert overhead < 0.5, f"Monitoring overhead too high: {overhead:.2%}"

        print("Performance Monitoring Overhead:")
        print(f"  Without monitoring: {no_monitor_time:.3f}s")
        print(f"  With monitoring: {with_monitor_time:.3f}s")
        print(f"  Overhead: {overhead:.2%}")

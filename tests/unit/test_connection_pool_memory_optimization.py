"""Unit tests for connection pool and memory optimization."""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from devcycle.core.acp.cache.connection_pool_optimizer import (
    ConnectionPoolOptimizer,
    PoolConfiguration,
    PoolOptimizationStrategy,
)
from devcycle.core.acp.cache.memory_optimizer import (
    CompressionAlgorithm,
    EvictionPolicy,
    MemoryMetrics,
    MemoryOptimizationRecommendation,
    MemoryOptimizer,
)


class TestConnectionPoolOptimizer:
    """Test cases for connection pool optimizer."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        mock_client = Mock()
        mock_client.info = AsyncMock(
            return_value={
                "used_memory": 1024000,
                "used_memory_peak": 2048000,
                "connected_clients": 5,
            }
        )
        return mock_client

    @pytest.fixture
    def pool_optimizer(self):
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
        return ConnectionPoolOptimizer("redis://localhost:6379", config)

    def test_pool_configuration_creation(self):
        """Test creating pool configuration."""
        config = PoolConfiguration(
            min_connections=10,
            max_connections=50,
            max_idle_connections=20,
            connection_timeout=10.0,
            socket_timeout=10.0,
            socket_keepalive=True,
            socket_keepalive_options={},
            retry_on_timeout=True,
            health_check_interval=60.0,
        )

        assert config.min_connections == 10
        assert config.max_connections == 50
        assert config.max_idle_connections == 20
        assert config.connection_timeout == 10.0

    def test_record_connection_event(self, pool_optimizer):
        """Test recording connection events."""
        pool_optimizer.record_connection_event("connection_created", 0.1)
        pool_optimizer.record_connection_event("connection_destroyed", 0.05)

        assert len(pool_optimizer.connection_events) == 2
        assert pool_optimizer.connection_events[0][1] == "connection_created"
        assert pool_optimizer.connection_events[1][1] == "connection_destroyed"

    def test_generate_optimization_recommendations(self, pool_optimizer):
        """Test generating optimization recommendations."""
        # High utilization
        recommendations = pool_optimizer._generate_optimization_recommendations(
            0.9, 50.0, 0.8
        )
        assert len(recommendations) > 0
        assert any(rec["type"] == "increase_pool_size" for rec in recommendations)

        # Low utilization
        recommendations = pool_optimizer._generate_optimization_recommendations(
            0.2, 10.0, 0.9
        )
        assert any(rec["type"] == "decrease_pool_size" for rec in recommendations)

        # High wait time
        recommendations = pool_optimizer._generate_optimization_recommendations(
            0.5, 200.0, 0.7
        )
        assert any(
            rec["type"] in ["increase_pool_size", "decrease_timeout"]
            for rec in recommendations
        )

    def test_set_optimization_strategy(self, pool_optimizer):
        """Test setting optimization strategy."""
        pool_optimizer.set_optimization_strategy(PoolOptimizationStrategy.STATIC)
        assert pool_optimizer.optimization_strategy == PoolOptimizationStrategy.STATIC

    def test_enable_disable_optimization(self, pool_optimizer):
        """Test enabling/disabling optimization."""
        assert pool_optimizer.optimization_enabled is True

        pool_optimizer.disable_optimization()
        assert pool_optimizer.optimization_enabled is False

        pool_optimizer.enable_optimization()
        assert pool_optimizer.optimization_enabled is True

    def test_set_optimization_interval(self, pool_optimizer):
        """Test setting optimization interval."""
        pool_optimizer.set_optimization_interval(10)
        assert pool_optimizer.optimization_interval == timedelta(minutes=10)

    def test_get_pool_configuration(self, pool_optimizer):
        """Test getting pool configuration."""
        config = pool_optimizer.get_pool_configuration()

        assert "min_connections" in config
        assert "max_connections" in config
        assert "connection_timeout" in config
        assert "optimization_strategy" in config
        assert "optimization_enabled" in config


class TestMemoryOptimizer:
    """Test cases for memory optimizer."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        mock_client = Mock()
        mock_client.info = AsyncMock(
            return_value={
                "used_memory": 1024000,
                "used_memory_peak": 2048000,
                "used_memory_rss": 1500000,
                "mem_fragmentation_ratio": 1.2,
                "expired_keys": 100,
                "evicted_keys": 50,
            }
        )
        mock_client.keys = AsyncMock(return_value=["key1", "key2", "key3"])
        mock_client.memory_usage = AsyncMock(return_value=1024)
        mock_client.type = AsyncMock(return_value="string")
        mock_client.config_set = AsyncMock()
        return mock_client

    @pytest.fixture
    def memory_optimizer(self, mock_redis_client):
        """Create memory optimizer."""
        return MemoryOptimizer(mock_redis_client)

    def test_memory_metrics_creation(self):
        """Test creating memory metrics."""
        metrics = MemoryMetrics(
            used_memory=1024000,
            used_memory_peak=2048000,
            used_memory_rss=1500000,
            used_memory_ratio=0.5,
            memory_fragmentation_ratio=1.2,
            total_keys=1000,
            expired_keys=100,
            evicted_keys=50,
            memory_usage_by_type={"string": 500000, "hash": 300000},
            largest_keys=[("key1", 1024), ("key2", 512)],
        )

        assert metrics.used_memory == 1024000
        assert metrics.used_memory_ratio == 0.5
        assert metrics.total_keys == 1000

    @pytest.mark.asyncio
    async def test_compress_decompress_value(self, memory_optimizer):
        """Test compressing and decompressing values."""
        test_data = {"key": "value", "number": 123, "list": [1, 2, 3]}

        # Compress
        compressed = await memory_optimizer.compress_value(test_data)
        assert isinstance(compressed, bytes)
        assert len(compressed) > 0

        # Decompress
        decompressed = await memory_optimizer.decompress_value(compressed)
        assert decompressed == test_data

    @pytest.mark.asyncio
    async def test_compress_small_value(self, memory_optimizer):
        """Test that small values are not compressed."""
        small_data = "small"

        # Set compression threshold high
        memory_optimizer.compression_threshold = 10000

        compressed = await memory_optimizer.compress_value(small_data)
        decompressed = await memory_optimizer.decompress_value(compressed)

        assert decompressed == small_data

    def test_set_memory_threshold(self, memory_optimizer):
        """Test setting memory threshold."""
        memory_optimizer.set_memory_threshold(0.9)
        assert memory_optimizer.memory_threshold == 0.9

        # Test bounds
        memory_optimizer.set_memory_threshold(2.0)
        assert memory_optimizer.memory_threshold == 1.0

        memory_optimizer.set_memory_threshold(0.05)
        assert memory_optimizer.memory_threshold == 0.1

    def test_set_compression_algorithm(self, memory_optimizer):
        """Test setting compression algorithm."""
        memory_optimizer.set_compression_algorithm(CompressionAlgorithm.LZ4)
        assert memory_optimizer.compression_algorithm == CompressionAlgorithm.LZ4

    def test_set_compression_threshold(self, memory_optimizer):
        """Test setting compression threshold."""
        memory_optimizer.set_compression_threshold(2048)
        assert memory_optimizer.compression_threshold == 2048

        # Test minimum threshold
        memory_optimizer.set_compression_threshold(50)
        assert memory_optimizer.compression_threshold == 100

    def test_enable_disable_compression(self, memory_optimizer):
        """Test enabling/disabling compression."""
        assert memory_optimizer.compression_enabled is True

        memory_optimizer.disable_compression()
        assert memory_optimizer.compression_enabled is False

        memory_optimizer.enable_compression()
        assert memory_optimizer.compression_enabled is True

    def test_get_memory_configuration(self, memory_optimizer):
        """Test getting memory configuration."""
        config = memory_optimizer.get_memory_configuration()

        assert "memory_threshold" in config
        assert "compression_enabled" in config
        assert "compression_algorithm" in config
        assert "compression_threshold" in config
        assert "eviction_policy" in config

    @pytest.mark.asyncio
    async def test_generate_memory_recommendations(self, memory_optimizer):
        """Test generating memory recommendations."""
        # High memory usage
        metrics = MemoryMetrics(
            used_memory=1000000,
            used_memory_peak=2000000,
            used_memory_rss=1500000,
            used_memory_ratio=0.95,  # High usage
            memory_fragmentation_ratio=1.2,
            total_keys=1000,
            expired_keys=100,
            evicted_keys=50,
            memory_usage_by_type={"string": 500000},
            largest_keys=[("key1", 2048)],  # Large key
        )

        recommendations = await memory_optimizer._generate_memory_recommendations(
            metrics
        )

        assert len(recommendations) > 0
        assert any(
            rec.recommendation_type == "eviction_policy" for rec in recommendations
        )
        assert any(rec.recommendation_type == "compression" for rec in recommendations)

    @pytest.mark.asyncio
    async def test_apply_eviction_policy(self, memory_optimizer, mock_redis_client):
        """Test applying eviction policy."""
        await memory_optimizer._set_eviction_policy("allkeys-lru")

        mock_redis_client.config_set.assert_called_once_with(
            "maxmemory-policy", "allkeys-lru"
        )
        assert memory_optimizer.eviction_policy == EvictionPolicy.ALLKEYS_LRU

    def test_compression_algorithm_enum(self):
        """Test compression algorithm enum."""
        assert CompressionAlgorithm.GZIP.value == "gzip"
        assert CompressionAlgorithm.LZ4.value == "lz4"
        assert CompressionAlgorithm.ZSTD.value == "zstd"
        assert CompressionAlgorithm.NONE.value == "none"

    def test_eviction_policy_enum(self):
        """Test eviction policy enum."""
        assert EvictionPolicy.ALLKEYS_LRU.value == "allkeys-lru"
        assert EvictionPolicy.ALLKEYS_LFU.value == "allkeys-lfu"
        assert EvictionPolicy.VOLATILE_LRU.value == "volatile-lru"
        assert EvictionPolicy.VOLATILE_LFU.value == "volatile-lfu"
        assert EvictionPolicy.VOLATILE_TTL.value == "volatile-ttl"
        assert EvictionPolicy.NOEVICTION.value == "noeviction"

    def test_memory_optimization_recommendation(self):
        """Test memory optimization recommendation."""
        rec = MemoryOptimizationRecommendation(
            recommendation_type="compression",
            description="Enable compression",
            current_value=False,
            recommended_value=True,
            expected_savings=1024,
            priority=3,
        )

        assert rec.recommendation_type == "compression"
        assert rec.description == "Enable compression"
        assert rec.current_value is False
        assert rec.recommended_value is True
        assert rec.expected_savings == 1024
        assert rec.priority == 3


class TestIntegration:
    """Integration tests for optimization systems."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client for integration tests."""
        mock_client = Mock()
        mock_client.info = AsyncMock(
            return_value={
                "used_memory": 1024000,
                "used_memory_peak": 2048000,
                "connected_clients": 5,
                "mem_fragmentation_ratio": 1.2,
                "expired_keys": 100,
                "evicted_keys": 50,
            }
        )
        mock_client.keys = AsyncMock(return_value=["key1", "key2"])
        mock_client.memory_usage = AsyncMock(return_value=1024)
        mock_client.type = AsyncMock(return_value="string")
        mock_client.config_set = AsyncMock()
        return mock_client

    @pytest.mark.asyncio
    async def test_pool_and_memory_optimization_together(self, mock_redis_client):
        """Test pool and memory optimization working together."""
        # Create optimizers
        pool_config = PoolConfiguration(
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

        pool_optimizer = ConnectionPoolOptimizer("redis://localhost:6379", pool_config)
        memory_optimizer = MemoryOptimizer(mock_redis_client)

        # Test configuration
        pool_config_dict = pool_optimizer.get_pool_configuration()
        memory_config_dict = memory_optimizer.get_memory_configuration()

        assert "max_connections" in pool_config_dict
        assert "memory_threshold" in memory_config_dict

        # Test event recording
        pool_optimizer.record_connection_event("connection_created", 0.1)
        assert len(pool_optimizer.connection_events) == 1

        # Test compression
        test_data = {"test": "data"}
        compressed = await memory_optimizer.compress_value(test_data)
        decompressed = await memory_optimizer.decompress_value(compressed)
        assert decompressed == test_data

    def test_optimization_strategies(self):
        """Test different optimization strategies."""
        strategies = [
            PoolOptimizationStrategy.STATIC,
            PoolOptimizationStrategy.DYNAMIC,
            PoolOptimizationStrategy.ADAPTIVE,
        ]

        for strategy in strategies:
            assert strategy.value in ["static", "dynamic", "adaptive"]

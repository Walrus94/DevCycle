"""Unit tests for advanced caching features."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from devcycle.core.acp.cache.batch_operations import (
    BatchOperation,
    BatchOperationType,
    RedisBatchProcessor,
    batch_delete,
    batch_exists,
    batch_get,
    batch_set,
)
from devcycle.core.acp.cache.cache_optimizer import CacheAccessPattern, CacheOptimizer
from devcycle.core.acp.cache.cache_warmer import (
    CacheWarmer,
    WarmingRule,
    WarmingStrategy,
)


class TestCacheOptimizer:
    """Test cases for cache optimizer."""

    @pytest.fixture
    def mock_acp_cache(self):
        """Create a mock ACP cache."""
        mock_cache = Mock()
        mock_cache.get = AsyncMock()
        mock_cache.set = AsyncMock()
        return mock_cache

    @pytest.fixture
    def cache_optimizer(self, mock_acp_cache):
        """Create cache optimizer."""
        return CacheOptimizer(mock_acp_cache)

    def test_record_access(self, cache_optimizer):
        """Test recording cache access."""
        key = "test_key"
        ttl = 3600.0

        # Record access
        asyncio.run(cache_optimizer.record_access(key, ttl))

        # Check pattern was created
        assert key in cache_optimizer.access_patterns
        pattern = cache_optimizer.access_patterns[key]
        assert pattern.access_count == 1
        assert pattern.avg_ttl == ttl
        assert pattern.hit_ratio == 1.0

    def test_record_multiple_accesses(self, cache_optimizer):
        """Test recording multiple accesses."""
        key = "test_key"

        # Record multiple accesses
        for i in range(5):
            asyncio.run(cache_optimizer.record_access(key, 3600.0))

        pattern = cache_optimizer.access_patterns[key]
        assert pattern.access_count == 5

    @pytest.mark.asyncio
    async def test_analyze_access_patterns(self, cache_optimizer):
        """Test analyzing access patterns."""
        # Set up some access patterns
        cache_optimizer.access_patterns["key1"] = CacheAccessPattern(
            key="key1",
            access_count=10,
            last_access=datetime.now(timezone.utc),
            first_access=datetime.now(timezone.utc) - timedelta(hours=1),
            avg_ttl=300.0,
            hit_ratio=0.8,
            access_frequency=0.0,
        )

        # Add some access times
        now = datetime.now(timezone.utc)
        for i in range(10):
            cache_optimizer.key_access_times["key1"].append(now - timedelta(minutes=i))

        # Analyze patterns
        await cache_optimizer._analyze_access_patterns()

        pattern = cache_optimizer.access_patterns["key1"]
        assert pattern.access_frequency > 0

    @pytest.mark.asyncio
    async def test_generate_recommendations(self, cache_optimizer):
        """Test generating optimization recommendations."""
        # Set up high-frequency pattern
        cache_optimizer.access_patterns["high_freq"] = CacheAccessPattern(
            key="high_freq",
            access_count=100,
            last_access=datetime.now(timezone.utc),
            first_access=datetime.now(timezone.utc) - timedelta(hours=1),
            avg_ttl=200.0,  # Low TTL
            hit_ratio=0.9,
            access_frequency=10.0,  # High frequency
        )

        # Set up low-frequency pattern
        cache_optimizer.access_patterns["low_freq"] = CacheAccessPattern(
            key="low_freq",
            access_count=5,
            last_access=datetime.now(timezone.utc),
            first_access=datetime.now(timezone.utc) - timedelta(hours=1),
            avg_ttl=2000.0,  # High TTL
            hit_ratio=0.3,
            access_frequency=0.05,  # Low frequency
        )

        recommendations = await cache_optimizer._generate_recommendations()

        assert len(recommendations) > 0
        assert any(rec.key_pattern == "high_freq" for rec in recommendations)
        assert any(rec.key_pattern == "low_freq" for rec in recommendations)

    @pytest.mark.asyncio
    async def test_adjust_key_ttl(self, cache_optimizer, mock_acp_cache):
        """Test adjusting key TTL."""
        key = "test_key"
        new_ttl = 7200.0

        # Mock cache get/set
        mock_acp_cache.get.return_value = "test_value"
        mock_acp_cache.set.return_value = True

        await cache_optimizer._adjust_key_ttl(key, new_ttl)

        mock_acp_cache.get.assert_called_once_with(key)
        mock_acp_cache.set.assert_called_once_with(key, "test_value", ttl=new_ttl)

    def test_enable_disable_optimization(self, cache_optimizer):
        """Test enabling/disabling optimization."""
        assert cache_optimizer.optimization_enabled is True

        cache_optimizer.disable_optimization()
        assert cache_optimizer.optimization_enabled is False

        cache_optimizer.enable_optimization()
        assert cache_optimizer.optimization_enabled is True

    def test_set_optimization_interval(self, cache_optimizer):
        """Test setting optimization interval."""
        cache_optimizer.set_optimization_interval(2)
        assert cache_optimizer.optimization_interval == timedelta(hours=2)


class TestCacheWarmer:
    """Test cases for cache warmer."""

    @pytest.fixture
    def mock_acp_cache(self):
        """Create a mock ACP cache."""
        mock_cache = Mock()
        mock_cache.set = AsyncMock()
        mock_cache.redis = Mock()
        mock_cache.redis.set = AsyncMock()
        return mock_cache

    @pytest.fixture
    def cache_warmer(self, mock_acp_cache):
        """Create cache warmer."""
        return CacheWarmer(mock_acp_cache)

    def test_add_warming_rule(self, cache_warmer):
        """Test adding warming rule."""

        async def data_loader(key):
            return f"data_for_{key}"

        rule = WarmingRule(
            name="test_rule",
            key_pattern="test_*",
            data_loader=data_loader,
            priority=1,
            ttl=3600.0,
        )

        cache_warmer.add_warming_rule(rule)

        assert "test_rule" in cache_warmer.warming_rules
        assert cache_warmer.warming_statistics.total_rules == 1
        assert cache_warmer.warming_statistics.enabled_rules == 1

    def test_remove_warming_rule(self, cache_warmer):
        """Test removing warming rule."""
        # Add a rule first
        rule = WarmingRule(
            name="test_rule",
            key_pattern="test_*",
            data_loader=lambda x: None,
            priority=1,
        )
        cache_warmer.add_warming_rule(rule)

        # Remove it
        cache_warmer.remove_warming_rule("test_rule")

        assert "test_rule" not in cache_warmer.warming_rules
        assert cache_warmer.warming_statistics.total_rules == 0

    def test_enable_disable_warming_rule(self, cache_warmer):
        """Test enabling/disabling warming rule."""
        rule = WarmingRule(
            name="test_rule",
            key_pattern="test_*",
            data_loader=lambda x: None,
            priority=1,
        )
        cache_warmer.add_warming_rule(rule)

        # Disable
        cache_warmer.disable_warming_rule("test_rule")
        assert not cache_warmer.warming_rules["test_rule"].enabled
        assert cache_warmer.warming_statistics.enabled_rules == 0

        # Enable
        cache_warmer.enable_warming_rule("test_rule")
        assert cache_warmer.warming_rules["test_rule"].enabled
        assert cache_warmer.warming_statistics.enabled_rules == 1

    @pytest.mark.asyncio
    async def test_warm_rule(self, cache_warmer, mock_acp_cache):
        """Test warming a specific rule."""

        async def data_loader(key):
            return f"warmed_data_for_{key}"

        rule = WarmingRule(
            name="test_rule",
            key_pattern="test_key",
            data_loader=data_loader,
            priority=1,
            ttl=3600.0,
        )

        mock_acp_cache.redis.set.return_value = True

        await cache_warmer._warm_rule(rule)

        mock_acp_cache.redis.set.assert_called_once_with(
            "test_key", '"warmed_data_for_test_key"', ex=3600
        )
        assert rule.last_warmed is not None
        assert rule.warm_count == 1

    def test_pattern_matching(self, cache_warmer):
        """Test pattern matching."""
        # Exact match
        assert cache_warmer._pattern_matches("test_key", "test_key")
        assert not cache_warmer._pattern_matches("test_key", "other_key")

        # Wildcard match
        assert cache_warmer._pattern_matches("test_key", "test_*")
        assert cache_warmer._pattern_matches("test_value", "test_*")
        assert not cache_warmer._pattern_matches("other_key", "test_*")

    def test_add_remove_warming_strategy(self, cache_warmer):
        """Test adding/removing warming strategies."""
        # Add strategy
        cache_warmer.add_warming_strategy(WarmingStrategy.SCHEDULED)
        assert WarmingStrategy.SCHEDULED in cache_warmer.warming_strategies

        # Remove strategy
        cache_warmer.remove_warming_strategy(WarmingStrategy.SCHEDULED)
        assert WarmingStrategy.SCHEDULED not in cache_warmer.warming_strategies

    def test_enable_disable_warming(self, cache_warmer):
        """Test enabling/disabling warming."""
        assert cache_warmer.warming_enabled is True

        cache_warmer.disable_warming()
        assert cache_warmer.warming_enabled is False

        cache_warmer.enable_warming()
        assert cache_warmer.warming_enabled is True

    def test_get_warming_statistics(self, cache_warmer):
        """Test getting warming statistics."""
        stats = cache_warmer.get_warming_statistics()

        assert "warming_enabled" in stats
        assert "strategies" in stats
        assert "total_rules" in stats
        assert "enabled_rules" in stats
        assert "rules" in stats


class TestBatchOperations:
    """Test cases for batch operations."""

    @pytest.fixture
    def mock_acp_cache(self):
        """Create a mock ACP cache."""
        mock_cache = Mock()
        mock_cache.redis = Mock()
        mock_cache.redis.mget = AsyncMock()
        mock_cache.redis.pipeline = Mock()
        mock_cache.redis.delete = AsyncMock()
        mock_cache.redis.exists = AsyncMock()
        return mock_cache

    @pytest.fixture
    def batch_processor(self, mock_acp_cache):
        """Create batch processor."""
        return RedisBatchProcessor(mock_acp_cache)

    def test_batch_operation_creation(self):
        """Test creating batch operations."""
        op = BatchOperation(BatchOperationType.GET, "test_key")

        assert op.operation_type == BatchOperationType.GET
        assert op.key == "test_key"
        assert op.value is None
        assert op.result is None
        assert op.error is None

    def test_split_into_batches(self, batch_processor):
        """Test splitting operations into batches."""
        operations = [
            BatchOperation(BatchOperationType.GET, f"key_{i}") for i in range(250)
        ]

        batches = batch_processor._split_into_batches(operations)

        assert len(batches) == 3  # 250 / 100 = 3 batches
        assert len(batches[0]) == 100
        assert len(batches[1]) == 100
        assert len(batches[2]) == 50

    def test_group_operations_by_type(self, batch_processor):
        """Test grouping operations by type."""
        operations = [
            BatchOperation(BatchOperationType.GET, "key1"),
            BatchOperation(BatchOperationType.SET, "key2", "value2"),
            BatchOperation(BatchOperationType.GET, "key3"),
            BatchOperation(BatchOperationType.DELETE, "key4"),
        ]

        grouped = batch_processor._group_operations_by_type(operations)

        assert len(grouped[BatchOperationType.GET]) == 2
        assert len(grouped[BatchOperationType.SET]) == 1
        assert len(grouped[BatchOperationType.DELETE]) == 1

    @pytest.mark.asyncio
    async def test_execute_get_operations(self, batch_processor, mock_acp_cache):
        """Test executing GET operations."""
        operations = [
            BatchOperation(BatchOperationType.GET, "key1"),
            BatchOperation(BatchOperationType.GET, "key2"),
        ]

        mock_acp_cache.redis.mget.return_value = ["value1", "value2"]

        await batch_processor._execute_get_operations(operations)

        assert operations[0].result == "value1"
        assert operations[1].result == "value2"
        assert operations[0].error is None
        assert operations[1].error is None

    @pytest.mark.asyncio
    async def test_execute_set_operations(self, batch_processor, mock_acp_cache):
        """Test executing SET operations."""
        operations = [
            BatchOperation(BatchOperationType.SET, "key1", "value1", ttl=3600),
            BatchOperation(BatchOperationType.SET, "key2", "value2"),
        ]

        mock_pipeline = Mock()
        mock_pipeline.execute = AsyncMock(return_value=[True, True])
        mock_acp_cache.redis.pipeline.return_value = mock_pipeline

        await batch_processor._execute_set_operations(operations)

        assert operations[0].result is True
        assert operations[1].result is True
        assert operations[0].error is None
        assert operations[1].error is None

    @pytest.mark.asyncio
    async def test_execute_batch(self, batch_processor, mock_acp_cache):
        """Test executing a complete batch."""
        operations = [
            BatchOperation(BatchOperationType.GET, "key1"),
            BatchOperation(BatchOperationType.SET, "key2", "value2"),
        ]

        # Mock Redis operations
        mock_acp_cache.redis.mget.return_value = ["value1"]
        mock_pipeline = Mock()
        mock_pipeline.execute = AsyncMock(return_value=[True])
        mock_acp_cache.redis.pipeline.return_value = mock_pipeline

        result = await batch_processor.execute_batch(operations)

        assert result.total_operations == 2
        assert result.successful_operations == 2
        assert result.failed_operations == 0
        assert result.execution_time_ms >= 0  # Can be 0 for very fast operations
        assert (
            result.throughput_ops_per_second >= 0
        )  # Can be 0 for very fast operations

    def test_performance_statistics(self, batch_processor):
        """Test performance statistics tracking."""
        stats = batch_processor.get_performance_statistics()

        assert "total_batches_processed" in stats
        assert "total_operations_processed" in stats
        assert "average_batch_time_ms" in stats
        assert "average_throughput_ops_per_second" in stats
        assert "batch_size" in stats
        assert "max_concurrent_batches" in stats

    def test_set_batch_size(self, batch_processor):
        """Test setting batch size."""
        batch_processor.set_batch_size(50)
        assert batch_processor.batch_size == 50

    def test_set_max_concurrent_batches(self, batch_processor):
        """Test setting max concurrent batches."""
        batch_processor.set_max_concurrent_batches(5)
        assert batch_processor.max_concurrent_batches == 5


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    @pytest.fixture
    def mock_acp_cache(self):
        """Create a mock ACP cache."""
        mock_cache = Mock()
        mock_cache.redis = Mock()
        mock_cache.redis.mget = AsyncMock()
        return mock_cache

    @pytest.fixture
    def batch_processor(self, mock_acp_cache):
        """Create batch processor."""
        return RedisBatchProcessor(mock_acp_cache)

    @pytest.mark.asyncio
    async def test_batch_get(self, batch_processor, mock_acp_cache):
        """Test batch_get convenience function."""
        keys = ["key1", "key2", "key3"]
        mock_acp_cache.redis.mget.return_value = ["value1", "value2", "value3"]

        result = await batch_get(batch_processor, keys)

        assert result.total_operations == 3
        assert result.successful_operations == 3
        assert len(result.operations) == 3

    @pytest.mark.asyncio
    async def test_batch_set(self, batch_processor, mock_acp_cache):
        """Test batch_set convenience function."""
        key_value_pairs = [("key1", "value1"), ("key2", "value2")]
        mock_pipeline = Mock()
        mock_pipeline.execute = AsyncMock(return_value=[True, True])
        mock_acp_cache.redis.pipeline.return_value = mock_pipeline

        result = await batch_set(batch_processor, key_value_pairs, ttl=3600)

        assert result.total_operations == 2
        assert result.successful_operations == 2

    @pytest.mark.asyncio
    async def test_batch_delete(self, batch_processor, mock_acp_cache):
        """Test batch_delete convenience function."""
        keys = ["key1", "key2"]
        mock_acp_cache.redis.delete = AsyncMock(return_value=2)

        result = await batch_delete(batch_processor, keys)

        assert result.total_operations == 2
        assert result.successful_operations == 2

    @pytest.mark.asyncio
    async def test_batch_exists(self, batch_processor, mock_acp_cache):
        """Test batch_exists convenience function."""
        keys = ["key1", "key2"]
        mock_acp_cache.redis.exists = AsyncMock(return_value=2)

        result = await batch_exists(batch_processor, keys)

        assert result.total_operations == 2
        assert result.successful_operations == 2

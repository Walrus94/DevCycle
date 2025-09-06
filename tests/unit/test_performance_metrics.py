"""Unit tests for performance metrics collection."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from devcycle.core.acp.metrics.acp_metrics import ACPMetricsCollector
from devcycle.core.acp.metrics.decorators import (
    monitor_acp_operation,
    monitor_operation,
    monitor_redis_operation,
)
from devcycle.core.acp.metrics.performance_monitor import PerformanceMonitor
from devcycle.core.acp.metrics.redis_metrics import RedisMetricsCollector


class TestRedisMetricsCollector:
    """Test cases for Redis metrics collector."""

    @pytest.fixture
    def mock_redis_cache(self):
        """Create a mock Redis cache."""
        mock_cache = Mock()
        mock_cache.redis = Mock()
        mock_cache.redis.info = AsyncMock(
            return_value={
                "used_memory": 1024000,
                "used_memory_peak": 2048000,
                "connected_clients": 5,
                "total_commands_processed": 1000,
                "keyspace_hits": 800,
                "keyspace_misses": 200,
                "expired_keys": 50,
                "evicted_keys": 10,
                "keyspace": {"db0": {"keys": 100}},
                "uptime_in_seconds": 3600,
            }
        )
        return mock_cache

    @pytest.fixture
    def redis_metrics(self, mock_redis_cache):
        """Create Redis metrics collector."""
        return RedisMetricsCollector(mock_redis_cache)

    def test_record_operation(self, redis_metrics):
        """Test recording Redis operations."""
        # Record successful operation
        redis_metrics.record_operation("GET", "test_key", 10.5, True)

        assert len(redis_metrics.operation_history) == 1
        assert redis_metrics.operation_counts["GET"] == 1
        assert redis_metrics.error_counts == {}

        # Record failed operation
        redis_metrics.record_operation(
            "SET", "test_key", 5.2, False, "Connection timeout"
        )

        assert len(redis_metrics.operation_history) == 2
        assert redis_metrics.operation_counts["SET"] == 1
        assert redis_metrics.error_counts["Connection timeout"] == 1

    def test_get_performance_snapshot(self, redis_metrics):
        """Test getting performance snapshot."""
        # Set up Redis info manually for testing
        redis_metrics.redis_info = {
            "memory_usage": 1024000,
            "memory_peak": 2048000,
            "connected_clients": 5,
            "total_commands_processed": 1000,
            "keyspace_hits": 800,
            "keyspace_misses": 200,
            "expired_keys": 50,
            "evicted_keys": 10,
            "keyspace": {"db0": {"keys": 100}},
            "uptime_seconds": 3600,
        }

        # Record some operations
        redis_metrics.record_operation("GET", "key1", 10.0, True)
        redis_metrics.record_operation("SET", "key2", 20.0, True)
        redis_metrics.record_operation("DEL", "key3", 5.0, False, "Key not found")

        snapshot = redis_metrics.get_performance_snapshot()

        assert snapshot.total_operations == 3
        assert snapshot.successful_operations == 2
        assert snapshot.failed_operations == 1
        assert abs(snapshot.average_latency_ms - 11.67) < 0.01  # (10 + 20 + 5) / 3
        assert snapshot.cache_hit_ratio == 0.8  # 800 / (800 + 200)
        assert snapshot.memory_usage_bytes == 1024000

    def test_get_operation_breakdown(self, redis_metrics):
        """Test getting operation breakdown."""
        # Record operations
        redis_metrics.record_operation("GET", "key1", 10.0, True)
        redis_metrics.record_operation("GET", "key2", 15.0, True)
        redis_metrics.record_operation("SET", "key3", 20.0, False, "Error")

        breakdown = redis_metrics.get_operation_breakdown()

        assert "GET" in breakdown
        assert "SET" in breakdown
        assert breakdown["GET"]["count"] == 2
        assert breakdown["GET"]["successful"] == 2
        assert breakdown["SET"]["count"] == 1
        assert breakdown["SET"]["failed"] == 1

    def test_get_health_score(self, redis_metrics):
        """Test getting health score."""
        # Record some operations
        redis_metrics.record_operation("GET", "key1", 10.0, True)
        redis_metrics.record_operation("SET", "key2", 20.0, True)

        health_score = redis_metrics.get_health_score()

        assert 0 <= health_score <= 100
        assert health_score > 50  # Should be good with successful operations

    def test_reset_metrics(self, redis_metrics):
        """Test resetting metrics."""
        # Record some operations
        redis_metrics.record_operation("GET", "key1", 10.0, True)

        # Reset
        redis_metrics.reset_metrics()

        assert len(redis_metrics.operation_history) == 0
        assert redis_metrics.operation_counts == {}
        assert redis_metrics.error_counts == {}


class TestACPMetricsCollector:
    """Test cases for ACP metrics collector."""

    @pytest.fixture
    def acp_metrics(self):
        """Create ACP metrics collector."""
        return ACPMetricsCollector()

    def test_record_operation(self, acp_metrics):
        """Test recording ACP operations."""
        # Record successful operation
        acp_metrics.record_operation("agent_registry", "register_agent", 50.0, True)

        assert len(acp_metrics.operation_history) == 1
        assert acp_metrics.service_counts["agent_registry"] == 1
        assert acp_metrics.operation_counts["agent_registry.register_agent"] == 1

        # Record failed operation
        acp_metrics.record_operation(
            "workflow_engine", "start_workflow", 100.0, False, "Agent not found"
        )

        assert len(acp_metrics.operation_history) == 2
        assert acp_metrics.service_counts["workflow_engine"] == 1
        assert acp_metrics.error_counts["Agent not found"] == 1

    def test_get_performance_snapshot(self, acp_metrics):
        """Test getting performance snapshot."""
        # Record some operations
        acp_metrics.record_operation("agent_registry", "register_agent", 50.0, True)
        acp_metrics.record_operation("workflow_engine", "start_workflow", 100.0, True)
        acp_metrics.record_operation(
            "message_router", "route_message", 25.0, False, "No route found"
        )

        snapshot = acp_metrics.get_performance_snapshot()

        assert snapshot.total_operations == 3
        assert snapshot.successful_operations == 2
        assert snapshot.failed_operations == 1
        assert abs(snapshot.average_latency_ms - 58.33) < 0.01  # (50 + 100 + 25) / 3

    def test_get_service_breakdown(self, acp_metrics):
        """Test getting service breakdown."""
        # Record operations
        acp_metrics.record_operation("agent_registry", "register_agent", 50.0, True)
        acp_metrics.record_operation("agent_registry", "unregister_agent", 30.0, True)
        acp_metrics.record_operation(
            "workflow_engine", "start_workflow", 100.0, False, "Error"
        )

        breakdown = acp_metrics.get_service_breakdown()

        assert "agent_registry" in breakdown
        assert "workflow_engine" in breakdown
        assert breakdown["agent_registry"]["count"] == 2
        assert breakdown["agent_registry"]["successful"] == 2
        assert breakdown["workflow_engine"]["count"] == 1
        assert breakdown["workflow_engine"]["failed"] == 1

    def test_update_service_metrics(self, acp_metrics):
        """Test updating service-specific metrics."""
        # Update agent registry metrics
        acp_metrics.update_agent_registry_metrics(
            registered_agents=5, active_agents=3, health_check_failures=1
        )

        metrics = acp_metrics.get_agent_registry_metrics()
        assert metrics["registered_agents"] == 5
        assert metrics["active_agents"] == 3
        assert metrics["health_check_failures"] == 1

    def test_reset_metrics(self, acp_metrics):
        """Test resetting metrics."""
        # Record some operations
        acp_metrics.record_operation("agent_registry", "register_agent", 50.0, True)

        # Reset
        acp_metrics.reset_metrics()

        assert len(acp_metrics.operation_history) == 0
        assert acp_metrics.service_counts == {}
        assert acp_metrics.operation_counts == {}


class TestPerformanceMonitor:
    """Test cases for performance monitor."""

    @pytest.fixture
    def mock_redis_cache(self):
        """Create a mock Redis cache."""
        mock_cache = Mock()
        mock_cache.redis = Mock()
        mock_cache.redis.info = AsyncMock(
            return_value={
                "used_memory": 1024000,
                "used_memory_peak": 2048000,
                "connected_clients": 5,
                "total_commands_processed": 1000,
                "keyspace_hits": 800,
                "keyspace_misses": 200,
                "expired_keys": 50,
                "evicted_keys": 10,
                "keyspace": {"db0": {"keys": 100}},
                "uptime_in_seconds": 3600,
            }
        )
        return mock_cache

    @pytest.fixture
    def performance_monitor(self, mock_redis_cache):
        """Create performance monitor."""
        return PerformanceMonitor(mock_redis_cache)

    @pytest.mark.asyncio
    async def test_start_stop(self, performance_monitor):
        """Test starting and stopping the monitor."""
        await performance_monitor.start()
        assert performance_monitor._running is True

        await performance_monitor.stop()
        assert performance_monitor._running is False

    def test_record_operations(self, performance_monitor):
        """Test recording operations."""
        # Record Redis operation
        performance_monitor.record_redis_operation("GET", "test_key", 10.0, True)

        # Record ACP operation
        performance_monitor.record_acp_operation(
            "agent_registry", "register_agent", 50.0, True
        )

        # Check metrics
        redis_snapshot = performance_monitor.get_redis_metrics()
        acp_snapshot = performance_monitor.get_acp_metrics()

        assert redis_snapshot.total_operations == 1
        assert acp_snapshot.total_operations == 1

    def test_get_performance_summary(self, performance_monitor):
        """Test getting performance summary."""
        # Record some operations
        performance_monitor.record_redis_operation("GET", "test_key", 10.0, True)
        performance_monitor.record_acp_operation(
            "agent_registry", "register_agent", 50.0, True
        )

        summary = performance_monitor.get_performance_summary()

        assert "timestamp" in summary
        assert "overall_health" in summary
        assert "redis" in summary
        assert "acp" in summary
        assert "services" in summary

    def test_health_thresholds(self, performance_monitor):
        """Test health thresholds."""
        thresholds = performance_monitor.get_health_thresholds()
        assert "redis_memory_usage_percentage" in thresholds
        assert "redis_latency_ms" in thresholds
        assert "acp_success_rate" in thresholds

        # Set new thresholds
        new_thresholds = {"redis_memory_usage_percentage": 90.0}
        performance_monitor.set_health_thresholds(new_thresholds)

        updated_thresholds = performance_monitor.get_health_thresholds()
        assert updated_thresholds["redis_memory_usage_percentage"] == 90.0

    def test_reset_all_metrics(self, performance_monitor):
        """Test resetting all metrics."""
        # Record some operations
        performance_monitor.record_redis_operation("GET", "test_key", 10.0, True)
        performance_monitor.record_acp_operation(
            "agent_registry", "register_agent", 50.0, True
        )

        # Reset
        performance_monitor.reset_all_metrics()

        redis_snapshot = performance_monitor.get_redis_metrics()
        acp_snapshot = performance_monitor.get_acp_metrics()

        assert redis_snapshot.total_operations == 0
        assert acp_snapshot.total_operations == 0


class TestDecorators:
    """Test cases for performance monitoring decorators."""

    @pytest.fixture
    def mock_performance_monitor(self):
        """Create a mock performance monitor."""
        monitor = Mock()
        monitor.record_redis_operation = Mock()
        monitor.record_acp_operation = Mock()
        return monitor

    def test_monitor_redis_operation_decorator(self, mock_performance_monitor):
        """Test Redis operation monitoring decorator."""

        @monitor_redis_operation("test_operation")
        async def test_redis_operation(self, key, value):
            return f"processed_{key}_{value}"

        # Mock the self object with performance_monitor
        class MockRedisService:
            def __init__(self):
                self.performance_monitor = mock_performance_monitor

        service = MockRedisService()

        # Test async function
        result = asyncio.run(test_redis_operation(service, "test_key", "test_value"))

        assert result == "processed_test_key_test_value"
        mock_performance_monitor.record_redis_operation.assert_called_once()

        # Check the call arguments
        call_args = mock_performance_monitor.record_redis_operation.call_args
        assert call_args[0][0] == "test_operation"  # operation
        assert call_args[0][1] == "test_key"  # key
        assert call_args[0][2] >= 0  # duration_ms (can be 0 for very fast operations)
        assert call_args[0][3] is True  # success

    def test_monitor_acp_operation_decorator(self, mock_performance_monitor):
        """Test ACP operation monitoring decorator."""

        @monitor_acp_operation("test_service", "test_operation")
        async def test_acp_operation(self, param):
            return {"result": f"processed_{param}", "metadata": {"count": 1}}

        # Mock the self object with performance_monitor
        class MockACPService:
            def __init__(self):
                self.performance_monitor = mock_performance_monitor

        service = MockACPService()

        # Test async function
        result = asyncio.run(test_acp_operation(service, "test_param"))

        assert result["result"] == "processed_test_param"
        mock_performance_monitor.record_acp_operation.assert_called_once()

        # Check the call arguments
        call_args = mock_performance_monitor.record_acp_operation.call_args
        assert call_args[0][0] == "test_service"  # service
        assert call_args[0][1] == "test_operation"  # operation
        assert call_args[0][2] >= 0  # duration_ms (can be 0 for very fast operations)
        assert call_args[0][3] is True  # success
        assert call_args[0][5] == {"count": 1}  # metadata

    def test_monitor_operation_context_manager(self, mock_performance_monitor):
        """Test operation monitoring context manager."""

        async def test_context_manager():
            async with monitor_operation(
                mock_performance_monitor, "test_service", "test_operation"
            ):
                await asyncio.sleep(0.01)  # Simulate some work
                return "success"

        result = asyncio.run(test_context_manager())

        assert result == "success"
        mock_performance_monitor.record_acp_operation.assert_called_once()

        # Check the call arguments
        call_args = mock_performance_monitor.record_acp_operation.call_args
        assert call_args[0][0] == "test_service"  # service
        assert call_args[0][1] == "test_operation"  # operation
        assert call_args[0][2] >= 0  # duration_ms (can be 0 for very fast operations)
        assert call_args[0][3] is True  # success

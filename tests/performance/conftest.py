"""
Performance test configuration and fixtures.

This module provides shared configuration and fixtures for performance tests.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

import pytest


class PerformanceTestConfig:
    """Configuration for performance tests."""

    # Performance thresholds (in seconds)
    BASIC_OPERATIONS_THRESHOLD = 5.0
    BATCH_OPERATIONS_THRESHOLD = 3.0
    CONCURRENT_OPERATIONS_THRESHOLD = 3.0
    CACHE_WARMING_THRESHOLD = 2.0
    COMPRESSION_THRESHOLD = 0.1
    END_TO_END_THRESHOLD = 10.0

    # Load test parameters
    BASIC_OPERATIONS_COUNT = 1000
    BATCH_OPERATIONS_COUNT = 1000
    CONCURRENT_OPERATIONS_COUNT = 500
    CACHE_WARMING_COUNT = 50
    MEMORY_LOAD_COUNT = 100

    # Performance expectations
    MIN_BATCH_SPEEDUP = 1.5
    MAX_MONITORING_OVERHEAD = 0.5
    MIN_CACHE_HIT_RATIO = 0.5
    MAX_COMPRESSION_RATIO = 0.8


@pytest.fixture(scope="session")
def performance_config():
    """Return performance test configuration."""
    return PerformanceTestConfig()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


class PerformanceMetrics:
    """Collect and analyze performance metrics."""

    def __init__(self) -> None:
        """Initialize the performance collector."""
        self.metrics: Dict[str, List[float]] = {}
        self.start_times: Dict[str, float] = {}

    def start_timer(self, name: str) -> None:
        """Start a performance timer."""
        self.start_times[name] = time.time()

    def end_timer(self, name: str) -> float:
        """End a performance timer and return duration."""
        if name not in self.start_times:
            raise ValueError(f"Timer '{name}' was not started")

        duration = time.time() - self.start_times[name]

        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(duration)

        return duration

    def get_average(self, name: str) -> float:
        """Get average time for a metric."""
        if name not in self.metrics or not self.metrics[name]:
            return 0.0
        return sum(self.metrics[name]) / len(self.metrics[name])

    def get_min(self, name: str) -> float:
        """Get minimum time for a metric."""
        if name not in self.metrics or not self.metrics[name]:
            return 0.0
        return min(self.metrics[name])

    def get_max(self, name: str) -> float:
        """Get maximum time for a metric."""
        if name not in self.metrics or not self.metrics[name]:
            return 0.0
        return max(self.metrics[name])

    def get_summary(self) -> Dict[str, Dict[str, float]]:
        """Get performance summary."""
        summary = {}
        for name, times in self.metrics.items():
            summary[name] = {
                "count": len(times),
                "average": self.get_average(name),
                "min": self.get_min(name),
                "max": self.get_max(name),
                "total": sum(times),
            }
        return summary


@pytest.fixture
def perf_metrics():
    """Return performance metrics collector."""
    return PerformanceMetrics()


def pytest_configure(config):
    """Configure pytest for performance tests."""
    # Add custom markers
    config.addinivalue_line("markers", "performance: mark test as a performance test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "benchmark: mark test as a benchmark")


def pytest_collection_modifyitems(config, items):
    """Modify test collection for performance tests."""
    for item in items:
        # Add performance marker to all tests in performance directory
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)

        # Add slow marker to benchmark tests
        if "benchmark" in item.name:
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.benchmark)


class PerformanceAssertions:
    """Custom assertions for performance tests."""

    @staticmethod
    def assert_operation_time(
        actual_time: float, expected_max: float, operation_name: str
    ):
        """Assert operation time is within expected limits."""
        assert (
            actual_time <= expected_max
        ), f"{operation_name} took {actual_time:.3f}s, expected <= {expected_max:.3f}s"

    @staticmethod
    def assert_speedup(actual_speedup: float, expected_min: float, operation_name: str):
        """Assert speedup meets minimum requirements."""
        assert actual_speedup >= expected_min, (
            f"{operation_name} speedup was {actual_speedup:.2f}x, "
            f"expected >= {expected_min:.2f}x"
        )

    @staticmethod
    def assert_overhead(
        actual_overhead: float, expected_max: float, operation_name: str
    ):
        """Assert overhead is within acceptable limits."""
        assert actual_overhead <= expected_max, (
            f"{operation_name} overhead was {actual_overhead:.2%}, "
            f"expected <= {expected_max:.2%}"
        )

    @staticmethod
    def assert_throughput(
        actual_ops: int,
        actual_time: float,
        expected_min_ops_per_sec: float,
        operation_name: str,
    ):
        """Assert throughput meets minimum requirements."""
        ops_per_sec = actual_ops / actual_time if actual_time > 0 else 0
        assert ops_per_sec >= expected_min_ops_per_sec, (
            f"{operation_name} throughput was {ops_per_sec:.0f} ops/sec, "
            f"expected >= {expected_min_ops_per_sec:.0f} ops/sec"
        )


@pytest.fixture
def perf_assertions():
    """Return performance assertions helper."""
    return PerformanceAssertions()


# Performance test data generators
class TestDataGenerator:
    """Generate test data for performance tests."""

    @staticmethod
    def generate_key_value_pairs(
        count: int, key_prefix: str = "test", value_size: int = 100
    ) -> List[tuple]:
        """Generate key-value pairs for testing."""
        return [(f"{key_prefix}_{i}", "x" * value_size) for i in range(count)]

    @staticmethod
    def generate_large_data(size: int) -> Dict[str, Any]:
        """Generate large data structure for testing."""
        return {
            "data": "x" * size,
            "numbers": list(range(size // 10)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "nested": {
                "deep_data": "y" * (size // 2),
                "more_data": list(range(size // 20)),
            },
        }

    @staticmethod
    def generate_access_patterns(count: int, key_count: int = 10) -> List[str]:
        """Generate access patterns for cache optimization testing."""
        import random

        return [f"pattern_key_{random.randint(0, key_count - 1)}" for _ in range(count)]


@pytest.fixture
def test_data_generator():
    """Test data generator."""
    return TestDataGenerator()


# Performance test utilities
class PerformanceUtils:
    """Utilities for performance testing."""

    @staticmethod
    async def measure_operation_time(coro, operation_name: str = "operation") -> float:
        """Measure the time taken by an async operation."""
        start_time = time.time()
        await coro
        duration = time.time() - start_time
        print(f"{operation_name}: {duration:.3f}s")
        return duration

    @staticmethod
    async def run_concurrent_operations(
        operations: List[Callable], max_concurrent: int = 100
    ) -> List[Any]:
        """Run operations concurrently with a limit."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_with_semaphore(operation):
            async with semaphore:
                return await operation()

        tasks = [run_with_semaphore(op) for op in operations]
        return await asyncio.gather(*tasks)

    @staticmethod
    def calculate_performance_metrics(times: List[float]) -> Dict[str, float]:
        """Calculate performance metrics from a list of times."""
        if not times:
            return {}

        return {
            "count": len(times),
            "total": sum(times),
            "average": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "median": sorted(times)[len(times) // 2],
        }


@pytest.fixture
def perf_utils():
    """Return performance utilities."""
    return PerformanceUtils()

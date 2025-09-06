"""
ACP service performance metrics collection.

This module provides metrics collection for ACP services including
agent registry, workflow engine, and message router performance.
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ...logging import get_logger

logger = get_logger(__name__)


@dataclass
class ACPOperationMetrics:
    """Metrics for an ACP service operation."""

    service: str
    operation: str
    duration_ms: float
    success: bool
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ACPPerformanceSnapshot:
    """Snapshot of ACP service performance metrics."""

    timestamp: datetime
    total_operations: int
    successful_operations: int
    failed_operations: int
    average_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    operations_per_second: float
    service_breakdown: Dict[str, Dict[str, Any]]
    error_breakdown: Dict[str, int]
    health_score: float


class ACPMetricsCollector:
    """Collects and analyzes ACP service performance metrics."""

    def __init__(self, window_size: int = 1000):
        """
        Initialize ACP metrics collector.

        Args:
            window_size: Number of operations to keep in sliding window
        """
        self.window_size = window_size
        self.operation_history: deque = deque(maxlen=window_size)
        self.service_counts: Dict[str, int] = defaultdict(int)
        self.operation_counts: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.latency_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # Performance tracking
        self.start_time = datetime.now(timezone.utc)
        self.last_snapshot_time = self.start_time

        # Service-specific metrics
        self.agent_registry_metrics = {
            "registered_agents": 0,
            "active_agents": 0,
            "health_check_failures": 0,
            "discovery_operations": 0,
        }

        self.workflow_engine_metrics = {
            "active_workflows": 0,
            "completed_workflows": 0,
            "failed_workflows": 0,
            "total_steps_executed": 0,
            "average_workflow_duration_ms": 0,
        }

        self.message_router_metrics = {
            "messages_routed": 0,
            "routing_failures": 0,
            "average_routing_latency_ms": 0,
            "queue_depth": 0,
        }

    def record_operation(
        self,
        service: str,
        operation: str,
        duration_ms: float,
        success: bool,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an ACP service operation for metrics collection."""
        metrics = ACPOperationMetrics(
            service=service,
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            error=error,
            metadata=metadata or {},
        )

        # Add to history
        self.operation_history.append(metrics)

        # Update counters
        self.service_counts[service] += 1
        self.operation_counts[f"{service}.{operation}"] += 1
        if not success and error:
            self.error_counts[error] += 1

        # Update latency history
        self.latency_history[f"{service}.{operation}"].append(duration_ms)

    def update_agent_registry_metrics(self, **kwargs: Any) -> None:
        """Update agent registry specific metrics."""
        for key, value in kwargs.items():
            if key in self.agent_registry_metrics:
                self.agent_registry_metrics[key] = value

    def update_workflow_engine_metrics(self, **kwargs: Any) -> None:
        """Update workflow engine specific metrics."""
        for key, value in kwargs.items():
            if key in self.workflow_engine_metrics:
                self.workflow_engine_metrics[key] = value

    def update_message_router_metrics(self, **kwargs: Any) -> None:
        """Update message router specific metrics."""
        for key, value in kwargs.items():
            if key in self.message_router_metrics:
                self.message_router_metrics[key] = value

    def get_performance_snapshot(self) -> ACPPerformanceSnapshot:
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

        # Calculate operations per second
        time_diff = (now - self.last_snapshot_time).total_seconds()
        ops_per_second = total_ops / time_diff if time_diff > 0 else 0

        # Get service breakdown
        service_breakdown = self.get_service_breakdown()

        # Get error breakdown
        error_breakdown = dict(self.error_counts)

        # Calculate health score
        health_score = self._calculate_health_score()

        snapshot = ACPPerformanceSnapshot(
            timestamp=now,
            total_operations=total_ops,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            average_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            operations_per_second=ops_per_second,
            service_breakdown=service_breakdown,
            error_breakdown=error_breakdown,
            health_score=health_score,
        )

        self.last_snapshot_time = now
        return snapshot

    def get_service_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get breakdown of operations by service."""
        breakdown = {}

        for service in self.service_counts:
            service_operations = [
                op for op in self.operation_history if op.service == service
            ]

            if service_operations:
                latencies = [op.duration_ms for op in service_operations]
                successful = sum(1 for op in service_operations if op.success)

                breakdown[service] = {
                    "count": len(service_operations),
                    "successful": successful,
                    "failed": len(service_operations) - successful,
                    "success_rate": successful / len(service_operations),
                    "avg_latency_ms": sum(latencies) / len(latencies),
                    "min_latency_ms": min(latencies),
                    "max_latency_ms": max(latencies),
                    "p95_latency_ms": self._calculate_percentile(sorted(latencies), 95),
                    "p99_latency_ms": self._calculate_percentile(sorted(latencies), 99),
                }

        return breakdown

    def get_operation_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get breakdown of operations by type."""
        breakdown = {}

        for operation in self.operation_counts:
            operation_metrics = [
                op
                for op in self.operation_history
                if f"{op.service}.{op.operation}" == operation
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

    def get_top_slow_operations(self, limit: int = 10) -> List[ACPOperationMetrics]:
        """Get top slowest operations."""
        return sorted(
            self.operation_history, key=lambda x: x.duration_ms, reverse=True
        )[:limit]

    def get_recent_errors(self, limit: int = 10) -> List[ACPOperationMetrics]:
        """Get recent failed operations."""
        errors = [op for op in self.operation_history if not op.success]
        return sorted(errors, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_service_health(self) -> Dict[str, float]:
        """Get health scores for each service."""
        service_health = {}

        for service in self.service_counts:
            service_operations = [
                op for op in self.operation_history if op.service == service
            ]

            if service_operations:
                success_rate = sum(1 for op in service_operations if op.success) / len(
                    service_operations
                )
                avg_latency = sum(op.duration_ms for op in service_operations) / len(
                    service_operations
                )
                latency_score = max(
                    0, 1.0 - (avg_latency / 1000)
                )  # Penalize > 1s latency

                health_score = (success_rate * 0.7 + latency_score * 0.3) * 100
                service_health[service] = min(100, max(0, health_score))
            else:
                service_health[service] = 100.0

        return service_health

    def _calculate_percentile(
        self, sorted_values: List[float], percentile: int
    ) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]

    def _calculate_health_score(self) -> float:
        """Calculate overall ACP health score (0-100)."""
        if not self.operation_history:
            return 100.0

        # Calculate success rate
        success_rate = sum(1 for op in self.operation_history if op.success) / len(
            self.operation_history
        )

        # Calculate average latency
        avg_latency = sum(op.duration_ms for op in self.operation_history) / len(
            self.operation_history
        )
        latency_score = max(0, 1.0 - (avg_latency / 1000))  # Penalize > 1s latency

        # Calculate service diversity (more services = better)
        service_diversity = min(
            1.0, len(self.service_counts) / 3
        )  # Normalize to 3 services

        # Weighted average
        health_score: float = (
            success_rate * 0.5 + latency_score * 0.3 + service_diversity * 0.2
        ) * 100

        return min(100, max(0, health_score))

    def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        self.operation_history.clear()
        self.service_counts.clear()
        self.operation_counts.clear()
        self.error_counts.clear()
        for latency_deque in self.latency_history.values():
            latency_deque.clear()
        self.start_time = datetime.now(timezone.utc)
        self.last_snapshot_time = self.start_time
        logger.info("ACP metrics reset")

    def get_agent_registry_metrics(self) -> Dict[str, Any]:
        """Get agent registry specific metrics."""
        return dict(self.agent_registry_metrics)

    def get_workflow_engine_metrics(self) -> Dict[str, Any]:
        """Get workflow engine specific metrics."""
        return dict(self.workflow_engine_metrics)

    def get_message_router_metrics(self) -> Dict[str, Any]:
        """Get message router specific metrics."""
        return dict(self.message_router_metrics)

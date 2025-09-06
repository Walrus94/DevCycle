"""
ACP Monitoring System - Kibana Compatible.

This module provides monitoring and metrics collection for ACP agents
with structured logging compatible with Kibana/ELK stack.
"""

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from devcycle.core.acp.models import ACPResponse
from devcycle.core.acp.services.agent_registry import ACPAgentRegistry
from devcycle.core.acp.services.message_router import ACPMessageRouter


class LogLevel(str, Enum):
    """Log levels for structured logging."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ACPMetric:
    """Structured metric for ACP monitoring."""

    timestamp: str
    metric_name: str
    metric_value: float
    metric_unit: str
    agent_id: Optional[str] = None
    workflow_id: Optional[str] = None
    tags: Optional[Dict[str, str]] = None

    def to_kibana_format(self) -> Dict[str, Any]:
        """Convert to Kibana-compatible format."""
        return {
            "@timestamp": self.timestamp,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "metric_unit": self.metric_unit,
            "agent_id": self.agent_id,
            "workflow_id": self.workflow_id,
            "tags": self.tags or {},
            "service": "acp",
            "environment": "production",
        }


@dataclass
class ACPEvent:
    """Structured event for ACP monitoring."""

    timestamp: str
    event_type: str
    event_category: str
    message: str
    agent_id: Optional[str] = None
    workflow_id: Optional[str] = None
    severity: str = "INFO"
    metadata: Optional[Dict[str, Any]] = None

    def to_kibana_format(self) -> Dict[str, Any]:
        """Convert to Kibana-compatible format."""
        return {
            "@timestamp": self.timestamp,
            "event_type": self.event_type,
            "event_category": self.event_category,
            "message": self.message,
            "agent_id": self.agent_id,
            "workflow_id": self.workflow_id,
            "severity": self.severity,
            "metadata": self.metadata or {},
            "service": "acp",
            "environment": "production",
        }


class ACPKibanaLogger:
    """Kibana-compatible logger for ACP events and metrics."""

    def __init__(self, log_file: str = "/var/log/acp/acp.log"):
        """Initialize the Kibana logger."""
        self.log_file = log_file
        self._ensure_log_directory()

    def _ensure_log_directory(self) -> None:
        """Ensure log directory exists."""
        import os

        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def log_metric(self, metric: ACPMetric) -> None:
        """Log a metric in Kibana-compatible format."""
        log_entry = {"type": "metric", **metric.to_kibana_format()}
        self._write_log(log_entry)

    def log_event(self, event: ACPEvent) -> None:
        """Log an event in Kibana-compatible format."""
        log_entry = {"type": "event", **event.to_kibana_format()}
        self._write_log(log_entry)

    def _write_log(self, log_entry: Dict[str, Any]) -> None:
        """Write structured log entry."""
        with open(self.log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")


class ACPMonitor:
    """ACP system monitoring with Kibana compatibility."""

    def __init__(
        self, agent_registry: ACPAgentRegistry, message_router: ACPMessageRouter
    ):
        """Initialize the ACP monitor."""
        self.agent_registry = agent_registry
        self.message_router = message_router
        self.logger = ACPKibanaLogger()
        self.metrics_history: List[ACPMetric] = []
        self.events_history: List[ACPEvent] = []

        # Performance counters
        self.message_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.start_time = time.time()

    async def collect_agent_metrics(self) -> Dict[str, Any]:
        """Collect agent-specific metrics."""
        agents = list(self.agent_registry.agents.values())
        health_status = await self.agent_registry.health_check_all()

        # Calculate agent metrics
        total_agents = len(agents)
        active_agents = sum(1 for status in health_status.values() if status)
        offline_agents = total_agents - active_agents

        # Log agent metrics
        agent_metric = ACPMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_name="agent_count",
            metric_value=total_agents,
            metric_unit="count",
            tags={"status": "total"},
        )
        self.logger.log_metric(agent_metric)

        active_metric = ACPMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_name="agent_count",
            metric_value=active_agents,
            metric_unit="count",
            tags={"status": "active"},
        )
        self.logger.log_metric(active_metric)

        # Log agent health events
        for agent_id, is_healthy in health_status.items():
            event = ACPEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="agent_health_check",
                event_category="health",
                message=(
                    f"Agent {agent_id} health check: "
                    f"{'healthy' if is_healthy else 'unhealthy'}"
                ),
                agent_id=agent_id,
                severity="INFO" if is_healthy else "WARNING",
            )
            self.logger.log_event(event)

        return {
            "total_agents": total_agents,
            "active_agents": active_agents,
            "offline_agents": offline_agents,
            "health_status": health_status,
        }

    async def collect_message_metrics(self) -> Dict[str, Any]:
        """Collect message processing metrics."""
        # Calculate message processing rate
        current_time = time.time()
        uptime = current_time - self.start_time
        message_rate = self.message_count / uptime if uptime > 0 else 0

        # Calculate average response time
        avg_response_time = (
            self.total_response_time / self.message_count
            if self.message_count > 0
            else 0
        )

        # Calculate error rate
        error_rate = (
            self.error_count / self.message_count if self.message_count > 0 else 0
        )

        # Log message metrics
        rate_metric = ACPMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_name="message_processing_rate",
            metric_value=message_rate,
            metric_unit="messages_per_second",
        )
        self.logger.log_metric(rate_metric)

        response_time_metric = ACPMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_name="average_response_time",
            metric_value=avg_response_time,
            metric_unit="milliseconds",
        )
        self.logger.log_metric(response_time_metric)

        error_rate_metric = ACPMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_name="error_rate",
            metric_value=error_rate,
            metric_unit="percentage",
        )
        self.logger.log_metric(error_rate_metric)

        return {
            "total_messages": self.message_count,
            "error_count": self.error_count,
            "message_rate": message_rate,
            "average_response_time": avg_response_time,
            "error_rate": error_rate,
        }

    async def collect_workflow_metrics(self) -> Dict[str, Any]:
        """Collect workflow execution metrics."""
        # This would integrate with the workflow engine
        # For now, return placeholder metrics
        workflow_metric = ACPMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_name="active_workflows",
            metric_value=0,  # Would be actual count from workflow engine
            metric_unit="count",
        )
        self.logger.log_metric(workflow_metric)

        return {"active_workflows": 0, "completed_workflows": 0, "failed_workflows": 0}

    async def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect overall system metrics."""
        import psutil

        # System resource metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Log system metrics
        cpu_metric = ACPMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_name="cpu_usage",
            metric_value=cpu_percent,
            metric_unit="percentage",
        )
        self.logger.log_metric(cpu_metric)

        memory_metric = ACPMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_name="memory_usage",
            metric_value=memory.percent,
            metric_unit="percentage",
        )
        self.logger.log_metric(memory_metric)

        return {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_available": memory.available,
            "disk_usage": disk.percent,
            "disk_free": disk.free,
        }

    async def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all ACP system metrics."""
        agent_metrics = await self.collect_agent_metrics()
        message_metrics = await self.collect_message_metrics()
        workflow_metrics = await self.collect_workflow_metrics()
        system_metrics = await self.collect_system_metrics()

        # Log overall health status
        overall_health = (
            "healthy" if message_metrics["error_rate"] < 0.1 else "degraded"
        )

        health_event = ACPEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="system_health_check",
            event_category="health",
            message=f"System health: {overall_health}",
            severity="INFO" if overall_health == "healthy" else "WARNING",
        )
        self.logger.log_event(health_event)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_health": overall_health,
            "agents": agent_metrics,
            "messages": message_metrics,
            "workflows": workflow_metrics,
            "system": system_metrics,
        }

    def record_message_processed(
        self, response: ACPResponse, processing_time_ms: float
    ) -> None:
        """Record a processed message for metrics."""
        self.message_count += 1
        self.total_response_time += processing_time_ms

        if not response.success:
            self.error_count += 1

        # Log message processing event
        event = ACPEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="message_processed",
            event_category="message",
            message=f"Message processed in {processing_time_ms:.2f}ms",
            severity="ERROR" if not response.success else "INFO",
            metadata={
                "success": response.success,
                "processing_time_ms": processing_time_ms,
                "message_id": getattr(response, "message_id", None),
            },
        )
        self.logger.log_event(event)

    def record_agent_event(
        self, agent_id: str, event_type: str, message: str, severity: str = "INFO"
    ) -> None:
        """Record an agent-specific event."""
        event = ACPEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            event_category="agent",
            message=message,
            agent_id=agent_id,
            severity=severity,
        )
        self.logger.log_event(event)

    def get_kibana_dashboard_config(self) -> Dict[str, Any]:
        """Get Kibana dashboard configuration for ACP monitoring."""
        return {
            "title": "ACP System Monitoring",
            "description": "Real-time monitoring of ACP agents and workflows",
            "panels": [
                {
                    "title": "Agent Health Status",
                    "type": "metric",
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"service": "acp"}},
                                {"term": {"metric_name": "agent_count"}},
                            ]
                        }
                    },
                    "visualization": "bar_chart",
                },
                {
                    "title": "Message Processing Rate",
                    "type": "metric",
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"service": "acp"}},
                                {"term": {"metric_name": "message_processing_rate"}},
                            ]
                        }
                    },
                    "visualization": "line_chart",
                },
                {
                    "title": "Error Rate",
                    "type": "metric",
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"service": "acp"}},
                                {"term": {"metric_name": "error_rate"}},
                            ]
                        }
                    },
                    "visualization": "gauge",
                },
                {
                    "title": "System Events",
                    "type": "event",
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"service": "acp"}},
                                {"term": {"type": "event"}},
                            ]
                        }
                    },
                    "visualization": "data_table",
                },
            ],
        }

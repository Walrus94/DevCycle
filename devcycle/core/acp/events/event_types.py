"""ACP Event types and data structures for real-time event streaming."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field


class ACPEventType(str, Enum):
    """Types of ACP events that can be published."""

    # Agent Events
    AGENT_STATUS_CHANGED = "agent_status_changed"
    AGENT_HEARTBEAT = "agent_heartbeat"
    AGENT_REGISTERED = "agent_registered"
    AGENT_UNREGISTERED = "agent_unregistered"
    AGENT_HEALTH_CHECK_FAILED = "agent_health_check_failed"

    # Workflow Events
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_STEP_COMPLETED = "workflow_step_completed"
    WORKFLOW_STEP_FAILED = "workflow_step_failed"
    WORKFLOW_PROGRESS = "workflow_progress"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"

    # System Events
    SYSTEM_HEALTH_UPDATE = "system_health_update"
    PERFORMANCE_METRICS = "performance_metrics"
    CACHE_HIT_RATIO = "cache_hit_ratio"
    ERROR_ALERT = "error_alert"

    # Message Events
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_FAILED = "message_failed"


class ACPEvent(BaseModel):
    """Base ACP event structure."""

    event_type: ACPEventType = Field(..., description="Type of event")
    event_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp",
    )
    source: str = Field(
        ..., description="Source of the event (agent_id, workflow_id, etc.)"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Event-specific data"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional event metadata"
    )

    model_config = {"use_enum_values": True}


class AgentStatusEvent(ACPEvent):
    """Event for agent status changes."""

    event_type: ACPEventType = ACPEventType.AGENT_STATUS_CHANGED

    def __init__(self, agent_id: str, old_status: str, new_status: str, **kwargs: Any):
        """Initialize agent status changed event."""
        timestamp = datetime.now(timezone.utc).timestamp()
        super().__init__(
            event_id=f"agent_status_{agent_id}_{timestamp}",
            source=agent_id,
            data={
                "agent_id": agent_id,
                "old_status": old_status,
                "new_status": new_status,
            },
            **kwargs,
        )


class WorkflowProgressEvent(ACPEvent):
    """Event for workflow progress updates."""

    event_type: ACPEventType = ACPEventType.WORKFLOW_PROGRESS

    def __init__(self, workflow_id: str, step_id: str, progress: int, **kwargs: Any):
        """Initialize workflow progress event."""
        timestamp = datetime.now(timezone.utc).timestamp()
        super().__init__(
            event_id=f"workflow_progress_{workflow_id}_{step_id}_{timestamp}",
            source=workflow_id,
            data={
                "workflow_id": workflow_id,
                "step_id": step_id,
                "progress": progress,
                "percentage": min(100, max(0, progress)),
            },
            **kwargs,
        )


class SystemHealthEvent(ACPEvent):
    """Event for system health updates."""

    event_type: ACPEventType = ACPEventType.SYSTEM_HEALTH_UPDATE

    def __init__(
        self, component: str, status: str, metrics: Dict[str, Any], **kwargs: Any
    ):
        """Initialize system health update event."""
        timestamp = datetime.now(timezone.utc).timestamp()
        super().__init__(
            event_id=f"system_health_{component}_{timestamp}",
            source=component,
            data={"component": component, "status": status, "metrics": metrics},
            **kwargs,
        )

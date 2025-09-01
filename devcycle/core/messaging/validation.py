"""
Message validation models for DevCycle.

This module defines the Pydantic models for validating message requests,
including request models, validation configuration, and validation results.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from ..protocols.message import AgentAction, AgentEvent, MessageType


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool
    errors: List[str]
    warnings: Optional[List[str]] = None

    def __post_init__(self) -> None:
        """Post-initialization validation."""
        if self.warnings is None:
            self.warnings = []


class MessageSendRequest(BaseModel):
    """Request model for sending a single message."""

    agent_id: str = Field(
        ..., min_length=1, max_length=100, description="Target agent ID"
    )
    action: str = Field(
        ..., min_length=1, max_length=200, description="Action to perform"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Message data payload"
    )
    priority: Optional[str] = Field(
        None, pattern="^(low|normal|high|urgent)$", description="Message priority level"
    )
    ttl: Optional[int] = Field(
        None, ge=0, le=86400, description="Time to live in seconds (0-24 hours)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata for the message"
    )

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Validate that the action is a known action."""
        known_actions = [action.value for action in AgentAction] + [
            event.value for event in AgentEvent
        ]
        if v not in known_actions:
            # Allow custom actions but log them
            return v
        return v

    @field_validator("data")
    @classmethod
    def validate_data_size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data size (basic check)."""
        # This is a basic check - more comprehensive validation will be done in
        # middleware
        if len(str(v)) > 1024 * 1024:  # 1MB limit
            raise ValueError("Data payload too large")
        return v


class MessageBroadcastRequest(BaseModel):
    """Request model for broadcasting messages to multiple agents."""

    agent_types: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of agent types to broadcast to",
    )
    action: str = Field(
        ..., min_length=1, max_length=200, description="Action to perform"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Message data payload"
    )
    exclude_agent_ids: Optional[List[str]] = Field(
        None, description="Agent IDs to exclude from broadcast"
    )

    @field_validator("agent_types")
    @classmethod
    def validate_agent_types(cls, v: List[str]) -> List[str]:
        """Validate agent types."""
        valid_types = [
            "business_analyst",
            "developer",
            "tester",
            "deployer",
            "monitor",
            "custom",
        ]
        for agent_type in v:
            if agent_type not in valid_types:
                raise ValueError(f"Invalid agent type: {agent_type}")
        return v


class MessageRouteRequest(BaseModel):
    """Request model for routing messages based on capabilities."""

    capabilities: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Required capabilities for message routing",
    )
    action: str = Field(
        ..., min_length=1, max_length=200, description="Action to perform"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Message data payload"
    )
    load_balancing: Optional[str] = Field(
        None,
        pattern="^(round_robin|least_busy|random)$",
        description="Load balancing strategy",
    )

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, v: List[str]) -> List[str]:
        """Validate capabilities."""
        valid_capabilities = [
            "text_processing",
            "code_generation",
            "testing",
            "deployment",
            "monitoring",
            "analysis",
            "planning",
        ]
        for capability in v:
            if capability not in valid_capabilities:
                raise ValueError(f"Invalid capability: {capability}")
        return v


class MessageValidationConfig(BaseModel):
    """Configuration for message validation."""

    max_message_size_bytes: int = Field(
        default=1024 * 1024,
        ge=1024,
        le=10 * 1024 * 1024,
        description="Maximum message size in bytes (1MB-10MB)",
    )
    max_data_size_bytes: int = Field(
        default=512 * 1024,
        ge=512,
        le=5 * 1024 * 1024,
        description="Maximum data payload size in bytes (512KB-5MB)",
    )
    allowed_actions: List[str] = Field(
        default_factory=list,
        description="List of allowed actions (empty means all allowed)",
    )
    required_agent_online: bool = Field(
        default=True, description="Whether to require target agent to be online"
    )
    validate_agent_capabilities: bool = Field(
        default=True, description="Whether to validate agent capabilities"
    )
    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum number of retry attempts"
    )
    enable_warnings: bool = Field(
        default=True, description="Whether to generate validation warnings"
    )

    @field_validator("allowed_actions")
    @classmethod
    def validate_allowed_actions(cls, v: List[str]) -> List[str]:
        """Validate allowed actions list."""
        if v:
            known_actions = [action.value for action in AgentAction] + [
                event.value for event in AgentEvent
            ]
            for action in v:
                if action not in known_actions:
                    # Allow custom actions in allowed list
                    pass
        return v


class MessageHistoryRequest(BaseModel):
    """Request model for retrieving message history."""

    agent_id: Optional[str] = Field(None, description="Filter by agent ID")
    message_type: Optional[str] = Field(None, description="Filter by message type")
    status: Optional[str] = Field(None, description="Filter by message status")
    limit: int = Field(
        default=100, ge=1, le=1000, description="Maximum number of messages"
    )
    offset: int = Field(default=0, ge=0, description="Number of messages to skip")

    @field_validator("message_type")
    @classmethod
    def validate_message_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate message type."""
        if v is not None:
            valid_types = [msg_type.value for msg_type in MessageType]
            if v not in valid_types:
                raise ValueError(f"Invalid message type: {v}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate message status."""
        if v is not None:
            valid_statuses = [
                "pending",
                "in_progress",
                "completed",
                "failed",
                "stopped",
                "retrying",
                "timeout",
                "cancelled",
            ]
            if v not in valid_statuses:
                raise ValueError(f"Invalid status: {v}")
        return v


class QueueStatusRequest(BaseModel):
    """Request model for queue status queries."""

    include_details: bool = Field(
        default=False, description="Whether to include detailed queue information"
    )
    include_metrics: bool = Field(
        default=True, description="Whether to include queue metrics"
    )


class MessageRetryRequest(BaseModel):
    """Request model for retrying failed messages."""

    max_retries: Optional[int] = Field(
        None, ge=1, le=10, description="Maximum retry attempts for this retry"
    )
    delay_seconds: Optional[int] = Field(
        None, ge=0, le=3600, description="Delay before retry in seconds"
    )
    priority: Optional[str] = Field(
        None,
        pattern="^(low|normal|high|urgent)$",
        description="Priority for the retry attempt",
    )

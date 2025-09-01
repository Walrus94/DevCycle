"""
Message response models for DevCycle.

This module defines the response models for message handling endpoints,
including message responses, history responses, and queue status responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..protocols.message import MessageStatus, MessageType


class MessageResponse(BaseModel):
    """Response model for message operations."""

    message_id: str = Field(..., description="Unique message identifier")
    agent_id: str = Field(..., description="Target agent ID")
    action: str = Field(..., description="Action performed")
    status: MessageStatus = Field(..., description="Current message status")
    created_at: datetime = Field(..., description="Message creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    data: Optional[Dict[str, Any]] = Field(None, description="Message data payload")
    priority: Optional[str] = Field(None, description="Message priority")
    ttl: Optional[int] = Field(None, description="Time to live in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retry attempts")


class MessageHistoryResponse(BaseModel):
    """Response model for message history queries."""

    message_id: str = Field(..., description="Unique message identifier")
    agent_id: str = Field(..., description="Target agent ID")
    action: str = Field(..., description="Action performed")
    message_type: MessageType = Field(..., description="Type of message")
    status: MessageStatus = Field(..., description="Current message status")
    created_at: datetime = Field(..., description="Message creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    execution_time_ms: Optional[int] = Field(
        None, description="Execution time in milliseconds"
    )
    data_size_bytes: int = Field(..., description="Size of message data in bytes")
    priority: Optional[str] = Field(None, description="Message priority")
    error: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retry attempts")


class MessageDetailResponse(BaseModel):
    """Detailed response model for a specific message."""

    message_id: str = Field(..., description="Unique message identifier")
    agent_id: str = Field(..., description="Target agent ID")
    action: str = Field(..., description="Action performed")
    message_type: MessageType = Field(..., description="Type of message")
    status: MessageStatus = Field(..., description="Current message status")
    created_at: datetime = Field(..., description="Message creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    execution_time_ms: Optional[int] = Field(
        None, description="Execution time in milliseconds"
    )
    data: Dict[str, Any] = Field(..., description="Message data payload")
    data_size_bytes: int = Field(..., description="Size of message data in bytes")
    priority: Optional[str] = Field(None, description="Message priority")
    ttl: Optional[int] = Field(None, description="Time to live in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    queue_position: Optional[int] = Field(None, description="Position in queue")
    processing_started_at: Optional[datetime] = Field(
        None, description="Processing start timestamp"
    )


class QueueStatusResponse(BaseModel):
    """Response model for queue status queries."""

    queue_name: str = Field(..., description="Name of the queue")
    total_messages: int = Field(..., description="Total messages in queue")
    pending_messages: int = Field(..., description="Messages waiting to be processed")
    processing_messages: int = Field(
        ..., description="Messages currently being processed"
    )
    completed_messages: int = Field(..., description="Successfully completed messages")
    failed_messages: int = Field(..., description="Failed messages")
    retry_messages: int = Field(..., description="Messages waiting for retry")
    average_processing_time_ms: Optional[int] = Field(
        None, description="Average processing time"
    )
    queue_health: str = Field(..., description="Queue health status")
    last_activity: datetime = Field(..., description="Last queue activity timestamp")
    metrics: Optional[Dict[str, Any]] = Field(
        None, description="Additional queue metrics"
    )


class MessageBroadcastResponse(BaseModel):
    """Response model for message broadcast operations."""

    broadcast_id: str = Field(..., description="Unique broadcast identifier")
    total_agents: int = Field(..., description="Total number of target agents")
    successful_sends: int = Field(..., description="Number of successful message sends")
    failed_sends: int = Field(..., description="Number of failed message sends")
    skipped_agents: int = Field(..., description="Number of agents skipped")
    message_ids: List[str] = Field(..., description="List of created message IDs")
    created_at: datetime = Field(..., description="Broadcast creation timestamp")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Detailed results per agent"
    )


class MessageRouteResponse(BaseModel):
    """Response model for message routing operations."""

    message_id: str = Field(..., description="Unique message identifier")
    selected_agent_id: str = Field(..., description="ID of the selected agent")
    routing_strategy: str = Field(..., description="Routing strategy used")
    available_agents: int = Field(
        ..., description="Number of available agents considered"
    )
    agent_capabilities: List[str] = Field(
        ..., description="Capabilities of selected agent"
    )
    agent_load: Dict[str, Any] = Field(
        ..., description="Load information of selected agent"
    )
    routing_reason: str = Field(..., description="Reason for agent selection")
    created_at: datetime = Field(..., description="Routing timestamp")


class MessageRetryResponse(BaseModel):
    """Response model for message retry operations."""

    message_id: str = Field(..., description="Unique message identifier")
    retry_attempt: int = Field(..., description="Current retry attempt number")
    max_retries: int = Field(..., description="Maximum retry attempts")
    retry_delay_seconds: Optional[int] = Field(None, description="Delay before retry")
    original_error: Optional[str] = Field(None, description="Original error message")
    retry_reason: str = Field(..., description="Reason for retry")
    scheduled_at: datetime = Field(..., description="Scheduled retry timestamp")
    status: MessageStatus = Field(..., description="Updated message status")


class MessageCancelResponse(BaseModel):
    """Response model for message cancellation operations."""

    message_id: str = Field(..., description="Unique message identifier")
    cancelled: bool = Field(..., description="Whether cancellation was successful")
    previous_status: MessageStatus = Field(
        ..., description="Status before cancellation"
    )
    cancellation_reason: Optional[str] = Field(
        None, description="Reason for cancellation"
    )
    cancelled_at: datetime = Field(..., description="Cancellation timestamp")


class MessageValidationResponse(BaseModel):
    """Response model for message validation operations."""

    is_valid: bool = Field(..., description="Whether the message is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    validation_time_ms: int = Field(..., description="Validation processing time")
    validated_at: datetime = Field(..., description="Validation timestamp")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Detailed validation results"
    )


class AgentAvailabilityResponse(BaseModel):
    """Response model for agent availability checks."""

    agent_id: str = Field(..., description="Agent identifier")
    is_available: bool = Field(..., description="Whether agent is available")
    status: str = Field(..., description="Current agent status")
    capabilities: List[str] = Field(..., description="Agent capabilities")
    current_load: Dict[str, Any] = Field(..., description="Current load information")
    last_heartbeat: Optional[datetime] = Field(
        None, description="Last heartbeat timestamp"
    )
    response_time_ms: Optional[int] = Field(None, description="Agent response time")
    unavailable_reason: Optional[str] = Field(
        None, description="Reason for unavailability"
    )
    checked_at: datetime = Field(..., description="Availability check timestamp")

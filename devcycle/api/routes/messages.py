"""
Message handling endpoints for the DevCycle API.

This module provides endpoints for message routing and handling between agents.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...core.auth.fastapi_users import current_active_user
from ...core.auth.tortoise_models import User
from ...core.dependencies import get_agent_availability_service, get_message_validator
from ...core.messaging.middleware import MessageValidator
from ...core.messaging.responses import (
    AgentAvailabilityResponse,
    MessageBroadcastResponse,
    MessageCancelResponse,
    MessageDetailResponse,
    MessageHistoryResponse,
    MessageResponse,
    MessageRetryResponse,
    MessageRouteResponse,
    QueueStatusResponse,
)
from ...core.messaging.validation import (
    MessageBroadcastRequest,
    MessageRouteRequest,
    MessageSendRequest,
)
from ...core.messaging.validation_errors import (
    AgentUnavailableError,
    MessageValidationError,
)
from ...core.protocols.message import MessageStatus, MessageType
from ...core.services.agent_availability_service import AgentAvailabilityService

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post(
    "/send", response_model=MessageResponse, status_code=status.HTTP_201_CREATED
)
async def send_message(
    request: MessageSendRequest,
    validator: MessageValidator = Depends(get_message_validator),
    availability_service: AgentAvailabilityService = Depends(
        get_agent_availability_service
    ),
    user: User = Depends(current_active_user),
) -> MessageResponse:
    """
    Send a message to a specific agent.

    This endpoint validates the message request, checks agent availability,
    and sends the message to the specified agent.
    """
    # Validate request
    validation_result = await validator.validate_message_send(request.dict())
    if not validation_result.is_valid:
        raise MessageValidationError(validation_result.errors)

    # Check agent availability
    if not await availability_service.is_agent_available(request.agent_id):
        raise AgentUnavailableError(request.agent_id)

    # TODO: Implement actual message sending logic
    # For now, return a mock response
    message_id = str(uuid4())

    return MessageResponse(
        message_id=message_id,
        agent_id=request.agent_id,
        action=request.action,
        status=MessageStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        data=request.data,
        error=None,
        priority=request.priority,
        ttl=request.ttl,
        metadata=request.metadata,
    )


@router.post(
    "/broadcast",
    response_model=MessageBroadcastResponse,
    status_code=status.HTTP_201_CREATED,
)
async def broadcast_message(
    request: MessageBroadcastRequest,
    validator: MessageValidator = Depends(get_message_validator),
    availability_service: AgentAvailabilityService = Depends(
        get_agent_availability_service
    ),
) -> MessageBroadcastResponse:
    """
    Broadcast a message to multiple agents.

    This endpoint sends the same message to all agents of the specified types,
    excluding any agents in the exclude list.
    """
    # Validate request
    validation_result = await validator.validate_message_broadcast(request.dict())
    if not validation_result.is_valid:
        raise MessageValidationError(validation_result.errors)

    # TODO: Implement actual broadcast logic
    # For now, return a mock response
    broadcast_id = str(uuid4())
    message_ids = [str(uuid4()) for _ in range(3)]  # Mock 3 messages

    return MessageBroadcastResponse(
        broadcast_id=broadcast_id,
        total_agents=len(request.agent_types),
        successful_sends=3,
        failed_sends=0,
        skipped_agents=0,
        message_ids=message_ids,
        created_at=datetime.now(timezone.utc),
        details={"mock": "broadcast details"},
    )


@router.post(
    "/route", response_model=MessageRouteResponse, status_code=status.HTTP_201_CREATED
)
async def route_message(
    request: MessageRouteRequest,
    validator: MessageValidator = Depends(get_message_validator),
    availability_service: AgentAvailabilityService = Depends(
        get_agent_availability_service
    ),
) -> MessageRouteResponse:
    """
    Route a message to an appropriate agent based on capabilities.

    This endpoint automatically selects the best available agent based on
    required capabilities and load balancing strategy.
    """
    # Validate request
    validation_result = await validator.validate_message_route(request.dict())
    if not validation_result.is_valid:
        raise MessageValidationError(validation_result.errors)

    # Get available agents with required capabilities
    available_agents = []
    for capability in request.capabilities:
        agents = await availability_service.get_available_agents_by_capability(
            capability
        )
        available_agents.extend(agents)

    if not available_agents:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No agents available with required capabilities",
        )

    # Select agent based on load balancing strategy
    selected_agent_id = available_agents[0]  # Simple selection for now

    if request.load_balancing == "least_busy":
        selected_agent_id = (
            await availability_service.get_least_busy_agent(request.capabilities)
            or available_agents[0]
        )

    # Get agent capabilities and load info
    agent_capabilities = await availability_service.get_agent_capabilities(
        selected_agent_id
    )
    agent_load = await availability_service.get_agent_load(selected_agent_id)

    # TODO: Implement actual message routing logic
    message_id = str(uuid4())

    return MessageRouteResponse(
        message_id=message_id,
        selected_agent_id=selected_agent_id,
        routing_strategy=request.load_balancing or "round_robin",
        available_agents=len(available_agents),
        agent_capabilities=agent_capabilities,
        agent_load=agent_load,
        routing_reason="Agent selected based on capabilities and load balancing",
        created_at=datetime.now(timezone.utc),
    )


@router.get("/history", response_model=List[MessageHistoryResponse])
async def get_message_history(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    message_type: Optional[str] = Query(None, description="Filter by message type"),
    status: Optional[str] = Query(None, description="Filter by message status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of messages"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
) -> List[MessageHistoryResponse]:
    """
    Get message history with optional filtering.

    This endpoint retrieves message history with support for filtering
    by agent ID, message type, and status, with pagination.
    """
    # TODO: Implement actual message history retrieval
    # For now, return mock data
    mock_messages = []
    for i in range(min(limit, 5)):  # Return up to 5 mock messages
        mock_messages.append(
            MessageHistoryResponse(
                message_id=str(uuid4()),
                agent_id=agent_id or f"agent_{i}",
                action="analyze_business_requirement",
                message_type=MessageType.COMMAND,
                status=MessageStatus.COMPLETED,
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                execution_time_ms=1500,
                data_size_bytes=1024,
                priority="normal",
                error=None,
            )
        )

    return mock_messages


@router.get("/{message_id}", response_model=MessageDetailResponse)
async def get_message_detail(message_id: str) -> MessageDetailResponse:
    """
    Get detailed information about a specific message.

    This endpoint retrieves comprehensive details about a specific message,
    including its full data payload and processing history.
    """
    # TODO: Implement actual message detail retrieval
    # For now, return mock data
    return MessageDetailResponse(
        message_id=message_id,
        agent_id="business_analyst",
        action="analyze_business_requirement",
        message_type=MessageType.COMMAND,
        status=MessageStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        execution_time_ms=1500,
        data={"requirement": "Sample business requirement"},
        data_size_bytes=1024,
        priority="normal",
        ttl=3600,
        metadata={"source": "api"},
        error=None,
        retry_count=0,
        max_retries=3,
        queue_position=None,
        processing_started_at=datetime.now(timezone.utc),
    )


@router.get("/agent/{agent_id}", response_model=List[MessageHistoryResponse])
async def get_agent_messages(
    agent_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of messages"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
) -> List[MessageHistoryResponse]:
    """
    Get message history for a specific agent.

    This endpoint retrieves all messages sent to or from a specific agent,
    with pagination support.
    """
    # TODO: Implement actual agent message history retrieval
    # For now, return mock data
    mock_messages = []
    for i in range(min(limit, 3)):  # Return up to 3 mock messages
        mock_messages.append(
            MessageHistoryResponse(
                message_id=str(uuid4()),
                agent_id=agent_id,
                action="analyze_business_requirement",
                message_type=MessageType.COMMAND,
                status=MessageStatus.COMPLETED,
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                execution_time_ms=1500,
                data_size_bytes=1024,
                priority="normal",
                error=None,
            )
        )

    return mock_messages


@router.get("/queue/status", response_model=QueueStatusResponse)
async def get_queue_status() -> QueueStatusResponse:
    """
    Get current queue status and statistics.

    This endpoint provides information about the message queue,
    including message counts, processing times, and health status.
    """
    # TODO: Implement actual queue status retrieval
    # For now, return mock data
    return QueueStatusResponse(
        queue_name="default",
        total_messages=150,
        pending_messages=25,
        processing_messages=5,
        completed_messages=100,
        failed_messages=10,
        retry_messages=10,
        average_processing_time_ms=1200,
        queue_health="healthy",
        last_activity=datetime.now(timezone.utc),
        metrics={
            "throughput_messages_per_minute": 45,
            "error_rate_percent": 6.7,
            "average_queue_depth": 30,
        },
    )


@router.post("/queue/retry/{message_id}", response_model=MessageRetryResponse)
async def retry_message(message_id: str) -> MessageRetryResponse:
    """
    Retry a failed message.

    This endpoint retries a message that has failed processing,
    with configurable retry parameters.
    """
    # TODO: Implement actual message retry logic
    # For now, return mock data
    return MessageRetryResponse(
        message_id=message_id,
        retry_attempt=1,
        max_retries=3,
        retry_delay_seconds=30,
        original_error="Connection timeout",
        retry_reason="Message failed due to network issues",
        scheduled_at=datetime.now(timezone.utc),
        status=MessageStatus.RETRYING,
    )


@router.delete("/queue/{message_id}", response_model=MessageCancelResponse)
async def cancel_message(message_id: str) -> MessageCancelResponse:
    """
    Cancel a pending message.

    This endpoint cancels a message that is still pending or in progress,
    preventing it from being processed further.
    """
    # TODO: Implement actual message cancellation logic
    # For now, return mock data
    return MessageCancelResponse(
        message_id=message_id,
        cancelled=True,
        previous_status=MessageStatus.PENDING,
        cancellation_reason="User requested cancellation",
        cancelled_at=datetime.now(timezone.utc),
    )


@router.get("/agent/{agent_id}/availability", response_model=AgentAvailabilityResponse)
async def check_agent_availability(
    agent_id: str,
    availability_service: AgentAvailabilityService = Depends(
        get_agent_availability_service
    ),
) -> AgentAvailabilityResponse:
    """
    Check the availability of a specific agent.

    This endpoint provides detailed information about an agent's availability,
    capabilities, and current load.
    """
    # Check agent availability
    is_available = await availability_service.is_agent_available(agent_id)
    capabilities = await availability_service.get_agent_capabilities(agent_id)
    load_info = await availability_service.get_agent_load(agent_id)

    return AgentAvailabilityResponse(
        agent_id=agent_id,
        is_available=is_available,
        status=load_info.get("status", "unknown"),
        capabilities=capabilities,
        current_load=load_info,
        last_heartbeat=load_info.get("last_heartbeat"),
        response_time_ms=load_info.get("response_time_ms"),
        unavailable_reason=None if is_available else "Agent is offline or busy",
        checked_at=datetime.now(timezone.utc),
    )

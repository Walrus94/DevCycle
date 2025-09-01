"""
Message validation error responses for DevCycle.

This module defines custom HTTP exceptions for message validation errors,
following the existing error handling patterns in the codebase.
"""

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from ..errors import ErrorType, create_error_response


class MessageValidationError(HTTPException):
    """Custom exception for message validation errors."""

    def __init__(
        self,
        errors: List[str],
        error_code: str = "MESSAGE_VALIDATION_FAILED",
        error_context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize message validation error."""
        if error_context is None:
            error_context = {}

        error_context["validation_errors"] = errors

        detail = create_error_response(
            error_type=ErrorType.VALIDATION_ERROR,
            error_code=error_code,
            error_message="Message validation failed",
            error_context=error_context,
            source="message_validation",
        )
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class AgentUnavailableError(HTTPException):
    """Exception for when target agent is unavailable."""

    def __init__(self, agent_id: str, reason: Optional[str] = None):
        """Initialize agent unavailable error."""
        error_context = {"agent_id": agent_id}
        if reason:
            error_context["reason"] = reason

        detail = create_error_response(
            error_type=ErrorType.RESOURCE_ERROR,
            error_code="AGENT_UNAVAILABLE",
            error_message=f"Agent {agent_id} is not available",
            error_context=error_context,
            source="agent_availability",
        )
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


class MessageSizeError(HTTPException):
    """Exception for when message size exceeds limits."""

    def __init__(self, actual_size: int, max_size: int, size_type: str = "message"):
        """Initialize message size error."""
        detail = create_error_response(
            error_type=ErrorType.VALIDATION_ERROR,
            error_code="MESSAGE_SIZE_EXCEEDED",
            error_message=f"{size_type.title()} size exceeds limit",
            error_context={
                "actual_size": actual_size,
                "max_size": max_size,
                "size_type": size_type,
            },
            source="message_validation",
        )
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=detail
        )


class MessageActionError(HTTPException):
    """Exception for invalid message actions."""

    def __init__(self, action: str, allowed_actions: Optional[List[str]] = None):
        """Initialize message action error."""
        error_context: Dict[str, Any] = {"action": action}
        if allowed_actions:
            error_context["allowed_actions"] = allowed_actions

        detail = create_error_response(
            error_type=ErrorType.VALIDATION_ERROR,
            error_code="INVALID_MESSAGE_ACTION",
            error_message=f"Invalid action: {action}",
            error_context=error_context,
            source="message_validation",
        )
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class AgentCapabilityError(HTTPException):
    """Exception for when agent lacks required capabilities."""

    def __init__(
        self,
        agent_id: str,
        required_capabilities: List[str],
        available_capabilities: List[str],
    ):
        """Initialize agent capability error."""
        detail = create_error_response(
            error_type=ErrorType.VALIDATION_ERROR,
            error_code="AGENT_CAPABILITY_MISMATCH",
            error_message=f"Agent {agent_id} lacks required capabilities",
            error_context={
                "agent_id": agent_id,
                "required_capabilities": required_capabilities,
                "available_capabilities": available_capabilities,
            },
            source="agent_validation",
        )
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class MessageQueueError(HTTPException):
    """Exception for message queue operations."""

    def __init__(self, operation: str, message_id: str, reason: str):
        """Initialize message queue error."""
        detail = create_error_response(
            error_type=ErrorType.PROCESSING_ERROR,
            error_code="MESSAGE_QUEUE_ERROR",
            error_message=(
                f"Queue operation '{operation}' failed for message {message_id}"
            ),
            error_context={
                "operation": operation,
                "message_id": message_id,
                "reason": reason,
            },
            source="message_queue",
        )
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )


class MessageNotFoundError(HTTPException):
    """Exception for when a message is not found."""

    def __init__(self, message_id: str):
        """Initialize message not found error."""
        detail = create_error_response(
            error_type=ErrorType.RESOURCE_ERROR,
            error_code="MESSAGE_NOT_FOUND",
            error_message=f"Message {message_id} not found",
            error_context={"message_id": message_id},
            source="message_service",
        )
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class MessageRetryError(HTTPException):
    """Exception for message retry operations."""

    def __init__(
        self, message_id: str, reason: str, max_retries_exceeded: bool = False
    ):
        """Initialize message retry error."""
        error_code = (
            "MAX_RETRIES_EXCEEDED" if max_retries_exceeded else "MESSAGE_RETRY_FAILED"
        )
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if max_retries_exceeded
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        detail = create_error_response(
            error_type=ErrorType.PROCESSING_ERROR,
            error_code=error_code,
            error_message=f"Message retry failed for {message_id}",
            error_context={
                "message_id": message_id,
                "reason": reason,
                "max_retries_exceeded": max_retries_exceeded,
            },
            source="message_retry",
        )
        super().__init__(status_code=status_code, detail=detail)


class MessageTimeoutError(HTTPException):
    """Exception for message timeout operations."""

    def __init__(self, message_id: str, timeout_seconds: int):
        """Initialize message timeout error."""
        detail = create_error_response(
            error_type=ErrorType.TIMEOUT_ERROR,
            error_code="MESSAGE_TIMEOUT",
            error_message=(
                f"Message {message_id} timed out after {timeout_seconds} seconds"
            ),
            error_context={
                "message_id": message_id,
                "timeout_seconds": timeout_seconds,
            },
            source="message_processing",
        )
        super().__init__(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail=detail)

"""
Unit tests for message validation error handling.

This module tests the custom HTTP exceptions for message validation errors,
ensuring proper error responses and status codes.
"""

from fastapi import HTTPException, status

from devcycle.core.messaging.validation_errors import (
    AgentCapabilityError,
    AgentUnavailableError,
    MessageActionError,
    MessageNotFoundError,
    MessageQueueError,
    MessageRetryError,
    MessageSizeError,
    MessageTimeoutError,
    MessageValidationError,
)


class TestMessageValidationError:
    """Test cases for MessageValidationError."""

    def test_message_validation_error_creation(self):
        """Test creating a MessageValidationError with basic parameters."""
        errors = ["Field 'agent_id' is required", "Invalid action format"]
        error = MessageValidationError(errors=errors)

        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert isinstance(error.detail, dict)
        assert error.detail["error_type"] == "validation_error"
        assert error.detail["error_code"] == "MESSAGE_VALIDATION_FAILED"
        assert error.detail["error_message"] == "Message validation failed"
        assert error.detail["error_context"]["validation_errors"] == errors
        assert error.detail["source"] == "message_validation"

    def test_message_validation_error_with_custom_code(self):
        """Test creating a MessageValidationError with custom error code."""
        errors = ["Invalid format"]
        error = MessageValidationError(
            errors=errors, error_code="CUSTOM_VALIDATION_ERROR"
        )

        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.detail["error_code"] == "CUSTOM_VALIDATION_ERROR"

    def test_message_validation_error_with_context(self):
        """Test creating a MessageValidationError with additional context."""
        errors = ["Invalid data"]
        context = {"field": "data", "value": "invalid_value"}
        error = MessageValidationError(errors=errors, error_context=context)

        assert error.detail["error_context"]["validation_errors"] == errors
        assert error.detail["error_context"]["field"] == "data"
        assert error.detail["error_context"]["value"] == "invalid_value"


class TestAgentUnavailableError:
    """Test cases for AgentUnavailableError."""

    def test_agent_unavailable_error_creation(self):
        """Test creating an AgentUnavailableError with basic parameters."""
        error = AgentUnavailableError(agent_id="test_agent")

        assert error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert isinstance(error.detail, dict)
        assert error.detail["error_type"] == "resource_error"
        assert error.detail["error_code"] == "AGENT_UNAVAILABLE"
        assert error.detail["error_message"] == "Agent test_agent is not available"
        assert error.detail["error_context"]["agent_id"] == "test_agent"
        assert error.detail["source"] == "agent_availability"

    def test_agent_unavailable_error_with_reason(self):
        """Test creating an AgentUnavailableError with reason."""
        error = AgentUnavailableError(agent_id="test_agent", reason="Agent is offline")

        assert error.detail["error_context"]["agent_id"] == "test_agent"
        assert error.detail["error_context"]["reason"] == "Agent is offline"


class TestMessageSizeError:
    """Test cases for MessageSizeError."""

    def test_message_size_error_creation(self):
        """Test creating a MessageSizeError with basic parameters."""
        error = MessageSizeError(actual_size=2048, max_size=1024, size_type="message")

        assert error.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert isinstance(error.detail, dict)
        assert error.detail["error_type"] == "validation_error"
        assert error.detail["error_code"] == "MESSAGE_SIZE_EXCEEDED"
        assert error.detail["error_message"] == "Message size exceeds limit"
        assert error.detail["error_context"]["actual_size"] == 2048
        assert error.detail["error_context"]["max_size"] == 1024
        assert error.detail["error_context"]["size_type"] == "message"
        assert error.detail["source"] == "message_validation"

    def test_message_size_error_data_type(self):
        """Test creating a MessageSizeError for data type."""
        error = MessageSizeError(actual_size=512000, max_size=256000, size_type="data")

        assert error.detail["error_message"] == "Data size exceeds limit"
        assert error.detail["error_context"]["size_type"] == "data"


class TestMessageActionError:
    """Test cases for MessageActionError."""

    def test_message_action_error_creation(self):
        """Test creating a MessageActionError with basic parameters."""
        error = MessageActionError(action="invalid_action")

        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert isinstance(error.detail, dict)
        assert error.detail["error_type"] == "validation_error"
        assert error.detail["error_code"] == "INVALID_MESSAGE_ACTION"
        assert error.detail["error_message"] == "Invalid action: invalid_action"
        assert error.detail["error_context"]["action"] == "invalid_action"
        assert error.detail["source"] == "message_validation"

    def test_message_action_error_with_allowed_actions(self):
        """Test creating a MessageActionError with allowed actions list."""
        allowed_actions = ["action1", "action2", "action3"]
        error = MessageActionError(
            action="invalid_action", allowed_actions=allowed_actions
        )

        assert error.detail["error_context"]["action"] == "invalid_action"
        assert error.detail["error_context"]["allowed_actions"] == allowed_actions


class TestAgentCapabilityError:
    """Test cases for AgentCapabilityError."""

    def test_agent_capability_error_creation(self):
        """Test creating an AgentCapabilityError with basic parameters."""
        required_capabilities = ["text_processing", "analysis"]
        available_capabilities = ["text_processing"]

        error = AgentCapabilityError(
            agent_id="test_agent",
            required_capabilities=required_capabilities,
            available_capabilities=available_capabilities,
        )

        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert isinstance(error.detail, dict)
        assert error.detail["error_type"] == "validation_error"
        assert error.detail["error_code"] == "AGENT_CAPABILITY_MISMATCH"
        assert (
            error.detail["error_message"]
            == "Agent test_agent lacks required capabilities"
        )
        assert error.detail["error_context"]["agent_id"] == "test_agent"
        assert (
            error.detail["error_context"]["required_capabilities"]
            == required_capabilities
        )
        assert (
            error.detail["error_context"]["available_capabilities"]
            == available_capabilities
        )
        assert error.detail["source"] == "agent_validation"


class TestMessageQueueError:
    """Test cases for MessageQueueError."""

    def test_message_queue_error_creation(self):
        """Test creating a MessageQueueError with basic parameters."""
        error = MessageQueueError(
            operation="enqueue", message_id="msg_123", reason="Queue is full"
        )

        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert isinstance(error.detail, dict)
        assert error.detail["error_type"] == "processing_error"
        assert error.detail["error_code"] == "MESSAGE_QUEUE_ERROR"
        assert (
            error.detail["error_message"]
            == "Queue operation 'enqueue' failed for message msg_123"
        )
        assert error.detail["error_context"]["operation"] == "enqueue"
        assert error.detail["error_context"]["message_id"] == "msg_123"
        assert error.detail["error_context"]["reason"] == "Queue is full"
        assert error.detail["source"] == "message_queue"


class TestMessageNotFoundError:
    """Test cases for MessageNotFoundError."""

    def test_message_not_found_error_creation(self):
        """Test creating a MessageNotFoundError with basic parameters."""
        error = MessageNotFoundError(message_id="msg_123")

        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert isinstance(error.detail, dict)
        assert error.detail["error_type"] == "resource_error"
        assert error.detail["error_code"] == "MESSAGE_NOT_FOUND"
        assert error.detail["error_message"] == "Message msg_123 not found"
        assert error.detail["error_context"]["message_id"] == "msg_123"
        assert error.detail["source"] == "message_service"


class TestMessageRetryError:
    """Test cases for MessageRetryError."""

    def test_message_retry_error_creation(self):
        """Test creating a MessageRetryError with basic parameters."""
        error = MessageRetryError(message_id="msg_123", reason="Network timeout")

        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert isinstance(error.detail, dict)
        assert error.detail["error_type"] == "processing_error"
        assert error.detail["error_code"] == "MESSAGE_RETRY_FAILED"
        assert error.detail["error_message"] == "Message retry failed for msg_123"
        assert error.detail["error_context"]["message_id"] == "msg_123"
        assert error.detail["error_context"]["reason"] == "Network timeout"
        assert error.detail["error_context"]["max_retries_exceeded"] is False
        assert error.detail["source"] == "message_retry"

    def test_message_retry_error_max_retries_exceeded(self):
        """Test creating a MessageRetryError when max retries exceeded."""
        error = MessageRetryError(
            message_id="msg_123",
            reason="All retry attempts failed",
            max_retries_exceeded=True,
        )

        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.detail["error_code"] == "MAX_RETRIES_EXCEEDED"
        assert error.detail["error_context"]["max_retries_exceeded"] is True


class TestMessageTimeoutError:
    """Test cases for MessageTimeoutError."""

    def test_message_timeout_error_creation(self):
        """Test creating a MessageTimeoutError with basic parameters."""
        error = MessageTimeoutError(message_id="msg_123", timeout_seconds=30)

        assert error.status_code == status.HTTP_408_REQUEST_TIMEOUT
        assert isinstance(error.detail, dict)
        assert error.detail["error_type"] == "timeout_error"
        assert error.detail["error_code"] == "MESSAGE_TIMEOUT"
        assert (
            error.detail["error_message"]
            == "Message msg_123 timed out after 30 seconds"
        )
        assert error.detail["error_context"]["message_id"] == "msg_123"
        assert error.detail["error_context"]["timeout_seconds"] == 30
        assert error.detail["source"] == "message_processing"


class TestErrorResponseStructure:
    """Test cases for error response structure consistency."""

    def test_all_errors_have_consistent_structure(self):
        """Test that all error types have consistent response structure."""
        errors = [
            MessageValidationError(errors=["test"]),
            AgentUnavailableError(agent_id="test"),
            MessageSizeError(actual_size=100, max_size=50),
            MessageActionError(action="test"),
            AgentCapabilityError(
                agent_id="test",
                required_capabilities=["cap1"],
                available_capabilities=[],
            ),
            MessageQueueError(operation="test", message_id="test", reason="test"),
            MessageNotFoundError(message_id="test"),
            MessageRetryError(message_id="test", reason="test"),
            MessageTimeoutError(message_id="test", timeout_seconds=30),
        ]

        for error in errors:
            assert isinstance(error, HTTPException)
            assert isinstance(error.detail, dict)
            assert "error_type" in error.detail
            assert "error_code" in error.detail
            assert "error_message" in error.detail
            assert "source" in error.detail
            assert "error_context" in error.detail

    def test_error_types_are_correct(self):
        """Test that error types are correctly assigned."""
        assert (
            MessageValidationError(errors=["test"]).detail["error_type"]
            == "validation_error"
        )
        assert (
            AgentUnavailableError(agent_id="test").detail["error_type"]
            == "resource_error"
        )
        assert (
            MessageSizeError(actual_size=100, max_size=50).detail["error_type"]
            == "validation_error"
        )
        assert (
            MessageActionError(action="test").detail["error_type"] == "validation_error"
        )
        assert (
            AgentCapabilityError(
                agent_id="test",
                required_capabilities=["cap1"],
                available_capabilities=[],
            ).detail["error_type"]
            == "validation_error"
        )
        assert (
            MessageQueueError(
                operation="test", message_id="test", reason="test"
            ).detail["error_type"]
            == "processing_error"
        )
        assert (
            MessageNotFoundError(message_id="test").detail["error_type"]
            == "resource_error"
        )
        assert (
            MessageRetryError(message_id="test", reason="test").detail["error_type"]
            == "processing_error"
        )
        assert (
            MessageTimeoutError(message_id="test", timeout_seconds=30).detail[
                "error_type"
            ]
            == "timeout_error"
        )


class TestErrorIntegration:
    """Integration tests for error handling."""

    def test_error_chain_workflow(self):
        """Test a complete error handling workflow."""
        # Simulate a validation error
        validation_error = MessageValidationError(
            errors=["Invalid agent ID", "Missing required field"],
            error_code="VALIDATION_FAILED",
        )
        assert validation_error.status_code == 400
        assert len(validation_error.detail["error_context"]["validation_errors"]) == 2

        # Simulate an agent availability check
        availability_error = AgentUnavailableError(
            agent_id="business_analyst_1", reason="Agent is offline"
        )
        assert availability_error.status_code == 503
        assert (
            availability_error.detail["error_context"]["reason"] == "Agent is offline"
        )

        # Simulate a message size error
        size_error = MessageSizeError(
            actual_size=2048000, max_size=1048576, size_type="message"  # 2MB  # 1MB
        )
        assert size_error.status_code == 413
        assert (
            size_error.detail["error_context"]["actual_size"]
            > size_error.detail["error_context"]["max_size"]
        )

    def test_error_with_complex_context(self):
        """Test error creation with complex context data."""
        context = {
            "request_id": "req_123",
            "user_id": "user_456",
            "timestamp": "2024-01-01T12:00:00Z",
            "additional_data": {"field": "value", "nested": {"key": "value"}},
        }

        error = MessageValidationError(
            errors=["Complex validation failed"], error_context=context
        )

        assert error.detail["error_context"]["request_id"] == "req_123"
        assert error.detail["error_context"]["user_id"] == "user_456"
        assert error.detail["error_context"]["timestamp"] == "2024-01-01T12:00:00Z"
        assert error.detail["error_context"]["additional_data"]["field"] == "value"
        assert (
            error.detail["error_context"]["additional_data"]["nested"]["key"] == "value"
        )

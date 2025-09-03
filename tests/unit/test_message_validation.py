"""
Unit tests for message validation functionality.

This module tests the message validation models, validation logic,
and related functionality for the DevCycle messaging system.
"""

import pytest

from devcycle.core.messaging.validation import (
    MessageBroadcastRequest,
    MessageHistoryRequest,
    MessageRetryRequest,
    MessageRouteRequest,
    MessageSendRequest,
    MessageValidationConfig,
    QueueStatusRequest,
    ValidationResult,
)
from devcycle.core.protocols.message import AgentAction, AgentEvent, MessageType


class TestValidationResult:
    """Test cases for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating a ValidationResult with required fields."""
        result = ValidationResult(
            is_valid=True, errors=["Error 1", "Error 2"], warnings=["Warning 1"]
        )

        assert result.is_valid is True
        assert result.errors == ["Error 1", "Error 2"]
        assert result.warnings == ["Warning 1"]

    def test_validation_result_default_warnings(self):
        """Test that warnings defaults to empty list if not provided."""
        result = ValidationResult(is_valid=False, errors=["Error 1"])

        assert result.is_valid is False
        assert result.errors == ["Error 1"]
        assert result.warnings == []

    def test_validation_result_post_init(self):
        """Test post-initialization validation."""
        result = ValidationResult(is_valid=True, errors=[], warnings=None)

        assert result.warnings == []


class TestMessageSendRequest:
    """Test cases for MessageSendRequest model."""

    def test_valid_message_send_request(self):
        """Test creating a valid MessageSendRequest."""
        request = MessageSendRequest(
            agent_id="test_agent",
            action="analyze_business_requirement",
            data={"requirement": "Test requirement"},
            priority="high",
            ttl=3600,
            metadata={"source": "test"},
        )

        assert request.agent_id == "test_agent"
        assert request.action == "analyze_business_requirement"
        assert request.data == {"requirement": "Test requirement"}
        assert request.priority == "high"
        assert request.ttl == 3600
        assert request.metadata == {"source": "test"}

    def test_message_send_request_minimal(self):
        """Test creating a MessageSendRequest with minimal required fields."""
        request = MessageSendRequest(agent_id="test_agent", action="test_action")

        assert request.agent_id == "test_agent"
        assert request.action == "test_action"
        assert request.data == {}
        assert request.priority is None
        assert request.ttl is None
        assert request.metadata is None

    def test_message_send_request_invalid_priority(self):
        """Test that invalid priority raises validation error."""
        with pytest.raises(ValueError, match="String should match pattern"):
            MessageSendRequest(
                agent_id="test_agent", action="test_action", priority="invalid_priority"
            )

    def test_message_send_request_invalid_ttl(self):
        """Test that invalid TTL raises validation error."""
        with pytest.raises(ValueError, match="Input should be less than or equal to"):
            MessageSendRequest(
                agent_id="test_agent", action="test_action", ttl=100000  # Too high
            )

    def test_message_send_request_negative_ttl(self):
        """Test that negative TTL raises validation error."""
        with pytest.raises(
            ValueError, match="Input should be greater than or equal to"
        ):
            MessageSendRequest(agent_id="test_agent", action="test_action", ttl=-1)

    def test_message_send_request_known_action(self):
        """Test validation with known action."""
        request = MessageSendRequest(
            agent_id="test_agent", action=AgentAction.ANALYZE_BUSINESS_REQUIREMENT.value
        )

        assert request.action == AgentAction.ANALYZE_BUSINESS_REQUIREMENT.value

    def test_message_send_request_custom_action(self):
        """Test validation with custom action (should be allowed)."""
        request = MessageSendRequest(agent_id="test_agent", action="custom_action_123")

        assert request.action == "custom_action_123"

    def test_message_send_request_large_data(self):
        """Test validation with data that's too large."""
        large_data = {"data": "x" * (1024 * 1024 + 1)}  # Just over 1MB

        with pytest.raises(ValueError, match="Data payload too large"):
            MessageSendRequest(
                agent_id="test_agent", action="test_action", data=large_data
            )


class TestMessageBroadcastRequest:
    """Test cases for MessageBroadcastRequest model."""

    def test_valid_broadcast_request(self):
        """Test creating a valid MessageBroadcastRequest."""
        request = MessageBroadcastRequest(
            agent_types=["business_analyst", "developer"],
            action="notify_update",
            data={"update": "Test update"},
            exclude_agent_ids=["agent_1", "agent_2"],
        )

        assert request.agent_types == ["business_analyst", "developer"]
        assert request.action == "notify_update"
        assert request.data == {"update": "Test update"}
        assert request.exclude_agent_ids == ["agent_1", "agent_2"]

    def test_broadcast_request_invalid_agent_type(self):
        """Test that invalid agent type raises validation error."""
        with pytest.raises(ValueError, match="Invalid agent type"):
            MessageBroadcastRequest(agent_types=["invalid_type"], action="test_action")

    def test_broadcast_request_too_many_agent_types(self):
        """Test that too many agent types raises validation error."""
        agent_types = ["business_analyst"] * 11  # More than max of 10

        with pytest.raises(ValueError, match="List should have at most"):
            MessageBroadcastRequest(agent_types=agent_types, action="test_action")

    def test_broadcast_request_empty_agent_types(self):
        """Test that empty agent types raises validation error."""
        with pytest.raises(ValueError, match="List should have at least"):
            MessageBroadcastRequest(agent_types=[], action="test_action")


class TestMessageRouteRequest:
    """Test cases for MessageRouteRequest model."""

    def test_valid_route_request(self):
        """Test creating a valid MessageRouteRequest."""
        request = MessageRouteRequest(
            capabilities=["text_processing", "analysis"],
            action="process_text",
            data={"text": "Sample text"},
            load_balancing="least_busy",
        )

        assert request.capabilities == ["text_processing", "analysis"]
        assert request.action == "process_text"
        assert request.data == {"text": "Sample text"}
        assert request.load_balancing == "least_busy"

    def test_route_request_invalid_capability(self):
        """Test that invalid capability raises validation error."""
        with pytest.raises(ValueError, match="Invalid capability"):
            MessageRouteRequest(
                capabilities=["invalid_capability"], action="test_action"
            )

    def test_route_request_invalid_load_balancing(self):
        """Test that invalid load balancing strategy raises validation error."""
        with pytest.raises(ValueError, match="String should match pattern"):
            MessageRouteRequest(
                capabilities=["text_processing"],
                action="test_action",
                load_balancing="invalid_strategy",
            )

    def test_route_request_too_many_capabilities(self):
        """Test that too many capabilities raises validation error."""
        capabilities = ["text_processing"] * 6  # More than max of 5

        with pytest.raises(ValueError, match="List should have at most"):
            MessageRouteRequest(capabilities=capabilities, action="test_action")


class TestMessageValidationConfig:
    """Test cases for MessageValidationConfig model."""

    def test_validation_config_defaults(self):
        """Test MessageValidationConfig with default values."""
        config = MessageValidationConfig()

        assert config.max_message_size_bytes == 1024 * 1024  # 1MB
        assert config.max_data_size_bytes == 512 * 1024  # 512KB
        assert config.allowed_actions == []
        assert config.required_agent_online is True
        assert config.validate_agent_capabilities is True
        assert config.max_retries == 3
        assert config.enable_warnings is True

    def test_validation_config_custom_values(self):
        """Test MessageValidationConfig with custom values."""
        config = MessageValidationConfig(
            max_message_size_bytes=2 * 1024 * 1024,  # 2MB
            max_data_size_bytes=1024 * 1024,  # 1MB
            allowed_actions=["action1", "action2"],
            required_agent_online=False,
            validate_agent_capabilities=False,
            max_retries=5,
            enable_warnings=False,
        )

        assert config.max_message_size_bytes == 2 * 1024 * 1024
        assert config.max_data_size_bytes == 1024 * 1024
        assert config.allowed_actions == ["action1", "action2"]
        assert config.required_agent_online is False
        assert config.validate_agent_capabilities is False
        assert config.max_retries == 5
        assert config.enable_warnings is False

    def test_validation_config_invalid_message_size(self):
        """Test that invalid message size raises validation error."""
        with pytest.raises(ValueError, match="Input should be less than or equal to"):
            MessageValidationConfig(max_message_size_bytes=20 * 1024 * 1024)  # Too high

    def test_validation_config_invalid_data_size(self):
        """Test that invalid data size raises validation error."""
        with pytest.raises(ValueError, match="Input should be less than or equal to"):
            MessageValidationConfig(max_data_size_bytes=10 * 1024 * 1024)  # Too high

    def test_validation_config_invalid_retries(self):
        """Test that invalid retry count raises validation error."""
        with pytest.raises(ValueError, match="Input should be less than or equal to"):
            MessageValidationConfig(max_retries=15)  # Too high


class TestMessageHistoryRequest:
    """Test cases for MessageHistoryRequest model."""

    def test_valid_history_request(self):
        """Test creating a valid MessageHistoryRequest."""
        request = MessageHistoryRequest(
            agent_id="test_agent",
            message_type=MessageType.COMMAND.value,
            status="completed",
            limit=50,
            offset=10,
        )

        assert request.agent_id == "test_agent"
        assert request.message_type == MessageType.COMMAND.value
        assert request.status == "completed"
        assert request.limit == 50
        assert request.offset == 10

    def test_history_request_defaults(self):
        """Test MessageHistoryRequest with default values."""
        request = MessageHistoryRequest()

        assert request.agent_id is None
        assert request.message_type is None
        assert request.status is None
        assert request.limit == 100
        assert request.offset == 0

    def test_history_request_invalid_message_type(self):
        """Test that invalid message type raises validation error."""
        with pytest.raises(ValueError, match="Invalid message type"):
            MessageHistoryRequest(message_type="invalid_type")

    def test_history_request_invalid_status(self):
        """Test that invalid status raises validation error."""
        with pytest.raises(ValueError, match="Invalid status"):
            MessageHistoryRequest(status="invalid_status")

    def test_history_request_invalid_limit(self):
        """Test that invalid limit raises validation error."""
        with pytest.raises(ValueError, match="Input should be less than or equal to"):
            MessageHistoryRequest(limit=2000)  # Too high

    def test_history_request_invalid_offset(self):
        """Test that invalid offset raises validation error."""
        with pytest.raises(
            ValueError, match="Input should be greater than or equal to"
        ):
            MessageHistoryRequest(offset=-1)


class TestQueueStatusRequest:
    """Test cases for QueueStatusRequest model."""

    def test_valid_queue_status_request(self):
        """Test creating a valid QueueStatusRequest."""
        request = QueueStatusRequest(include_details=True, include_metrics=False)

        assert request.include_details is True
        assert request.include_metrics is False

    def test_queue_status_request_defaults(self):
        """Test QueueStatusRequest with default values."""
        request = QueueStatusRequest()

        assert request.include_details is False
        assert request.include_metrics is True


class TestMessageRetryRequest:
    """Test cases for MessageRetryRequest model."""

    def test_valid_retry_request(self):
        """Test creating a valid MessageRetryRequest."""
        request = MessageRetryRequest(max_retries=5, delay_seconds=60, priority="high")

        assert request.max_retries == 5
        assert request.delay_seconds == 60
        assert request.priority == "high"

    def test_retry_request_defaults(self):
        """Test MessageRetryRequest with default values."""
        request = MessageRetryRequest()

        assert request.max_retries is None
        assert request.delay_seconds is None
        assert request.priority is None

    def test_retry_request_invalid_priority(self):
        """Test that invalid priority raises validation error."""
        with pytest.raises(ValueError, match="String should match pattern"):
            MessageRetryRequest(priority="invalid_priority")

    def test_retry_request_invalid_max_retries(self):
        """Test that invalid max retries raises validation error."""
        with pytest.raises(ValueError, match="Input should be less than or equal to"):
            MessageRetryRequest(max_retries=15)  # Too high

    def test_retry_request_invalid_delay(self):
        """Test that invalid delay raises validation error."""
        with pytest.raises(ValueError, match="Input should be less than or equal to"):
            MessageRetryRequest(delay_seconds=4000)  # Too high


class TestMessageValidationIntegration:
    """Integration tests for message validation."""

    def test_complete_validation_workflow(self):
        """Test a complete validation workflow with multiple request types."""
        # Test send request
        send_request = MessageSendRequest(
            agent_id="business_analyst_1",
            action=AgentAction.ANALYZE_BUSINESS_REQUIREMENT.value,
            data={"requirement": "Create a user management system"},
            priority="high",
        )
        assert send_request.agent_id == "business_analyst_1"
        assert send_request.action == AgentAction.ANALYZE_BUSINESS_REQUIREMENT.value

        # Test broadcast request
        broadcast_request = MessageBroadcastRequest(
            agent_types=["developer", "tester"],
            action="deploy_notification",
            data={"version": "1.0.0"},
        )
        assert len(broadcast_request.agent_types) == 2
        assert "developer" in broadcast_request.agent_types

        # Test route request
        route_request = MessageRouteRequest(
            capabilities=["code_generation", "testing"],
            action="generate_test_code",
            load_balancing="least_busy",
        )
        assert len(route_request.capabilities) == 2
        assert route_request.load_balancing == "least_busy"

        # Test validation config
        config = MessageValidationConfig(max_retries=5, enable_warnings=True)
        assert config.max_retries == 5
        assert config.enable_warnings is True

    def test_validation_with_real_agent_actions(self):
        """Test validation with real agent actions from the enum."""
        # Test all known agent actions
        for action in AgentAction:
            request = MessageSendRequest(
                agent_id="test_agent", action=action.value, data={}
            )
            assert request.action == action.value

        # Test all known agent events
        for event in AgentEvent:
            request = MessageSendRequest(
                agent_id="test_agent", action=event.value, data={}
            )
            assert request.action == event.value

    def test_validation_with_real_message_types(self):
        """Test validation with real message types from the enum."""
        for msg_type in MessageType:
            request = MessageHistoryRequest(message_type=msg_type.value, limit=10)
            assert request.message_type == msg_type.value

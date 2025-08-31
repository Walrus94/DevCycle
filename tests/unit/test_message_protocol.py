"""
Tests for the message protocol implementation.
"""

import pytest

from devcycle.core.protocols import (
    AgentAction,
    AgentEvent,
    Message,
    MessageStatus,
    MessageType,
    create_command,
    create_event,
)


@pytest.mark.unit
class TestMessageProtocol:
    """Test the message protocol implementation."""

    def test_create_command_message(self) -> None:
        """Test creating a command message."""
        data = {"business_task": "Create user authentication system"}
        message = create_command("analyze_business_requirement", data)

        assert message.header.message_type == MessageType.COMMAND
        assert message.body.action == "analyze_business_requirement"
        assert message.body.data == data
        assert message.body.status == MessageStatus.PENDING

    def test_create_event_message(self) -> None:
        """Test creating an event message."""
        data = {"progress": 0.5, "step": "analyzing_requirements"}
        message = create_event("analysis_progress", data, MessageStatus.IN_PROGRESS)

        assert message.header.message_type == MessageType.EVENT
        assert message.body.action == "analysis_progress"
        assert message.body.data == data
        assert message.body.status == MessageStatus.IN_PROGRESS

    def test_message_serialization(self) -> None:
        """Test message serialization to dictionary."""
        message = create_command("test_action", {"key": "value"})
        message_dict = message.to_dict()

        assert "header" in message_dict
        assert "body" in message_dict
        assert message_dict["header"]["message_type"] == "command"
        assert message_dict["body"]["action"] == "test_action"

    def test_message_deserialization(self) -> None:
        """Test message deserialization from dictionary."""
        original_message = create_event("test_event", {"key": "value"})
        message_dict = original_message.to_dict()

        reconstructed_message = Message.from_dict(message_dict)

        assert (
            reconstructed_message.header.message_type
            == original_message.header.message_type
        )
        assert reconstructed_message.body.action == original_message.body.action
        assert reconstructed_message.body.data == original_message.body.data

    def test_agent_actions_enum(self) -> None:
        """Test agent action enum values."""
        assert (
            AgentAction.ANALYZE_BUSINESS_REQUIREMENT.value
            == "analyze_business_requirement"
        )
        assert AgentAction.GET_ANALYSIS_STATUS.value == "get_analysis_status"
        assert AgentAction.STOP_ANALYSIS.value == "stop_analysis"

    def test_agent_events_enum(self) -> None:
        """Test agent event enum values."""
        assert AgentEvent.ANALYSIS_STARTED.value == "analysis_started"
        assert AgentEvent.ANALYSIS_PROGRESS.value == "analysis_progress"
        assert AgentEvent.ANALYSIS_COMPLETE.value == "analysis_complete"
        assert AgentEvent.ANALYSIS_FAILED.value == "analysis_failed"
        assert AgentEvent.ANALYSIS_STOPPED.value == "analysis_stopped"

    def test_message_status_enum(self) -> None:
        """Test message status enum values."""
        assert MessageStatus.PENDING.value == "pending"
        assert MessageStatus.IN_PROGRESS.value == "in_progress"
        assert MessageStatus.COMPLETED.value == "completed"
        assert MessageStatus.FAILED.value == "failed"
        assert MessageStatus.STOPPED.value == "stopped"

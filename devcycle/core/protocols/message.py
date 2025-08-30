"""
Message protocol definitions for DevCycle agent communication.

This module defines the structure and types for messages exchanged between
the system and agents, starting with the business analyst agent.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict
from uuid import uuid4


class MessageType(Enum):
    """Types of messages in the system."""

    COMMAND = "command"  # System → Agent
    EVENT = "event"  # Agent → System
    RESPONSE = "response"  # Agent → System (direct response)


class AgentAction(Enum):
    """Actions that the business analyst agent can perform."""

    ANALYZE_BUSINESS_REQUIREMENT = "analyze_business_requirement"
    GET_ANALYSIS_STATUS = "get_analysis_status"
    STOP_ANALYSIS = "stop_analysis"


class AgentEvent(Enum):
    """Events that the business analyst agent can emit."""

    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_PROGRESS = "analysis_progress"
    ANALYSIS_COMPLETE = "analysis_complete"
    ANALYSIS_FAILED = "analysis_failed"
    ANALYSIS_STOPPED = "analysis_stopped"


class MessageStatus(Enum):
    """Status values for messages and operations."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class MessageHeader:
    """Header information for all messages."""

    message_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    agent_id: str = "business_analyst"
    message_type: MessageType = MessageType.COMMAND
    version: str = "1.0"


@dataclass
class MessageBody:
    """Body content for messages."""

    action: str
    data: Dict[str, Any]
    status: MessageStatus = MessageStatus.PENDING


@dataclass
class Message:
    """Complete message structure for agent communication."""

    header: MessageHeader
    body: MessageBody

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        return {
            "header": {
                "message_id": self.header.message_id,
                "timestamp": self.header.timestamp.isoformat(),
                "agent_id": self.header.agent_id,
                "message_type": self.header.message_type.value,
                "version": self.header.version,
            },
            "body": {
                "action": self.body.action,
                "data": self.body.data,
                "status": self.body.status.value,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary format."""
        header_data = data["header"]
        body_data = data["body"]

        header = MessageHeader(
            message_id=header_data["message_id"],
            timestamp=datetime.fromisoformat(header_data["timestamp"]),
            agent_id=header_data["agent_id"],
            message_type=MessageType(header_data["message_type"]),
            version=header_data["version"],
        )

        body = MessageBody(
            action=body_data["action"],
            data=body_data["data"],
            status=MessageStatus(body_data["status"]),
        )

        return cls(header=header, body=body)


# Convenience functions for creating common message types
def create_command(action: str, data: Dict[str, Any]) -> Message:
    """Create a command message from system to agent."""
    header = MessageHeader(message_type=MessageType.COMMAND)
    body = MessageBody(action=action, data=data)
    return Message(header=header, body=body)


def create_event(
    action: str, data: Dict[str, Any], status: MessageStatus = MessageStatus.PENDING
) -> Message:
    """Create an event message from agent to system."""
    header = MessageHeader(message_type=MessageType.EVENT)
    body = MessageBody(action=action, data=data, status=status)
    return Message(header=header, body=body)

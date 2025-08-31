"""
Message queue interface definitions.

This module defines the abstract interfaces for message queue implementations,
ensuring consistent behavior across different backend types.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from devcycle.core.protocols.message import Message

from ..config import QueuePriority


@dataclass
class QueueMessage:
    """Message structure for queue operations."""

    message: Message
    priority: QueuePriority = QueuePriority.NORMAL
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    queue_id: str = field(default_factory=lambda: str(uuid4()))
    ttl: Optional[float] = None
    max_retries: int = 3
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Post-initialization validation."""
        if self.ttl is None:
            self.ttl = 0.0
        if self.metadata is None:
            self.metadata = {}


class MessageQueueInterface(ABC):
    """Abstract interface for message queue implementations."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the message queue."""
        pass

    @abstractmethod
    async def put(
        self,
        message: Message,
        priority: Optional[QueuePriority] = None,
        ttl: Optional[float] = None,
        max_retries: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Put a message in the queue."""
        pass

    @abstractmethod
    async def get(self, timeout: Optional[float] = None) -> Optional[QueueMessage]:
        """Get the next message from the queue."""
        pass

    @abstractmethod
    async def mark_completed(self, message_id: str) -> None:
        """Mark a message as completed."""
        pass

    @abstractmethod
    async def mark_failed(self, message_id: str, retry: bool = True) -> None:
        """Mark a message as failed."""
        pass

    @abstractmethod
    async def cancel(self, message_id: str) -> bool:
        """Cancel a message (if supported)."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the queue and cleanup resources."""
        pass

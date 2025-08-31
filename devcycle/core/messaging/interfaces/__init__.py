"""
Message queue interfaces for DevCycle agent communication.

This package defines the abstract interfaces that different message queue
implementations must follow.
"""

from .queue import MessageQueueInterface

__all__ = ["MessageQueueInterface"]

"""
Message queue factory for creating different backend implementations.

This module provides a factory pattern for creating message queue instances
based on configuration, supporting multiple backend types.
"""

from typing import Dict, Type

from .config import MessagingConfig, QueueBackend
from .implementations.kafka.queue import KafkaMessageQueue
from .interfaces.queue import MessageQueueInterface


class MessageQueueFactory:
    """Factory for creating message queue instances."""

    _backends: Dict[QueueBackend, Type[MessageQueueInterface]] = {
        QueueBackend.KAFKA: KafkaMessageQueue,
    }

    @classmethod
    def register_backend(
        cls, backend: QueueBackend, implementation: Type[MessageQueueInterface]
    ) -> None:
        """Register a new backend implementation."""
        cls._backends[backend] = implementation

    @classmethod
    def create_queue(cls, config: MessagingConfig) -> MessageQueueInterface:
        """Create a message queue instance based on configuration."""
        backend = config.backend
        if backend not in cls._backends:
            raise ValueError(f"Unsupported backend: {backend}")

        implementation = cls._backends[backend]
        return implementation(config)  # type: ignore[call-arg]

    @classmethod
    def available_backends(cls) -> list[QueueBackend]:
        """Get list of available backend types."""
        return list(cls._backends.keys())

    @classmethod
    def create_queue_from_dict(cls, config_dict: Dict) -> MessageQueueInterface:
        """Create a message queue from dictionary configuration."""
        config = MessagingConfig.from_dict(config_dict)
        return cls.create_queue(config)

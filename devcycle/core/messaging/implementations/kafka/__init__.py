"""
Kafka message queue implementations.

This package contains Kafka-based implementations of the message queue
interface for scalable, reliable agent communication.
"""

from .queue import KafkaMessageQueue

__all__ = ["KafkaMessageQueue"]

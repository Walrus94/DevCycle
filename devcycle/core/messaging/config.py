"""
Configuration management for DevCycle messaging system.

This module provides configuration options for choosing between different
message queue implementations (in-memory, Kafka, etc.).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class QueueBackend(Enum):
    """Available queue backend implementations."""

    IN_MEMORY = "in_memory"
    KAFKA = "kafka"


class QueuePriority(Enum):
    """Message queue priority levels."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class KafkaConfig:
    """Configuration for Kafka backend."""

    bootstrap_servers: str = "localhost:9092"
    topic_prefix: str = "devcycle"
    consumer_group: str = "devcycle-agents"
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = True
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 3000

    # Producer settings
    acks: str = "all"
    retries: int = 3
    batch_size: int = 16384
    linger_ms: int = 5

    # Topic settings
    num_partitions: int = 3
    replication_factor: int = 1  # For local development


@dataclass
class InMemoryConfig:
    """Configuration for in-memory backend."""

    max_size: int = 10000
    cleanup_interval: float = 60.0
    enable_persistence: bool = False


@dataclass
class MessagingConfig:
    """Main configuration for the messaging system."""

    # Backend selection
    backend: QueueBackend = QueueBackend.IN_MEMORY

    # Backend-specific configurations
    kafka: Optional[KafkaConfig] = None
    in_memory: Optional[InMemoryConfig] = None

    # General settings
    default_priority: QueuePriority = QueuePriority.NORMAL
    default_ttl: Optional[float] = None
    default_max_retries: int = 3

    # Performance settings
    batch_size: int = 100
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        """Set default configurations based on backend."""
        if self.backend == QueueBackend.KAFKA and self.kafka is None:
            self.kafka = KafkaConfig()
        elif self.backend == QueueBackend.IN_MEMORY and self.in_memory is None:
            self.in_memory = InMemoryConfig()

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "MessagingConfig":
        """Create configuration from dictionary."""
        backend_str = config_dict.get("backend", "in_memory")
        backend = QueueBackend(backend_str)

        # Extract backend-specific configs
        kafka_config = None
        if "kafka" in config_dict:
            kafka_config = KafkaConfig(**config_dict["kafka"])

        in_memory_config = None
        if "in_memory" in config_dict:
            in_memory_config = InMemoryConfig(**config_dict["in_memory"])

        # Extract other settings
        default_priority_str = config_dict.get("default_priority", "NORMAL")
        default_priority = (
            QueuePriority[default_priority_str]
            if isinstance(default_priority_str, str)
            else default_priority_str
        )

        return cls(
            backend=backend,
            kafka=kafka_config,
            in_memory=in_memory_config,
            default_priority=default_priority,
            default_ttl=config_dict.get("default_ttl"),
            default_max_retries=config_dict.get("default_max_retries", 3),
            batch_size=config_dict.get("batch_size", 100),
            timeout_seconds=config_dict.get("timeout_seconds", 30.0),
        )

    def get_backend_config(self, backend: str) -> Optional[KafkaConfig]:
        """Get backend-specific configuration."""
        if backend == "kafka":
            return self.kafka
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        config_dict: Dict[str, Any] = {
            "backend": self.backend.value,
            "default_priority": self.default_priority.name,
            "default_ttl": self.default_ttl,
            "default_max_retries": self.default_max_retries,
            "batch_size": self.batch_size,
            "timeout_seconds": self.timeout_seconds,
        }

        if self.kafka:
            config_dict["kafka"] = self.kafka.__dict__

        return config_dict

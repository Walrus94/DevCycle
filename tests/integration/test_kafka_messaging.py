"""
Tests for Kafka messaging implementation.

This module tests the Kafka-based message queue implementation,
ensuring it properly implements the MessageQueueInterface.
"""

import asyncio
from typing import cast
from unittest.mock import patch

import pytest

from devcycle.core.messaging.config import (
    KafkaConfig,
    MessagingConfig,
    QueueBackend,
    QueuePriority,
)
from devcycle.core.messaging.factory import MessageQueueFactory
from devcycle.core.messaging.implementations.kafka.queue import KafkaMessageQueue
from devcycle.core.messaging.interfaces.queue import QueueMessage
from devcycle.core.protocols.message import Message, MessageStatus, create_event


@pytest.mark.integration
class TestKafkaConfig:
    """Test Kafka configuration."""

    def test_kafka_config_defaults(self) -> None:
        """Test Kafka configuration default values."""
        config = KafkaConfig()
        assert config.bootstrap_servers == "localhost:9092"
        assert config.topic_prefix == "devcycle"
        assert config.num_partitions == 3
        assert config.replication_factor == 1
        assert config.acks == "all"
        assert config.retries == 3
        assert config.batch_size == 16384
        assert config.linger_ms == 5
        assert config.consumer_group == "devcycle-agents"
        assert config.auto_offset_reset == "earliest"
        assert config.enable_auto_commit is True
        assert config.session_timeout_ms == 30000
        assert config.heartbeat_interval_ms == 3000

    def test_kafka_config_custom_values(self) -> None:
        """Test Kafka configuration with custom values."""
        config = KafkaConfig(
            bootstrap_servers="kafka:9092",
            topic_prefix="custom",
            num_partitions=5,
            replication_factor=3,
            acks="1",
            retries=5,
            batch_size=32768,
            linger_ms=100,
            consumer_group="custom-group",
            auto_offset_reset="latest",
            enable_auto_commit=False,
            session_timeout_ms=60000,
            heartbeat_interval_ms=5000,
        )

        assert config.bootstrap_servers == "kafka:9092"
        assert config.topic_prefix == "custom"
        assert config.num_partitions == 5
        assert config.replication_factor == 3
        assert config.acks == "1"
        assert config.retries == 5
        assert config.batch_size == 32768
        assert config.linger_ms == 100
        assert config.consumer_group == "custom-group"
        assert config.auto_offset_reset == "latest"
        assert config.enable_auto_commit is False
        assert config.session_timeout_ms == 60000
        assert config.heartbeat_interval_ms == 5000


@pytest.mark.integration
class TestMessagingConfig:
    """Test messaging configuration."""

    def test_messaging_config_defaults(self) -> None:
        """Test messaging configuration default values."""
        config = MessagingConfig()
        assert config.backend == QueueBackend.IN_MEMORY
        assert config.kafka is None
        assert config.default_priority == QueuePriority.NORMAL
        assert config.default_ttl is None
        assert config.default_max_retries == 3
        assert config.batch_size == 100
        assert config.timeout_seconds == 30.0

    def test_messaging_config_kafka_backend(self) -> None:
        """Test messaging configuration with Kafka backend."""
        config = MessagingConfig(backend=QueueBackend.KAFKA)
        assert config.backend == QueueBackend.KAFKA
        assert config.kafka is not None
        assert config.kafka.bootstrap_servers == "localhost:9092"

    def test_messaging_config_from_dict(self) -> None:
        """Test messaging configuration from dictionary."""
        config_dict = {
            "backend": "kafka",
            "kafka": {
                "bootstrap_servers": "custom:9092",
                "topic_prefix": "custom",
            },
            "default_priority": "HIGH",
            "default_ttl": 3600,
            "default_max_retries": 5,
        }

        config = MessagingConfig.from_dict(config_dict)
        assert config.backend == QueueBackend.KAFKA
        assert config.kafka is not None
        assert config.kafka.bootstrap_servers == "custom:9092"
        assert config.kafka.topic_prefix == "custom"
        assert config.default_priority == QueuePriority.HIGH
        assert config.default_ttl == 3600
        assert config.default_max_retries == 5

    def test_messaging_config_get_backend_config(self) -> None:
        """Test getting backend-specific configuration."""
        config = MessagingConfig(backend=QueueBackend.KAFKA)
        kafka_config = config.get_backend_config("kafka")
        assert kafka_config is not None
        assert isinstance(kafka_config, KafkaConfig)


@pytest.mark.integration
class TestMessageQueueFactory:
    """Test message queue factory."""

    def test_factory_available_backends(self) -> None:
        """Test factory available backends."""
        backends = MessageQueueFactory.available_backends()
        assert QueueBackend.KAFKA in backends

    def test_factory_create_kafka_queue(self) -> None:
        """Test factory creating Kafka queue."""
        config = MessagingConfig(backend=QueueBackend.KAFKA)
        queue = MessageQueueFactory.create_queue(config)
        assert queue is not None
        assert hasattr(queue, "put")
        assert hasattr(queue, "get")

    def test_factory_create_queue_from_dict(self) -> None:
        """Test factory creating queue from dictionary."""
        config_dict = {"backend": "kafka"}
        queue = MessageQueueFactory.create_queue_from_dict(config_dict)
        assert queue is not None

    def test_factory_unsupported_backend(self) -> None:
        """Test factory with unsupported backend."""
        config = MessagingConfig(backend="unsupported")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="Unsupported backend"):
            MessageQueueFactory.create_queue(config)


@pytest.mark.integration
class TestKafkaMessageQueue:
    """Test Kafka message queue implementation."""

    @pytest.fixture
    def queue_config(self) -> MessagingConfig:
        """Create configuration for queue tests."""
        return MessagingConfig(
            backend=QueueBackend.KAFKA,
            kafka=KafkaConfig(
                bootstrap_servers="test:9092",
                topic_prefix="test",
                consumer_group="test-group",
            ),
        )

    @pytest.fixture
    def test_message(self) -> Message:
        """Create a test message."""
        return create_event(
            "test_action",
            {"test": "data"},
            MessageStatus.PENDING,
        )

    @pytest.mark.asyncio
    async def test_kafka_queue_initialization(
        self, queue_config: MessagingConfig
    ) -> None:
        """Test Kafka queue initialization."""
        queue = MessageQueueFactory.create_queue(queue_config)
        assert queue is not None
        assert hasattr(queue, "initialize")
        assert hasattr(queue, "put")
        assert hasattr(queue, "get")

    @pytest.mark.asyncio
    async def test_kafka_queue_initialize_success(
        self, queue_config: MessagingConfig
    ) -> None:
        """Test successful Kafka queue initialization."""
        queue = MessageQueueFactory.create_queue(queue_config)

        with (
            patch.object(queue, "ensure_topics") as mock_topics,
            patch.object(queue, "init_producer") as mock_producer,
            patch.object(queue, "init_consumer") as mock_consumer,
        ):
            await queue.initialize()

            mock_topics.assert_called_once()
            mock_producer.assert_called_once()
            mock_consumer.assert_called_once()

            # Ensure background consumer task is cleaned up to avoid pending-task logs
            await queue.close()

    @pytest.mark.asyncio
    async def test_kafka_queue_initialize_already_running(
        self, queue_config: MessagingConfig
    ) -> None:
        """Test Kafka queue initialization when already running."""
        queue = MessageQueueFactory.create_queue(queue_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        with patch.object(queue, "ensure_topics") as mock_topics:
            await queue.initialize()
            mock_topics.assert_not_called()

    @pytest.mark.asyncio
    async def test_kafka_queue_put_message_success(
        self, queue_config: MessagingConfig, test_message: QueueMessage
    ) -> None:
        """Test successful message put operation."""
        queue = MessageQueueFactory.create_queue(queue_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        with patch.object(queue, "send_message") as mock_send:
            message_id = await queue.put(test_message)  # type: ignore[arg-type]
            assert message_id is not None
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_kafka_queue_put_message_not_initialized(
        self, queue_config: MessagingConfig, test_message: QueueMessage
    ) -> None:
        """Test message put when queue not initialized."""
        queue = MessageQueueFactory.create_queue(queue_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = False

        with pytest.raises(RuntimeError, match="not initialized"):
            await queue.put(test_message)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_kafka_queue_get_message_success(
        self, queue_config: MessagingConfig
    ) -> None:
        """Test successful message get operation."""
        queue = MessageQueueFactory.create_queue(queue_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        with patch.object(queue, "get_next_message") as mock_get:
            mock_get.return_value = "test_message"
            result = await queue.get()
            assert result == "test_message"  # type: ignore[comparison-overlap]
            # Cleanup to avoid pending consumer task warnings
            await queue.close()

    @pytest.mark.asyncio
    async def test_kafka_queue_get_message_timeout(
        self, queue_config: MessagingConfig
    ) -> None:
        """Test message get with timeout."""
        queue = MessageQueueFactory.create_queue(queue_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        with patch.object(queue, "get_next_message") as mock_get:
            mock_get.return_value = None
            result = await queue.get(timeout=1.0)
            assert result is None
            # Cleanup to avoid pending consumer task warnings
            await queue.close()

    @pytest.mark.asyncio
    async def test_kafka_queue_get_message_not_initialized(
        self, queue_config: MessagingConfig
    ) -> None:
        """Test message get when queue not initialized."""
        queue = MessageQueueFactory.create_queue(queue_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = False

        with pytest.raises(RuntimeError, match="not initialized"):
            await queue.get()

    @pytest.mark.asyncio
    async def test_kafka_queue_mark_completed(
        self, queue_config: MessagingConfig
    ) -> None:
        """Test marking message as completed."""
        queue = MessageQueueFactory.create_queue(queue_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True
        kafka_queue._processing = {"test-123"}

        await queue.mark_completed("test-123")
        assert "test-123" not in kafka_queue._processing

    @pytest.mark.asyncio
    async def test_kafka_queue_mark_failed(self, queue_config: MessagingConfig) -> None:
        """Test marking message as failed."""
        queue = MessageQueueFactory.create_queue(queue_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True
        kafka_queue._processing = {"test-123"}

        await queue.mark_failed("test-123")
        assert "test-123" not in kafka_queue._processing

    @pytest.mark.asyncio
    async def test_kafka_queue_cancel_not_supported(
        self, queue_config: MessagingConfig
    ) -> None:
        """Test that cancel operation is not supported."""
        queue = MessageQueueFactory.create_queue(queue_config)

        result = await queue.cancel("test-123")
        assert result is False

    @pytest.mark.asyncio
    async def test_kafka_queue_get_stats(self, queue_config: MessagingConfig) -> None:
        """Test getting queue statistics."""
        queue = MessageQueueFactory.create_queue(queue_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue._stats["total_messages"] = 10
        kafka_queue._stats["processed_messages"] = 5

        stats = queue.get_stats()
        assert stats["total_messages"] == 10
        assert stats["processed_messages"] == 5

    @pytest.mark.asyncio
    async def test_kafka_queue_close_success(
        self, queue_config: MessagingConfig
    ) -> None:
        """Test successful queue close."""
        queue = MessageQueueFactory.create_queue(queue_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        # Create a real asyncio task that can be cancelled
        async def dummy_task() -> None:
            while True:
                await asyncio.sleep(0.1)

        kafka_queue._consumer_task = asyncio.create_task(dummy_task())

        await queue.close()
        assert not kafka_queue.running

    @pytest.mark.asyncio
    async def test_kafka_queue_close_not_running(
        self, queue_config: MessagingConfig
    ) -> None:
        """Test queue close when not running."""
        queue = MessageQueueFactory.create_queue(queue_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = False

        await queue.close()
        assert not kafka_queue.running


@pytest.mark.integration
class TestKafkaMessageRouting:
    """Test Kafka message routing functionality."""

    @pytest.fixture
    def routing_config(self) -> MessagingConfig:
        """Create configuration for routing tests."""
        return MessagingConfig(
            backend=QueueBackend.KAFKA,
            kafka=KafkaConfig(
                bootstrap_servers="test:9092",
                topic_prefix="routing-test",
                consumer_group="routing-group",
            ),
        )

    @pytest.mark.asyncio
    async def test_message_routing_with_priority(
        self, routing_config: MessagingConfig
    ) -> None:
        """Test message routing with priority levels."""
        queue = MessageQueueFactory.create_queue(routing_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        test_message = create_event(
            "test_action",
            {"task": "priority-test"},
            MessageStatus.PENDING,
        )

        with patch.object(queue, "send_message") as mock_send:
            message_id = await queue.put(test_message, priority=QueuePriority.HIGH)

            assert message_id is not None
            mock_send.assert_called_once()

            # Verify the message data structure
            call_args = mock_send.call_args[0][0]
            assert call_args["message"]["body"]["action"] == "test_action"
            assert call_args["priority"] == QueuePriority.HIGH.value
            # Cleanup
            await queue.close()

    @pytest.mark.asyncio
    async def test_message_routing_with_metadata(
        self, routing_config: MessagingConfig
    ) -> None:
        """Test message routing with rich metadata."""
        queue = MessageQueueFactory.create_queue(routing_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        test_message = create_event(
            "test_action",
            {"task": "metadata-test"},
            MessageStatus.PENDING,
        )

        metadata = {
            "source_agent": "test-agent",
            "target_agent": "business-analyst",
            "correlation_id": "test-123",
            "request_id": "req-456",
            "user_id": "user-789",
            "session_id": "session-abc",
            "environment": "test",
            "version": "1.0.0",
        }

        with patch.object(queue, "send_message") as mock_send:
            message_id = await queue.put(test_message, metadata=metadata)

            assert message_id is not None

            # Verify all metadata is preserved
            call_args = mock_send.call_args[0][0]
            assert call_args["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_message_routing_with_ttl(
        self, routing_config: MessagingConfig
    ) -> None:
        """Test message routing with time-to-live."""
        queue = MessageQueueFactory.create_queue(routing_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        test_message = create_event(
            "test_action",
            {"task": "ttl-test"},
            MessageStatus.PENDING,
        )

        with patch.object(queue, "send_message") as mock_send:
            # Send with 30 second TTL
            message_id = await queue.put(test_message, ttl=30.0)

            assert message_id is not None

            # Verify TTL is set
            call_args = mock_send.call_args[0][0]
            assert call_args["ttl"] == 30.0

    @pytest.mark.asyncio
    async def test_message_routing_with_retry_config(
        self, routing_config: MessagingConfig
    ) -> None:
        """Test message routing with retry configuration."""
        queue = MessageQueueFactory.create_queue(routing_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        test_message = create_event(
            "test_action",
            {"task": "retry-test"},
            MessageStatus.PENDING,
        )

        with patch.object(queue, "send_message") as mock_send:
            # Send with custom retry configuration
            message_id = await queue.put(
                test_message,
                max_retries=5,
                metadata={"retry_config": "custom"},
            )

            assert message_id is not None

            # Verify retry configuration is set
            call_args = mock_send.call_args[0][0]
            assert call_args["max_retries"] == 5
            assert call_args["metadata"]["retry_config"] == "custom"


@pytest.mark.integration
class TestKafkaErrorHandling:
    """Test Kafka error handling."""

    @pytest.fixture
    def error_config(self) -> MessagingConfig:
        """Create configuration for error handling tests."""
        return MessagingConfig(
            backend=QueueBackend.KAFKA,
            kafka=KafkaConfig(
                bootstrap_servers="test:9092",
                topic_prefix="error-test",
                consumer_group="error-group",
            ),
        )

    @pytest.mark.asyncio
    async def test_kafka_connection_error_handling(
        self, error_config: MessagingConfig
    ) -> None:
        """Test handling of Kafka connection errors."""
        queue = MessageQueueFactory.create_queue(error_config)

        with patch.object(queue, "ensure_topics") as mock_topics:
            mock_topics.side_effect = Exception("Connection failed")

            with pytest.raises(Exception, match="Connection failed"):
                await queue.initialize()

    @pytest.mark.asyncio
    async def test_kafka_topic_creation_error_handling(
        self, error_config: MessagingConfig
    ) -> None:
        """Test handling of Kafka connection errors."""
        queue = MessageQueueFactory.create_queue(error_config)

        with patch.object(queue, "ensure_topics") as mock_topics:
            mock_topics.side_effect = Exception("Topic creation failed")

            with pytest.raises(Exception, match="Topic creation failed"):
                await queue.initialize()

    @pytest.mark.asyncio
    async def test_kafka_message_send_error_handling(
        self, error_config: MessagingConfig
    ) -> None:
        """Test handling of Kafka message send errors."""
        queue = MessageQueueFactory.create_queue(error_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        test_message = create_event(
            "test_action",
            {"task": "error-test"},
            MessageStatus.PENDING,
        )

        with patch.object(queue, "send_message") as mock_send:
            mock_send.side_effect = Exception("Send failed")

            with pytest.raises(Exception, match="Send failed"):
                await queue.put(test_message)
            # Cleanup
            await queue.close()

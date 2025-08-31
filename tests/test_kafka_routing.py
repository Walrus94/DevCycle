"""
Tests for Kafka routing functionality.

This module tests the Kafka message routing implementation,
including topic management, consumer groups, and message consumption.
"""

import json
from typing import cast
from unittest.mock import Mock, patch

import pytest

from devcycle.core.messaging.config import (
    KafkaConfig,
    MessagingConfig,
    QueueBackend,
    QueuePriority,
)
from devcycle.core.messaging.factory import MessageQueueFactory
from devcycle.core.messaging.implementations.kafka.queue import KafkaMessageQueue
from devcycle.core.protocols.message import AgentAction, create_command


class TestKafkaTopicManagement:
    """Test Kafka topic management functionality."""

    @pytest.fixture
    def topic_config(self) -> MessagingConfig:
        """Create configuration for topic management tests."""
        return MessagingConfig(
            backend=QueueBackend.KAFKA,
            kafka=KafkaConfig(
                bootstrap_servers="test:9092",
                topic_prefix="routing-test",
                num_partitions=3,
                replication_factor=1,
            ),
        )

    @pytest.mark.asyncio
    async def test_topic_creation_success(self, topic_config: MessagingConfig) -> None:
        """Test successful topic creation."""
        queue = MessageQueueFactory.create_queue(topic_config)
        kafka_queue = cast(KafkaMessageQueue, queue)

        # Mock the admin client and topic creation
        mock_admin = Mock()
        mock_admin.create_topics.return_value = None

        with patch(
            "devcycle.core.messaging.implementations.kafka.queue.AdminClient",
            return_value=mock_admin,
        ):
            await kafka_queue.initialize()

            # Verify topic creation was called with correct parameters
            mock_admin.create_topics.assert_called_once()
            created_topic = mock_admin.create_topics.call_args[0][0][0]

            assert created_topic.topic == "routing-test.messages"
            assert created_topic.num_partitions == 3
            assert created_topic.replication_factor == 1

    @pytest.mark.asyncio
    async def test_topic_already_exists(self, topic_config: MessagingConfig) -> None:
        """Test handling when topic already exists."""
        queue = MessageQueueFactory.create_queue(topic_config)
        kafka_queue = cast(KafkaMessageQueue, queue)

        # Mock the admin client to simulate topic already exists
        mock_admin = Mock()
        from confluent_kafka import KafkaException

        mock_admin.create_topics.side_effect = KafkaException("Topic already exists")

        with patch(
            "devcycle.core.messaging.implementations.kafka.queue.AdminClient",
            return_value=mock_admin,
        ):
            # Should not raise an exception
            await kafka_queue.ensure_topics()

            # Verify topic creation was attempted
            mock_admin.create_topics.assert_called_once()

    @pytest.mark.asyncio
    async def test_topic_creation_failure(self, topic_config: MessagingConfig) -> None:
        """Test handling of topic creation failure."""
        queue = MessageQueueFactory.create_queue(topic_config)
        kafka_queue = cast(KafkaMessageQueue, queue)

        # Mock the admin client to simulate topic creation failure
        mock_admin = Mock()
        mock_admin.create_topics.side_effect = Exception("Topic creation failed")

        with patch(
            "devcycle.core.messaging.implementations.kafka.queue.AdminClient",
            return_value=mock_admin,
        ):
            with pytest.raises(Exception, match="Topic creation failed"):
                await kafka_queue.ensure_topics()


class TestKafkaConsumerGroups:
    """Test Kafka consumer group functionality."""

    @pytest.fixture
    def consumer_config(self) -> MessagingConfig:
        """Create configuration for consumer group tests."""
        return MessagingConfig(
            backend=QueueBackend.KAFKA,
            kafka=KafkaConfig(
                bootstrap_servers="test:9092",
                topic_prefix="consumer-test",
                consumer_group="test-consumer-group",
                auto_offset_reset="earliest",
                enable_auto_commit=True,
            ),
        )

    @pytest.mark.asyncio
    async def test_consumer_group_configuration(
        self, consumer_config: MessagingConfig
    ) -> None:
        """Test consumer group configuration."""
        queue = MessageQueueFactory.create_queue(consumer_config)
        kafka_queue = cast(KafkaMessageQueue, queue)

        # Mock the consumer creation
        mock_consumer = Mock()

        with patch(
            "devcycle.core.messaging.implementations.kafka.queue.Consumer",
            return_value=mock_consumer,
        ):
            await kafka_queue.init_consumer()

            # Verify consumer was created with correct configuration
            mock_consumer.subscribe.assert_called_once_with(["consumer-test.messages"])

    @pytest.mark.asyncio
    async def test_consumer_group_subscription(
        self, consumer_config: MessagingConfig
    ) -> None:
        """Test consumer group subscription to topics."""
        queue = MessageQueueFactory.create_queue(consumer_config)
        kafka_queue = cast(KafkaMessageQueue, queue)

        # Mock the consumer
        mock_consumer = Mock()

        with patch(
            "devcycle.core.messaging.implementations.kafka.queue.Consumer",
            return_value=mock_consumer,
        ):
            await kafka_queue.init_consumer()

            # Verify subscription
            mock_consumer.subscribe.assert_called_once()
            subscribed_topics = mock_consumer.subscribe.call_args[0][0]
            assert "consumer-test.messages" in subscribed_topics


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
    async def test_message_routing_to_topic(
        self, routing_config: MessagingConfig
    ) -> None:
        """Test basic message routing to Kafka topic."""
        queue = MessageQueueFactory.create_queue(routing_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        test_message = create_command(
            AgentAction.ANALYZE_BUSINESS_REQUIREMENT.value, {"task": "routing-test"}
        )

        with patch.object(queue, "send_message") as mock_send:
            message_id = await queue.put(test_message)

            assert message_id is not None
            mock_send.assert_called_once()

            # Verify the message data structure
            call_args = mock_send.call_args[0][0]
            assert (
                call_args["message"]["body"]["action"] == "analyze_business_requirement"
            )
            assert call_args["priority"] == QueuePriority.NORMAL.value

    @pytest.mark.asyncio
    async def test_message_routing_with_custom_priority(
        self, routing_config: MessagingConfig
    ) -> None:
        """Test message routing with custom priority levels."""
        queue = MessageQueueFactory.create_queue(routing_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        test_message = create_command(
            AgentAction.ANALYZE_BUSINESS_REQUIREMENT.value, {"task": "priority-test"}
        )

        with patch.object(queue, "send_message") as mock_send:
            # Send with high priority
            high_id = await queue.put(test_message, priority=QueuePriority.HIGH)

            # Send with urgent priority
            urgent_id = await queue.put(test_message, priority=QueuePriority.URGENT)

            assert high_id != urgent_id

            # Verify priorities were set correctly
            call_args = mock_send.call_args_list
            assert call_args[0][0][0]["priority"] == QueuePriority.HIGH.value
            assert call_args[1][0][0]["priority"] == QueuePriority.URGENT.value

    @pytest.mark.asyncio
    async def test_message_routing_with_metadata(
        self, routing_config: MessagingConfig
    ) -> None:
        """Test message routing with rich metadata."""
        queue = MessageQueueFactory.create_queue(routing_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        test_message = create_command(
            AgentAction.ANALYZE_BUSINESS_REQUIREMENT.value, {"task": "metadata-test"}
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

        test_message = create_command(
            AgentAction.ANALYZE_BUSINESS_REQUIREMENT.value, {"task": "ttl-test"}
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

        test_message = create_command(
            AgentAction.ANALYZE_BUSINESS_REQUIREMENT.value, {"task": "retry-test"}
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


class TestKafkaMessageConsumption:
    """Test Kafka message consumption functionality."""

    @pytest.fixture
    def consumption_config(self) -> MessagingConfig:
        """Create configuration for consumption tests."""
        return MessagingConfig(
            backend=QueueBackend.KAFKA,
            kafka=KafkaConfig(
                bootstrap_servers="test:9092",
                topic_prefix="consumption",
                consumer_group="consumption-group",
            ),
        )

    @pytest.mark.asyncio
    async def test_message_consumption_success(
        self, consumption_config: MessagingConfig
    ) -> None:
        """Test successful message consumption."""
        queue = MessageQueueFactory.create_queue(consumption_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        # Mock a Kafka message
        mock_kafka_message = Mock()
        message_data = json.dumps(
            {
                "queue_id": "test-123",
                "priority": QueuePriority.NORMAL.value,
                "created_at": 1234567890.0,
                "ttl": None,
                "max_retries": 3,
                "metadata": {"test": True},
                "message": {
                    "header": {
                        "message_id": "msg-123",
                        "agent_id": "test-agent",
                        "message_type": "command",
                        "timestamp": "2025-08-31T00:00:00Z",
                        "version": "1.0",
                    },
                    "body": {
                        "action": "analyze_business_requirement",
                        "data": {"task": "test"},
                        "status": "pending",
                    },
                },
            }
        ).encode("utf-8")

        # Mock the value method to return the message data
        mock_kafka_message.value.return_value = message_data

        # Mock the error method to return None (no error)
        mock_kafka_message.error.return_value = None

        # Mock the consumer to return our message
        mock_consumer = Mock()
        mock_consumer.poll.return_value = mock_kafka_message
        kafka_queue._consumer = mock_consumer

        # Test message consumption
        result = await kafka_queue.get_next_message()

        assert result is not None
        assert result.queue_id == "test-123"
        assert result.priority == QueuePriority.NORMAL
        assert result.metadata is not None
        assert result.metadata["test"] is True

    @pytest.mark.asyncio
    async def test_message_consumption_with_error(
        self, consumption_config: MessagingConfig
    ) -> None:
        """Test message consumption with Kafka errors."""
        queue = MessageQueueFactory.create_queue(consumption_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        # Mock Kafka error
        mock_kafka_message = Mock()
        mock_error = Mock()
        mock_error.code = lambda: 1  # Non-EOF error
        mock_kafka_message.error.return_value = mock_error

        mock_consumer = Mock()
        mock_consumer.poll.return_value = mock_kafka_message
        kafka_queue._consumer = mock_consumer

        # Test error handling
        result = await kafka_queue.get_next_message()

        assert result is None  # Should return None for errors

    @pytest.mark.asyncio
    async def test_message_consumption_timeout(
        self, consumption_config: MessagingConfig
    ) -> None:
        """Test message consumption timeout handling."""
        queue = MessageQueueFactory.create_queue(consumption_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        # Mock consumer timeout
        mock_consumer = Mock()
        mock_consumer.poll.return_value = None  # No message available
        kafka_queue._consumer = mock_consumer

        # Test timeout handling
        result = await kafka_queue.get_next_message()

        assert result is None  # Should return None for timeout


class TestKafkaRoutingIntegration:
    """Integration tests for Kafka routing."""

    @pytest.fixture
    def integration_config(self) -> MessagingConfig:
        """Create configuration for integration tests."""
        return MessagingConfig(
            backend=QueueBackend.KAFKA,
            kafka=KafkaConfig(
                bootstrap_servers="test:9092",
                topic_prefix="integration",
                consumer_group="integration-group",
            ),
        )

    @pytest.mark.asyncio
    async def test_end_to_end_message_routing(
        self, integration_config: MessagingConfig
    ) -> None:
        """Test end-to-end message routing through Kafka."""
        queue = MessageQueueFactory.create_queue(integration_config)
        kafka_queue = cast(KafkaMessageQueue, queue)
        kafka_queue.running = True

        # Create test message
        test_message = create_command(
            AgentAction.ANALYZE_BUSINESS_REQUIREMENT.value, {"task": "integration-test"}
        )

        # Mock the send operation
        with patch.object(queue, "send_message") as mock_send:
            # Send message
            message_id = await queue.put(
                test_message,
                priority=QueuePriority.HIGH,
                metadata={"integration": True},
                ttl=60.0,
                max_retries=3,
            )

            assert message_id is not None

            # Verify message was sent with correct parameters
            call_args = mock_send.call_args[0][0]
            assert (
                call_args["message"]["body"]["action"] == "analyze_business_requirement"
            )
            assert call_args["priority"] == QueuePriority.HIGH.value
            assert call_args["metadata"]["integration"] is True
            assert call_args["ttl"] == 60.0
            assert call_args["max_retries"] == 3


if __name__ == "__main__":
    pytest.main([__file__])

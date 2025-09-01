"""
Kafka message queue implementation.

This module implements the MessageQueueInterface using Apache Kafka
as the backend for scalable, reliable message queuing.
"""

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from confluent_kafka import Consumer, KafkaError, KafkaException, Producer
from confluent_kafka.admin import AdminClient, NewTopic

from devcycle.core.protocols.message import Message

from ....logging import get_logger
from ...config import KafkaConfig, MessagingConfig, QueuePriority
from ...interfaces.queue import MessageQueueInterface, QueueMessage


class KafkaMessageQueue(MessageQueueInterface):
    """
    Kafka-based message queue implementation.

    This implementation uses Kafka topics for message queuing, providing
    scalability, reliability, and persistence out of the box.
    """

    def __init__(self, config: MessagingConfig):
        self.config = config
        self.kafka_config = config.kafka or KafkaConfig()
        self.logger = get_logger(__name__)

        # Kafka clients
        self._producer: Optional[Producer] = None
        self._consumer: Optional[Consumer] = None
        self._admin_client: Optional[AdminClient] = None

        # Thread pool for Kafka operations
        self._executor = ThreadPoolExecutor(max_workers=4)

        # Topic management
        self._topics_created = False
        self._topic_name = f"{self.kafka_config.topic_prefix}.messages"

        # Message tracking
        self._processing: set[str] = set()
        self._stats = {
            "total_messages": 0,
            "processed_messages": 0,
            "failed_messages": 0,
            "dropped_messages": 0,
            "avg_processing_time": 0.0,
        }

        # Async support
        self._lock = asyncio.Lock()
        self.running = False
        self._consumer_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize the Kafka queue."""
        async with self._lock:
            if self.running:
                return

            # Create topics if they don't exist
            await self.ensure_topics()

            # Initialize producer
            await self.init_producer()

            # Initialize consumer
            await self.init_consumer()

            # Start consumer loop
            self._consumer_task = asyncio.create_task(self._consumer_loop())

            self.running = True

    async def put(
        self,
        message: Message,
        priority: Optional[QueuePriority] = None,
        ttl: Optional[float] = None,
        max_retries: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Put a message in the queue."""
        if not self.running:
            raise RuntimeError("Queue not initialized")

        # Generate unique message ID
        message_id = str(uuid.uuid4())

        # Create queue message
        queue_message = QueueMessage(
            message=message,
            priority=priority if priority is not None else self.config.default_priority,
            created_at=time.time(),
            queue_id=message_id,
            ttl=ttl if ttl is not None else self.config.default_ttl,
            max_retries=max_retries
            if max_retries is not None
            else self.config.default_max_retries,
            metadata=metadata if metadata is not None else {},
        )

        # Update statistics
        self._stats["total_messages"] += 1

        # Send to Kafka
        await self.send_message(
            {
                "message": message.to_dict(),
                "priority": queue_message.priority.value,
                "created_at": queue_message.created_at,
                "queue_id": queue_message.queue_id,
                "ttl": queue_message.ttl,
                "max_retries": queue_message.max_retries,
                "metadata": queue_message.metadata,
            }
        )

        return message_id

    async def get(self, timeout: Optional[float] = None) -> Optional[QueueMessage]:
        """Get next message from Kafka topic."""
        if not self.running:
            raise RuntimeError("Queue not initialized. Call initialize() first.")

        # For Kafka, we need to implement a polling mechanism
        # This is a simplified version - in practice, you'd want more
        # sophisticated handling
        start_time = time.time()

        while True:
            # Check if we have a message in the consumer
            message = await self.get_next_message()
            if message:
                return message

            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                return None

            # Wait a bit before polling again
            await asyncio.sleep(0.1)

    async def mark_completed(self, queue_id: str) -> None:
        """Mark message as completed."""
        async with self._lock:
            if queue_id in self._processing:
                self._processing.remove(queue_id)
                self._stats["processed_messages"] += 1

    async def mark_failed(self, queue_id: str, retry: bool = True) -> None:
        """Mark message as failed, optionally retrying."""
        async with self._lock:
            if queue_id in self._processing:
                self._processing.remove(queue_id)

                if retry:
                    # For Kafka, we could send to a retry topic
                    # For now, just mark as failed
                    pass

                self._stats["failed_messages"] += 1

    async def cancel(self, queue_id: str) -> bool:
        """Cancel a queued message."""
        # In Kafka, we can't easily cancel messages that are already sent
        # We could mark them as cancelled in metadata, but they'll still be consumed
        # For now, return False to indicate cancellation is not supported
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            **self._stats,
            "processing_count": len(self._processing),
            "backend": "kafka",
            "topic": self._topic_name,
            "bootstrap_servers": self.kafka_config.bootstrap_servers,
        }

    async def close(self) -> None:
        """Close the Kafka queue and cleanup resources."""
        async with self._lock:
            if not self.running:
                return

            # Stop consumer
            if self._consumer_task:
                self._consumer_task.cancel()
                try:
                    await self._consumer_task
                except asyncio.CancelledError:
                    pass

            # Close Kafka clients
            if self._consumer:
                self._consumer.close()
            if self._producer:
                # confluent_kafka.Producer does not expose close();
                # flush to ensure delivery
                self._producer.flush()
            # AdminClient does not require explicit close
            # Set references to None for GC friendliness
            self._consumer = None
            self._producer = None
            self._admin_client = None

            # Shutdown thread pool
            self._executor.shutdown(wait=True)

            self.running = False

    async def ensure_topics(self) -> None:
        """Ensure Kafka topics exist."""
        if self._topics_created:
            return

        # Create admin client
        admin_config = {
            "bootstrap.servers": self.kafka_config.bootstrap_servers,
        }
        self._admin_client = AdminClient(admin_config)

        # Create topic
        topic = NewTopic(
            self._topic_name,
            num_partitions=self.kafka_config.num_partitions,
            replication_factor=self.kafka_config.replication_factor,
        )

        # Create topic (this is synchronous, so we run it in thread pool)
        loop = asyncio.get_event_loop()
        try:
            if self._admin_client is not None:

                def create_topics() -> Any:
                    r = self._admin_client.create_topics(  # type: ignore[union-attr]
                        [topic]
                    )
                    return r

                await loop.run_in_executor(self._executor, create_topics)
            else:
                raise RuntimeError("Admin client not initialized")
        except KafkaException as e:
            # Topic might already exist, which is fine
            if "already exists" not in str(e):
                raise

        self._topics_created = True

    async def init_producer(self) -> None:
        """Initialize Kafka producer."""
        producer_config = {
            "bootstrap.servers": self.kafka_config.bootstrap_servers,
            "acks": self.kafka_config.acks,
            "retries": self.kafka_config.retries,
            "batch.size": self.kafka_config.batch_size,
            "linger.ms": self.kafka_config.linger_ms,
        }

        loop = asyncio.get_event_loop()
        self._producer = await loop.run_in_executor(
            self._executor, lambda: Producer(producer_config)
        )

    async def init_consumer(self) -> None:
        """Initialize Kafka consumer."""
        consumer_config = {
            "bootstrap.servers": self.kafka_config.bootstrap_servers,
            "group.id": self.kafka_config.consumer_group,
            "auto.offset.reset": self.kafka_config.auto_offset_reset,
            "enable.auto.commit": self.kafka_config.enable_auto_commit,
            "session.timeout.ms": self.kafka_config.session_timeout_ms,
            "heartbeat.interval.ms": self.kafka_config.heartbeat_interval_ms,
        }

        loop = asyncio.get_event_loop()
        self._consumer = await loop.run_in_executor(
            self._executor, lambda: Consumer(consumer_config)
        )

        # Subscribe to topic
        if self._consumer is not None:
            self._consumer.subscribe([self._topic_name])

    async def send_message(self, message_data: Dict[str, Any]) -> None:
        """Send message to Kafka topic."""
        if self._producer is None:
            raise RuntimeError("Producer not initialized")

        # Serialize message
        message_json = json.dumps(message_data)

        # Send to Kafka
        loop = asyncio.get_event_loop()
        if self._producer is not None:

            def produce_message() -> Any:
                return self._producer.produce(  # type: ignore[union-attr]
                    self._topic_name,
                    message_json.encode("utf-8"),
                    callback=self._delivery_report,
                )

            await loop.run_in_executor(self._executor, produce_message)
        else:
            raise RuntimeError("Producer not initialized")

    async def get_next_message(self) -> Optional[QueueMessage]:
        """Get next message from consumer."""
        # Poll for messages (this is synchronous, so run in thread pool)
        loop = asyncio.get_event_loop()
        try:
            if self._consumer is None:
                return None

            message = await loop.run_in_executor(
                self._executor,
                lambda: self._consumer.poll(timeout=0.1),  # type: ignore[union-attr]
            )

            if message is None:
                return None

            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    return None
                else:
                    # Log error and continue
                    self.logger.error(
                        "Kafka consumer error",
                        error_code=message.error().code(),
                        error_message=str(message.error()),
                        event_type="kafka_consumer_error",
                    )
                    return None

            # Parse message
            message_data = json.loads(message.value().decode("utf-8"))

            # Reconstruct queue message from consumed data
            queue_message = QueueMessage(
                message=Message.from_dict(message_data["message"]),
                priority=QueuePriority(message_data["priority"]),
                created_at=message_data["created_at"],
                queue_id=message_data["queue_id"],
                ttl=message_data["ttl"],
                max_retries=message_data["max_retries"],
                metadata=message_data["metadata"],
            )

            # Mark as processing
            async with self._lock:
                self._processing.add(queue_message.queue_id)

            return queue_message

        except Exception as e:
            self.logger.error(
                "Error getting message from Kafka",
                error_type=type(e).__name__,
                error_message=str(e),
                event_type="kafka_message_error",
            )
            return None

    async def _consumer_loop(self) -> None:
        """Main consumer loop."""
        while self.running:
            try:
                # Get next message
                message = await self.get_next_message()
                if message:
                    # Process message (in a real implementation, you'd have a callback)
                    pass

                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    "Error in consumer loop",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    event_type="kafka_consumer_loop_error",
                )
                await asyncio.sleep(1)

    def _delivery_report(self, err: Any, msg: Any) -> None:
        """Callback for message delivery reports."""
        if err is not None:
            self.logger.error(
                "Message delivery failed",
                error_message=str(err),
                topic=msg.topic() if msg else None,
                partition=msg.partition() if msg else None,
                event_type="kafka_delivery_failed",
            )
        else:
            self.logger.debug(
                "Message delivered successfully",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
                event_type="kafka_delivery_success",
            )

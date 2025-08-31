"""
Kafka messaging demonstration for DevCycle.

This example shows how to use the Kafka message queue implementation
for agent communication.
"""

import asyncio
import time

from devcycle.core.messaging.config import (
    KafkaConfig,
    MessagingConfig,
    QueueBackend,
    QueuePriority,
)
from devcycle.core.messaging.factory import MessageQueueFactory
from devcycle.core.protocols.message import MessageStatus, create_event


async def main() -> None:
    """Main demonstration function."""
    print("Starting Kafka messaging demonstration...")

    # Create configuration for Kafka backend
    config = MessagingConfig(
        backend=QueueBackend.KAFKA,
        kafka=KafkaConfig(
            bootstrap_servers="localhost:9092",
            topic_prefix="demo",
            consumer_group="demo-consumer",
        ),
    )

    # Create message queue
    queue = MessageQueueFactory.create_queue(config)

    try:
        # Initialize the queue
        print("Initializing Kafka queue...")
        await queue.initialize()
        print("Queue initialized successfully!")

        # Create a test message
        message = create_event(
            "analysis_started",
            {"status": "started", "timestamp": "2025-08-31T00:00:00Z"},
            MessageStatus.IN_PROGRESS,
        )

        # Put message in queue
        message_id = await queue.put(
            message,
            priority=QueuePriority.NORMAL,
            metadata={"demo": True, "backend": "kafka"},
        )

        print(f"Message sent with ID: {message_id}")

        # Wait a moment for message to be processed
        await asyncio.sleep(1)

        # Get message from queue
        print("Retrieving message from queue...")
        received_message = await queue.get(timeout=5.0)

        if received_message:
            print(f"Received message: {received_message.message}")
            print(f"Priority: {received_message.priority}")
            print(f"Metadata: {received_message.metadata}")

            # Mark message as completed
            await queue.mark_completed(received_message.queue_id)
            print("Message marked as completed")
        else:
            print("No message received")

    except Exception as e:
        print(f"Error during demonstration: {e}")
    finally:
        # Clean up
        print("Cleaning up...")
        await queue.close()
        print("Demonstration completed!")


async def run_performance_test() -> None:
    """Run a simple performance test."""
    print("\nStarting performance test...")

    config = MessagingConfig(
        backend=QueueBackend.KAFKA,
        kafka=KafkaConfig(
            bootstrap_servers="localhost:9092",
            topic_prefix="perf-test",
            consumer_group="perf-consumer",
        ),
    )

    queue = MessageQueueFactory.create_queue(config)

    try:
        await queue.initialize()

        # Send multiple messages
        start_time = time.time()
        message_count = 100

        for i in range(message_count):
            message = create_event(
                f"test_action_{i}",
                {"index": i, "timestamp": time.time()},
                MessageStatus.PENDING,
            )

            await queue.put(message, priority=QueuePriority.NORMAL)

        send_time = time.time() - start_time
        print(f"Sent {message_count} messages in {send_time:.2f} seconds")
        print(f"Rate: {message_count / send_time:.2f} messages/second")

        # Receive messages
        start_time = time.time()
        received_count = 0

        for _ in range(message_count):
            received_message = await queue.get(timeout=1.0)
            if received_message:
                await queue.mark_completed(received_message.queue_id)
                received_count += 1

        receive_time = time.time() - start_time
        print(f"Received {received_count} messages in {receive_time:.2f} seconds")
        print(f"Rate: {received_count / receive_time:.2f} messages/second")

    except Exception as e:
        print(f"Error during performance test: {e}")
    finally:
        await queue.close()


if __name__ == "__main__":
    asyncio.run(main())

"""
Redis Pub/Sub implementation for ACP real-time events.

This module provides Redis-based event publishing and subscription
for real-time ACP system updates.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

import redis

from ...cache.redis_cache import RedisCache
from ...logging import get_logger
from .event_types import (
    ACPEvent,
    ACPEventType,
    AgentStatusEvent,
    SystemHealthEvent,
    WorkflowProgressEvent,
)

logger = get_logger(__name__)


class RedisACPEvents:
    """Redis Pub/Sub service for ACP real-time events."""

    def __init__(self, redis_cache: RedisCache):
        """
        Initialize Redis ACP events service.

        Args:
            redis_cache: Redis cache instance for Pub/Sub operations
        """
        self.redis = redis_cache.redis_client  # Get the underlying redis-py client
        self.key_prefix = "acp:events:"
        self.subscribers: Dict[str, Set[Callable]] = {}
        self.pubsub: Optional[redis.client.PubSub] = None
        self._running = False

    def _get_channel(self, channel: str) -> str:
        """Get the full Redis channel name with prefix."""
        return f"{self.key_prefix}{channel}"

    async def start(self) -> None:
        """Start the Redis events service."""
        if self._running:
            return

        self.pubsub = self.redis.pubsub()
        self._running = True

        # Start background task for processing events
        asyncio.create_task(self._process_events())
        logger.info("Redis ACP Events service started")

    async def stop(self) -> None:
        """Stop the Redis events service."""
        if not self._running:
            return

        self._running = False
        if self.pubsub is not None:
            self.pubsub.close()
        logger.info("Redis ACP Events service stopped")

    async def _process_events(self) -> None:
        """Background task to process incoming events."""
        while self._running:
            try:
                if self.pubsub is None:
                    await asyncio.sleep(0.1)
                    continue
                message = self.pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "message":
                    await self._handle_event(message)
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                await asyncio.sleep(1)

    async def _handle_event(self, message: Dict[str, Any]) -> None:
        """Handle incoming event message."""
        try:
            channel = message["channel"].decode("utf-8")
            data = json.loads(message["data"].decode("utf-8"))

            # Notify subscribers
            if channel in self.subscribers:
                for callback in self.subscribers[channel]:
                    try:
                        await callback(data)
                    except Exception as e:
                        logger.error(f"Error in event callback: {e}")
        except Exception as e:
            logger.error(f"Error handling event: {e}")

    # Agent Events
    async def publish_agent_status_change(
        self, agent_id: str, old_status: str, new_status: str
    ) -> None:
        """Publish agent status change event."""
        event = AgentStatusEvent(agent_id, old_status, new_status)
        await self._publish_event("agent_status", event)
        logger.debug(
            f"Published agent status change: {agent_id} {old_status} -> {new_status}"
        )

    async def publish_agent_registered(
        self, agent_id: str, agent_info: Dict[str, Any]
    ) -> None:
        """Publish agent registration event."""
        timestamp = datetime.now(timezone.utc).timestamp()
        event = ACPEvent(
            event_type=ACPEventType.AGENT_REGISTERED,
            event_id=f"agent_registered_{agent_id}_{timestamp}",
            source=agent_id,
            data={"agent_id": agent_id, "agent_info": agent_info},
        )
        await self._publish_event("agent_events", event)
        logger.debug(f"Published agent registered: {agent_id}")

    async def publish_agent_unregistered(self, agent_id: str) -> None:
        """Publish agent unregistration event."""
        timestamp = datetime.now(timezone.utc).timestamp()
        event = ACPEvent(
            event_type=ACPEventType.AGENT_UNREGISTERED,
            event_id=f"agent_unregistered_{agent_id}_{timestamp}",
            source=agent_id,
            data={"agent_id": agent_id},
        )
        await self._publish_event("agent_events", event)
        logger.debug(f"Published agent unregistered: {agent_id}")

    async def publish_agent_health_check_failed(
        self, agent_id: str, error: str
    ) -> None:
        """Publish agent health check failure event."""
        timestamp = datetime.now(timezone.utc).timestamp()
        event = ACPEvent(
            event_type=ACPEventType.AGENT_HEALTH_CHECK_FAILED,
            event_id=f"agent_health_failed_{agent_id}_{timestamp}",
            source=agent_id,
            data={"agent_id": agent_id, "error": error},
        )
        await self._publish_event("agent_events", event)
        logger.warning(f"Published agent health check failed: {agent_id} - {error}")

    # Workflow Events
    async def publish_workflow_started(
        self, workflow_id: str, workflow_info: Dict[str, Any]
    ) -> None:
        """Publish workflow started event."""
        timestamp = datetime.now(timezone.utc).timestamp()
        event = ACPEvent(
            event_type=ACPEventType.WORKFLOW_STARTED,
            event_id=f"workflow_started_{workflow_id}_{timestamp}",
            source=workflow_id,
            data={"workflow_id": workflow_id, "workflow_info": workflow_info},
        )
        await self._publish_event("workflow_events", event)
        logger.debug(f"Published workflow started: {workflow_id}")

    async def publish_workflow_progress(
        self, workflow_id: str, step_id: str, progress: int
    ) -> None:
        """Publish workflow progress event."""
        event = WorkflowProgressEvent(workflow_id, step_id, progress)
        await self._publish_event(f"workflow_events:{workflow_id}", event)
        await self._publish_event(
            "workflow_events", event
        )  # Also publish to general channel
        logger.debug(
            f"Published workflow progress: {workflow_id} step {step_id} - {progress}%"
        )

    async def publish_workflow_step_completed(
        self, workflow_id: str, step_id: str, result: Dict[str, Any]
    ) -> None:
        """Publish workflow step completion event."""
        timestamp = datetime.now(timezone.utc).timestamp()
        event = ACPEvent(
            event_type=ACPEventType.WORKFLOW_STEP_COMPLETED,
            event_id=f"workflow_step_completed_{workflow_id}_{step_id}_{timestamp}",
            source=workflow_id,
            data={"workflow_id": workflow_id, "step_id": step_id, "result": result},
        )
        await self._publish_event(f"workflow_events:{workflow_id}", event)
        await self._publish_event("workflow_events", event)
        logger.debug(f"Published workflow step completed: {workflow_id} step {step_id}")

    async def publish_workflow_step_failed(
        self, workflow_id: str, step_id: str, error: str
    ) -> None:
        """Publish workflow step failure event."""
        timestamp = datetime.now(timezone.utc).timestamp()
        event = ACPEvent(
            event_type=ACPEventType.WORKFLOW_STEP_FAILED,
            event_id=f"workflow_step_failed_{workflow_id}_{step_id}_{timestamp}",
            source=workflow_id,
            data={"workflow_id": workflow_id, "step_id": step_id, "error": error},
        )
        await self._publish_event(f"workflow_events:{workflow_id}", event)
        await self._publish_event("workflow_events", event)
        logger.debug(
            f"Published workflow step failed: {workflow_id} step {step_id} - {error}"
        )

    async def publish_workflow_completed(
        self, workflow_id: str, result: Dict[str, Any]
    ) -> None:
        """Publish workflow completion event."""
        timestamp = datetime.now(timezone.utc).timestamp()
        event = ACPEvent(
            event_type=ACPEventType.WORKFLOW_COMPLETED,
            event_id=f"workflow_completed_{workflow_id}_{timestamp}",
            source=workflow_id,
            data={"workflow_id": workflow_id, "result": result},
        )
        await self._publish_event(f"workflow_events:{workflow_id}", event)
        await self._publish_event("workflow_events", event)
        logger.debug(f"Published workflow completed: {workflow_id}")

    async def publish_workflow_failed(self, workflow_id: str, error: str) -> None:
        """Publish workflow failure event."""
        timestamp = datetime.now(timezone.utc).timestamp()
        event = ACPEvent(
            event_type=ACPEventType.WORKFLOW_FAILED,
            event_id=f"workflow_failed_{workflow_id}_{timestamp}",
            source=workflow_id,
            data={"workflow_id": workflow_id, "error": error},
        )
        await self._publish_event(f"workflow_events:{workflow_id}", event)
        await self._publish_event("workflow_events", event)
        logger.warning(f"Published workflow failed: {workflow_id} - {error}")

    # System Events
    async def publish_system_health_update(
        self, component: str, status: str, metrics: Dict[str, Any]
    ) -> None:
        """Publish system health update event."""
        event = SystemHealthEvent(component, status, metrics)
        await self._publish_event("system_health", event)
        logger.debug(f"Published system health update: {component} - {status}")

    async def publish_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Publish performance metrics event."""
        event = ACPEvent(
            event_type=ACPEventType.PERFORMANCE_METRICS,
            event_id=f"performance_metrics_{datetime.now(timezone.utc).timestamp()}",
            source="system",
            data=metrics,
        )
        await self._publish_event("performance_metrics", event)
        logger.debug("Published performance metrics")

    async def publish_error_alert(
        self, component: str, error: str, severity: str = "error"
    ) -> None:
        """Publish error alert event."""
        timestamp = datetime.now(timezone.utc).timestamp()
        event = ACPEvent(
            event_type=ACPEventType.ERROR_ALERT,
            event_id=f"error_alert_{component}_{timestamp}",
            source=component,
            data={"component": component, "error": error, "severity": severity},
        )
        await self._publish_event("error_alerts", event)
        logger.warning(f"Published error alert: {component} - {error}")

    # Subscription Management
    async def subscribe_to_agent_events(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Subscribe to agent events."""
        channel = self._get_channel("agent_events")
        if self.pubsub is not None:
            self.pubsub.subscribe(channel)
        if callback is not None:
            if channel not in self.subscribers:
                self.subscribers[channel] = set()
            self.subscribers[channel].add(callback)
        logger.debug("Subscribed to agent events")

    async def subscribe_to_workflow_events(
        self,
        workflow_id: Optional[str] = None,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        """Subscribe to workflow events."""
        if workflow_id:
            channel = self._get_channel(f"workflow_events:{workflow_id}")
        else:
            channel = self._get_channel("workflow_events")

        if self.pubsub is not None:
            self.pubsub.subscribe(channel)
        if callback is not None:
            if channel not in self.subscribers:
                self.subscribers[channel] = set()
            self.subscribers[channel].add(callback)
        logger.debug(f"Subscribed to workflow events: {workflow_id or 'all'}")

    async def subscribe_to_system_health(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Subscribe to system health events."""
        channel = self._get_channel("system_health")
        if self.pubsub is not None:
            self.pubsub.subscribe(channel)
        if callback is not None:
            if channel not in self.subscribers:
                self.subscribers[channel] = set()
            self.subscribers[channel].add(callback)
        logger.debug("Subscribed to system health events")

    async def subscribe_to_performance_metrics(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Subscribe to performance metrics events."""
        channel = self._get_channel("performance_metrics")
        if self.pubsub is not None:
            self.pubsub.subscribe(channel)
        if callback is not None:
            if channel not in self.subscribers:
                self.subscribers[channel] = set()
            self.subscribers[channel].add(callback)
        logger.debug("Subscribed to performance metrics events")

    async def subscribe_to_error_alerts(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Subscribe to error alert events."""
        channel = self._get_channel("error_alerts")
        if self.pubsub is not None:
            self.pubsub.subscribe(channel)
        if callback is not None:
            if channel not in self.subscribers:
                self.subscribers[channel] = set()
            self.subscribers[channel].add(callback)
        logger.debug("Subscribed to error alert events")

    # Internal Methods
    async def _publish_event(self, channel: str, event: ACPEvent) -> None:
        """Publish an event to a Redis channel."""
        try:
            full_channel = self._get_channel(channel)
            event_data = event.model_dump()
            self.redis.publish(full_channel, json.dumps(event_data, default=str))
        except Exception as e:
            logger.error(f"Error publishing event to {channel}: {e}")

    async def get_active_channels(self) -> List[str]:
        """Get list of active Redis channels."""
        try:
            channels = self.redis.pubsub_channels(self._get_channel("*"))
            return [str(channel) for channel in channels]
        except Exception as e:
            logger.error(f"Error getting active channels: {e}")
            return []

    async def get_subscriber_count(self, channel: str) -> int:
        """Get number of subscribers for a channel."""
        try:
            full_channel = self._get_channel(channel)
            count = self.redis.pubsub_numsub(full_channel)
            return count[0][1] if count and len(count) > 0 else 0
        except Exception as e:
            logger.error(f"Error getting subscriber count for {channel}: {e}")
            return 0

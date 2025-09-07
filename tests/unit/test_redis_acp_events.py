"""Unit tests for Redis ACP Events service."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from devcycle.core.acp.events.event_types import ACPEventType
from devcycle.core.acp.events.redis_events import RedisACPEvents


class TestRedisACPEvents:
    """Test cases for Redis ACP Events service."""

    @pytest.fixture
    def mock_redis_cache(self):
        """Create a mock Redis cache."""
        mock_cache = Mock()
        mock_redis = Mock()
        mock_redis.publish = Mock()

        # Create a proper mock pubsub object
        mock_pubsub = Mock()
        mock_pubsub.subscribe = Mock()
        mock_pubsub.close = Mock()
        mock_pubsub.get_message = AsyncMock(return_value=None)
        mock_redis.pubsub.return_value = mock_pubsub

        mock_redis.pubsub_channels = Mock(return_value=[])
        mock_redis.pubsub_numsub = Mock(return_value={})
        mock_cache.redis_client = mock_redis
        mock_cache.redis = mock_redis
        return mock_cache

    @pytest.fixture
    def redis_events(self, mock_redis_cache):
        """Create RedisACPEvents instance with mocked dependencies."""
        return RedisACPEvents(mock_redis_cache)

    @pytest.mark.asyncio
    async def test_publish_agent_status_change(self, redis_events, mock_redis_cache):
        """Test publishing agent status change event."""
        agent_id = "test-agent-1"
        old_status = "offline"
        new_status = "online"

        await redis_events.publish_agent_status_change(agent_id, old_status, new_status)

        # Verify Redis publish was called
        mock_redis_cache.redis_client.publish.assert_called_once()
        call_args = mock_redis_cache.redis_client.publish.call_args

        # Check channel name
        assert call_args[0][0] == "acp:events:agent_status"

        # Check event data
        event_data = json.loads(call_args[0][1])
        assert event_data["event_type"] == ACPEventType.AGENT_STATUS_CHANGED
        assert event_data["source"] == agent_id
        assert event_data["data"]["agent_id"] == agent_id
        assert event_data["data"]["old_status"] == old_status
        assert event_data["data"]["new_status"] == new_status

    @pytest.mark.asyncio
    async def test_publish_agent_registered(self, redis_events, mock_redis_cache):
        """Test publishing agent registration event."""
        agent_id = "test-agent-1"
        agent_info = {
            "agent_name": "Test Agent",
            "agent_version": "1.0.0",
            "capabilities": ["test_capability"],
        }

        await redis_events.publish_agent_registered(agent_id, agent_info)

        # Verify Redis publish was called
        mock_redis_cache.redis_client.publish.assert_called_once()
        call_args = mock_redis_cache.redis_client.publish.call_args

        # Check channel name
        assert call_args[0][0] == "acp:events:agent_events"

        # Check event data
        event_data = json.loads(call_args[0][1])
        assert event_data["event_type"] == ACPEventType.AGENT_REGISTERED
        assert event_data["source"] == agent_id
        assert event_data["data"]["agent_id"] == agent_id
        assert event_data["data"]["agent_info"] == agent_info

    @pytest.mark.asyncio
    async def test_publish_workflow_progress(self, redis_events, mock_redis_cache):
        """Test publishing workflow progress event."""
        workflow_id = "test-workflow-1"
        step_id = "step-1"
        progress = 50

        await redis_events.publish_workflow_progress(workflow_id, step_id, progress)

        # Verify Redis publish was called twice (general and specific channels)
        assert mock_redis_cache.redis_client.publish.call_count == 2

        # Check specific workflow channel (first call)
        specific_call = mock_redis_cache.redis_client.publish.call_args_list[0]
        assert specific_call[0][0] == f"acp:events:workflow_events:{workflow_id}"

        # Check general workflow events channel (second call)
        general_call = mock_redis_cache.redis_client.publish.call_args_list[1]
        assert general_call[0][0] == "acp:events:workflow_events"

        # Check event data
        event_data = json.loads(specific_call[0][1])
        assert event_data["event_type"] == ACPEventType.WORKFLOW_PROGRESS
        assert event_data["source"] == workflow_id
        assert event_data["data"]["workflow_id"] == workflow_id
        assert event_data["data"]["step_id"] == step_id
        assert event_data["data"]["progress"] == progress
        assert event_data["data"]["percentage"] == 50

    @pytest.mark.asyncio
    async def test_publish_workflow_step_completed(
        self, redis_events, mock_redis_cache
    ):
        """Test publishing workflow step completion event."""
        workflow_id = "test-workflow-1"
        step_id = "step-1"
        result = {"output": "test_result"}

        await redis_events.publish_workflow_step_completed(workflow_id, step_id, result)

        # Verify Redis publish was called twice
        assert mock_redis_cache.redis_client.publish.call_count == 2

        # Check event data
        call_args = mock_redis_cache.redis_client.publish.call_args_list[0]
        event_data = json.loads(call_args[0][1])
        assert event_data["event_type"] == ACPEventType.WORKFLOW_STEP_COMPLETED
        assert event_data["source"] == workflow_id
        assert event_data["data"]["workflow_id"] == workflow_id
        assert event_data["data"]["step_id"] == step_id
        assert event_data["data"]["result"] == result

    @pytest.mark.asyncio
    async def test_publish_system_health_update(self, redis_events, mock_redis_cache):
        """Test publishing system health update event."""
        component = "redis"
        status = "healthy"
        metrics = {"cpu_usage": 45.2, "memory_usage": 78.1}

        await redis_events.publish_system_health_update(component, status, metrics)

        # Verify Redis publish was called
        mock_redis_cache.redis_client.publish.assert_called_once()
        call_args = mock_redis_cache.redis_client.publish.call_args

        # Check channel name
        assert call_args[0][0] == "acp:events:system_health"

        # Check event data
        event_data = json.loads(call_args[0][1])
        assert event_data["event_type"] == ACPEventType.SYSTEM_HEALTH_UPDATE
        assert event_data["source"] == component
        assert event_data["data"]["component"] == component
        assert event_data["data"]["status"] == status
        assert event_data["data"]["metrics"] == metrics

    @pytest.mark.asyncio
    async def test_publish_error_alert(self, redis_events, mock_redis_cache):
        """Test publishing error alert event."""
        component = "workflow_engine"
        error = "Workflow execution failed"
        severity = "error"

        await redis_events.publish_error_alert(component, error, severity)

        # Verify Redis publish was called
        mock_redis_cache.redis_client.publish.assert_called_once()
        call_args = mock_redis_cache.redis_client.publish.call_args

        # Check channel name
        assert call_args[0][0] == "acp:events:error_alerts"

        # Check event data
        event_data = json.loads(call_args[0][1])
        assert event_data["event_type"] == ACPEventType.ERROR_ALERT
        assert event_data["source"] == component
        assert event_data["data"]["component"] == component
        assert event_data["data"]["error"] == error
        assert event_data["data"]["severity"] == severity

    @pytest.mark.asyncio
    async def test_subscribe_to_agent_events(self, redis_events, mock_redis_cache):
        """Test subscribing to agent events."""
        callback = AsyncMock()

        # Mock pubsub
        mock_pubsub = Mock()
        mock_pubsub.subscribe = Mock()
        mock_redis_cache.redis_client.pubsub.return_value = mock_pubsub
        redis_events.pubsub = mock_pubsub  # Set pubsub directly

        await redis_events.subscribe_to_agent_events(callback)

        # Verify subscription
        mock_pubsub.subscribe.assert_called_once_with("acp:events:agent_events")
        assert "acp:events:agent_events" in redis_events.subscribers
        assert callback in redis_events.subscribers["acp:events:agent_events"]

    @pytest.mark.asyncio
    async def test_subscribe_to_workflow_events(self, redis_events, mock_redis_cache):
        """Test subscribing to workflow events."""
        callback = AsyncMock()
        workflow_id = "test-workflow-1"

        # Mock pubsub
        mock_pubsub = Mock()
        mock_pubsub.subscribe = Mock()
        mock_redis_cache.redis_client.pubsub.return_value = mock_pubsub
        redis_events.pubsub = mock_pubsub  # Set pubsub directly

        await redis_events.subscribe_to_workflow_events(workflow_id, callback)

        # Verify subscription
        expected_channel = f"acp:events:workflow_events:{workflow_id}"
        mock_pubsub.subscribe.assert_called_once_with(expected_channel)
        assert expected_channel in redis_events.subscribers
        assert callback in redis_events.subscribers[expected_channel]

    @pytest.mark.asyncio
    async def test_get_active_channels(self, redis_events, mock_redis_cache):
        """Test getting active channels."""
        mock_channels = [b"acp:events:agent_events", b"acp:events:workflow_events"]
        mock_redis_cache.redis.pubsub_channels = Mock(return_value=mock_channels)

        channels = await redis_events.get_active_channels()

        assert channels == [
            "b'acp:events:agent_events'",
            "b'acp:events:workflow_events'",
        ]

    @pytest.mark.asyncio
    async def test_get_subscriber_count(self, redis_events, mock_redis_cache):
        """Test getting subscriber count for a channel."""
        channel = "agent_events"
        expected_count = 5
        mock_redis_cache.redis.pubsub_numsub = Mock(
            return_value=[(f"acp:events:{channel}".encode("utf-8"), expected_count)]
        )

        count = await redis_events.get_subscriber_count(channel)

        assert count == expected_count

    @pytest.mark.asyncio
    async def test_start_and_stop(self, redis_events, mock_redis_cache):
        """Test starting and stopping the events service."""
        # Mock pubsub
        mock_pubsub = Mock()
        mock_pubsub.close = Mock()
        mock_redis_cache.redis_client.pubsub.return_value = mock_pubsub

        # Test start
        await redis_events.start()
        assert redis_events._running is True
        assert redis_events.pubsub is not None

        # Test stop
        await redis_events.stop()
        assert redis_events._running is False
        mock_pubsub.close.assert_called_once()

    def test_event_types_enum(self):
        """Test that all event types are properly defined."""
        expected_types = [
            "agent_status_changed",
            "agent_heartbeat",
            "agent_registered",
            "agent_unregistered",
            "agent_health_check_failed",
            "workflow_started",
            "workflow_step_completed",
            "workflow_step_failed",
            "workflow_progress",
            "workflow_completed",
            "workflow_failed",
            "system_health_update",
            "performance_metrics",
            "cache_hit_ratio",
            "error_alert",
            "message_sent",
            "message_received",
            "message_failed",
        ]

        for event_type in expected_types:
            assert hasattr(ACPEventType, event_type.upper())
            assert getattr(ACPEventType, event_type.upper()) == event_type

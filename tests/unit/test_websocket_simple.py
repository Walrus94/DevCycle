"""Simplified WebSocket tests that avoid hanging issues."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from devcycle.api.routes.websocket import ConnectionManager, websocket_router


class TestConnectionManagerSimple:
    """Simplified test cases for ConnectionManager."""

    @pytest.fixture
    def manager(self):
        """Create a ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = Mock()
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.receive_text = AsyncMock()
        return websocket

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, manager, mock_websocket):
        """Test WebSocket connection and disconnection."""
        client_id = "test-client-1"

        # Test connect
        await manager.connect(mock_websocket, client_id)
        assert client_id in manager.active_connections
        assert client_id in manager.connection_subscriptions
        mock_websocket.accept.assert_called_once()

        # Test disconnect
        manager.disconnect(client_id)
        assert client_id not in manager.active_connections
        assert client_id not in manager.connection_subscriptions

    @pytest.mark.asyncio
    async def test_send_personal_message(self, manager, mock_websocket):
        """Test sending personal message."""
        client_id = "test-client-1"
        message = "test message"

        # Add connection
        manager.active_connections[client_id] = mock_websocket

        await manager.send_personal_message(message, client_id)
        mock_websocket.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_personal_message_disconnected(self, manager):
        """Test sending message to disconnected client."""
        client_id = "nonexistent-client"
        message = "test message"

        # Should not raise exception
        await manager.send_personal_message(message, client_id)

    @pytest.mark.asyncio
    async def test_broadcast(self, manager):
        """Test broadcasting message to all clients."""
        client_id1 = "client-1"
        client_id2 = "client-2"
        message = "broadcast message"

        # Create mock websockets
        mock_ws1 = Mock()
        mock_ws1.send_text = AsyncMock()
        mock_ws2 = Mock()
        mock_ws2.send_text = AsyncMock()

        # Add connections
        manager.active_connections[client_id1] = mock_ws1
        manager.active_connections[client_id2] = mock_ws2

        await manager.broadcast(message)

        # Should be called once for each client
        mock_ws1.send_text.assert_called_once_with(message)
        mock_ws2.send_text.assert_called_once_with(message)

    def test_websocket_status_endpoint(self):
        """Test WebSocket status endpoint without WebSocket connections."""
        app = FastAPI()
        app.include_router(websocket_router)
        client = TestClient(app)

        response = client.get("/ws/status")
        assert response.status_code == 200

        data = response.json()
        assert "active_connections" in data
        assert "connected_clients" in data
        assert "subscription_counts" in data
        assert data["active_connections"] == 0

    @pytest.mark.asyncio
    async def test_subscribe_to_events_mock(self, manager):
        """Test subscribing to events with mocked Redis."""
        client_id = "test-client-1"
        event_types = {"agent_events", "workflow_events"}

        # Mock Redis events
        mock_redis_events = Mock()
        mock_redis_events.start = AsyncMock()
        mock_redis_events.subscribe_to_agent_events = AsyncMock()
        mock_redis_events.subscribe_to_workflow_events = AsyncMock()

        # Mock the get_redis_events function to return the mock
        async def mock_get_redis_events():
            return mock_redis_events

        with patch(
            "devcycle.api.routes.websocket.get_redis_events",
            side_effect=mock_get_redis_events,
        ):
            await manager.subscribe_to_events(client_id, event_types)

        assert client_id in manager.connection_subscriptions
        assert manager.connection_subscriptions[client_id] == event_types
        assert manager.redis_events == mock_redis_events

    def test_websocket_router_registration(self):
        """Test that WebSocket router is properly registered."""
        app = FastAPI()
        app.include_router(websocket_router)

        # Check that routes are registered
        routes = [route.path for route in app.routes]
        assert "/ws/events" in routes
        assert "/ws/workflow/{workflow_id}" in routes
        assert "/ws/status" in routes

    def test_websocket_router_prefix(self):
        """Test WebSocket router prefix."""
        assert websocket_router.prefix == "/ws"
        assert "websocket" in websocket_router.tags

    @pytest.mark.asyncio
    async def test_handle_agent_event(self, manager):
        """Test handling agent events."""
        client_id = "test-client-1"
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()

        # Set up connection and subscription
        manager.active_connections[client_id] = mock_websocket
        manager.connection_subscriptions[client_id] = {"agent_events"}

        # Test agent event
        event_data = {
            "event_type": "agent_status_changed",
            "agent_id": "test-agent",
            "old_status": "offline",
            "new_status": "online",
        }

        await manager._handle_agent_event(event_data, client_id)
        mock_websocket.send_text.assert_called_once()

        # Verify message content
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == "agent_event"
        assert message["data"] == event_data

    @pytest.mark.asyncio
    async def test_handle_workflow_event(self, manager):
        """Test handling workflow events."""
        client_id = "test-client-1"
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()

        # Set up connection and subscription
        manager.active_connections[client_id] = mock_websocket
        manager.connection_subscriptions[client_id] = {"workflow_events"}

        # Test workflow event
        event_data = {
            "event_type": "workflow_progress",
            "workflow_id": "test-workflow",
            "step_id": "step-1",
            "progress": 50,
        }

        await manager._handle_workflow_event(event_data, client_id)
        mock_websocket.send_text.assert_called_once()

        # Verify message content
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == "workflow_event"
        assert message["data"] == event_data

    @pytest.mark.asyncio
    async def test_handle_system_health_event(self, manager):
        """Test handling system health events."""
        client_id = "test-client-1"
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()

        # Set up connection and subscription
        manager.active_connections[client_id] = mock_websocket
        manager.connection_subscriptions[client_id] = {"system_health"}

        # Test system health event
        event_data = {
            "event_type": "system_health_update",
            "component": "redis",
            "status": "healthy",
            "metrics": {"cpu_usage": 45.2},
        }

        await manager._handle_system_health_event(event_data, client_id)
        mock_websocket.send_text.assert_called_once()

        # Verify message content
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == "system_health_event"
        assert message["data"] == event_data

    @pytest.mark.asyncio
    async def test_handle_performance_metrics_event(self, manager):
        """Test handling performance metrics events."""
        client_id = "test-client-1"
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()

        # Set up connection and subscription
        manager.active_connections[client_id] = mock_websocket
        manager.connection_subscriptions[client_id] = {"performance_metrics"}

        # Test performance metrics event
        event_data = {
            "event_type": "performance_metrics",
            "cpu_usage": 45.2,
            "memory_usage": 78.1,
            "timestamp": "2024-01-01T00:00:00Z",
        }

        await manager._handle_performance_metrics_event(event_data, client_id)
        mock_websocket.send_text.assert_called_once()

        # Verify message content
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == "performance_metrics_event"
        assert message["data"] == event_data

    @pytest.mark.asyncio
    async def test_handle_error_alert_event(self, manager):
        """Test handling error alert events."""
        client_id = "test-client-1"
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()

        # Set up connection and subscription
        manager.active_connections[client_id] = mock_websocket
        manager.connection_subscriptions[client_id] = {"error_alerts"}

        # Test error alert event
        event_data = {
            "event_type": "error_alert",
            "component": "workflow_engine",
            "error": "Workflow execution failed",
            "severity": "error",
        }

        await manager._handle_error_alert_event(event_data, client_id)
        mock_websocket.send_text.assert_called_once()

        # Verify message content
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == "error_alert_event"
        assert message["data"] == event_data

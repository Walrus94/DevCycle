"""
WebSocket routes for real-time ACP events.

This module provides WebSocket endpoints for real-time event streaming
from the ACP system to connected clients.
"""

import json
import logging
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter

from ...core.acp.events.redis_events import RedisACPEvents
from ...core.dependencies import get_redis_events

logger = logging.getLogger(__name__)

websocket_router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections and event subscriptions."""

    def __init__(self) -> None:
        """Initialize the WebSocket manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_subscriptions: Dict[str, Set[str]] = {}
        self.redis_events: Optional[RedisACPEvents] = None

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept a WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_subscriptions[client_id] = set()
        logger.info(f"WebSocket client {client_id} connected")

    def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.connection_subscriptions:
            del self.connection_subscriptions[client_id]
        logger.info(f"WebSocket client {client_id} disconnected")

    async def send_personal_message(self, message: str, client_id: str) -> None:
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(self, message: str) -> None:
        """Broadcast a message to all connected clients."""
        disconnected_clients = []
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    async def subscribe_to_events(self, client_id: str, event_types: Set[str]) -> None:
        """Subscribe a client to specific event types."""
        if client_id not in self.connection_subscriptions:
            self.connection_subscriptions[client_id] = set()

        self.connection_subscriptions[client_id].update(event_types)

        # Set up Redis event subscriptions if not already done
        if not self.redis_events:
            self.redis_events = get_redis_events()
            await self.redis_events.start()

        # Subscribe to relevant Redis channels
        for event_type in event_types:
            if event_type == "agent_events":

                def agent_callback(data: Dict[str, Any]) -> None:
                    # Schedule the async function to run
                    import asyncio

                    asyncio.create_task(self._handle_agent_event(data, client_id))

                await self.redis_events.subscribe_to_agent_events(agent_callback)
            elif event_type == "workflow_events":

                def workflow_callback(data: Dict[str, Any]) -> None:
                    # Schedule the async function to run
                    import asyncio

                    asyncio.create_task(self._handle_workflow_event(data, client_id))

                await self.redis_events.subscribe_to_workflow_events(
                    callback=workflow_callback
                )
            elif event_type == "system_health":

                def system_health_callback(data: Dict[str, Any]) -> None:
                    # Schedule the async function to run
                    import asyncio

                    asyncio.create_task(
                        self._handle_system_health_event(data, client_id)
                    )

                await self.redis_events.subscribe_to_system_health(
                    system_health_callback
                )
            elif event_type == "performance_metrics":

                def performance_callback(data: Dict[str, Any]) -> None:
                    # Schedule the async function to run
                    import asyncio

                    asyncio.create_task(
                        self._handle_performance_metrics_event(data, client_id)
                    )

                await self.redis_events.subscribe_to_performance_metrics(
                    performance_callback
                )
            elif event_type == "error_alerts":

                def error_callback(data: Dict[str, Any]) -> None:
                    # Schedule the async function to run
                    import asyncio

                    asyncio.create_task(self._handle_error_alert_event(data, client_id))

                await self.redis_events.subscribe_to_error_alerts(error_callback)

    async def _handle_agent_event(self, data: Dict[str, Any], client_id: str) -> None:
        """Handle agent events for a specific client."""
        if (
            client_id in self.connection_subscriptions
            and "agent_events" in self.connection_subscriptions[client_id]
        ):
            message = json.dumps({"type": "agent_event", "data": data})
            await self.send_personal_message(message, client_id)

    async def _handle_workflow_event(
        self, data: Dict[str, Any], client_id: str
    ) -> None:
        """Handle workflow events for a specific client."""
        if (
            client_id in self.connection_subscriptions
            and "workflow_events" in self.connection_subscriptions[client_id]
        ):
            message = json.dumps({"type": "workflow_event", "data": data})
            await self.send_personal_message(message, client_id)

    async def _handle_system_health_event(
        self, data: Dict[str, Any], client_id: str
    ) -> None:
        """Handle system health events for a specific client."""
        if (
            client_id in self.connection_subscriptions
            and "system_health" in self.connection_subscriptions[client_id]
        ):
            message = json.dumps({"type": "system_health_event", "data": data})
            await self.send_personal_message(message, client_id)

    async def _handle_performance_metrics_event(
        self, data: Dict[str, Any], client_id: str
    ) -> None:
        """Handle performance metrics events for a specific client."""
        if (
            client_id in self.connection_subscriptions
            and "performance_metrics" in self.connection_subscriptions[client_id]
        ):
            message = json.dumps({"type": "performance_metrics_event", "data": data})
            await self.send_personal_message(message, client_id)

    async def _handle_error_alert_event(
        self, data: Dict[str, Any], client_id: str
    ) -> None:
        """Handle error alert events for a specific client."""
        if (
            client_id in self.connection_subscriptions
            and "error_alerts" in self.connection_subscriptions[client_id]
        ):
            message = json.dumps({"type": "error_alert_event", "data": data})
            await self.send_personal_message(message, client_id)


# Global connection manager
manager = ConnectionManager()


@websocket_router.websocket("/events")
async def websocket_endpoint(
    websocket: WebSocket, client_id: str = "anonymous"
) -> None:
    """Websocket endpoint for real-time ACP events."""
    await manager.connect(websocket, client_id)

    try:
        while True:
            # Wait for client messages
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                if message_type == "subscribe":
                    # Client wants to subscribe to specific event types
                    event_types = set(message.get("event_types", []))
                    await manager.subscribe_to_events(client_id, event_types)

                    # Send confirmation
                    await manager.send_personal_message(
                        json.dumps(
                            {
                                "type": "subscription_confirmed",
                                "event_types": list(event_types),
                            }
                        ),
                        client_id,
                    )

                elif message_type == "ping":
                    # Client ping - send pong
                    await manager.send_personal_message(
                        json.dumps({"type": "pong"}), client_id
                    )

                else:
                    # Unknown message type
                    await manager.send_personal_message(
                        json.dumps(
                            {
                                "type": "error",
                                "message": f"Unknown message type: {message_type}",
                            }
                        ),
                        client_id,
                    )

            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({"type": "error", "message": "Invalid JSON message"}),
                    client_id,
                )

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        manager.disconnect(client_id)


@websocket_router.websocket("/workflow/{workflow_id}")
async def workflow_websocket_endpoint(
    websocket: WebSocket, workflow_id: str, client_id: str = "anonymous"
) -> None:
    """Websocket endpoint for specific workflow events."""
    await manager.connect(websocket, client_id)

    try:
        # Subscribe to workflow-specific events
        await manager.subscribe_to_events(client_id, {"workflow_events"})

        # Send initial confirmation
        await manager.send_personal_message(
            json.dumps(
                {"type": "workflow_subscription_confirmed", "workflow_id": workflow_id}
            ),
            client_id,
        )

        while True:
            # Wait for client messages
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                if message_type == "ping":
                    await manager.send_personal_message(
                        json.dumps({"type": "pong"}), client_id
                    )
                else:
                    await manager.send_personal_message(
                        json.dumps(
                            {
                                "type": "error",
                                "message": f"Unknown message type: {message_type}",
                            }
                        ),
                        client_id,
                    )

            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({"type": "error", "message": "Invalid JSON message"}),
                    client_id,
                )

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"Workflow WebSocket error for {client_id}: {e}")
        manager.disconnect(client_id)


@websocket_router.get("/status")
async def websocket_status() -> Dict[str, Any]:
    """Get WebSocket connection status."""
    return {
        "active_connections": len(manager.active_connections),
        "connected_clients": list(manager.active_connections.keys()),
        "subscription_counts": {
            client_id: len(subscriptions)
            for client_id, subscriptions in manager.connection_subscriptions.items()
        },
    }

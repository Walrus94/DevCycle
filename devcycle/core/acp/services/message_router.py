"""
ACP Message Router service.

Handles message routing, load balancing, and error handling.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, cast

from ..config import ACPConfig
from ..models import ACPAgentStatus, ACPMessage, ACPResponse
from .agent_registry import ACPAgentRegistry

logger = logging.getLogger(__name__)


class ACPAgent(Protocol):
    """Protocol for ACP agents."""

    agent_id: str

    async def handle_message(self, message: ACPMessage) -> ACPResponse:
        """Handle a message and return a response."""
        ...


class ACPMessageRouter:
    """ACP message router for DevCycle."""

    def __init__(self, config: ACPConfig, agent_registry: ACPAgentRegistry):
        """Initialize the message router."""
        self.config = config
        self.agent_registry = agent_registry
        self.message_queue: Dict[str, ACPMessage] = {}
        self.processing_messages: Dict[str, asyncio.Task] = {}

        # Message routing statistics
        self.stats = {
            "messages_processed": 0,
            "messages_successful": 0,
            "messages_failed": 0,
            "messages_pending": 0,
            "avg_processing_time_ms": 0.0,
            "max_processing_time_ms": 0.0,
            "min_processing_time_ms": float("inf"),
        }

    def _create_error_response(
        self, message_id: str, error: str, error_code: str = "ERROR"
    ) -> ACPResponse:
        """Create an error response."""
        return ACPResponse(
            response_id=f"resp_{message_id}",
            message_id=message_id,
            success=False,
            error=error,
            error_code=error_code,
        )

    async def route_message(self, message: ACPMessage) -> ACPResponse:
        """Route a message to the appropriate agent."""
        start_time = datetime.now(timezone.utc)

        try:
            # Validate message
            if not self._validate_message(message):
                return self._create_error_response(
                    message.message_id, "Invalid message format", "INVALID_MESSAGE"
                )

            # Check if target agent exists
            if message.target_agent_id:
                target_agent = self.agent_registry.get_agent_instance(
                    message.target_agent_id
                )
                if not target_agent:
                    return self._create_error_response(
                        message.message_id,
                        f"Target agent {message.target_agent_id} not found",
                        "AGENT_NOT_FOUND",
                    )

                # Check if target agent is healthy
                if not self.agent_registry.agent_health.get(
                    message.target_agent_id, False
                ):
                    return self._create_error_response(
                        message.message_id,
                        f"Target agent {message.target_agent_id} is not healthy",
                        "AGENT_UNHEALTHY",
                    )

                # Route to specific agent
                return await self._route_to_agent(message, target_agent)

            else:
                # Route based on message type and capabilities
                return await self._route_by_capability(message)

        except Exception as e:
            logger.error(f"Message routing error: {e}")
            return self._create_error_response(
                message.message_id, f"Routing error: {str(e)}", "ROUTING_ERROR"
            )

        finally:
            # Update statistics
            processing_time = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            self._update_stats(processing_time)

    async def route_workflow_message(
        self, message: ACPMessage, workflow_id: str
    ) -> ACPResponse:
        """Route a message as part of a workflow."""
        try:
            # Add workflow context to message
            message.workflow_id = workflow_id
            message.metadata["workflow_id"] = workflow_id

            # Route the message
            response = await self.route_message(message)

            # Add workflow context to response
            response.metadata["workflow_id"] = workflow_id

            return response

        except Exception as e:
            logger.error(f"Workflow message routing error: {e}")
            return self._create_error_response(
                message.message_id,
                f"Workflow routing error: {str(e)}",
                "WORKFLOW_ROUTING_ERROR",
            )

    async def broadcast_message(
        self, message: ACPMessage, capability: Optional[str] = None
    ) -> List[ACPResponse]:
        """Broadcast a message to multiple agents."""
        try:
            if capability:
                # Broadcast to agents with specific capability
                agents = await self.agent_registry.discover_agents(capability)
            else:
                # Broadcast to all online agents
                agents = await self.agent_registry.list_agents(ACPAgentStatus.ONLINE)

            if not agents:
                logger.warning(
                    f"No agents found for broadcast (capability: {capability})"
                )
                return []

            # Send message to all agents concurrently
            tasks = []
            for agent in agents:
                task = asyncio.create_task(
                    self._send_to_agent(message, cast(ACPAgent, agent))
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions and return valid responses
            valid_responses = []
            for response in responses:
                if isinstance(response, ACPResponse):
                    valid_responses.append(response)
                else:
                    logger.error(f"Broadcast error: {response}")

            logger.info(
                f"Broadcasted message to {len(agents)} agents, "
                f"got {len(valid_responses)} responses"
            )
            return valid_responses

        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            return []

    async def get_message_status(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a message."""
        if message_id in self.message_queue:
            return {
                "status": "queued",
                "message_id": message_id,
                "created_at": self.message_queue[message_id].created_at.isoformat(),
            }

        if message_id in self.processing_messages:
            return {
                "status": "processing",
                "message_id": message_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
            }

        return None

    async def cancel_message(self, message_id: str) -> bool:
        """Cancel a pending or processing message."""
        try:
            # Cancel if processing
            if message_id in self.processing_messages:
                task = self.processing_messages[message_id]
                task.cancel()
                del self.processing_messages[message_id]
                logger.info(f"Cancelled processing message {message_id}")
                return True

            # Remove from queue if queued
            if message_id in self.message_queue:
                del self.message_queue[message_id]
                logger.info(f"Cancelled queued message {message_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to cancel message {message_id}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return self.stats.copy()

    def _validate_message(self, message: ACPMessage) -> bool:
        """Validate message format and content."""
        try:
            # Check required fields
            if not message.message_id or not message.message_type:
                return False

            # Check message size
            message_size = len(str(message.content).encode("utf-8"))
            if message_size > self.config.message_max_size:
                logger.warning(
                    f"Message {message.message_id} exceeds size limit: "
                    f"{message_size} bytes"
                )
                return False

            # Check expiration
            if message.expires_at and message.expires_at < datetime.now(timezone.utc):
                logger.warning(f"Message {message.message_id} has expired")
                return False

            return True

        except Exception as e:
            logger.error(f"Message validation error: {e}")
            return False

    async def _route_to_agent(self, message: ACPMessage, agent: Any) -> ACPResponse:
        """Route message to a specific agent."""
        try:
            # Update agent status to busy
            await self.agent_registry.update_agent_status(
                agent.agent_id, ACPAgentStatus.BUSY
            )

            # Send message to agent
            response = await self._send_to_agent(message, cast(ACPAgent, agent))

            # Update agent status back to online
            await self.agent_registry.update_agent_status(
                agent.agent_id, ACPAgentStatus.ONLINE
            )

            return response

        except Exception as e:
            # Update agent status to error
            await self.agent_registry.update_agent_status(
                agent.agent_id, ACPAgentStatus.ERROR
            )
            raise e

    async def _route_by_capability(self, message: ACPMessage) -> ACPResponse:
        """Route message based on message type and agent capabilities."""
        try:
            # Map message types to capabilities
            capability_map = {
                "generate_code": "code_generation",
                "analyze_code": "code_analysis",
                "refactor_code": "code_refactoring",
                "generate_tests": "testing",
                "run_tests": "testing",
                "deploy_application": "deployment",
                "rollback_deployment": "deployment",
                "scale_application": "deployment",
                "analyze_coverage": "testing",
            }

            capability = capability_map.get(message.message_type)
            if not capability:
                return self._create_error_response(
                    message.message_id,
                    f"No capability mapping for message type {message.message_type}",
                    "UNKNOWN_MESSAGE_TYPE",
                )

            # Find agents with the required capability
            agent_infos = await self.agent_registry.discover_agents(capability)
            if not agent_infos:
                return self._create_error_response(
                    message.message_id,
                    f"No agents found with capability {capability}",
                    "NO_AGENTS_FOUND",
                )

            # Get agent instances
            agents = []
            for agent_info in agent_infos:
                agent_instance = self.agent_registry.get_agent_instance(
                    agent_info.agent_id
                )
                if agent_instance:
                    agents.append(agent_instance)

            if not agents:
                return self._create_error_response(
                    message.message_id,
                    "No agent instances available",
                    "NO_AGENT_INSTANCES",
                )

            # Select best agent (simple round-robin for now)
            selected_agent = self._select_best_agent(agents, message)
            if not selected_agent:
                return self._create_error_response(
                    message.message_id, "No suitable agent found", "NO_SUITABLE_AGENT"
                )

            # Route to selected agent
            return await self._route_to_agent(message, selected_agent)

        except Exception as e:
            logger.error(f"Capability-based routing error: {e}")
            raise e

    async def _send_to_agent(self, message: ACPMessage, agent: ACPAgent) -> ACPResponse:
        """Send message to a specific agent."""
        try:
            # Call the agent's handle_message method
            response = await agent.handle_message(message)

            # Debug logging
            logger.info(
                f"Agent {agent.agent_id} returned response type: {type(response)}"
            )
            logger.info(f"Response content: {response}")

            # Add processing time metadata
            processing_time = self._estimate_processing_time(message)
            response.processing_time_ms = processing_time * 1000

            return response

        except Exception as e:
            logger.error(f"Failed to send message to agent {agent.agent_id}: {e}")
            return self._create_error_response(
                message.message_id,
                f"Agent communication error: {str(e)}",
                "AGENT_COMMUNICATION_ERROR",
            )

    def _select_best_agent(
        self, agents: List[Any], message: ACPMessage
    ) -> Optional[Any]:
        """Select the best agent from a list of candidates."""
        if not agents:
            return None

        # Simple selection strategy: choose agent with lowest current runs
        # In a real implementation, this could be more sophisticated
        return min(agents, key=lambda agent: agent.current_runs)

    def _estimate_processing_time(self, message: ACPMessage) -> float:
        """Estimate processing time for a message."""
        # Base processing time
        base_time = 0.1

        # Add complexity based on message type
        complexity_multipliers = {
            "generate_code": 2.0,
            "analyze_code": 1.5,
            "refactor_code": 2.5,
            "generate_tests": 1.8,
            "run_tests": 1.0,
            "deploy_application": 3.0,
            "rollback_deployment": 1.5,
            "scale_application": 2.0,
            "analyze_coverage": 1.2,
        }

        multiplier = complexity_multipliers.get(message.message_type, 1.0)
        return base_time * multiplier

    def _update_stats(self, processing_time_ms: float) -> None:
        """Update router statistics."""
        self.stats["messages_processed"] += 1
        self.stats["avg_processing_time_ms"] = (
            self.stats["avg_processing_time_ms"]
            * (self.stats["messages_processed"] - 1)
            + processing_time_ms
        ) / self.stats["messages_processed"]
        self.stats["max_processing_time_ms"] = max(
            self.stats["max_processing_time_ms"], processing_time_ms
        )
        self.stats["min_processing_time_ms"] = min(
            self.stats["min_processing_time_ms"], processing_time_ms
        )

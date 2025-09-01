"""
Agent availability service for DevCycle.

This module provides services for checking agent availability and capabilities,
ensuring that messages are only sent to agents that can process them.
"""

import asyncio
from typing import Any, Dict, List, Optional

from ..agents.models import AgentStatus
from ..logging import get_logger
from ..repositories.agent_repository import AgentRepository

logger = get_logger(__name__)


class AgentAvailabilityService:
    """Service for checking agent availability and capabilities."""

    def __init__(self, agent_repository: AgentRepository) -> None:
        """Initialize the agent availability service."""
        self.agent_repository = agent_repository
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 30  # 30 seconds cache TTL
        self._last_cache_update = 0

    async def is_agent_available(self, agent_id: str) -> bool:
        """
        Check if an agent is available for processing messages.

        Args:
            agent_id: The ID of the agent to check

        Returns:
            True if the agent is available, False otherwise
        """
        try:
            # Check cache first
            if self._is_cache_valid(agent_id):
                cached_data = self._cache.get(agent_id, {})
                return bool(cached_data.get("available", False))

            # Get fresh data from repository
            agent = await self.agent_repository.get_by_name(agent_id)

            if not agent:
                logger.warning(f"Agent {agent_id} not found")
                return False

            # Check if agent is online and not busy
            is_available = (
                agent.status == AgentStatus.ONLINE.value
                and not self._is_agent_busy(agent)
                and not self._is_agent_in_maintenance(agent)
            )

            # Update cache
            self._update_cache(
                agent_id,
                {
                    "available": is_available,
                    "status": agent.status,
                    "capabilities": agent.capabilities,
                    "last_check": asyncio.get_event_loop().time(),
                },
            )

            return is_available

        except Exception as e:
            logger.error(f"Error checking agent availability for {agent_id}: {e}")
            return False

    async def get_agent_capabilities(self, agent_id: str) -> List[str]:
        """
        Get the capabilities of a specific agent.

        Args:
            agent_id: The ID of the agent

        Returns:
            List of capability strings
        """
        try:
            # Check cache first
            if self._is_cache_valid(agent_id):
                cached_data = self._cache.get(agent_id, {})
                capabilities = cached_data.get("capabilities", [])
                return capabilities if isinstance(capabilities, list) else []

            # Get fresh data from repository
            agent = await self.agent_repository.get_by_name(agent_id)

            if not agent:
                logger.warning(f"Agent {agent_id} not found")
                return []

            # Parse capabilities from JSON string
            import json

            try:
                parsed_capabilities: list[str] = (
                    json.loads(agent.capabilities) if agent.capabilities else []
                )
            except json.JSONDecodeError:
                parsed_capabilities = []

            # Update cache
            self._update_cache(
                agent_id,
                {
                    "capabilities": parsed_capabilities,
                    "last_check": asyncio.get_event_loop().time(),
                },
            )

            return parsed_capabilities

        except Exception as e:
            logger.error(f"Error getting agent capabilities for {agent_id}: {e}")
            return []

    async def validate_agent_capability(self, agent_id: str, capability: str) -> bool:
        """
        Validate if an agent has a specific capability.

        Args:
            agent_id: The ID of the agent
            capability: The capability to check

        Returns:
            True if the agent has the capability, False otherwise
        """
        try:
            agent_capabilities = await self.get_agent_capabilities(agent_id)
            return capability in agent_capabilities

        except Exception as e:
            logger.error(f"Error validating agent capability for {agent_id}: {e}")
            return False

    async def get_available_agents_by_capability(self, capability: str) -> List[str]:
        """
        Get all available agents with a specific capability.

        Args:
            capability: The capability to filter by

        Returns:
            List of available agent IDs
        """
        try:
            # Get agents with the specified capability
            agents = await self.agent_repository.get_agents_by_capability(capability)

            # Filter for online and available agents
            available_agents = []
            for agent in agents:
                if (
                    agent.status == AgentStatus.ONLINE.value
                    and not self._is_agent_busy(agent)
                    and not self._is_agent_in_maintenance(agent)
                ):
                    available_agents.append(str(agent.id))

            return available_agents

        except Exception as e:
            logger.error(
                f"Error getting available agents by capability {capability}: {e}"
            )
            return []

    async def get_agent_load(self, agent_id: str) -> Dict[str, Any]:
        """
        Get the current load information for an agent.

        Args:
            agent_id: The ID of the agent

        Returns:
            Dictionary containing load information
        """
        try:
            agent = await self.agent_repository.get_by_name(agent_id)

            if not agent:
                return {"error": "Agent not found"}

            # Parse configuration from JSON
            import json

            try:
                configuration = (
                    json.loads(agent.configuration) if agent.configuration else {}
                )
            except json.JSONDecodeError:
                configuration = {}

            max_concurrent_tasks = configuration.get("max_concurrent_tasks", 1)
            current_tasks = getattr(agent, "current_tasks", 0) or 0

            return {
                "agent_id": agent_id,
                "status": agent.status,
                "current_tasks": current_tasks,
                "max_concurrent_tasks": max_concurrent_tasks,
                "available_slots": max(0, max_concurrent_tasks - current_tasks),
                "last_heartbeat": agent.last_heartbeat,
                "response_time_ms": agent.response_time_ms,
            }

        except Exception as e:
            logger.error(f"Error getting agent load for {agent_id}: {e}")
            return {"error": str(e)}

    async def get_least_busy_agent(self, capabilities: List[str]) -> Optional[str]:
        """
        Get the least busy agent with the specified capabilities.

        Args:
            capabilities: List of required capabilities

        Returns:
            Agent ID of the least busy agent, or None if no suitable agent found
        """
        try:
            # Get all agents with the required capabilities
            available_agents = await self.get_available_agents_by_capability(
                capabilities[0]
            )

            if not available_agents:
                return None

            # Get load information for all available agents
            agent_loads = []
            for agent_id in available_agents:
                load_info = await self.get_agent_load(agent_id)
                if "error" not in load_info:
                    agent_loads.append((agent_id, load_info))

            if not agent_loads:
                return None

            # Sort by available slots (descending) and response time (ascending)
            agent_loads.sort(
                key=lambda x: (
                    x[1]["available_slots"],
                    -x[1].get("response_time_ms", 0),
                ),
                reverse=True,
            )

            return agent_loads[0][0]

        except Exception as e:
            logger.error(f"Error getting least busy agent: {e}")
            return None

    def _is_agent_busy(self, agent: Any) -> bool:
        """Check if an agent is busy."""
        # Parse configuration from JSON
        import json

        try:
            configuration = (
                json.loads(agent.configuration) if agent.configuration else {}
            )
        except json.JSONDecodeError:
            configuration = {}

        current_tasks = getattr(agent, "current_tasks", 0) or 0
        max_tasks = configuration.get("max_concurrent_tasks", 1)

        return bool(current_tasks >= max_tasks)

    def _is_agent_in_maintenance(self, agent: Any) -> bool:
        """Check if an agent is in maintenance mode."""
        return bool(getattr(agent, "status", None) == AgentStatus.MAINTENANCE.value)

    def _is_cache_valid(self, agent_id: str) -> bool:
        """Check if cached data is still valid."""
        if agent_id not in self._cache:
            return False

        cached_time = self._cache[agent_id].get("last_check", 0)
        current_time = asyncio.get_event_loop().time()

        return bool((current_time - float(cached_time)) < self._cache_ttl)

    def _update_cache(self, agent_id: str, data: Dict[str, Any]) -> None:
        """Update the cache with new data."""
        if agent_id not in self._cache:
            self._cache[agent_id] = {}

        self._cache[agent_id].update(data)

    # _get_agent_by_id method removed - using repository pattern instead

    def clear_cache(self, agent_id: Optional[str] = None) -> None:
        """
        Clear the cache for a specific agent or all agents.

        Args:
            agent_id: Specific agent ID to clear, or None to clear all
        """
        if agent_id:
            self._cache.pop(agent_id, None)
        else:
            self._cache.clear()
        logger.debug(f"Cleared cache for agent: {agent_id or 'all'}")

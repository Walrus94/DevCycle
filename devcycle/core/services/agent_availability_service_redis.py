"""
Enhanced agent availability service with Redis caching for DevCycle.

This module provides an improved version of the agent availability service that uses
Redis for distributed caching, improving performance and enabling better scalability.
"""

import time
from typing import Any, Dict, List, Optional

from ..agents.models import AgentStatus
from ..cache.redis_cache import get_cache
from ..logging import get_logger
from ..repositories.agent_repository import AgentRepository

logger = get_logger(__name__)


class RedisAgentAvailabilityService:
    """Enhanced service for checking agent availability with Redis caching."""

    def __init__(self, agent_repository: AgentRepository) -> None:
        """Initialize the Redis-backed agent availability service."""
        self.agent_repository = agent_repository
        self.cache = get_cache("devcycle:agent:")
        self._cache_ttl = 30  # 30 seconds cache TTL

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
            cache_key = f"availability:{agent_id}"
            cached_data = self.cache.get(cache_key)

            if cached_data and self._is_cache_valid(cached_data):
                logger.debug(f"Cache hit for agent availability: {agent_id}")
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
            cache_data = {
                "available": is_available,
                "status": agent.status,
                "capabilities": agent.capabilities,
                "last_check": time.time(),
            }
            self.cache.set(cache_key, cache_data, self._cache_ttl)

            logger.debug(f"Updated cache for agent availability: {agent_id}")
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
            cache_key = f"capabilities:{agent_id}"
            cached_data = self.cache.get(cache_key)

            if cached_data and self._is_cache_valid(cached_data):
                logger.debug(f"Cache hit for agent capabilities: {agent_id}")
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
            cache_data = {
                "capabilities": parsed_capabilities,
                "last_check": time.time(),
            }
            self.cache.set(cache_key, cache_data, self._cache_ttl)

            logger.debug(f"Updated cache for agent capabilities: {agent_id}")
            return [str(cap) for cap in parsed_capabilities]

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
            # Check cache first
            cache_key = f"agents_by_capability:{capability}"
            cached_data = self.cache.get(cache_key)

            if cached_data and self._is_cache_valid(cached_data):
                logger.debug(f"Cache hit for agents by capability: {capability}")
                agent_ids = cached_data.get("agent_ids", [])
                return [str(agent_id) for agent_id in agent_ids] if agent_ids else []

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

            # Update cache
            cache_data = {
                "agent_ids": available_agents,
                "last_check": time.time(),
            }
            self.cache.set(cache_key, cache_data, self._cache_ttl)

            logger.debug(f"Updated cache for agents by capability: {capability}")
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
            # Check cache first
            cache_key = f"load:{agent_id}"
            cached_data = self.cache.get(cache_key)

            if cached_data and self._is_cache_valid(cached_data):
                logger.debug(f"Cache hit for agent load: {agent_id}")
                load_info = cached_data.get("load_info", {})
                return {str(k): v for k, v in load_info.items()} if load_info else {}

            agent = await self.agent_repository.get_by_name(agent_id)

            if not agent:
                return {"error": "Agent not found"}

            # Parse configuration from JSON
            import json

            try:
                configuration: dict[str, Any] = (
                    json.loads(agent.configuration) if agent.configuration else {}
                )
            except json.JSONDecodeError:
                configuration = {}

            max_concurrent_tasks = configuration.get("max_concurrent_tasks", 1)
            current_tasks = getattr(agent, "current_tasks", 0) or 0

            load_info = {
                "agent_id": agent_id,
                "status": agent.status,
                "current_tasks": current_tasks,
                "max_concurrent_tasks": max_concurrent_tasks,
                "available_slots": max(0, max_concurrent_tasks - current_tasks),
                "last_heartbeat": agent.last_heartbeat,
                "response_time_ms": agent.response_time_ms,
            }

            # Update cache
            cache_data = {
                "load_info": load_info,
                "last_check": time.time(),
            }
            self.cache.set(cache_key, cache_data, self._cache_ttl)

            logger.debug(f"Updated cache for agent load: {agent_id}")
            return {str(k): v for k, v in load_info.items()}

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

    def _is_cache_valid(self, cached_data: Dict[str, Any]) -> bool:
        """Check if cached data is still valid."""
        if not cached_data:
            return False

        cached_time = cached_data.get("last_check", 0)
        current_time = time.time()

        return bool((current_time - float(cached_time)) < self._cache_ttl)

    def clear_cache(self, agent_id: Optional[str] = None) -> int:
        """
        Clear the cache for a specific agent or all agents.

        Args:
            agent_id: Specific agent ID to clear, or None to clear all

        Returns:
            Number of cache entries cleared
        """
        if agent_id:
            # Clear all cache entries for this agent
            patterns = [
                f"availability:{agent_id}",
                f"capabilities:{agent_id}",
                f"load:{agent_id}",
            ]
            cleared = 0
            for pattern in patterns:
                cleared += self.cache.delete(pattern)
            logger.debug(f"Cleared cache for agent: {agent_id} ({cleared} entries)")
            return cleared
        else:
            # Clear all agent-related cache
            cleared = self.cache.clear_pattern("availability:*")
            cleared += self.cache.clear_pattern("capabilities:*")
            cleared += self.cache.clear_pattern("load:*")
            cleared += self.cache.clear_pattern("agents_by_capability:*")
            logger.debug(f"Cleared all agent cache ({cleared} entries)")
            return cleared

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return self.cache.get_stats()

    def health_check(self) -> bool:
        """
        Check if the cache service is healthy.

        Returns:
            True if cache is accessible, False otherwise
        """
        return self.cache.health_check()

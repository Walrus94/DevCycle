"""
ACP Agent Registry service.

Manages agent registration, discovery, and health monitoring.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

from ...cache.acp_cache import ACPCache
from ..config import ACPConfig
from ..events.redis_events import RedisACPEvents
from ..models import ACPAgentInfo, ACPAgentStatus

logger = logging.getLogger(__name__)


class ACPAgentRegistry:
    """ACP-native agent registry with real discovery and communication."""

    def __init__(
        self,
        config: ACPConfig,
        acp_cache: Optional[ACPCache] = None,
        events: Optional[RedisACPEvents] = None,
    ):
        """Initialize the agent registry."""
        self.config = config
        self.acp_cache = acp_cache
        self.events = events
        self.agents: Dict[str, Any] = {}  # Store actual agent instances
        self.agent_infos: Dict[str, ACPAgentInfo] = {}  # Store agent info separately
        self.capabilities_index: Dict[str, Set[str]] = defaultdict(set)
        self.agent_health: Dict[str, bool] = {}
        self.agent_last_seen: Dict[str, datetime] = {}

        # Start background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._discovery_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the agent registry background tasks."""
        if self.config.health_check_interval > 0:
            self._health_check_task = asyncio.create_task(self._health_check_loop())

        if self.config.discovery_enabled:
            self._discovery_task = asyncio.create_task(self._discovery_loop())

        logger.info("ACP Agent Registry started")

    async def stop(self) -> None:
        """Stop the agent registry background tasks."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        if self._discovery_task:
            self._discovery_task.cancel()
            try:
                await self._discovery_task
            except asyncio.CancelledError:
                pass

        logger.info("ACP Agent Registry stopped")

    async def register_agent(self, agent: Any) -> bool:
        """Register an agent with the ACP system."""
        try:
            # Get agent info from the agent instance
            agent_info = agent.get_agent_info()

            # Validate agent info
            if not agent_info.agent_id or not agent_info.agent_name:
                logger.error("Invalid agent info: missing required fields")
                return False

            # Check if agent already exists
            if agent_info.agent_id in self.agents:
                logger.warning(
                    f"Agent {agent_info.agent_id} already registered, updating info"
                )

            # Register agent instance and info
            self.agents[agent_info.agent_id] = agent
            self.agent_infos[agent_info.agent_id] = agent_info
            self.agent_health[agent_info.agent_id] = True
            self.agent_last_seen[agent_info.agent_id] = datetime.now(timezone.utc)

            # Update capabilities index
            await self._update_capabilities_index(agent_info)

            # Cache agent status in Redis if cache is available
            if self.acp_cache:
                await self.acp_cache.cache_agent_status(
                    agent_info.agent_id,
                    {
                        "status": "online",
                        "last_seen": datetime.now(timezone.utc).isoformat(),
                        "current_runs": 0,
                        "max_runs": agent_info.max_concurrent_runs,
                    },
                )

                # Cache agent metadata
                await self.acp_cache.cache_agent_metadata(
                    agent_info.agent_id,
                    {
                        "agent_id": agent_info.agent_id,
                        "agent_name": agent_info.agent_name,
                        "agent_version": agent_info.agent_version,
                        "capabilities": agent_info.capabilities,
                        "input_types": agent_info.input_types,
                        "output_types": agent_info.output_types,
                        "is_stateful": agent_info.is_stateful,
                        "max_concurrent_runs": agent_info.max_concurrent_runs,
                        "hf_model_name": agent_info.hf_model_name,
                    },
                )

                # Publish agent registered event
                if self.events:
                    await self.events.publish_agent_registered(
                        agent_info.agent_id,
                        {
                            "agent_name": agent_info.agent_name,
                            "agent_version": agent_info.agent_version,
                            "capabilities": agent_info.capabilities,
                            "max_concurrent_runs": agent_info.max_concurrent_runs,
                        },
                    )

                # Update capability mappings in Redis
                for capability in agent_info.capabilities:
                    current_agents = await self.acp_cache.discover_agents_by_capability(
                        capability
                    )
                    if agent_info.agent_id not in current_agents:
                        current_agents.append(agent_info.agent_id)
                    await self.acp_cache.cache_capability_mapping(
                        capability, current_agents
                    )

            logger.info(f"Agent {agent_info.agent_id} registered successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            return False

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the ACP system."""
        try:
            if agent_id not in self.agents:
                logger.warning(f"Agent {agent_id} not found for unregistration")
                return False

            # Remove from all indexes
            agent_info = self.agents[agent_id]
            for capability in agent_info.capabilities:
                self.capabilities_index[capability].discard(agent_id)

            # Remove from registries
            del self.agents[agent_id]
            del self.agent_health[agent_id]
            del self.agent_last_seen[agent_id]

            # Publish agent unregistered event
            if self.events:
                await self.events.publish_agent_unregistered(agent_id)

            logger.info(f"Agent {agent_id} unregistered successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False

    async def discover_agents(self, capability: str) -> List[ACPAgentInfo]:
        """Discover agents with specific capabilities."""
        try:
            # Try Redis cache first if available
            if self.acp_cache:
                cached_agent_ids = await self.acp_cache.discover_agents_by_capability(
                    capability
                )
                if cached_agent_ids:
                    # Return cached results, filtering for healthy agents
                    healthy_agents = []
                    for agent_id in cached_agent_ids:
                        if agent_id in self.agents and self.agent_health.get(
                            agent_id, False
                        ):
                            healthy_agents.append(self.agent_infos[agent_id])

                    logger.debug(
                        f"Found {len(healthy_agents)} healthy agents with capability "
                        f"'{capability}' from cache"
                    )
                    return healthy_agents

            # Fallback to local capabilities index
            agent_ids = self.capabilities_index.get(capability, set())
            healthy_agents = []

            for agent_id in agent_ids:
                if agent_id in self.agents and self.agent_health.get(agent_id, False):
                    healthy_agents.append(self.agent_infos[agent_id])

            logger.debug(
                f"Found {len(healthy_agents)} healthy agents with capability "
                f"'{capability}' from local index"
            )
            return healthy_agents

        except Exception as e:
            logger.error(
                f"Failed to discover agents with capability '{capability}': {e}"
            )
            return []

    def get_agent_instance(self, agent_id: str) -> Optional[Any]:
        """Get agent instance by ID."""
        return self.agents.get(agent_id)

    def get_agent_info(self, agent_id: str) -> Optional[ACPAgentInfo]:
        """Get agent info by ID."""
        return self.agent_infos.get(agent_id)

    async def get_agent(self, agent_id: str) -> Optional[ACPAgentInfo]:
        """Get agent information by ID."""
        return self.agent_infos.get(agent_id)

    async def list_agents(
        self, status: Optional[ACPAgentStatus] = None
    ) -> List[ACPAgentInfo]:
        """List all agents, optionally filtered by status."""
        agents = list(self.agent_infos.values())

        if status:
            agents = [agent for agent in agents if agent.status == status]

        return agents

    async def update_agent_status(self, agent_id: str, status: ACPAgentStatus) -> bool:
        """Update agent status."""
        try:
            if agent_id not in self.agents:
                logger.warning(f"Agent {agent_id} not found for status update")
                return False

            self.agents[agent_id].status = status
            self.agents[agent_id].last_heartbeat = datetime.now(timezone.utc)
            self.agent_last_seen[agent_id] = datetime.now(timezone.utc)

            # Update Redis cache if available
            if self.acp_cache:
                await self.acp_cache.cache_agent_status(
                    agent_id,
                    {
                        "status": status.value,
                        "last_seen": datetime.now(timezone.utc).isoformat(),
                        "current_runs": getattr(
                            self.agents[agent_id], "current_runs", 0
                        ),
                        "max_runs": getattr(
                            self.agents[agent_id], "max_concurrent_runs", 1
                        ),
                    },
                )

                # Update heartbeat
                await self.acp_cache.update_agent_heartbeat(agent_id)

            logger.debug(f"Agent {agent_id} status updated to {status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update agent {agent_id} status: {e}")
            return False

    async def health_check_all(self) -> Dict[str, bool]:
        """Perform health check on all agents."""
        health_status = {}

        for agent_id, agent_info in self.agents.items():
            try:
                # Check if agent is responsive
                is_healthy = await self._check_agent_health(agent_id)
                self.agent_health[agent_id] = is_healthy
                health_status[agent_id] = is_healthy

                if is_healthy:
                    self.agent_last_seen[agent_id] = datetime.now(timezone.utc)
                else:
                    logger.warning(f"Agent {agent_id} failed health check")
                    # Publish health check failure event
                    if self.events:
                        await self.events.publish_agent_health_check_failed(
                            agent_id, "Health check failed"
                        )

            except Exception as e:
                logger.error(f"Health check failed for agent {agent_id}: {e}")
                self.agent_health[agent_id] = False
                health_status[agent_id] = False

        return health_status

    async def get_metrics(self) -> Dict[str, Any]:
        """Get registry metrics."""
        total_agents = len(self.agents)
        online_agents = sum(
            1 for agent in self.agents.values() if agent.status == ACPAgentStatus.ONLINE
        )
        busy_agents = sum(
            1 for agent in self.agents.values() if agent.status == ACPAgentStatus.BUSY
        )
        error_agents = sum(
            1 for agent in self.agents.values() if agent.status == ACPAgentStatus.ERROR
        )
        healthy_agents = sum(
            1 for is_healthy in self.agent_health.values() if is_healthy
        )

        return {
            "total_agents": total_agents,
            "online_agents": online_agents,
            "busy_agents": busy_agents,
            "error_agents": error_agents,
            "healthy_agents": healthy_agents,
            "capabilities_count": len(self.capabilities_index),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    async def _update_capabilities_index(self, agent_info: ACPAgentInfo) -> None:
        """Update the capabilities index for an agent."""
        # Remove old capabilities
        for capability, agent_ids in self.capabilities_index.items():
            agent_ids.discard(agent_info.agent_id)

        # Add new capabilities
        for capability in agent_info.capabilities:
            self.capabilities_index[capability].add(agent_info.agent_id)

    async def _check_agent_health(self, agent_id: str) -> bool:
        """Check if a specific agent is healthy."""
        try:
            # This would typically involve sending a ping message to the agent
            # For now, we'll use a simple timeout-based check
            agent_info = self.agents.get(agent_id)
            if not agent_info:
                return False

            # Check if agent has been seen recently
            last_seen = self.agent_last_seen.get(agent_id)
            if last_seen:
                time_since_last_seen = datetime.now(timezone.utc) - last_seen
                if time_since_last_seen > timedelta(
                    seconds=self.config.health_check_timeout * 2
                ):
                    return False

            return True

        except Exception as e:
            logger.error(f"Health check error for agent {agent_id}: {e}")
            return False

    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self.health_check_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    async def _discovery_loop(self) -> None:
        """Background discovery loop."""
        while True:
            try:
                await asyncio.sleep(self.config.discovery_interval)
                # This would typically involve discovering new agents
                # For now, we'll just log the discovery check
                logger.debug("Performing agent discovery check")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Discovery loop error: {e}")

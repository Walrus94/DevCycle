"""
Agent service for DevCycle.

This module contains business logic for agent management operations,
including registration, health monitoring, discovery, and lifecycle management.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..agents.models import (
    Agent,
    AgentCapability,
    AgentConfiguration,
    AgentHealth,
    AgentHeartbeat,
    AgentRegistration,
    AgentResponse,
    AgentStatus,
    AgentTask,
    AgentType,
    AgentUpdate,
)
from ..repositories.agent_repository import AgentRepository, AgentTaskRepository
from .base import BaseService


class AgentService(BaseService[Agent]):
    """Service for agent management operations."""

    def __init__(
        self, agent_repository: AgentRepository, task_repository: AgentTaskRepository
    ):
        """Initialize agent service."""
        super().__init__(agent_repository)
        self.agent_repository = agent_repository
        self.task_repository = task_repository

    async def register_agent(self, registration: AgentRegistration) -> AgentResponse:
        """Register a new agent with business logic validation."""
        # Check if agent name already exists
        existing_agent = await self.agent_repository.get_by_name(registration.name)
        if existing_agent:
            raise ValueError(f"Agent with name '{registration.name}' already exists")

        # Validate capabilities
        if not registration.capabilities:
            raise ValueError("Agent must have at least one capability")

        # Set default configuration if not provided
        if not registration.configuration:
            registration.configuration = AgentConfiguration()

        # Create agent data
        agent_data = {
            "name": registration.name,
            "agent_type": registration.agent_type.value,
            "description": registration.description,
            "version": registration.version,
            "capabilities": json.dumps(
                [cap.value for cap in registration.capabilities]
            ),
            "configuration": json.dumps(registration.configuration.dict()),
            "metadata_json": json.dumps(registration.metadata),
            "status": AgentStatus.OFFLINE.value,
            "is_active": True,
        }

        # Create agent through repository
        agent = await self.repository.create(**agent_data)

        # Convert to response model
        return await self._to_agent_response(agent)

    async def update_agent(
        self, agent_id: UUID, update_data: AgentUpdate
    ) -> Optional[AgentResponse]:
        """Update agent with business logic validation."""
        # Get existing agent
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None

        # Check name uniqueness if changing
        if update_data.name and update_data.name != agent.name:
            existing_agent = await self.agent_repository.get_by_name(update_data.name)
            if existing_agent and existing_agent.id != agent_id:
                raise ValueError(f"Agent with name '{update_data.name}' already exists")

        # Prepare update data
        update_dict = {}
        if update_data.name:
            update_dict["name"] = update_data.name
        if update_data.description is not None:
            update_dict["description"] = update_data.description
        if update_data.version:
            update_dict["version"] = update_data.version
        if update_data.capabilities is not None:
            update_dict["capabilities"] = json.dumps(
                [cap.value for cap in update_data.capabilities]
            )
        if update_data.configuration is not None:
            update_dict["configuration"] = json.dumps(update_data.configuration.dict())
        if update_data.metadata is not None:
            update_dict["metadata_json"] = json.dumps(update_data.metadata)

        # Update agent
        updated_agent = await self.repository.update(agent_id, **update_dict)
        if updated_agent:
            return await self._to_agent_response(updated_agent)
        return None

    async def get_agent_by_name(self, name: str) -> Optional[AgentResponse]:
        """Get agent by name."""
        agent = await self.agent_repository.get_by_name(name)
        if agent:
            return await self._to_agent_response(agent)
        return None

    async def get_agents_by_type(self, agent_type: AgentType) -> List[AgentResponse]:
        """Get all agents of a specific type."""
        agents = await self.agent_repository.get_by_type(agent_type)
        return [await self._to_agent_response(agent) for agent in agents]

    async def get_online_agents(self) -> List[AgentResponse]:
        """Get all online agents."""
        agents = await self.agent_repository.get_online_agents()
        return [await self._to_agent_response(agent) for agent in agents]

    async def get_available_agents(self) -> List[AgentResponse]:
        """Get agents available for new tasks."""
        agents = await self.agent_repository.get_available_agents()
        return [await self._to_agent_response(agent) for agent in agents]

    async def get_agents_by_capability(
        self, capability: AgentCapability
    ) -> List[AgentResponse]:
        """Get agents with a specific capability."""
        agents = await self.agent_repository.get_agents_by_capability(capability.value)
        return [await self._to_agent_response(agent) for agent in agents]

    async def get_agents_by_status(self, status: AgentStatus) -> List[AgentResponse]:
        """Get agents by status."""
        agents = await self.agent_repository.get_agents_by_status(status)
        return [await self._to_agent_response(agent) for agent in agents]

    async def search_agents(
        self,
        query: str,
        agent_type: Optional[AgentType] = None,
        status: Optional[AgentStatus] = None,
        limit: Optional[int] = None,
    ) -> List[AgentResponse]:
        """Search agents by query and filters."""
        agents = await self.agent_repository.search_agents(
            query, agent_type, status, limit
        )
        return [await self._to_agent_response(agent) for agent in agents]

    async def process_heartbeat(
        self, heartbeat: AgentHeartbeat
    ) -> Optional[AgentResponse]:
        """Process agent heartbeat and update health status."""
        # Get agent
        agent = await self.get_by_id(heartbeat.agent_id)
        if not agent:
            return None

        # Update agent health
        updated_agent = await self.agent_repository.update_agent_health(
            heartbeat.agent_id, heartbeat.status, error_message=heartbeat.error_message
        )

        if updated_agent:
            return await self._to_agent_response(updated_agent)
        return None

    async def mark_agent_offline(self, agent_id: UUID) -> Optional[AgentResponse]:
        """Mark agent as offline."""
        updated_agent = await self.agent_repository.mark_agent_offline(agent_id)
        if updated_agent:
            return await self._to_agent_response(updated_agent)
        return None

    async def deactivate_agent(self, agent_id: UUID) -> Optional[AgentResponse]:
        """Deactivate an agent."""
        updated_agent = await self.agent_repository.deactivate_agent(agent_id)
        if updated_agent:
            return await self._to_agent_response(updated_agent)
        return None

    async def activate_agent(self, agent_id: UUID) -> Optional[AgentResponse]:
        """Activate an agent."""
        updated_agent = await self.agent_repository.activate_agent(agent_id)
        if updated_agent:
            return await self._to_agent_response(updated_agent)
        return None

    async def get_agent_health(self, agent_id: UUID) -> Optional[AgentHealth]:
        """Get agent health status."""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None

        return AgentHealth(
            status=AgentStatus(agent.status),
            last_heartbeat=agent.last_heartbeat or datetime.utcnow(),
            response_time_ms=agent.response_time_ms,
            error_count=agent.error_count,
            last_error=agent.last_error,
            uptime_seconds=agent.uptime_seconds,
        )

    async def get_agent_statistics(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return await self.agent_repository.get_agent_statistics()

    async def cleanup_stale_agents(
        self, timeout_minutes: int = 5
    ) -> List[AgentResponse]:
        """Clean up stale agents by marking them offline."""
        stale_agents = await self.agent_repository.get_stale_agents(timeout_minutes)
        cleaned_agents = []

        for agent in stale_agents:
            updated_agent = await self.agent_repository.mark_agent_offline(agent.id)
            if updated_agent:
                cleaned_agents.append(await self._to_agent_response(updated_agent))

        return cleaned_agents

    async def assign_task_to_agent(
        self, agent_id: UUID, task_type: str, parameters: Dict[str, Any]
    ) -> Optional[AgentTask]:
        """Assign a task to an agent."""
        # Check if agent is available
        agent = await self.get_by_id(agent_id)
        if not agent or not agent.is_active:
            raise ValueError("Agent is not available for task assignment")

        if agent.status not in [AgentStatus.ONLINE.value, AgentStatus.BUSY.value]:
            raise ValueError("Agent is not in a state to accept tasks")

        # Create task
        task_data = {
            "agent_id": agent_id,
            "task_type": task_type,
            "status": "pending",
            "parameters": json.dumps(parameters),
        }

        task = await self.task_repository.create(**task_data)

        # Update agent status to busy
        await self.agent_repository.update_agent_status(agent_id, AgentStatus.BUSY)

        return task

    async def get_agent_tasks(self, agent_id: UUID) -> List[AgentTask]:
        """Get all tasks for an agent."""
        return await self.task_repository.get_tasks_by_agent(agent_id)

    async def update_task_status(
        self,
        task_id: UUID,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[AgentTask]:
        """Update task status."""
        updated_task = await self.task_repository.update_task_status(
            task_id, status, result, error
        )

        # If task is completed or failed, update agent status
        if updated_task and status in ["completed", "failed"]:
            agent = await self.get_by_id(updated_task.agent_id)
            if agent:
                # Check if agent has other pending/running tasks
                pending_tasks = await self.task_repository.get_tasks_by_agent(agent.id)
                has_active_tasks = any(
                    task.status in ["pending", "running"] for task in pending_tasks
                )

                if not has_active_tasks:
                    await self.agent_repository.update_agent_status(
                        agent.id, AgentStatus.ONLINE
                    )

        return updated_task

    async def get_agent_task_history(
        self, agent_id: UUID, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[AgentTask]:
        """Get task history for an agent."""
        return await self.task_repository.get_agent_task_history(
            agent_id, limit, offset
        )

    async def validate_business_rules(self, entity: Agent, **kwargs: Any) -> bool:
        """Validate business rules for agent operations."""
        # Basic validation rules
        if not entity.name:
            return False

        if not entity.agent_type:
            return False

        # Business rule: Active agents must have capabilities
        if entity.is_active and not entity.capabilities:
            return False

        return True

    async def apply_business_logic(self, entity: Agent, **kwargs: Any) -> Agent:
        """Apply business logic to agent."""
        # Apply business logic based on context
        if kwargs.get("is_new_agent"):
            # New agents start as offline
            entity.status = AgentStatus.OFFLINE.value
            entity.is_active = True

        if kwargs.get("deactivated"):
            # Deactivated agents are marked offline
            entity.status = AgentStatus.OFFLINE.value

        if kwargs.get("for_listing"):
            # Remove sensitive information for listing operations
            pass

        return entity

    async def _to_agent_response(self, agent: Agent) -> AgentResponse:
        """Convert Agent model to AgentResponse."""
        # Parse JSON fields
        try:
            capabilities = json.loads(agent.capabilities) if agent.capabilities else []
            configuration = (
                json.loads(agent.configuration) if agent.configuration else {}
            )
            metadata = json.loads(agent.metadata_json) if agent.metadata_json else {}
        except json.JSONDecodeError:
            capabilities = []
            configuration = {}
            metadata = {}

        # Create health object
        health = AgentHealth(
            status=AgentStatus(agent.status),
            last_heartbeat=agent.last_heartbeat or datetime.utcnow(),
            response_time_ms=agent.response_time_ms,
            error_count=agent.error_count,
            last_error=agent.last_error,
            uptime_seconds=agent.uptime_seconds,
        )

        # Create configuration object
        config = AgentConfiguration(**configuration)

        return AgentResponse(
            id=agent.id,
            name=agent.name,
            agent_type=AgentType(agent.agent_type),
            description=agent.description,
            version=agent.version,
            capabilities=[AgentCapability(cap) for cap in capabilities],
            configuration=config,
            status=AgentStatus(agent.status),
            health=health,
            metadata=metadata,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            last_seen=agent.last_seen or agent.created_at,
        )

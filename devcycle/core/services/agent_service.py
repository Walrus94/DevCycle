"""
Agent service using Tortoise ORM directly.

No repository pattern needed - direct ORM operations are clean and simple.
Service layer handles conversion from Tortoise models to Pydantic DTOs.
"""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from ..agents.models import AgentStatus
from ..database.tortoise_schemas import (
    AgentCreate,
    AgentResponse,
    AgentTaskCreate,
    AgentTaskResponse,
    AgentUpdate,
)
from ..models.tortoise_models import Agent, AgentTask


class AgentService:
    """Agent service using Tortoise ORM directly."""

    def __init__(
        self,
        agent_repository: Optional[Any] = None,
        task_repository: Optional[Any] = None,
        lifecycle_service: Optional[Any] = None,
    ) -> None:
        """Initialize the agent service with optional dependencies."""
        self.agent_repository = agent_repository
        self.task_repository = task_repository
        self.lifecycle_service = lifecycle_service

    async def get_agent_by_id(self, agent_id: UUID) -> Optional[AgentResponse]:
        """Get agent by ID."""
        agent = await Agent.get_or_none(id=agent_id)
        return AgentResponse.model_validate(agent) if agent else None

    async def get_agent_by_name(self, name: str) -> Optional[AgentResponse]:
        """Get agent by name."""
        agent = await Agent.get_or_none(name=name)
        return AgentResponse.model_validate(agent) if agent else None

    async def create_agent(self, agent_data: AgentCreate) -> AgentResponse:
        """Create a new agent."""
        agent = await Agent.create(**agent_data.model_dump())
        return AgentResponse.model_validate(agent)

    async def register_agent(self, registration_data: Any) -> AgentResponse:
        """Register a new agent (alias for create_agent for compatibility)."""
        import json

        # Convert AgentRegistration to AgentCreate format
        if hasattr(registration_data, "model_dump"):
            data = registration_data.model_dump()
        else:
            data = registration_data

        # Convert capabilities list to JSON string
        if "capabilities" in data and isinstance(data["capabilities"], list):
            data["capabilities"] = json.dumps(
                [
                    cap.value if hasattr(cap, "value") else str(cap)
                    for cap in data["capabilities"]
                ]
            )

        # Convert configuration dict to JSON string
        if "configuration" in data and isinstance(data["configuration"], dict):
            data["configuration"] = json.dumps(data["configuration"])

        # Convert metadata dict to JSON string and rename to metadata_json
        if "metadata" in data and isinstance(data["metadata"], dict):
            data["metadata_json"] = json.dumps(data["metadata"])
            del data["metadata"]

        agent_data = AgentCreate(**data)
        response = await self.create_agent(agent_data)

        # Register with lifecycle service if available
        if self.lifecycle_service:
            await self.lifecycle_service.register_agent(response.id)

        return response

    def get_agent_lifecycle_status(self, agent_id: UUID) -> dict[str, Any]:
        """Get agent lifecycle status."""
        if self.lifecycle_service:
            result = self.lifecycle_service.get_agent_status(agent_id)
            return dict(result) if result else {}
        return {"current_state": "unknown", "error": "No lifecycle service available"}

    def get_all_agent_lifecycle_statuses(self) -> dict[str, Any]:
        """Get all agent lifecycle statuses."""
        if self.lifecycle_service:
            result = self.lifecycle_service.get_all_agent_statuses()
            return dict(result) if result else {}
        return {}

    async def deploy_agent(self, agent_id: UUID) -> Optional[AgentResponse]:
        """Deploy an agent."""
        if self.lifecycle_service:
            success = await self.lifecycle_service.deploy_agent(agent_id)
            if success:
                return await self.get_agent_by_id(agent_id)
        return None

    async def start_agent(self, agent_id: UUID) -> Optional[AgentResponse]:
        """Start an agent."""
        if self.lifecycle_service:
            success = await self.lifecycle_service.start_agent(agent_id)
            if success:
                # Update repository status
                if self.agent_repository:
                    await self.agent_repository.update_agent_status(
                        agent_id, AgentStatus.ONLINE
                    )
                return await self.get_agent_by_id(agent_id)
        return None

    async def stop_agent(self, agent_id: UUID) -> Optional[AgentResponse]:
        """Stop an agent."""
        if self.lifecycle_service:
            success = await self.lifecycle_service.stop_agent(agent_id)
            if success:
                return await self.get_agent_by_id(agent_id)
        return None

    async def assign_task(self, agent_id: UUID) -> bool:
        """Assign a task to an agent."""
        if self.lifecycle_service:
            result = await self.lifecycle_service.assign_task(agent_id)
            return bool(result)
        return False

    async def complete_task(self, agent_id: UUID) -> bool:
        """Mark task as completed."""
        if self.lifecycle_service:
            result = await self.lifecycle_service.complete_task(agent_id)
            return bool(result)
        return False

    async def put_in_maintenance(
        self, agent_id: UUID, reason: str = "Maintenance"
    ) -> bool:
        """Put agent in maintenance mode."""
        if self.lifecycle_service:
            result = await self.lifecycle_service.put_in_maintenance(agent_id, reason)
            return bool(result)
        return False

    async def resume_from_maintenance(self, agent_id: UUID) -> bool:
        """Resume agent from maintenance mode."""
        if self.lifecycle_service:
            result = await self.lifecycle_service.resume_from_maintenance(agent_id)
            return bool(result)
        return False

    def get_operational_agents(self) -> List[UUID]:
        """Get list of operational agents."""
        if self.lifecycle_service:
            result = self.lifecycle_service.get_operational_agents()
            return list(result) if result else []
        return []

    def get_available_agents(self) -> List[UUID]:
        """Get list of available agents."""
        if self.lifecycle_service:
            result = self.lifecycle_service.get_available_agents()
            return list(result) if result else []
        return []

    def get_agents_in_error(self) -> List[UUID]:
        """Get list of agents in error state."""
        if self.lifecycle_service:
            result = self.lifecycle_service.get_agents_in_error()
            return list(result) if result else []
        return []

    def get_agents_in_maintenance(self) -> List[UUID]:
        """Get list of agents in maintenance state."""
        if self.lifecycle_service:
            result = self.lifecycle_service.get_agents_in_maintenance()
            return list(result) if result else []
        return []

    async def assign_task_to_agent(self, agent_id: UUID, task_data: Any) -> bool:
        """Assign a task to an agent."""
        # This is a placeholder implementation
        # In a real system, this would integrate with task management
        return True

    async def handle_error(self, agent_id: UUID, error_message: str) -> bool:
        """Handle agent error."""
        if self.lifecycle_service:
            result = await self.lifecycle_service.handle_error(agent_id, error_message)
            return bool(result)
        return False

    async def update_agent(
        self, agent_id: UUID, agent_data: AgentUpdate
    ) -> Optional[AgentResponse]:
        """Update an agent."""
        agent = await Agent.get_or_none(id=agent_id)
        if not agent:
            return None

        update_data = agent_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(agent, key, value)

        await agent.save()
        return AgentResponse.model_validate(agent)

    async def delete_agent(self, agent_id: UUID) -> bool:
        """Delete an agent."""
        agent = await Agent.get_or_none(id=agent_id)
        if not agent:
            return False

        await agent.delete()
        return True

    async def get_agents_by_status(self, status: str) -> List[AgentResponse]:
        """Get agents by status."""
        agents = await Agent.filter(status=status)
        return [AgentResponse.model_validate(agent) for agent in agents]

    async def get_active_agents(self) -> List[AgentResponse]:
        """Get all active agents."""
        agents = await Agent.filter(is_active=True)
        return [AgentResponse.model_validate(agent) for agent in agents]

    async def get_agents_by_type(self, agent_type: str) -> List[AgentResponse]:
        """Get agents by type."""
        agents = await Agent.filter(agent_type=agent_type)
        return [AgentResponse.model_validate(agent) for agent in agents]

    async def update_heartbeat(
        self, agent_id: UUID, response_time_ms: Optional[int] = None
    ) -> Optional[AgentResponse]:
        """Update agent heartbeat."""
        agent = await Agent.get_or_none(id=agent_id)
        if not agent:
            return None

        agent.last_heartbeat = datetime.now()
        agent.last_seen = datetime.now()
        if response_time_ms is not None:
            agent.response_time_ms = response_time_ms

        await agent.save()
        return AgentResponse.model_validate(agent)

    # Agent Task methods
    async def create_agent_task(self, task_data: AgentTaskCreate) -> AgentTaskResponse:
        """Create a new agent task."""
        task = await AgentTask.create(**task_data.model_dump())
        return AgentTaskResponse.model_validate(task)

    async def get_agent_tasks(self, agent_id: UUID) -> List[AgentTaskResponse]:
        """Get all tasks for an agent."""
        tasks = await AgentTask.filter(agent_id=agent_id)
        return [AgentTaskResponse.model_validate(task) for task in tasks]

    async def get_task_by_id(self, task_id: UUID) -> Optional[AgentTaskResponse]:
        """Get task by ID."""
        task = await AgentTask.get_or_none(id=task_id)
        return AgentTaskResponse.model_validate(task) if task else None

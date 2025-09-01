"""
Agent service for DevCycle.

This module contains business logic for agent management operations,
including registration, health monitoring, discovery, and lifecycle management.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..agents.lifecycle import AgentLifecycleService, AgentLifecycleState
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
    AgentTaskResponse,
    AgentType,
    AgentUpdate,
)
from ..repositories.agent_repository import AgentRepository, AgentTaskRepository


class AgentService:
    """Service for agent management operations."""

    def __init__(
        self,
        agent_repository: AgentRepository,
        task_repository: AgentTaskRepository,
        lifecycle_service: Optional[AgentLifecycleService] = None,
    ):
        """Initialize agent service."""
        self.agent_repository = agent_repository
        self.task_repository = task_repository
        self.lifecycle_service = lifecycle_service or AgentLifecycleService()

        # Register lifecycle event handlers
        self._register_lifecycle_handlers()

    def _register_lifecycle_handlers(self) -> None:
        """Register event handlers for lifecycle state changes."""
        # Event handlers will be registered per agent when needed
        # This is a placeholder for future global event handling
        pass

    async def _on_agent_state_change(
        self, event_type: str, data: Dict[str, Any]
    ) -> None:
        """Handle agent state change events."""
        agent_id = data.get("agent_id")
        to_state = data.get("to_state")

        if not agent_id:
            return

        # Update database status
        if to_state:
            await self.agent_repository.update_agent_status(
                agent_id, AgentStatus(to_state.value)
            )

        # Handle specific state transitions
        if to_state == AgentLifecycleState.ERROR:
            await self._handle_agent_error(
                agent_id, data.get("reason", "Unknown error")
            )
        elif to_state == AgentLifecycleState.OFFLINE:
            await self._handle_agent_offline(agent_id)
        elif to_state == AgentLifecycleState.ONLINE:
            await self._handle_agent_online(agent_id)

    async def _handle_agent_error(self, agent_id: UUID, error_reason: str) -> None:
        """Handle agent error state."""
        # Update error count and last error
        await self.agent_repository.update_agent_health(
            agent_id, AgentStatus.ERROR, error_message=error_reason
        )

    async def _handle_agent_offline(self, agent_id: UUID) -> None:
        """Handle agent going offline."""
        # Cancel any pending tasks
        pending_tasks = await self.task_repository.get_tasks_by_agent(agent_id)
        for task in pending_tasks:
            if task.status in ["pending", "running"]:
                await self.task_repository.update_task_status(
                    task.id, "cancelled", error="Agent went offline"
                )

    async def _handle_agent_online(self, agent_id: UUID) -> None:
        """Handle agent coming online."""
        # Agent is now available for new tasks
        pass

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
            "configuration": json.dumps(registration.configuration.model_dump()),
            "metadata_json": json.dumps(registration.metadata),
            "status": AgentStatus.OFFLINE.value,
            "is_active": True,
        }

        # Create agent through repository
        agent = await self.agent_repository.create(**agent_data)

        # Register with lifecycle service
        await self.lifecycle_service.register_agent(agent.id)

        # Register event handlers for this agent
        manager = self.lifecycle_service.get_manager(agent.id)
        manager.on_event("post_transition", self._on_agent_state_change)

        # Convert to response model
        return await self._to_agent_response(agent)

    async def update_agent(
        self, agent_id: UUID, update_data: AgentUpdate
    ) -> Optional[AgentResponse]:
        """Update agent with business logic validation."""
        # Get existing agent
        agent = await self.agent_repository.get_by_id(agent_id)
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
            update_dict["configuration"] = json.dumps(
                update_data.configuration.model_dump()
            )
        if update_data.metadata is not None:
            update_dict["metadata_json"] = json.dumps(update_data.metadata)

        # Update agent
        updated_agent = await self.agent_repository.update(agent_id, **update_dict)
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

    async def get_by_id(self, agent_id: UUID) -> Optional[AgentResponse]:
        """Get agent by ID and convert to response model."""
        agent = await self.agent_repository.get_by_id(agent_id)
        if not agent:
            return None
        return await self._to_agent_response(agent)

    async def get_all(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[AgentResponse]:
        """Get all agents and convert to response models."""
        agents = await self.agent_repository.get_all(limit=limit, offset=offset)
        return [await self._to_agent_response(agent) for agent in agents]

    async def delete(self, agent_id: UUID) -> bool:
        """Delete an agent."""
        return await self.agent_repository.delete(agent_id)

    async def process_heartbeat(
        self, heartbeat: AgentHeartbeat
    ) -> Optional[AgentResponse]:
        """Process agent heartbeat and update health status."""
        # Get agent
        agent = await self.agent_repository.get_by_id(heartbeat.agent_id)
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
            last_heartbeat=agent.last_heartbeat or datetime.now(timezone.utc),
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
        agent = await self.agent_repository.get_by_id(agent_id)
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

    async def get_agent_tasks(self, agent_id: UUID) -> List[AgentTaskResponse]:
        """Get all tasks for an agent."""
        tasks = await self.task_repository.get_tasks_by_agent(agent_id)
        return [await self._to_agent_task_response(task) for task in tasks]

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
    ) -> List[AgentTaskResponse]:
        """Get task history for an agent."""
        tasks = await self.task_repository.get_agent_task_history(
            agent_id, limit, offset
        )
        return [await self._to_agent_task_response(task) for task in tasks]

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
            # Handle capabilities - could be JSON string or already a list
            if agent.capabilities:
                if isinstance(agent.capabilities, str):
                    capabilities = json.loads(agent.capabilities)
                elif isinstance(agent.capabilities, list):
                    capabilities = agent.capabilities
                else:
                    capabilities = []
            else:
                capabilities = []

            # Handle configuration - should be JSON string
            if agent.configuration:
                if isinstance(agent.configuration, str):
                    configuration = json.loads(agent.configuration)
                elif isinstance(agent.configuration, dict):
                    configuration = agent.configuration
                else:
                    configuration = {}
            else:
                configuration = {}

            # Handle metadata - should be JSON string
            if agent.metadata_json:
                if isinstance(agent.metadata_json, str):
                    metadata = json.loads(agent.metadata_json)
                elif isinstance(agent.metadata_json, dict):
                    metadata = agent.metadata_json
                else:
                    metadata = {}
            else:
                metadata = {}
        except (json.JSONDecodeError, TypeError):
            capabilities = []
            configuration = {}
            metadata = {}

        # Create health object
        health = AgentHealth(
            status=AgentStatus(agent.status),
            last_heartbeat=agent.last_heartbeat or datetime.now(timezone.utc),
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

    async def _to_agent_task_response(self, task: AgentTask) -> AgentTaskResponse:
        """Convert AgentTask model to AgentTaskResponse."""
        # Parse JSON fields
        try:
            parameters = json.loads(task.parameters) if task.parameters else {}
            result = json.loads(task.result) if task.result else None
        except json.JSONDecodeError:
            parameters = {}
            result = None

        return AgentTaskResponse(
            id=task.id,
            agent_id=task.agent_id,
            task_type=task.task_type,
            status=task.status,
            parameters=parameters,
            result=result,
            error=task.error,
            created_at=task.created_at,
            updated_at=task.updated_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
        )

    # Lifecycle Management Methods

    async def start_agent(self, agent_id: UUID) -> Optional[AgentResponse]:
        """Start an agent with lifecycle management."""
        # Check if agent exists
        agent = await self.agent_repository.get_by_id(agent_id)
        if not agent:
            return None

        # Start through lifecycle service
        success = await self.lifecycle_service.start_agent(agent_id)
        if not success:
            return None

        # Update database status
        await self.agent_repository.update_agent_status(agent_id, AgentStatus.ONLINE)

        return await self._to_agent_response(agent)

    async def stop_agent(self, agent_id: UUID) -> Optional[AgentResponse]:
        """Stop an agent with lifecycle management."""
        # Stop through lifecycle service
        success = await self.lifecycle_service.stop_agent(agent_id)
        if not success:
            return None

        # Update database status
        await self.agent_repository.update_agent_status(agent_id, AgentStatus.OFFLINE)

        agent = await self.agent_repository.get_by_id(agent_id)
        return await self._to_agent_response(agent) if agent else None

    async def deploy_agent(self, agent_id: UUID) -> Optional[AgentResponse]:
        """Deploy an agent with lifecycle management."""
        # Deploy through lifecycle service
        success = await self.lifecycle_service.deploy_agent(agent_id)
        if not success:
            return None

        # Update database status
        await self.agent_repository.update_agent_status(agent_id, AgentStatus.DEPLOYED)

        agent = await self.agent_repository.get_by_id(agent_id)
        return await self._to_agent_response(agent) if agent else None

    async def put_agent_in_maintenance(
        self, agent_id: UUID, reason: str = "Scheduled maintenance"
    ) -> Optional[AgentResponse]:
        """Put agent in maintenance mode."""
        # Put in maintenance through lifecycle service
        success = await self.lifecycle_service.put_in_maintenance(agent_id, reason)
        if not success:
            return None

        # Update database status
        await self.agent_repository.update_agent_status(
            agent_id, AgentStatus.MAINTENANCE
        )

        agent = await self.agent_repository.get_by_id(agent_id)
        return await self._to_agent_response(agent) if agent else None

    async def resume_agent_from_maintenance(
        self, agent_id: UUID
    ) -> Optional[AgentResponse]:
        """Resume agent from maintenance mode."""
        # Resume from maintenance through lifecycle service
        success = await self.lifecycle_service.resume_from_maintenance(agent_id)
        if not success:
            return None

        # Update database status
        await self.agent_repository.update_agent_status(agent_id, AgentStatus.ONLINE)

        agent = await self.agent_repository.get_by_id(agent_id)
        return await self._to_agent_response(agent) if agent else None

    def get_agent_lifecycle_status(self, agent_id: UUID) -> Optional[Dict[str, Any]]:
        """Get agent lifecycle status."""
        return self.lifecycle_service.get_agent_status(agent_id)

    def get_all_agent_lifecycle_statuses(self) -> Dict[UUID, Dict[str, Any]]:
        """Get all agent lifecycle statuses."""
        return self.lifecycle_service.get_all_agent_statuses()

    def get_operational_agents(self) -> List[UUID]:
        """Get list of operational agents."""
        return self.lifecycle_service.get_operational_agents()

    def get_available_agent_ids(self) -> List[UUID]:
        """Get list of agents available for tasks."""
        return self.lifecycle_service.get_available_agents()

    def get_agents_in_error(self) -> List[UUID]:
        """Get list of agents in error state."""
        return self.lifecycle_service.get_agents_in_error()

    def get_agents_in_maintenance(self) -> List[UUID]:
        """Get list of agents in maintenance."""
        return self.lifecycle_service.get_agents_in_maintenance()

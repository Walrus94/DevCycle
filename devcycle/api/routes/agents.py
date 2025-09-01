"""
Agent management endpoints for the DevCycle API.

This module provides endpoints for agent registration, discovery, and management.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...core.agents.models import (
    AgentCapability,
    AgentHeartbeat,
    AgentRegistration,
    AgentResponse,
    AgentStatus,
    AgentTaskResponse,
    AgentType,
    AgentUpdate,
)
from ...core.auth.fastapi_users import current_active_user
from ...core.auth.models import User
from ...core.dependencies import get_agent_service
from ...core.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


# Authentication dependency for protected endpoints
def require_auth() -> Any:
    """Require authentication for protected endpoints."""
    return Depends(current_active_user)


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(
    registration: AgentRegistration,
    agent_service: AgentService = Depends(get_agent_service),
    user: User = Depends(current_active_user),
) -> AgentResponse:
    """
    Register a new agent.

    This endpoint allows agents to register themselves with the system,
    providing their capabilities, configuration, and metadata.
    """
    try:
        agent = await agent_service.register_agent(registration)
        return agent
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register agent",
        )


@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    agent_type: Optional[AgentType] = Query(None, description="Filter by agent type"),
    status_filter: Optional[AgentStatus] = Query(
        None, description="Filter by agent status"
    ),
    capability: Optional[AgentCapability] = Query(
        None, description="Filter by capability"
    ),
    limit: Optional[int] = Query(
        100, ge=1, le=1000, description="Maximum number of agents to return"
    ),
    offset: Optional[int] = Query(0, ge=0, description="Number of agents to skip"),
    agent_service: AgentService = Depends(get_agent_service),
    user: User = Depends(current_active_user),
) -> List[AgentResponse]:
    """
    List all agents with optional filtering.

    Supports filtering by type, status, and capabilities, with pagination.
    """
    try:
        if capability:
            agents = await agent_service.get_agents_by_capability(capability)
        elif agent_type:
            agents = await agent_service.get_agents_by_type(agent_type)
        elif status_filter:
            agents = await agent_service.get_agents_by_status(status_filter)
        else:
            agents = await agent_service.get_all(limit=limit, offset=offset)

        # Apply pagination manually for filtered results
        if offset:
            agents = agents[offset:]
        if limit:
            agents = agents[:limit]

        return agents
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agents",
        )


@router.get("/online", response_model=List[AgentResponse])
async def get_online_agents(
    agent_service: AgentService = Depends(get_agent_service),
) -> List[AgentResponse]:
    """
    Get all online agents.

    Returns agents that are currently online and available.
    """
    try:
        return await agent_service.get_online_agents()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve online agents",
        )


@router.get("/available", response_model=List[AgentResponse])
async def get_available_agents(
    agent_service: AgentService = Depends(get_agent_service),
) -> List[AgentResponse]:
    """
    Get agents available for new tasks.

    Returns agents that are online or busy but can accept new tasks.
    """
    try:
        return await agent_service.get_available_agents()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available agents",
        )


@router.get("/search", response_model=List[AgentResponse])
async def search_agents(
    query: str = Query(..., min_length=1, description="Search query"),
    agent_type: Optional[AgentType] = Query(None, description="Filter by agent type"),
    status_filter: Optional[AgentStatus] = Query(
        None, description="Filter by agent status"
    ),
    limit: Optional[int] = Query(
        50, ge=1, le=100, description="Maximum number of results"
    ),
    agent_service: AgentService = Depends(get_agent_service),
) -> List[AgentResponse]:
    """
    Search agents by query and filters.

    Searches agent names and descriptions with optional type and status filtering.
    """
    try:
        return await agent_service.search_agents(
            query, agent_type, status_filter, limit
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search agents",
        )


@router.get("/types", response_model=List[str])
async def get_agent_types() -> List[str]:
    """
    Get available agent types.

    Returns all supported agent types in the system.
    """
    return [agent_type.value for agent_type in AgentType]


@router.get("/capabilities", response_model=List[str])
async def get_agent_capabilities() -> List[str]:
    """
    Get available agent capabilities.

    Returns all supported agent capabilities in the system.
    """
    return [capability.value for capability in AgentCapability]


@router.get("/statuses", response_model=List[str])
async def get_agent_statuses() -> List[str]:
    """
    Get available agent statuses.

    Returns all supported agent statuses in the system.
    """
    return [status.value for status in AgentStatus]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID, agent_service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """
    Get agent by ID.

    Returns detailed information about a specific agent.
    """
    try:
        agent = await agent_service.get_by_id(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
            )
        return agent
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent",
        )


@router.get("/name/{agent_name}", response_model=AgentResponse)
async def get_agent_by_name(
    agent_name: str, agent_service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """
    Get agent by name.

    Returns detailed information about a specific agent by name.
    """
    try:
        agent = await agent_service.get_agent_by_name(agent_name)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
            )
        return agent
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent",
        )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    update_data: AgentUpdate,
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """
    Update agent information.

    Allows updating agent description, version, capabilities, and configuration.
    """
    try:
        agent = await agent_service.update_agent(agent_id, update_data)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
            )
        return agent
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent",
        )


@router.post("/{agent_id}/heartbeat", response_model=AgentResponse)
async def send_heartbeat(
    agent_id: UUID,
    heartbeat: AgentHeartbeat,
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """
    Send agent heartbeat.

    Agents use this endpoint to report their status and health information.
    """
    try:
        agent = await agent_service.process_heartbeat(heartbeat)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
            )
        return agent
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process heartbeat",
        )


@router.post("/{agent_id}/offline", response_model=AgentResponse)
async def mark_agent_offline(
    agent_id: UUID, agent_service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """
    Mark agent as offline.

    Manually mark an agent as offline (useful for maintenance or debugging).
    """
    try:
        agent = await agent_service.mark_agent_offline(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
            )
        return agent
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark agent offline",
        )


@router.post("/{agent_id}/deactivate", response_model=AgentResponse)
async def deactivate_agent(
    agent_id: UUID, agent_service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """
    Deactivate an agent.

    Deactivates an agent, preventing it from receiving new tasks.
    """
    try:
        agent = await agent_service.deactivate_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
            )
        return agent
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate agent",
        )


@router.post("/{agent_id}/activate", response_model=AgentResponse)
async def activate_agent(
    agent_id: UUID, agent_service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """
    Activate an agent.

    Reactivates a previously deactivated agent.
    """
    try:
        agent = await agent_service.activate_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
            )
        return agent
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate agent",
        )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID, agent_service: AgentService = Depends(get_agent_service)
) -> None:
    """
    Delete an agent.

    Permanently removes an agent from the system.
    """
    try:
        success = await agent_service.delete(agent_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete agent",
        )


@router.get("/{agent_id}/tasks", response_model=List[AgentTaskResponse])
async def get_agent_tasks(
    agent_id: UUID, agent_service: AgentService = Depends(get_agent_service)
) -> List[AgentTaskResponse]:
    """
    Get tasks for a specific agent.

    Returns all tasks assigned to the specified agent.
    """
    try:
        return await agent_service.get_agent_tasks(agent_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent tasks",
        )


@router.get("/{agent_id}/tasks/history", response_model=List[AgentTaskResponse])
async def get_agent_task_history(
    agent_id: UUID,
    limit: Optional[int] = Query(
        50, ge=1, le=100, description="Maximum number of tasks to return"
    ),
    offset: Optional[int] = Query(0, ge=0, description="Number of tasks to skip"),
    agent_service: AgentService = Depends(get_agent_service),
) -> List[AgentTaskResponse]:
    """
    Get task history for a specific agent.

    Returns paginated task history for the specified agent.
    """
    try:
        return await agent_service.get_agent_task_history(agent_id, limit, offset)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent task history",
        )


@router.get("/statistics/overview")
async def get_agent_statistics(
    agent_service: AgentService = Depends(get_agent_service),
) -> Dict[str, Any]:
    """
    Get agent statistics overview.

    Returns summary statistics about all agents in the system.
    """
    try:
        return await agent_service.get_agent_statistics()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent statistics",
        )


@router.post("/cleanup/stale", response_model=List[AgentResponse])
async def cleanup_stale_agents(
    timeout_minutes: int = Query(
        5, ge=1, le=60, description="Timeout in minutes for stale agents"
    ),
    agent_service: AgentService = Depends(get_agent_service),
) -> List[AgentResponse]:
    """
    Clean up stale agents.

    Marks agents as offline if they haven't sent a heartbeat within the
    specified timeout.
    """
    try:
        return await agent_service.cleanup_stale_agents(timeout_minutes)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup stale agents",
        )


# Lifecycle Management Endpoints


@router.get("/{agent_id}/lifecycle", response_model=Dict[str, Any])
async def get_agent_lifecycle_status(
    agent_id: UUID, agent_service: AgentService = Depends(get_agent_service)
) -> Dict[str, Any]:
    """
    Get agent lifecycle status.

    Returns detailed lifecycle information for the specified agent.
    """
    try:
        lifecycle_status = agent_service.get_agent_lifecycle_status(agent_id)
        if not lifecycle_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
            )
        return lifecycle_status
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent lifecycle status",
        )


@router.get("/lifecycle/statuses", response_model=Dict[str, Dict[str, Any]])
async def get_all_agent_lifecycle_statuses(
    agent_service: AgentService = Depends(get_agent_service),
) -> Dict[str, Dict[str, Any]]:
    """
    Get all agent lifecycle statuses.

    Returns lifecycle information for all agents in the system.
    """
    try:
        statuses = agent_service.get_all_agent_lifecycle_statuses()
        # Convert UUID keys to strings for JSON serialization
        return {str(agent_id): status for agent_id, status in statuses.items()}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent lifecycle statuses",
        )


@router.post("/{agent_id}/lifecycle/start", response_model=AgentResponse)
async def start_agent_lifecycle(
    agent_id: UUID, agent_service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """
    Start an agent through lifecycle management.

    Transitions agent to ONLINE state and makes it available for tasks.
    """
    try:
        agent = await agent_service.start_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
            )
        return agent
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start agent",
        )


@router.post("/{agent_id}/lifecycle/stop", response_model=AgentResponse)
async def stop_agent_lifecycle(
    agent_id: UUID, agent_service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """
    Stop an agent through lifecycle management.

    Transitions agent to OFFLINE state and stops task processing.
    """
    try:
        agent = await agent_service.stop_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
            )
        return agent
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop agent",
        )


@router.post("/{agent_id}/lifecycle/deploy", response_model=AgentResponse)
async def deploy_agent_lifecycle(
    agent_id: UUID, agent_service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """
    Deploy an agent through lifecycle management.

    Transitions agent to DEPLOYED state.
    """
    try:
        agent = await agent_service.deploy_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
            )
        return agent
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deploy agent",
        )


@router.post("/{agent_id}/lifecycle/maintenance", response_model=AgentResponse)
async def put_agent_in_maintenance(
    agent_id: UUID,
    reason: str = "Scheduled maintenance",
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """
    Put agent in maintenance mode.

    Transitions agent to MAINTENANCE state for scheduled maintenance.
    """
    try:
        agent = await agent_service.put_agent_in_maintenance(agent_id, reason)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
            )
        return agent
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to put agent in maintenance mode",
        )


@router.post("/{agent_id}/lifecycle/resume", response_model=AgentResponse)
async def resume_agent_from_maintenance(
    agent_id: UUID, agent_service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """
    Resume agent from maintenance mode.

    Transitions agent from MAINTENANCE to ONLINE state.
    """
    try:
        agent = await agent_service.resume_agent_from_maintenance(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
            )
        return agent
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume agent from maintenance",
        )


@router.get("/lifecycle/operational", response_model=List[str])
async def get_operational_agents(
    agent_service: AgentService = Depends(get_agent_service),
) -> List[str]:
    """
    Get list of operational agents.

    Returns agent IDs that are currently operational (ONLINE, BUSY, or IDLE).
    """
    try:
        operational_agents = agent_service.get_operational_agents()
        return [str(agent_id) for agent_id in operational_agents]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve operational agents",
        )


@router.get("/lifecycle/available", response_model=List[str])
async def get_available_agent_ids(
    agent_service: AgentService = Depends(get_agent_service),
) -> List[str]:
    """
    Get list of agents available for tasks.

    Returns agent IDs that are available for new task assignments.
    """
    try:
        available_agents = agent_service.get_available_agent_ids()
        return [str(agent_id) for agent_id in available_agents]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available agents",
        )


@router.get("/lifecycle/errors", response_model=List[str])
async def get_agents_in_error(
    agent_service: AgentService = Depends(get_agent_service),
) -> List[str]:
    """
    Get list of agents in error state.

    Returns agent IDs that are currently in an error state.
    """
    try:
        error_agents = agent_service.get_agents_in_error()
        return [str(agent_id) for agent_id in error_agents]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agents in error",
        )


@router.get("/lifecycle/maintenance", response_model=List[str])
async def get_agents_in_maintenance(
    agent_service: AgentService = Depends(get_agent_service),
) -> List[str]:
    """
    Get list of agents in maintenance.

    Returns agent IDs that are currently in maintenance mode.
    """
    try:
        maintenance_agents = agent_service.get_agents_in_maintenance()
        return [str(agent_id) for agent_id in maintenance_agents]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agents in maintenance",
        )

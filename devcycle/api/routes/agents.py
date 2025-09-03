"""
Agent API endpoints using Tortoise ORM.

Clean, simple endpoints with direct ORM operations.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from ...core.agents.models import AgentCapability, AgentType
from ...core.auth.fastapi_users import current_active_user
from ...core.auth.tortoise_models import User
from ...core.database.tortoise_schemas import (
    AgentCreate,
    AgentResponse,
    AgentTaskResponse,
    AgentUpdate,
)
from ...core.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/types")
async def get_agent_types() -> List[str]:
    """Get available agent types (public endpoint)."""
    return [agent_type.value for agent_type in AgentType]


@router.get("/capabilities")
async def get_agent_capabilities() -> List[str]:
    """Get available agent capabilities (public endpoint)."""
    return [capability.value for capability in AgentCapability]


@router.get("/statistics/overview")
async def get_agent_statistics_overview() -> dict:
    """Get agent statistics overview (public endpoint)."""
    # Get basic statistics
    # In a real implementation, these would query the database
    stats = {
        "total_agents": 0,
        "online_agents": 0,
        "active_agents": 0,
    }

    try:
        # Query the database for actual statistics
        from ...core.models.tortoise_models import Agent

        total_agents = await Agent.all().count()
        online_agents = await Agent.filter(status="online").count()
        active_agents = await Agent.filter(is_active=True).count()

        stats.update(
            {
                "total_agents": total_agents,
                "online_agents": online_agents,
                "active_agents": active_agents,
            }
        )
    except Exception:
        # Return default values if database query fails
        # This is intentional - we want to return default stats on any error
        pass  # nosec B110

    return stats


@router.post("/", response_model=AgentResponse)
async def create_agent(
    agent_data: AgentCreate, user: User = Depends(current_active_user)
) -> AgentResponse:
    """Create a new agent."""
    service = AgentService()
    return await service.create_agent(agent_data)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID, user: User = Depends(current_active_user)
) -> AgentResponse:
    """Get agent by ID."""
    service = AgentService()
    agent = await service.get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/", response_model=List[AgentResponse])
async def get_agents(
    status: Optional[str] = None,
    agent_type: Optional[str] = None,
    user: User = Depends(current_active_user),
) -> List[AgentResponse]:
    """Get agents with optional filtering."""
    service = AgentService()

    if status:
        return await service.get_agents_by_status(status)
    elif agent_type:
        return await service.get_agents_by_type(agent_type)
    else:
        return await service.get_active_agents()


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    user: User = Depends(current_active_user),
) -> AgentResponse:
    """Update an agent."""
    service = AgentService()
    agent = await service.update_agent(agent_id, agent_data)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: UUID, user: User = Depends(current_active_user)
) -> dict:
    """Delete an agent."""
    service = AgentService()
    success = await service.delete_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent deleted successfully"}


@router.post("/{agent_id}/heartbeat")
async def update_heartbeat(
    agent_id: UUID,
    response_time_ms: Optional[int] = None,
    user: User = Depends(current_active_user),
) -> dict:
    """Update agent heartbeat."""
    service = AgentService()
    agent = await service.update_heartbeat(agent_id, response_time_ms)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Heartbeat updated successfully"}


@router.get("/{agent_id}/tasks", response_model=List[AgentTaskResponse])
async def get_agent_tasks(
    agent_id: UUID, user: User = Depends(current_active_user)
) -> List[AgentTaskResponse]:
    """Get all tasks for an agent."""
    service = AgentService()
    return await service.get_agent_tasks(agent_id)

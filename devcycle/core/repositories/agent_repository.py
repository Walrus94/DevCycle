"""
Agent repository for DevCycle.

This module provides data access operations for agent management,
including registration, health monitoring, and task tracking.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..agents.models import Agent, AgentStatus, AgentTask, AgentType
from .base import BaseRepository


class AgentRepository(BaseRepository[Agent]):
    """Repository for agent management operations."""

    def __init__(self, session: AsyncSession):
        """Initialize agent repository."""
        super().__init__(session, Agent)
        # Type assertion to help MyPy understand the model type
        self.model = Agent

    async def get_by_name(self, name: str) -> Optional[Agent]:
        """Get agent by name."""
        stmt = select(self.model).where(self.model.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def get_by_type(self, agent_type: AgentType) -> List[Agent]:
        """Get all agents of a specific type."""
        stmt = select(self.model).where(self.model.agent_type == agent_type.value)
        result = await self.session.execute(stmt)
        return result.scalars().all()  # type: ignore[no-any-return]

    async def get_active_agents(self) -> List[Agent]:
        """Get all active agents."""
        stmt = select(self.model).where(self.model.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalars().all()  # type: ignore[no-any-return]

    async def get_agents_by_status(self, status: AgentStatus) -> List[Agent]:
        """Get agents by status."""
        stmt = select(self.model).where(self.model.status == status.value)
        result = await self.session.execute(stmt)
        return result.scalars().all()  # type: ignore[no-any-return]

    async def get_agents_by_capability(self, capability: str) -> List[Agent]:
        """Get agents that have a specific capability."""
        stmt = select(self.model).where(self.model.capabilities.contains(capability))
        result = await self.session.execute(stmt)
        return result.scalars().all()  # type: ignore[no-any-return]

    async def get_online_agents(self) -> List[Agent]:
        """Get all online agents."""
        return await self.get_agents_by_status(AgentStatus.ONLINE)

    async def get_available_agents(self) -> List[Agent]:
        """Get agents that are available for new tasks."""
        stmt = select(self.model).where(
            and_(
                self.model.is_active.is_(True),
                self.model.status.in_(
                    [AgentStatus.ONLINE.value, AgentStatus.BUSY.value]
                ),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()  # type: ignore[no-any-return]

    async def update_agent_status(
        self, agent_id: UUID, status: AgentStatus
    ) -> Optional[Agent]:
        """Update agent status."""
        stmt = (
            update(self.model)
            .where(self.model.id == agent_id)
            .values(status=status.value, updated_at=datetime.now(timezone.utc))
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def update_agent_health(
        self,
        agent_id: UUID,
        status: AgentStatus,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Agent]:
        """Update agent health information."""
        # First get the current agent to access its current values
        current_agent = await self.get_by_id(agent_id)
        if not current_agent:
            return None

        update_data: Dict[str, Any] = {
            "status": status.value,
            "last_heartbeat": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_seen": datetime.now(timezone.utc),
        }

        if response_time_ms is not None:
            update_data["response_time_ms"] = response_time_ms

        if error_message:
            update_data["error_count"] = (current_agent.error_count or 0) + 1
            update_data["last_error"] = error_message
        else:
            update_data["uptime_seconds"] = (
                current_agent.uptime_seconds or 0
            ) + 60  # Approximate

        stmt = (
            update(self.model)
            .where(self.model.id == agent_id)
            .values(**update_data)
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def get_stale_agents(self, timeout_minutes: int = 5) -> List[Agent]:
        """Get agents that haven't sent a heartbeat in the specified timeout."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        stmt = select(self.model).where(
            and_(
                self.model.is_active.is_(True),
                self.model.last_heartbeat < cutoff_time,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()  # type: ignore[no-any-return]

    async def mark_agent_offline(self, agent_id: UUID) -> Optional[Agent]:
        """Mark agent as offline."""
        return await self.update_agent_status(agent_id, AgentStatus.OFFLINE)

    async def deactivate_agent(self, agent_id: UUID) -> Optional[Agent]:
        """Deactivate an agent."""
        stmt = (
            update(self.model)
            .where(self.model.id == agent_id)
            .values(
                is_active=False,
                status=AgentStatus.OFFLINE.value,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def activate_agent(self, agent_id: UUID) -> Optional[Agent]:
        """Activate an agent."""
        stmt = (
            update(self.model)
            .where(self.model.id == agent_id)
            .values(
                is_active=True,
                status=AgentStatus.OFFLINE.value,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def search_agents(
        self,
        query: str,
        agent_type: Optional[AgentType] = None,
        status: Optional[AgentStatus] = None,
        limit: Optional[int] = None,
    ) -> List[Agent]:
        """Search agents by query and filters."""
        stmt = select(self.model)

        # Add filters
        if agent_type:
            stmt = stmt.where(self.model.agent_type == agent_type.value)
        if status:
            stmt = stmt.where(self.model.status == status.value)
        if query:
            stmt = stmt.where(
                self.model.name.ilike(f"%{query}%")
                | self.model.description.ilike(f"%{query}%")
            )

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return result.scalars().all()  # type: ignore[no-any-return]

    async def get_agent_statistics(self) -> Dict[str, Any]:
        """Get agent statistics."""
        # Total agents
        total_stmt = select(self.model.id)
        total_result = await self.session.execute(total_stmt)
        total_agents = len(total_result.scalars().all())

        # Active agents
        active_stmt = select(self.model.id).where(self.model.is_active.is_(True))
        active_result = await self.session.execute(active_stmt)
        active_agents = len(active_result.scalars().all())

        # Online agents
        online_stmt = select(self.model.id).where(
            self.model.status == AgentStatus.ONLINE.value
        )
        online_result = await self.session.execute(online_stmt)
        online_agents = len(online_result.scalars().all())

        # Agents by type
        type_stmt = select(self.model.agent_type, self.model.id)
        type_result = await self.session.execute(type_stmt)
        agents_by_type = {}
        for agent_type, _ in type_result:
            if agent_type not in agents_by_type:
                agents_by_type[agent_type] = 0
            agents_by_type[agent_type] += 1

        return {
            "total_agents": total_agents,
            "active_agents": active_agents,
            "online_agents": online_agents,
            "agents_by_type": agents_by_type,
        }


class AgentTaskRepository(BaseRepository[AgentTask]):
    """Repository for agent task operations."""

    def __init__(self, session: AsyncSession):
        """Initialize agent task repository."""
        super().__init__(session, AgentTask)

    async def get_tasks_by_agent(self, agent_id: UUID) -> List[AgentTask]:
        """Get all tasks for a specific agent."""
        stmt = select(self.model).where(self.model.agent_id == agent_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()  # type: ignore[no-any-return]

    async def get_tasks_by_status(self, status: str) -> List[AgentTask]:
        """Get tasks by status."""
        stmt = select(self.model).where(self.model.status == status)
        result = await self.session.execute(stmt)
        return result.scalars().all()  # type: ignore[no-any-return]

    async def get_pending_tasks(self) -> List[AgentTask]:
        """Get all pending tasks."""
        return await self.get_tasks_by_status("pending")

    async def get_running_tasks(self) -> List[AgentTask]:
        """Get all running tasks."""
        return await self.get_tasks_by_status("running")

    async def get_completed_tasks(self) -> List[AgentTask]:
        """Get all completed tasks."""
        return await self.get_tasks_by_status("completed")

    async def get_failed_tasks(self) -> List[AgentTask]:
        """Get all failed tasks."""
        return await self.get_tasks_by_status("failed")

    async def update_task_status(
        self,
        task_id: UUID,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[AgentTask]:
        """Update task status and result."""
        update_data = {"status": status, "updated_at": datetime.now(timezone.utc)}

        if status == "running":
            update_data["started_at"] = datetime.now(timezone.utc)
        elif status in ["completed", "failed"]:
            update_data["completed_at"] = datetime.now(timezone.utc)

        if result is not None:
            update_data["result"] = json.dumps(result)
        if error is not None:
            update_data["error"] = error

        stmt = (
            update(self.model)
            .where(self.model.id == task_id)
            .values(**update_data)
            .returning(self.model)
        )
        db_result = await self.session.execute(stmt)
        await self.session.commit()
        return db_result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def get_agent_task_history(
        self, agent_id: UUID, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[AgentTask]:
        """Get task history for an agent."""
        stmt = (
            select(self.model)
            .where(self.model.agent_id == agent_id)
            .order_by(self.model.created_at.desc())
        )

        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return result.scalars().all()  # type: ignore[no-any-return]

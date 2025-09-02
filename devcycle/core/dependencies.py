"""
Dependency injection for DevCycle.

This module provides simplified dependency injection functions for FastAPI,
using direct instantiation instead of complex factory patterns.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .agents.lifecycle import AgentLifecycleService
from .auth.fastapi_users import current_active_user
from .auth.models import User
from .database.connection import get_async_session
from .messaging.middleware import MessageValidator
from .messaging.validation import MessageValidationConfig
from .repositories.agent_repository import AgentRepository, AgentTaskRepository
from .services.agent_availability_service import AgentAvailabilityService
from .services.agent_service import AgentService

# UserRepository removed - using FastAPI Users SQLAlchemyUserDatabase directly

# UserService removed - using FastAPI Users directly


# Repository Dependencies - Direct instantiation
# UserRepository removed - using FastAPI Users SQLAlchemyUserDatabase directly


async def get_agent_repository(
    session: AsyncSession = Depends(get_async_session),
) -> AgentRepository:
    """
    Get agent repository dependency.

    Args:
        session: Database session

    Returns:
        AgentRepository instance
    """
    return AgentRepository(session)


async def get_agent_task_repository(
    session: AsyncSession = Depends(get_async_session),
) -> AgentTaskRepository:
    """
    Get agent task repository dependency.

    Args:
        session: Database session

    Returns:
        AgentTaskRepository instance
    """
    return AgentTaskRepository(session)


# Service Dependencies - Direct instantiation with repository dependencies
# UserService removed - using FastAPI Users directly


async def get_lifecycle_service() -> AgentLifecycleService:
    """
    Get agent lifecycle service dependency.

    Returns:
        AgentLifecycleService instance
    """
    return AgentLifecycleService()


async def get_agent_service(
    agent_repository: AgentRepository = Depends(get_agent_repository),
    agent_task_repository: AgentTaskRepository = Depends(get_agent_task_repository),
    lifecycle_service: AgentLifecycleService = Depends(get_lifecycle_service),
) -> AgentService:
    """
    Get agent service dependency with lifecycle integration.

    Args:
        agent_repository: Agent repository instance
        agent_task_repository: Agent task repository instance
        lifecycle_service: Lifecycle service instance

    Returns:
        AgentService instance
    """
    service = AgentService(agent_repository, agent_task_repository, lifecycle_service)
    return service


async def get_current_user_id(user: User = Depends(current_active_user)) -> UUID:
    """
    Get current user ID from authenticated user.

    Args:
        user: Current authenticated user from FastAPI Users

    Returns:
        Current user ID

    Raises:
        HTTPException: If user is not authenticated
    """
    return user.id  # type: ignore[no-any-return]


async def get_current_user(user: User = Depends(current_active_user)) -> User:
    """
    Get current authenticated user.

    Args:
        user: Current authenticated user from FastAPI Users

    Returns:
        Current user instance
    """
    return user


async def require_superuser(user: User = Depends(current_active_user)) -> User:
    """
    Require current user to be a superuser.

    Args:
        user: Current authenticated user

    Returns:
        Current user if superuser

    Raises:
        HTTPException: If user is not a superuser
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required",
        )
    return user


# Authenticated user service removed - using FastAPI Users directly


async def get_message_validator() -> MessageValidator:
    """
    Get message validator dependency.

    Returns:
        MessageValidator instance
    """
    config = MessageValidationConfig()
    return MessageValidator(config)


async def get_agent_availability_service(
    agent_repository: AgentRepository = Depends(get_agent_repository),
) -> AgentAvailabilityService:
    """
    Get agent availability service dependency.

    Args:
        agent_repository: Agent repository instance

    Returns:
        AgentAvailabilityService instance
    """
    return AgentAvailabilityService(agent_repository)

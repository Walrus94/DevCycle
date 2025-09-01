"""
Dependency injection for DevCycle.

This module provides simplified dependency injection functions for FastAPI,
using direct instantiation instead of complex factory patterns.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .auth.fastapi_users import current_active_user
from .auth.models import User
from .database.connection import get_async_session
from .messaging.middleware import MessageValidator
from .messaging.validation import MessageValidationConfig
from .repositories.agent_repository import AgentRepository, AgentTaskRepository
from .repositories.user_repository import UserRepository
from .services.agent_availability_service import AgentAvailabilityService
from .services.agent_service import AgentService
from .services.user_service import UserService


# Repository Dependencies - Direct instantiation
async def get_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserRepository:
    """
    Get user repository dependency.

    Args:
        session: Database session

    Returns:
        UserRepository instance
    """
    return UserRepository(session)


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
async def get_user_service(
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserService:
    """
    Get user service dependency.

    Args:
        user_repository: User repository instance

    Returns:
        UserService instance
    """
    return UserService(user_repository)


async def get_agent_service(
    agent_repository: AgentRepository = Depends(get_agent_repository),
    agent_task_repository: AgentTaskRepository = Depends(get_agent_task_repository),
) -> AgentService:
    """
    Get agent service dependency.

    Args:
        agent_repository: Agent repository instance
        agent_task_repository: Agent task repository instance

    Returns:
        AgentService instance
    """
    return AgentService(agent_repository, agent_task_repository)


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


async def get_authenticated_user_service(
    user_service: UserService = Depends(get_user_service),
    user_id: UUID = Depends(get_current_user_id),
) -> UserService:
    """
    Get user service for authenticated user.

    Args:
        user_service: User service instance
        user_id: Current user ID

    Returns:
        UserService instance
    """
    return user_service


async def get_message_validator() -> MessageValidator:
    """
    Get message validator dependency.

    Returns:
        MessageValidator instance
    """
    config = MessageValidationConfig()
    return MessageValidator(config)


async def get_agent_availability_service() -> AgentAvailabilityService:
    """
    Get agent availability service dependency.

    Returns:
        AgentAvailabilityService instance
    """
    return AgentAvailabilityService()

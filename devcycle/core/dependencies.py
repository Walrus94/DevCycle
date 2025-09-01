"""
Dependency injection for DevCycle.

This module provides dependency injection functions for FastAPI,
including services, repositories, and other core components.
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
from .repositories.factory import get_repository_factory
from .repositories.user_repository import UserRepository
from .services.agent_availability_service import AgentAvailabilityService
from .services.agent_service import AgentService
from .services.factory import get_service_factory
from .services.user_service import UserService


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
    repository_factory = get_repository_factory(session)
    return repository_factory.get_user_repository()


async def get_user_service(
    session: AsyncSession = Depends(get_async_session),
) -> UserService:
    """
    Get user service dependency.

    Args:
        session: Database session

    Returns:
        UserService instance
    """
    repository_factory = get_repository_factory(session)
    service_factory = get_service_factory(repository_factory)
    return service_factory.get_user_service()


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
    repository_factory = get_repository_factory(session)
    return repository_factory.get_agent_repository()


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
    repository_factory = get_repository_factory(session)
    return repository_factory.get_agent_task_repository()


async def get_agent_service(
    session: AsyncSession = Depends(get_async_session),
) -> AgentService:
    """
    Get agent service dependency.

    Args:
        session: Database session

    Returns:
        AgentService instance
    """
    repository_factory = get_repository_factory(session)
    service_factory = get_service_factory(repository_factory)
    return service_factory.get_agent_service()


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

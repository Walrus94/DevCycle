"""
Dependency injection for DevCycle.

This module provides simplified dependency injection functions for FastAPI,
using direct instantiation instead of complex factory patterns.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status

from .agents.lifecycle import AgentLifecycleService
from .auth.tortoise_fastapi_users import current_active_user
from .auth.tortoise_models import User
from .messaging.middleware import MessageValidator
from .messaging.validation import MessageValidationConfig
from .services.agent_availability_service import AgentAvailabilityService
from .services.agent_service import AgentService

# UserRepository removed - using FastAPI Users TortoiseUserDatabase directly

# UserService removed - using FastAPI Users directly


# Service Dependencies - Direct instantiation
# Repository pattern removed - using direct Tortoise ORM operations


async def get_lifecycle_service() -> AgentLifecycleService:
    """
    Get agent lifecycle service dependency.

    Returns:
        AgentLifecycleService instance
    """
    return AgentLifecycleService()


async def get_agent_service() -> AgentService:
    """
    Get agent service dependency.

    Returns:
        AgentService instance
    """
    return AgentService()


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
    return user.id


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
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentAvailabilityService:
    """
    Get agent availability service dependency.

    Args:
        agent_service: Agent service instance

    Returns:
        AgentAvailabilityService instance
    """
    return AgentAvailabilityService(agent_service)

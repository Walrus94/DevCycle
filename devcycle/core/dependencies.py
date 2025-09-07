"""
Dependency injection for DevCycle.

This module provides simplified dependency injection functions for FastAPI,
using direct instantiation instead of complex factory patterns.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status

from .acp.config import ACPConfig
from .acp.events.redis_events import RedisACPEvents
from .acp.services.agent_registry import ACPAgentRegistry
from .acp.services.message_router import ACPMessageRouter
from .acp.services.workflow_engine import ACPWorkflowEngine

# from .agents.lifecycle import AgentLifecycleService  # Removed - using ACP instead
from .auth.tortoise_fastapi_users import current_active_user
from .auth.tortoise_models import User
from .cache import ACPCache, get_cache

# Legacy messaging and agent services removed - using ACP instead

# UserRepository removed - using FastAPI Users TortoiseUserDatabase directly

# UserService removed - using FastAPI Users directly


# Service Dependencies - Direct instantiation
# Repository pattern removed - using direct Tortoise ORM operations


# async def get_lifecycle_service() -> AgentLifecycleService:
#     """
#     Get agent lifecycle service dependency.
#
#     Returns:
#         AgentLifecycleService instance
#     """
#     return AgentLifecycleService()
#
# # Removed - using ACP instead


# Legacy agent service removed - using ACP instead


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


# Legacy message validator and agent availability service removed - using ACP instead


# ACP Dependencies
def get_acp_config() -> ACPConfig:
    """
    Get ACP configuration.

    Returns:
        ACPConfig instance
    """
    return ACPConfig()


def get_acp_cache() -> ACPCache:
    """
    Get ACP cache instance.

    Returns:
        ACPCache instance
    """
    redis_cache = get_cache(key_prefix="devcycle:cache:")
    return ACPCache(redis_cache)


def get_agent_registry() -> ACPAgentRegistry:
    """
    Get ACP agent registry.

    Returns:
        ACPAgentRegistry instance
    """
    config = get_acp_config()
    acp_cache = get_acp_cache()
    events = get_redis_events()
    return ACPAgentRegistry(config, acp_cache, events)


def get_message_router() -> ACPMessageRouter:
    """
    Get ACP message router.

    Returns:
        ACPMessageRouter instance
    """
    config = get_acp_config()
    agent_registry = get_agent_registry()
    return ACPMessageRouter(config, agent_registry)


def get_redis_events() -> RedisACPEvents:
    """
    Get Redis ACP events service.

    Returns:
        RedisACPEvents instance
    """
    redis_cache = get_cache(key_prefix="devcycle:cache:")
    return RedisACPEvents(redis_cache)


def get_workflow_engine() -> ACPWorkflowEngine:
    """
    Get ACP workflow engine.

    Returns:
        ACPWorkflowEngine instance
    """
    from .acp.config import ACPWorkflowConfig

    config = ACPConfig()
    workflow_config = ACPWorkflowConfig()
    agent_registry = get_agent_registry()
    message_router = get_message_router()
    acp_cache = get_acp_cache()
    events = get_redis_events()
    return ACPWorkflowEngine(
        config, workflow_config, agent_registry, message_router, acp_cache, events
    )

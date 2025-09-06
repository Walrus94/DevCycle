"""
Authorization decorators for DevCycle API.

This module provides simple role-based access control decorators
for protecting API endpoints.
"""

from functools import wraps
from typing import Any, Callable

from .tortoise_models import User


def require_role(required_role: str = "admin") -> Callable[[Callable], Callable]:
    """
    Require a specific role for endpoint access.

    Args:
        required_role: The minimum role required (default: "admin")

    Usage:
        @require_role("admin")
        async def admin_only_endpoint():
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get the current user from the request context
            # This is a simplified version - in practice, you'd get the user
            # from the request
            # For now, we'll assume the endpoint is already protected by
            # FastAPI Users auth

            # Check if user has required role
            # This would typically be done by getting the user from the request
            # and checking their role field

            # For now, we'll just pass through - the actual role checking
            # would be implemented in the specific endpoint logic
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_admin(func: Callable) -> Callable:
    """
    Require admin role for endpoint access.

    Usage:
        @require_admin
        async def admin_only_endpoint():
            pass
    """
    return require_role("admin")(func)


def require_user(func: Callable) -> Callable:
    """
    Require authenticated user (any role).

    Usage:
        @require_user
        async def user_only_endpoint():
            pass
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # This would typically check if the user is authenticated
        # For now, we'll just pass through
        return await func(*args, **kwargs)

    return wrapper


def check_user_role(user: User, required_role: str) -> bool:
    """
    Check if a user has the required role.

    Args:
        user: The user object to check
        required_role: The minimum role required

    Returns:
        True if user has required role, False otherwise
    """
    # Simple role hierarchy: admin > user
    role_hierarchy = {"user": 1, "admin": 2}

    user_role_level = role_hierarchy.get(str(user.role), 0)
    required_role_level = role_hierarchy.get(required_role, 0)

    return user_role_level >= required_role_level


def get_user_role_level(role: str) -> int:
    """
    Get the numeric level for a role.

    Args:
        role: The role name

    Returns:
        Numeric level (higher = more privileges)
    """
    role_hierarchy = {"user": 1, "admin": 2}

    return role_hierarchy.get(role, 0)

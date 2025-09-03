"""
FastAPI Users configuration using Tortoise ORM.

Native integration with Tortoise ORM.
"""

from typing import AsyncGenerator

from fastapi_users_tortoise import TortoiseUserDatabase

from .tortoise_models import User


async def get_user_db() -> AsyncGenerator[TortoiseUserDatabase, None]:
    """Get user database instance."""
    yield TortoiseUserDatabase(User)


# FastAPI Users setup
# Note: This is a simplified setup - full authentication will be added later
# For now, we'll create a placeholder current_active_user


async def current_active_user() -> User:
    """Return placeholder for current active user - to be implemented with full auth."""
    # This is a temporary implementation
    # In a real app, this would get the user from the JWT token
    raise NotImplementedError("Authentication not yet implemented")

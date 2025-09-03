"""
FastAPI Users configuration for DevCycle.

This module provides the complete FastAPI Users setup with Tortoise ORM integration.
"""

from typing import Any

from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_tortoise import TortoiseUserDatabase

from .tortoise_models import User

# JWT Configuration
SECRET = "your-secret-key-here"  # nosec B105 - This is a placeholder for development
LIFETIME_SECONDS = 3600  # 1 hour

# Create transport and strategy
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")
jwt_strategy: JWTStrategy = JWTStrategy(
    secret=SECRET, lifetime_seconds=LIFETIME_SECONDS
)

# Create authentication backend
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=lambda: jwt_strategy,
)


# Create user database adapter
async def get_user_db() -> Any:
    """Get user database instance."""
    yield TortoiseUserDatabase(User)


# Create FastAPI Users instance
fastapi_users = FastAPIUsers[User, int](get_user_db, [auth_backend])

# Create current user dependency
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)

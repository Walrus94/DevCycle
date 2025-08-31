"""
FastAPI Users configuration for DevCycle.

This module configures FastAPI Users for authentication,
providing JWT-based authentication with a clean, simple setup.
"""

import os
from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_async_session
from .models import User

# JWT Configuration
SECRET = os.getenv("SECRET", "dev-secret-key-change-in-production")
LIFETIME_SECONDS = int(os.getenv("JWT_LIFETIME_SECONDS", "3600"))


class UserManager(BaseUserManager[User, UUID]):
    """User manager for FastAPI Users."""

    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    def parse_id(self, value: str) -> UUID:
        """Parse user ID from string."""
        return UUID(value)

    async def on_after_register(
        self, user: User, request: Optional[Request] = None
    ) -> None:
        """Handle post-registration actions."""
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        """Handle post-forgot-password actions."""
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        """Handle post-request-verify actions."""
        print(f"Verification requested for user {user.id}. Verification token: {token}")


async def get_user_db(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    """Get user database."""
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    """Get user manager."""
    yield UserManager(user_db)


# Authentication backend
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

jwt_strategy: JWTStrategy = JWTStrategy(
    secret=SECRET, lifetime_seconds=LIFETIME_SECONDS
)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=lambda: jwt_strategy,
)

# FastAPI Users instance
fastapi_users = FastAPIUsers[User, UUID](
    get_user_manager,
    [auth_backend],
)

# Dependencies
current_active_user = fastapi_users.current_user(active=True)
current_active_superuser = fastapi_users.current_user(active=True, superuser=True)

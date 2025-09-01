"""
FastAPI Users configuration for DevCycle.

This module configures FastAPI Users for authentication,
providing JWT-based authentication with a clean, simple setup.
"""

from typing import Any, AsyncGenerator, Optional
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

from ..config import get_config
from ..database.connection import get_async_session
from ..logging import get_logger
from .models import User


class UserManager(BaseUserManager[User, UUID]):
    """User manager for FastAPI Users."""

    def __init__(self, user_db: Any) -> None:
        super().__init__(user_db)
        self.logger = get_logger(__name__)
        config = get_config()
        self.reset_password_token_secret = config.security.secret_key
        self.verification_token_secret = config.security.secret_key

    def parse_id(self, value: str) -> UUID:
        """Parse user ID from string."""
        return UUID(value)

    async def on_after_register(
        self, user: User, request: Optional[Request] = None
    ) -> None:
        """Handle post-registration actions."""
        self.logger.info(
            "User registered successfully",
            user_id=str(user.id),
            user_email=user.email,
            event_type="user_registration",
        )

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        """Handle post-forgot-password actions."""
        self.logger.info(
            "Password reset requested",
            user_id=str(user.id),
            user_email=user.email,
            event_type="password_reset_request",
        )

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        """Handle post-request-verify actions."""
        self.logger.info(
            "Email verification requested",
            user_id=str(user.id),
            user_email=user.email,
            event_type="email_verification_request",
        )


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


def get_jwt_strategy() -> JWTStrategy:
    """Get JWT strategy with current configuration."""
    config = get_config()
    return JWTStrategy(
        secret=config.security.secret_key,
        lifetime_seconds=config.security.jwt_lifetime_seconds,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# FastAPI Users instance
fastapi_users = FastAPIUsers[User, UUID](
    get_user_manager,
    [auth_backend],
)

# Dependencies
current_active_user = fastapi_users.current_user(active=True)
current_active_superuser = fastapi_users.current_user(active=True, superuser=True)

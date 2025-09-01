"""
Authentication endpoints for DevCycle API using FastAPI Users.

This module provides authentication endpoints that integrate with FastAPI Users
for secure, industry-standard user management and authentication, while also
leveraging our service layer for custom business logic.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_users import schemas
from pydantic import BaseModel, ConfigDict, Field

from ...core.auth.fastapi_users import auth_backend, current_active_user, fastapi_users
from ...core.auth.models import User
from ...core.logging import get_logger

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = get_logger("api.auth.endpoints")


class UserInfo(BaseModel):
    """User information model."""

    id: UUID = Field(..., description="User identifier")
    email: str = Field(..., description="User email")
    is_active: bool = Field(..., description="Whether user is active")
    is_verified: bool = Field(..., description="Whether email is verified")
    is_superuser: bool = Field(..., description="Whether user is superuser")
    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")
    role: str = Field(..., description="User role (user/admin)")

    model_config = ConfigDict(from_attributes=True)


# User creation and update models are now handled by FastAPI Users schemas


class UserProfileUpdate(schemas.BaseUserUpdate):
    """User profile update model for FastAPI Users."""

    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")
    role: Optional[str] = Field(None, description="User role (user/admin)")

    model_config = ConfigDict(from_attributes=True)


# User list model is now handled by FastAPI Users built-in functionality


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    user: User = Depends(current_active_user),
) -> UserInfo:
    """
    Get current user information.

    Args:
        user: Current authenticated user

    Returns:
        UserInfo with current user details
    """
    return UserInfo(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
    )


# Registration is now handled by FastAPI Users built-in router
# See app.py for the included registration router


# User listing is now handled by FastAPI Users built-in router
# See app.py for the included users router


# User activation/deactivation is now handled by FastAPI Users built-in router
# See app.py for the included users router


# User deactivation is now handled by FastAPI Users built-in router


# User email verification is now handled by FastAPI Users built-in router


# User promotion to superuser is now handled by FastAPI Users built-in router


# Include FastAPI Users authentication routes for compatibility
# These provide: /auth/jwt/login, /auth/jwt/logout, etc.
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
)

# Include FastAPI Users user management routes for compatibility
# These provide: /auth/users/me, /auth/users/{id}, etc.
router.include_router(
    fastapi_users.get_users_router(UserInfo, UserProfileUpdate),
    prefix="/users",
)

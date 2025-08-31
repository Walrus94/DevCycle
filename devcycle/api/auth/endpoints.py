"""
Authentication endpoints for DevCycle API using FastAPI Users.

This module provides authentication endpoints that integrate with FastAPI Users
for secure, industry-standard user management and authentication, while also
leveraging our service layer for custom business logic.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users import schemas
from pydantic import BaseModel, Field

from ...core.auth.fastapi_users import auth_backend, current_active_user, fastapi_users
from ...core.auth.models import User
from ...core.dependencies import get_user_service, require_superuser
from ...core.logging import get_logger
from ...core.services.user_service import UserService

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

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """User creation model with business logic validation."""

    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update model."""

    email: Optional[str] = Field(None, description="User email address")
    is_active: Optional[bool] = Field(None, description="Whether user is active")
    is_verified: Optional[bool] = Field(None, description="Whether email is verified")
    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")

    class Config:
        from_attributes = True


class UserProfileUpdate(schemas.BaseUserUpdate):
    """User profile update model for FastAPI Users."""

    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")
    role: Optional[str] = Field(None, description="User role (user/admin)")

    class Config:
        from_attributes = True


class UserList(BaseModel):
    """User list response model."""

    users: List[UserInfo] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of users per page")


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


@router.post(
    "/users/register",
    response_model=UserInfo,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service),
) -> UserInfo:
    """
    Register a new user with business logic validation.

    Args:
        user_data: User registration data
        user_service: User service instance

    Returns:
        Created user information

    Raises:
        HTTPException: If validation fails or user already exists
    """
    try:
        user = await user_service.create_user(
            email=user_data.email, password=user_data.password
        )

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
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/users/active", response_model=UserList)
async def get_active_users(
    page: int = 1,
    page_size: int = 20,
    user_service: UserService = Depends(get_user_service),
    # Require superuser to view all users
    _: User = Depends(require_superuser),
) -> UserList:
    """
    Get active users with pagination.

    Args:
        page: Page number (1-based)
        page_size: Number of users per page
        user_service: User service instance
        _: Current authenticated superuser (required)

    Returns:
        Paginated list of active users
    """
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    offset = (page - 1) * page_size
    users = await user_service.get_active_users(limit=page_size, offset=offset)

    # Convert to UserInfo models
    user_infos = [
        UserInfo(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
        )
        for user in users
    ]

    return UserList(
        users=user_infos,
        total=len(user_infos),  # Note: This should ideally get total count from service
        page=page,
        page_size=page_size,
    )


@router.put("/users/{user_id}/activate", response_model=UserInfo)
async def activate_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(require_superuser),  # Require superuser to activate users
) -> UserInfo:
    """
    Activate a user account.

    Args:
        user_id: ID of user to activate
        user_service: User service instance
        _: Current authenticated superuser (required)

    Returns:
        Activated user information

    Raises:
        HTTPException: If user not found or activation fails
    """
    user = await user_service.activate_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

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


@router.put("/users/{user_id}/deactivate", response_model=UserInfo)
async def deactivate_user(
    user_id: UUID,
    reason: Optional[str] = None,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(require_superuser),  # Require superuser to deactivate users
) -> UserInfo:
    """
    Deactivate a user account.

    Args:
        user_id: ID of user to deactivate
        reason: Optional reason for deactivation
        user_service: User service instance
        _: Current authenticated superuser (required)

    Returns:
        Deactivated user information

    Raises:
        HTTPException: If user not found, deactivation fails, or user is superuser
    """
    try:
        user = await user_service.deactivate_user(user_id, reason=reason)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

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
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/users/{user_id}/verify", response_model=UserInfo)
async def verify_user_email(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(require_superuser),  # Require superuser to verify users
) -> UserInfo:
    """
    Verify a user's email address.

    Args:
        user_id: ID of user to verify
        user_service: User service instance
        _: Current authenticated superuser (required)

    Returns:
        Verified user information

    Raises:
        HTTPException: If user not found or verification fails
    """
    user = await user_service.verify_user_email(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

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


@router.put("/users/{user_id}/promote", response_model=UserInfo)
async def promote_to_superuser(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(require_superuser),  # Require superuser to promote users
) -> UserInfo:
    """
    Promote a user to superuser status.

    Args:
        user_id: ID of user to promote
        user_service: User service instance
        _: Current authenticated superuser (required)

    Returns:
        Promoted user information

    Raises:
                HTTPException: If user not found, promotion fails, or current user
            is not superuser
    """
    try:
        user = await user_service.promote_to_superuser(user_id, _.id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

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
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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

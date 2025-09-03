"""
Authentication endpoints for DevCycle API using FastAPI Users.

This module provides authentication endpoints that integrate with FastAPI Users
for secure, industry-standard user management and authentication, while also
leveraging our service layer for custom business logic.
"""

import uuid
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi_users import schemas
from pydantic import BaseModel, ConfigDict, Field

from ...core.auth.fastapi_users import auth_backend, current_active_user, fastapi_users
from ...core.auth.session_monitor import SessionMonitor
from ...core.auth.token_blacklist import TokenBlacklist
from ...core.auth.tortoise_models import User
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


class LogoutResponse(BaseModel):
    """Logout response model."""

    message: str = Field(..., description="Logout message")
    success: bool = Field(..., description="Whether logout was successful")


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    current_user: User = Depends(current_active_user),
    request: Request = None,
) -> LogoutResponse:
    """
    Logout user and invalidate current session.

    Args:
        current_user: Current authenticated user
        request: FastAPI request object

    Returns:
        LogoutResponse with success status

    Raises:
        HTTPException: If logout fails
    """
    try:
        # Get token from request
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix

            # Add token to blacklist
            blacklist = TokenBlacklist()

            # Calculate expiration from JWT payload
            import jwt

            from ...core.config import get_config

            config = get_config()
            payload = jwt.decode(
                token,
                config.security.secret_key,
                algorithms=["HS256"],
                options={
                    "verify_exp": False
                },  # Don't verify expiration for blacklisting
            )
            from datetime import datetime

            expires_at = datetime.fromtimestamp(payload["exp"])

            if blacklist.blacklist_token(token, expires_at):
                # Also remove from session tracking
                session_monitor = SessionMonitor()
                session_id = payload.get(
                    "jti", str(uuid.uuid4())
                )  # Use JTI or generate one
                session_monitor.remove_session(str(current_user.id), session_id)

                logger.info(
                    "User logged out successfully",
                    user_id=str(current_user.id),
                    user_email=current_user.email,
                    event_type="user_logout",
                )

                return LogoutResponse(
                    message="Successfully logged out",
                    success=True,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to logout - token could not be blacklisted",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid token provided",
            )
    except jwt.InvalidTokenError as e:
        logger.warning(
            "Invalid token during logout",
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token provided",
        )
    except Exception as e:
        logger.error(
            "Logout failed",
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}",
        )


@router.post("/logout-all", response_model=LogoutResponse)
async def logout_all_sessions(
    current_user: User = Depends(current_active_user),
) -> LogoutResponse:
    """
    Logout user from all active sessions.

    Args:
        current_user: Current authenticated user

    Returns:
        LogoutResponse with success status

    Raises:
        HTTPException: If logout all fails
    """
    try:
        session_monitor = SessionMonitor()
        removed_count = session_monitor.remove_all_sessions(str(current_user.id))

        logger.info(
            "User logged out from all sessions",
            user_id=str(current_user.id),
            user_email=current_user.email,
            removed_sessions=removed_count,
            event_type="user_logout_all",
        )

        return LogoutResponse(
            message=f"Logged out from all sessions ({removed_count} sessions removed)",
            success=True,
        )
    except Exception as e:
        logger.error(
            "Logout all sessions failed",
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout all failed: {str(e)}",
        )


@router.get("/sessions", response_model=dict)
async def get_user_sessions(
    current_user: User = Depends(current_active_user),
) -> dict:
    """
    Get current user's active sessions.

    Args:
        current_user: Current authenticated user

    Returns:
        Dictionary with active sessions information
    """
    try:
        session_monitor = SessionMonitor()
        sessions = session_monitor.get_active_sessions(str(current_user.id))

        # Clean up sensitive information
        for session in sessions:
            if "session_id" in session:
                session["session_id"] = session["session_id"][:8] + "..."

        logger.debug(
            "Retrieved user sessions",
            user_id=str(current_user.id),
            session_count=len(sessions),
        )

        return {
            "sessions": sessions,
            "total_sessions": len(sessions),
        }
    except Exception as e:
        logger.error(
            "Failed to get user sessions",
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sessions: {str(e)}",
        )

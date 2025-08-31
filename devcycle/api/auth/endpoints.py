"""
Authentication endpoints for DevCycle API.

This module provides login, logout, and session validation endpoints
that integrate with the Redis-based session management system.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from ...core.config import get_config
from ...core.logging import get_logger
from .sessions import SessionManager, get_session_manager

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = get_logger("api.auth.endpoints")


class LoginRequest(BaseModel):
    """Login request model."""

    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(default=False, description="Keep session active longer")


class LoginResponse(BaseModel):
    """Login response model."""

    success: bool = Field(..., description="Whether login was successful")
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email")
    roles: list[str] = Field(..., description="User roles")
    permissions: list[str] = Field(..., description="User permissions")
    expires_at: datetime = Field(..., description="Session expiration time")
    message: str = Field(..., description="Response message")


class LogoutResponse(BaseModel):
    """Logout response model."""

    success: bool = Field(..., description="Whether logout was successful")
    message: str = Field(..., description="Response message")


class SessionInfo(BaseModel):
    """Session information model."""

    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email")
    roles: list[str] = Field(..., description="User roles")
    permissions: list[str] = Field(..., description="User permissions")
    created_at: datetime = Field(..., description="Session creation time")
    expires_at: datetime = Field(..., description="Session expiration time")
    last_activity: datetime = Field(..., description="Last activity time")
    ip_address: Optional[str] = Field(None, description="IP address of session")
    user_agent: Optional[str] = Field(None, description="User agent string")


async def get_current_session(
    request: Request,
    session_manager: SessionManager = Depends(get_session_manager),
) -> SessionInfo:
    """
    Get current session from request.

    This dependency extracts the session ID from cookies or headers
    and validates the session.

    Args:
        request: FastAPI request object
        session_manager: Session manager instance

    Returns:
        SessionInfo object if session is valid

    Raises:
        HTTPException: If session is invalid or expired
    """
    # Get session ID from cookie or Authorization header
    session_id = _extract_session_id(request)

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session ID not provided"
        )

    # Validate session
    session_data = await session_manager.get_session(session_id)

    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    # Convert to SessionInfo model
    return SessionInfo(
        session_id=session_data.session_id,
        user_id=session_data.user_id,
        username=session_data.username,
        email=session_data.email,
        roles=session_data.roles,
        permissions=session_data.permissions,
        created_at=session_data.created_at,
        expires_at=session_data.expires_at,
        last_activity=session_data.last_activity,
        ip_address=session_data.ip_address,
        user_agent=session_data.user_agent,
    )


def _extract_session_id(request: Request) -> Optional[str]:
    """
    Extract session ID from request.

    Args:
        request: FastAPI request object

    Returns:
        Session ID if found, None otherwise
    """
    config = get_config().auth

    # Try to get from cookie first
    session_cookie = request.cookies.get(config.session_cookie_name)
    if session_cookie:
        return str(session_cookie)

    # Try to get from Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return str(auth_header[7:])  # Remove "Bearer " prefix

    return None


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    session_manager: SessionManager = Depends(get_session_manager),
) -> LoginResponse:
    """
    Authenticate user and create session.

    Args:
        login_data: Login credentials
        request: FastAPI request object
        response: FastAPI response object
        session_manager: Session manager instance

    Returns:
        LoginResponse with session information
    """
    try:
        # TODO: Implement actual user authentication
        # For now, use mock authentication
        user_data = await _authenticate_user(login_data.username, login_data.password)

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        # Create session
        session_data = await session_manager.create_session(
            user_data=user_data,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            metadata={
                "login_method": "password",
                "remember_me": login_data.remember_me,
            },
        )

        # Set session cookie
        config = get_config().auth
        response.set_cookie(
            key=config.session_cookie_name,
            value=session_data.session_id,
            max_age=session_data.expires_at.timestamp()
            - datetime.now(timezone.utc).timestamp(),
            secure=config.session_secure,
            httponly=config.session_httponly,
            samesite=config.session_samesite,
            path="/",
        )

        logger.info(f"User {user_data['username']} logged in successfully")

        return LoginResponse(
            success=True,
            session_id=session_data.session_id,
            user_id=session_data.user_id,
            username=session_data.username,
            email=session_data.email,
            roles=session_data.roles,
            permissions=session_data.permissions,
            expires_at=session_data.expires_at,
            message="Login successful",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed"
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    session_manager: SessionManager = Depends(get_session_manager),
) -> LogoutResponse:
    """
    Logout user and invalidate session.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        session_manager: Session manager instance

    Returns:
        LogoutResponse with status
    """
    try:
        # Get session ID
        session_id = _extract_session_id(request)

        if session_id:
            # Delete session
            await session_manager.delete_session(session_id)
            logger.info(f"Session {session_id} deleted during logout")

        # Clear session cookie
        config = get_config().auth
        response.delete_cookie(key=config.session_cookie_name, path="/")

        return LogoutResponse(success=True, message="Logout successful")

    except Exception as e:
        logger.error(f"Logout failed: {e}")
        # Even if logout fails, clear the cookie
        config = get_config().auth
        response.delete_cookie(key=config.session_cookie_name, path="/")

        return LogoutResponse(
            success=True, message="Logout completed (session cleanup may have failed)"
        )


@router.get("/session", response_model=SessionInfo)
async def get_session_info(
    session_info: SessionInfo = Depends(get_current_session),
) -> SessionInfo:
    """
    Get current session information.

    Args:
        session_info: Current session (from dependency)

    Returns:
        SessionInfo with current session details
    """
    return session_info


@router.post("/refresh")
async def refresh_session(
    session_info: SessionInfo = Depends(get_current_session),
    session_manager: SessionManager = Depends(get_session_manager),
) -> Dict[str, Any]:
    """
    Refresh session to extend expiration time.

    Args:
        session_info: Current session (from dependency)
        session_manager: Session manager instance

    Returns:
        Response with refresh status
    """
    try:
        # Update last activity (this extends the session)
        await session_manager._update_last_activity(session_info.session_id)

        logger.info(f"Session {session_info.session_id} refreshed")

        return {
            "success": True,
            "message": "Session refreshed successfully",
            "expires_at": session_info.expires_at,
        }

    except Exception as e:
        logger.error(f"Session refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh session",
        )


async def _authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate user credentials.

    TODO: Implement actual user authentication with database lookup
    and password hashing.

    Args:
        username: Username or email
        password: User password

    Returns:
        User data if authentication successful, None otherwise
    """
    # Mock authentication for development
    # In production, this would:
    # 1. Look up user in database
    # 2. Verify password hash
    # 3. Check if user is active
    # 4. Return user data with roles/permissions

    if username == "admin" and password == "admin123":
        return {
            "user_id": "admin_001",
            "username": "admin",
            "email": "admin@devcycle.dev",
            "roles": ["admin", "user"],
            "permissions": ["read", "write", "admin"],
        }
    elif username == "user" and password == "user123":
        return {
            "user_id": "user_001",
            "username": "user",
            "email": "user@devcycle.dev",
            "roles": ["user"],
            "permissions": ["read", "write"],
        }

    return None

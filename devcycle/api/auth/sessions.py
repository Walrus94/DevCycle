"""
Session management system for DevCycle API.

This module provides session-based authentication using Redis for storage,
with features like session creation, validation, rate limiting, and management.
"""

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from ...core.config import get_config
from ...core.logging import get_logger
from ...core.redis import get_redis


class SessionData(BaseModel):
    """Session data model."""

    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email")
    roles: list[str] = Field(default_factory=list, description="User roles")
    permissions: list[str] = Field(default_factory=list, description="User permissions")
    created_at: datetime = Field(..., description="Session creation time")
    expires_at: datetime = Field(..., description="Session expiration time")
    last_activity: datetime = Field(..., description="Last activity time")
    ip_address: Optional[str] = Field(None, description="IP address of session")
    user_agent: Optional[str] = Field(None, description="User agent string")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class SessionManager:
    """Session manager for Redis-based session storage."""

    def __init__(self) -> None:
        """Initialize session manager."""
        self.config = get_config().auth
        self.logger = get_logger("api.auth.sessions")

        # Session settings
        self.cookie_name = self.config.session_cookie_name
        self.max_age = self.config.session_max_age
        self.secure = self.config.session_secure
        self.httponly = self.config.session_httponly
        self.samesite = self.config.session_samesite

        # Rate limiting
        self.rate_limit_enabled = self.config.rate_limit_enabled
        self.rate_limit_requests = self.config.rate_limit_requests
        self.rate_limit_window = self.config.rate_limit_window

    async def create_session(
        self,
        user_data: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionData:
        """
        Create a new session for a user.

        Args:
            user_data: User information
            ip_address: IP address of the session
            user_agent: User agent string
            metadata: Additional session metadata

        Returns:
            SessionData object with session information
        """
        try:
            # Generate unique session ID
            session_id = self._generate_session_id()

            # Calculate timestamps
            now = datetime.now(timezone.utc)
            expires_at = now.replace(tzinfo=timezone.utc) + timedelta(
                seconds=self.max_age
            )

            # Create session data
            session_data = SessionData(
                session_id=session_id,
                user_id=user_data["user_id"],
                username=user_data["username"],
                email=user_data["email"],
                roles=user_data.get("roles", []),
                permissions=user_data.get("permissions", []),
                created_at=now,
                expires_at=expires_at,
                last_activity=now,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata or {},
            )

            # Store session in Redis
            await self._store_session(session_data)

            # Track user sessions
            await self._track_user_session(user_data["user_id"], session_id)

            self.logger.info(
                f"Created session {session_id} for user {user_data['username']}"
            )
            return session_data

        except Exception as e:
            self.logger.error(f"Failed to create session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session",
            )

    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Retrieve session data by session ID.

        Args:
            session_id: Session identifier

        Returns:
            SessionData object if valid, None otherwise
        """
        try:
            redis_client = await get_redis()

            # Get session data from Redis
            session_key = f"session:{session_id}"
            session_json = await redis_client.get(session_key)

            if not session_json:
                return None

            # Parse session data
            session_dict = json.loads(session_json)
            session_data = SessionData(**session_dict)

            # Check if session is expired
            if session_data.expires_at < datetime.now(timezone.utc):
                # Don't call delete_session here to avoid infinite loops
                # Just return None - expired sessions will be cleaned up separately
                return None

            # Update last activity
            await self._update_last_activity(session_id)

            return session_data

        except Exception as e:
            self.logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def validate_session(self, session_id: str) -> bool:
        """
        Validate if a session exists and is valid.

        Args:
            session_id: Session identifier

        Returns:
            True if session is valid, False otherwise
        """
        try:
            session_data = await self.get_session(session_id)
            return session_data is not None
        except Exception:
            return False

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False otherwise
        """
        try:
            redis_client = await get_redis()

            # Get session data to find user ID
            session_data = await self.get_session(session_id)
            if session_data:
                # Remove from user sessions tracking
                await self._untrack_user_session(session_data.user_id, session_id)

            # Delete session from Redis
            session_key = f"session:{session_id}"
            deleted = await redis_client.delete(session_key)

            # Delete rate limiting data
            rate_limit_key = f"rate_limit:session:{session_id}"
            await redis_client.delete(rate_limit_key)

            self.logger.info(f"Deleted session {session_id}")
            return deleted > 0

        except Exception as e:
            self.logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    async def delete_user_sessions(
        self, user_id: str, exclude_session_id: Optional[str] = None
    ) -> int:
        """
        Delete all sessions for a user (logout all devices).

        Args:
            user_id: User identifier
            exclude_session_id: Session ID to exclude from deletion

        Returns:
            Number of sessions deleted
        """
        try:
            redis_client = await get_redis()

            # Get all user sessions
            user_sessions_key = f"user:{user_id}:sessions"
            session_ids = await redis_client.smembers(user_sessions_key)

            deleted_count = 0
            for session_id in session_ids:
                if session_id != exclude_session_id:
                    if await self.delete_session(session_id):
                        deleted_count += 1

            self.logger.info(f"Deleted {deleted_count} sessions for user {user_id}")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to delete user sessions for {user_id}: {e}")
            return 0

    async def refresh_session(
        self, session_id: str, extend_by: Optional[int] = None
    ) -> bool:
        """
        Refresh a session by extending its expiration time.

        Args:
            session_id: Session identifier
            extend_by: Seconds to extend by (uses default if None)

        Returns:
            True if session was refreshed, False otherwise
        """
        try:
            session_data = await self.get_session(session_id)
            if not session_data:
                return False

            # Calculate new expiration
            extend_seconds = extend_by or self.max_age
            new_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=extend_seconds
            )

            # Update session data
            session_data.expires_at = new_expires_at
            session_data.last_activity = datetime.now(timezone.utc)

            # Store updated session
            await self._store_session(session_data)

            self.logger.info(f"Refreshed session {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to refresh session {session_id}: {e}")
            return False

    async def check_rate_limit(self, session_id: str) -> bool:
        """
        Check if session is within rate limits.

        Args:
            session_id: Session identifier

        Returns:
            True if within limits, False if rate limited
        """
        if not self.rate_limit_enabled:
            return True

        try:
            redis_client = await get_redis()
            rate_limit_key = f"rate_limit:session:{session_id}"

            # Increment request count
            current_count = await redis_client.incr(rate_limit_key)

            # Set expiration if this is the first request
            if current_count == 1:
                await redis_client.expire(rate_limit_key, self.rate_limit_window)

            # Check if within limits
            if current_count > self.rate_limit_requests:
                self.logger.warning(f"Rate limit exceeded for session {session_id}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Rate limit check failed for session {session_id}: {e}")
            # Allow request if rate limiting fails
            return True

    async def get_user_sessions(self, user_id: str) -> list[SessionData]:
        """
        Get all active sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            List of active sessions
        """
        try:
            redis_client = await get_redis()

            # Get all user session IDs
            user_sessions_key = f"user:{user_id}:sessions"
            session_ids = await redis_client.smembers(user_sessions_key)

            # Get session data for each ID
            sessions = []
            for session_id in session_ids:
                session_data = await self.get_session(session_id)
                if session_data:
                    sessions.append(session_data)

            return sessions

        except Exception as e:
            self.logger.error(f"Failed to get user sessions for {user_id}: {e}")
            return []

    def _generate_session_id(self) -> str:
        """Generate a cryptographically secure session ID."""
        return secrets.token_urlsafe(32)

    async def _store_session(self, session_data: SessionData) -> None:
        """Store session data in Redis."""
        redis_client = await get_redis()

        # Convert to JSON
        session_json = json.dumps(session_data.model_dump(), default=str)

        # Store with expiration
        session_key = f"session:{session_data.session_id}"
        await redis_client.setex(session_key, self.max_age, session_json)

    async def _track_user_session(self, user_id: str, session_id: str) -> None:
        """Track session ID in user's session set."""
        redis_client = await get_redis()

        user_sessions_key = f"user:{user_id}:sessions"
        await redis_client.sadd(user_sessions_key, session_id)
        await redis_client.expire(
            user_sessions_key, self.max_age * 2
        )  # Keep tracking longer

    async def _untrack_user_session(self, user_id: str, session_id: str) -> None:
        """Remove session ID from user's session set."""
        try:
            redis_client = await get_redis()

            user_sessions_key = f"user:{user_id}:sessions"
            await redis_client.srem(user_sessions_key, session_id)
        except Exception as e:
            self.logger.warning(f"Failed to untrack session {session_id}: {e}")

    async def _update_last_activity(self, session_id: str) -> None:
        """Update last activity timestamp for session."""
        try:
            session_data = await self.get_session(session_id)
            if session_data:
                session_data.last_activity = datetime.now(timezone.utc)
                await self._store_session(session_data)
        except Exception as e:
            self.logger.warning(
                f"Failed to update last activity for session {session_id}: {e}"
            )


# Global session manager instance
session_manager = SessionManager()


async def get_session_manager() -> SessionManager:
    """Get session manager instance."""
    return session_manager

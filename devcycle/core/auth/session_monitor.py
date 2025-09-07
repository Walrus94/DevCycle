"""
Session monitoring and management system.

This module provides functionality to track and manage user sessions,
enabling features like logout from all sessions and session monitoring.
"""

from datetime import datetime, timezone
from typing import List, Optional

import redis

from ..config import get_config
from ..logging import get_logger

logger = get_logger(__name__)


class SessionMonitor:
    """Monitor and manage user sessions using Redis."""

    def __init__(self) -> None:
        """Initialize session monitor with Redis connection."""
        config = get_config()
        self.redis_client = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            password=config.redis.password,
            db=config.redis.db,
            decode_responses=True,
            socket_timeout=config.redis.socket_timeout,
            socket_connect_timeout=config.redis.socket_connect_timeout,
            retry_on_timeout=config.redis.retry_on_timeout,
            max_connections=config.redis.max_connections,
        )
        self.session_prefix = "user_sessions:"
        self.session_info_prefix = "session_info:"
        logger.info("Session monitor initialized with Redis connection")

    def track_session(
        self,
        user_id: str,
        session_id: str,
        expires_at: datetime,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """
        Track active user session.

        Args:
            user_id: User identifier
            session_id: Unique session identifier
            expires_at: Session expiration datetime
            user_agent: User agent string (optional)
            ip_address: IP address (optional)

        Returns:
            True if session was tracked successfully, False otherwise
        """
        try:
            user_key = f"{self.session_prefix}{user_id}"
            session_info_key = f"{self.session_info_prefix}{session_id}"

            ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())

            if ttl > 0:
                # Add session to user's session set
                self.redis_client.sadd(user_key, session_id)
                self.redis_client.expire(user_key, ttl)

                # Store session metadata
                session_info = {
                    "user_id": user_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "user_agent": user_agent or "unknown",
                    "ip_address": ip_address or "unknown",
                }

                # Store session info with TTL
                for key, value in session_info.items():
                    self.redis_client.hset(session_info_key, key, value)
                self.redis_client.expire(session_info_key, ttl)

                logger.info(
                    "Session tracked successfully",
                    user_id=user_id,
                    session_id=session_id[:8] + "...",
                    expires_at=expires_at.isoformat(),
                    ttl=ttl,
                )
                return True
            else:
                logger.warning(
                    "Session already expired, not tracking",
                    user_id=user_id,
                    session_id=session_id[:8] + "...",
                    expires_at=expires_at.isoformat(),
                )
                return False
        except Exception as e:
            logger.error(
                "Failed to track session",
                error=str(e),
                user_id=user_id,
                session_id=session_id[:8] + "...",
            )
            return False

    def get_active_sessions(self, user_id: str) -> List[dict]:
        """
        Get list of active session information for user.

        Args:
            user_id: User identifier

        Returns:
            List of session information dictionaries
        """
        try:
            user_key = f"{self.session_prefix}{user_id}"
            session_ids = list(self.redis_client.smembers(user_key))

            sessions = []
            for session_id in session_ids:
                session_info_key = f"{self.session_info_prefix}{session_id}"
                session_info = self.redis_client.hgetall(session_info_key)

                if session_info:
                    # Add session_id to the info
                    session_info["session_id"] = session_id
                    sessions.append(session_info)
                else:
                    # Clean up orphaned session reference
                    self.redis_client.srem(user_key, session_id)

            logger.debug(
                "Retrieved active sessions",
                user_id=user_id,
                session_count=len(sessions),
            )

            return sessions
        except Exception as e:
            logger.error(
                "Failed to get active sessions",
                error=str(e),
                user_id=user_id,
            )
            return []

    def remove_session(self, user_id: str, session_id: str) -> bool:
        """
        Remove specific session for user.

        Args:
            user_id: User identifier
            session_id: Session identifier to remove

        Returns:
            True if session was removed successfully, False otherwise
        """
        try:
            user_key = f"{self.session_prefix}{user_id}"
            session_info_key = f"{self.session_info_prefix}{session_id}"

            # Remove from user's session set
            removed_from_set = self.redis_client.srem(user_key, session_id)

            # Remove session info
            removed_info = self.redis_client.delete(session_info_key)

            success = bool(removed_from_set or removed_info)

            if success:
                logger.info(
                    "Session removed successfully",
                    user_id=user_id,
                    session_id=session_id[:8] + "...",
                )
            else:
                logger.warning(
                    "Session not found for removal",
                    user_id=user_id,
                    session_id=session_id[:8] + "...",
                )

            return success
        except Exception as e:
            logger.error(
                "Failed to remove session",
                error=str(e),
                user_id=user_id,
                session_id=session_id[:8] + "...",
            )
            return False

    def remove_all_sessions(self, user_id: str) -> int:
        """
        Remove all sessions for user.

        Args:
            user_id: User identifier

        Returns:
            Number of sessions removed
        """
        try:
            user_key = f"{self.session_prefix}{user_id}"
            session_ids = list(self.redis_client.smembers(user_key))

            removed_count = 0
            for session_id in session_ids:
                session_info_key = f"{self.session_info_prefix}{session_id}"

                # Remove session info
                if self.redis_client.delete(session_info_key):
                    removed_count += 1

            # Remove user's session set
            self.redis_client.delete(user_key)

            logger.info(
                "All sessions removed for user",
                user_id=user_id,
                removed_count=removed_count,
            )

            return removed_count
        except Exception as e:
            logger.error(
                "Failed to remove all sessions",
                error=str(e),
                user_id=user_id,
            )
            return 0

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of expired sessions cleaned up
        """
        try:
            # Get all session info keys
            pattern = f"{self.session_info_prefix}*"
            session_info_keys = self.redis_client.keys(pattern)

            expired_count = 0
            current_time = datetime.now(timezone.utc)

            for session_info_key in session_info_keys:
                session_info = self.redis_client.hgetall(session_info_key)

                if session_info and "expires_at" in session_info:
                    try:
                        expires_at = datetime.fromisoformat(session_info["expires_at"])
                        if current_time > expires_at:
                            # Session expired, clean it up
                            session_id = session_info_key.replace(
                                self.session_info_prefix, ""
                            )
                            user_id = session_info.get("user_id")

                            if user_id:
                                user_key = f"{self.session_prefix}{user_id}"
                                self.redis_client.srem(user_key, session_id)

                            self.redis_client.delete(session_info_key)
                            expired_count += 1
                    except (ValueError, TypeError):
                        # Invalid date format, remove the session
                        self.redis_client.delete(session_info_key)
                        expired_count += 1

            if expired_count > 0:
                logger.info(
                    "Cleaned up expired sessions",
                    expired_count=expired_count,
                )

            return expired_count
        except Exception as e:
            logger.error(
                "Failed to cleanup expired sessions",
                error=str(e),
            )
            return 0

    def get_session_stats(self) -> dict:
        """
        Get session monitoring statistics.

        Returns:
            Dictionary with session statistics
        """
        try:
            # Count total active sessions
            user_pattern = f"{self.session_prefix}*"
            user_keys = self.redis_client.keys(user_pattern)

            total_sessions = 0
            for user_key in user_keys:
                session_count = self.redis_client.scard(user_key)
                total_sessions += session_count

            stats = {
                "total_active_sessions": total_sessions,
                "total_users_with_sessions": len(user_keys),
                "redis_connected": True,
            }

            logger.debug(
                "Retrieved session statistics",
                **stats,
            )

            return stats
        except Exception as e:
            logger.error(
                "Failed to get session statistics",
                error=str(e),
            )
            return {
                "total_active_sessions": 0,
                "total_users_with_sessions": 0,
                "redis_connected": False,
                "error": str(e),
            }

    def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if Redis is accessible, False otherwise
        """
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(
                "Redis health check failed",
                error=str(e),
            )
            return False

"""
JWT token blacklisting system for enhanced session management.

This module provides token blacklisting functionality to invalidate JWT tokens
immediately upon logout, preventing token reuse and improving security.
"""

import hashlib
from datetime import datetime, timezone

import redis

from ..config import get_config
from ..logging import get_logger

logger = get_logger(__name__)


class TokenBlacklist:
    """JWT token blacklisting system using Redis."""

    def __init__(self) -> None:
        """Initialize token blacklist with Redis connection."""
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
        self.blacklist_prefix = "jwt_blacklist:"
        logger.info("Token blacklist initialized with Redis connection")

    def blacklist_token(self, token: str, expires_at: datetime) -> bool:
        """
        Add token to blacklist.

        Args:
            token: JWT token to blacklist
            expires_at: Token expiration datetime

        Returns:
            True if token was successfully blacklisted, False otherwise
        """
        try:
            # Store token hash with expiration
            token_hash = self._hash_token(token)
            ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())

            if ttl > 0:
                self.redis_client.setex(
                    f"{self.blacklist_prefix}{token_hash}",
                    ttl,
                    str(expires_at.timestamp()),
                )
                logger.info(
                    "Token blacklisted successfully",
                    token_hash=token_hash[:8] + "...",
                    expires_at=expires_at.isoformat(),
                    ttl=ttl,
                )
                return True
            else:
                logger.warning(
                    "Token already expired, not blacklisting",
                    token_hash=token_hash[:8] + "...",
                    expires_at=expires_at.isoformat(),
                )
                return False
        except Exception as e:
            logger.error(
                "Failed to blacklist token",
                error=str(e),
                token_hash=self._hash_token(token)[:8] + "...",
            )
            return False

    def is_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted.

        Args:
            token: JWT token to check

        Returns:
            True if token is blacklisted, False otherwise
        """
        try:
            token_hash = self._hash_token(token)
            is_blacklisted = self.redis_client.exists(
                f"{self.blacklist_prefix}{token_hash}"
            )

            if is_blacklisted:
                logger.debug(
                    "Token found in blacklist",
                    token_hash=token_hash[:8] + "...",
                )

            return bool(is_blacklisted)
        except Exception as e:
            logger.error(
                "Failed to check token blacklist status",
                error=str(e),
                token_hash=self._hash_token(token)[:8] + "...",
            )
            # Fail secure - if we can't check, assume it's blacklisted
            return True

    def _hash_token(self, token: str) -> str:
        """
        Create hash of token for storage.

        Args:
            token: JWT token to hash

        Returns:
            SHA256 hash of the token
        """
        return hashlib.sha256(token.encode()).hexdigest()

    def cleanup_expired(self) -> int:
        """
        Clean up expired blacklist entries.

        Returns:
            Number of expired entries cleaned up
        """
        try:
            # Redis automatically expires keys, but we can clean up manually
            pattern = f"{self.blacklist_prefix}*"
            keys = self.redis_client.keys(pattern)
            expired_count = 0

            for key in keys:
                if not self.redis_client.exists(key):
                    expired_count += 1

            if expired_count > 0:
                logger.info(
                    "Cleaned up expired blacklist entries",
                    expired_count=expired_count,
                )

            return expired_count
        except Exception as e:
            logger.error(
                "Failed to cleanup expired blacklist entries",
                error=str(e),
            )
            return 0

    def get_blacklist_stats(self) -> dict:
        """
        Get blacklist statistics.

        Returns:
            Dictionary with blacklist statistics
        """
        try:
            pattern = f"{self.blacklist_prefix}*"
            keys = self.redis_client.keys(pattern)

            stats = {
                "total_blacklisted_tokens": len(keys),
                "redis_connected": True,
            }

            logger.debug(
                "Retrieved blacklist statistics",
                **stats,
            )

            return stats
        except Exception as e:
            logger.error(
                "Failed to get blacklist statistics",
                error=str(e),
            )
            return {
                "total_blacklisted_tokens": 0,
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

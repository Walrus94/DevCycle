"""
Enhanced JWT strategy with token blacklisting support.

This module extends the FastAPI Users JWT strategy to include token blacklisting
functionality for enhanced session management and security.
"""

from typing import Any, Optional

from fastapi_users.authentication import JWTStrategy
from fastapi_users.exceptions import FastAPIUsersException

from ..logging import get_logger
from .token_blacklist import TokenBlacklist

logger = get_logger(__name__)


class SecureJWTStrategy(JWTStrategy):
    """Enhanced JWT strategy with blacklisting support."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize secure JWT strategy with blacklist."""
        super().__init__(*args, **kwargs)
        self.blacklist = TokenBlacklist()
        logger.info("Secure JWT strategy initialized with token blacklisting")

    async def read_token(
        self, token: Optional[str], user_manager: Any
    ) -> Optional[Any]:
        """
        Read and validate JWT token with blacklist checking.

        Args:
            token: JWT token to validate
            user_manager: User manager instance

        Returns:
            User object if token is valid and not blacklisted

        Raises:
            InvalidToken: If token is blacklisted or invalid
        """
        # Check if token is blacklisted first
        if token and self.blacklist.is_blacklisted(token):
            logger.warning(
                "Blacklisted token attempted to be used",
                token_hash=self.blacklist._hash_token(token)[:8] + "...",
            )
            raise FastAPIUsersException("Token has been revoked")

        # Continue with normal JWT validation
        try:
            user = await super().read_token(token, user_manager)
            logger.debug(
                "Token validated successfully",
                user_id=str(user.id) if user else None,
            )
            return user
        except Exception as e:
            logger.warning(
                "Token validation failed",
                error=str(e),
                token_hash=(
                    self.blacklist._hash_token(token)[:8] + "..." if token else "None"
                ),
            )
            raise

    def get_blacklist_stats(self) -> dict:
        """
        Get token blacklist statistics.

        Returns:
            Dictionary with blacklist statistics
        """
        return self.blacklist.get_blacklist_stats()

    def health_check(self) -> bool:
        """
        Check if blacklist system is healthy.

        Returns:
            True if blacklist system is accessible, False otherwise
        """
        return self.blacklist.health_check()

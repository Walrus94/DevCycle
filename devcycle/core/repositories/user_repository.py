"""
User repository for DevCycle.

This module provides user-specific data access operations
extending the base repository pattern.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.models import User
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    User repository providing user-specific data access operations.

    This repository extends the base repository with user-specific
    methods like finding by email, checking authentication status, etc.
    """

    def __init__(self, session: AsyncSession):
        """Initialize user repository with session."""
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User's email address

        Returns:
            User instance or None if not found
        """
        return await self.find_one_by(email=email)

    async def get_active_users(self) -> List[User]:
        """
        Get all active users.

        Returns:
            List of active users
        """
        return await self.find_by(is_active=True)

    async def get_verified_users(self) -> List[User]:
        """
        Get all verified users.

        Returns:
            List of verified users
        """
        return await self.find_by(is_verified=True)

    async def get_superusers(self) -> List[User]:
        """
        Get all superusers.

        Returns:
            List of superusers
        """
        return await self.find_by(is_superuser=True)

    async def get_users_by_status(
        self,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        is_superuser: Optional[bool] = None,
    ) -> List[User]:
        """
        Get users filtered by status flags.

        Args:
            is_active: Filter by active status
            is_verified: Filter by verification status
            is_superuser: Filter by superuser status

        Returns:
            List of users matching the criteria
        """
        filters = {}
        if is_active is not None:
            filters["is_active"] = is_active
        if is_verified is not None:
            filters["is_verified"] = is_verified
        if is_superuser is not None:
            filters["is_superuser"] = is_superuser

        return await self.find_by(**filters)

    async def count_active_users(self) -> int:
        """
        Count total active users.

        Returns:
            Number of active users
        """
        stmt = select(self.model.id).where(self.model.is_active == True)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def count_verified_users(self) -> int:
        """
        Count total verified users.

        Returns:
            Number of verified users
        """
        stmt = select(self.model.id).where(self.model.is_verified == True)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def email_exists(self, email: str) -> bool:
        """
        Check if email address already exists.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        user = await self.get_by_email(email)
        return user is not None

    async def update_user_status(
        self,
        user_id: UUID,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        is_superuser: Optional[bool] = None,
    ) -> Optional[User]:
        """
        Update user status flags.

        Args:
            user_id: User identifier
            is_active: New active status
            is_verified: New verification status
            is_superuser: New superuser status

        Returns:
            Updated user instance or None if not found
        """
        updates = {}
        if is_active is not None:
            updates["is_active"] = is_active
        if is_verified is not None:
            updates["is_verified"] = is_verified
        if is_superuser is not None:
            updates["is_superuser"] = is_superuser

        if updates:
            return await self.update(user_id, **updates)
        return await self.get_by_id(user_id)

    async def deactivate_user(self, user_id: UUID) -> Optional[User]:
        """
        Deactivate a user.

        Args:
            user_id: User identifier

        Returns:
            Updated user instance or None if not found
        """
        return await self.update_user_status(user_id, is_active=False)

    async def activate_user(self, user_id: UUID) -> Optional[User]:
        """
        Activate a user.

        Args:
            user_id: User identifier

        Returns:
            Updated user instance or None if not found
        """
        return await self.update_user_status(user_id, is_active=True)

    async def verify_user(self, user_id: UUID) -> Optional[User]:
        """
        Mark user as verified.

        Args:
            user_id: User identifier

        Returns:
            Updated user instance or None if not found
        """
        return await self.update_user_status(user_id, is_verified=True)

    async def promote_to_superuser(self, user_id: UUID) -> Optional[User]:
        """
        Promote user to superuser.

        Args:
            user_id: User identifier

        Returns:
            Updated user instance or None if not found
        """
        return await self.update_user_status(user_id, is_superuser=True)

    async def demote_from_superuser(self, user_id: UUID) -> Optional[User]:
        """
        Demote user from superuser.

        Args:
            user_id: User identifier

        Returns:
            Updated user instance or None if not found
        """
        return await self.update_user_status(user_id, is_superuser=False)

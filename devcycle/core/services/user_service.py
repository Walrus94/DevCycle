"""
User service for DevCycle.

This module contains business logic for user management operations,
including validation, business rules, and complex user workflows.
"""

import re
from typing import Any, List, Optional
from uuid import UUID

from ..auth.models import User
from ..repositories.user_repository import UserRepository
from .base import BaseService


class UserService(BaseService[User]):
    """
    Service for user management operations.

    This service provides business logic for user operations including
    validation, business rules, and complex user workflows.
    """

    def __init__(self, user_repository: UserRepository):
        """
        Initialize user service.

        Args:
            user_repository: User repository instance
        """
        super().__init__(user_repository)
        self.user_repository = user_repository

    async def create_user(self, email: str, password: str, **kwargs: Any) -> User:
        """
        Create a new user with business logic validation.

        Args:
            email: User email address
            password: User password
            **kwargs: Additional user attributes

        Returns:
            Created user instance

        Raises:
            ValueError: If email or password validation fails
        """
        # Validate email format
        if not self._is_valid_email(email):
            raise ValueError("Invalid email format")

        # Validate password strength
        if not self._is_valid_password(password):
            raise ValueError("Password does not meet security requirements")

        # Check if email already exists
        if await self.user_repository.email_exists(email):
            raise ValueError("Email address already registered")

        # Hash the password before storing
        from ..auth import hash_password

        hashed_password = hash_password(password)

        # Create user through repository with hashed password
        user = await self.repository.create(
            email=email, hashed_password=hashed_password, **kwargs
        )

        # Apply business logic
        user = await self.apply_business_logic(user, is_new_user=True)

        return user

    async def update_user_profile(self, user_id: UUID, **kwargs: Any) -> Optional[User]:
        """
        Update user profile with business logic validation.

        Args:
            user_id: User identifier
            **kwargs: Profile attributes to update

        Returns:
            Updated user instance or None if not found

        Raises:
            ValueError: If validation fails
        """
        # Get existing user
        user = await self.get_by_id(user_id)
        if not user:
            return None

        # Validate email if being updated
        if "email" in kwargs:
            new_email = kwargs["email"]
            if not self._is_valid_email(new_email):
                raise ValueError("Invalid email format")

            # Check if new email conflicts with existing users
            existing_user = await self.user_repository.get_by_email(new_email)
            if existing_user and existing_user.id != user_id:
                raise ValueError("Email address already in use by another user")

        # Update user through repository
        updated_user = await self.repository.update(user_id, **kwargs)

        # Apply business logic
        if updated_user:
            updated_user = await self.apply_business_logic(
                updated_user, profile_updated=True
            )

        return updated_user

    async def update_user_password(
        self, user_id: UUID, new_password: str
    ) -> Optional[User]:
        """
        Update user password with business logic validation.

        Args:
            user_id: User identifier
            new_password: New password to set

        Returns:
            Updated user instance or None if not found

        Raises:
            ValueError: If validation fails
        """
        # Get existing user
        user = await self.get_by_id(user_id)
        if not user:
            return None

        # Validate new password
        if not self._is_valid_password(new_password):
            raise ValueError("Password does not meet security requirements")

        # Hash the new password
        from ..auth import hash_password

        hashed_password = hash_password(new_password)

        # Update password through repository
        updated_user = await self.repository.update(
            user_id, hashed_password=hashed_password
        )

        # Apply business logic
        if updated_user:
            updated_user = await self.apply_business_logic(
                updated_user, password_changed=True
            )

        return updated_user

    async def deactivate_user(
        self, user_id: UUID, reason: Optional[str] = None
    ) -> Optional[User]:
        """
        Deactivate user with business logic.

        Args:
            user_id: User identifier
            reason: Optional reason for deactivation

        Returns:
            Deactivated user instance or None if not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        # Business rule: Cannot deactivate superusers
        if user.is_superuser:
            raise ValueError("Cannot deactivate superuser accounts")

        # Deactivate user
        deactivated_user = await self.user_repository.deactivate_user(user_id)

        # Apply business logic
        if deactivated_user:
            deactivated_user = await self.apply_business_logic(
                deactivated_user, deactivated=True, deactivation_reason=reason
            )

        return deactivated_user

    async def activate_user(self, user_id: UUID) -> Optional[User]:
        """
        Activate user with business logic.

        Args:
            user_id: User identifier

        Returns:
            Activated user instance or None if not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        # Activate user
        activated_user = await self.user_repository.activate_user(user_id)

        # Apply business logic
        if activated_user:
            activated_user = await self.apply_business_logic(
                activated_user, activated=True
            )

        return activated_user

    async def verify_user_email(self, user_id: UUID) -> Optional[User]:
        """
        Verify user email with business logic.

        Args:
            user_id: User identifier

        Returns:
            Verified user instance or None if not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        # Verify user
        verified_user = await self.user_repository.verify_user(user_id)

        # Apply business logic
        if verified_user:
            verified_user = await self.apply_business_logic(
                verified_user, email_verified=True
            )

        return verified_user

    async def promote_to_superuser(
        self, user_id: UUID, promoted_by: UUID
    ) -> Optional[User]:
        """
        Promote user to superuser with business logic.

        Args:
            user_id: User identifier
            promoted_by: ID of user performing the promotion

        Returns:
            Promoted user instance or None if not found

        Raises:
            ValueError: If promotion is not allowed
        """
        # Get user to be promoted
        user = await self.get_by_id(user_id)
        if not user:
            return None

        # Get promoting user
        promoter = await self.get_by_id(promoted_by)
        if not promoter or not promoter.is_superuser:
            raise ValueError("Only superusers can promote other users")

        # Business rule: Cannot promote inactive users
        if not user.is_active:
            raise ValueError("Cannot promote inactive users to superuser")

        # Promote user
        promoted_user = await self.user_repository.promote_to_superuser(user_id)

        # Apply business logic
        if promoted_user:
            promoted_user = await self.apply_business_logic(
                promoted_user, promoted_to_superuser=True, promoted_by=promoted_by
            )

        return promoted_user

    async def get_active_users(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[User]:
        """
        Get active users with business logic filtering.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip

        Returns:
            List of active user instances
        """
        users = await self.user_repository.get_active_users()

        # Apply business logic filtering
        filtered_users = []
        for user in users:
            processed_user = await self.apply_business_logic(user, for_listing=True)
            if processed_user:
                filtered_users.append(processed_user)

        # Apply pagination
        if offset:
            filtered_users = filtered_users[offset:]
        if limit:
            filtered_users = filtered_users[:limit]

        return filtered_users

    async def search_users(self, query: str, limit: Optional[int] = None) -> List[User]:
        """
        Search users by query with business logic.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching user instances
        """
        # Simple search implementation - could be enhanced with full-text search
        users = await self.user_repository.get_all()

        # Filter by query
        matching_users = []
        query_lower = query.lower()

        for user in users:
            if query_lower in user.email.lower() or (
                hasattr(user, "name") and user.name and query_lower in user.name.lower()
            ):
                matching_users.append(user)

        # Apply business logic
        processed_users = []
        for user in matching_users:
            processed_user = await self.apply_business_logic(user, search_result=True)
            if processed_user:
                processed_users.append(processed_user)

        # Apply limit
        if limit:
            processed_users = processed_users[:limit]

        return processed_users

    async def validate_business_rules(self, entity: User, **kwargs: Any) -> bool:
        """
        Validate business rules for user operations.

        Args:
            entity: User instance to validate
            **kwargs: Additional validation context

        Returns:
            True if validation passes, False otherwise
        """
        # Basic validation rules
        if not entity.email:
            return False

        if not self._is_valid_email(entity.email):
            return False

        # Business rule: Superusers must be verified
        if entity.is_superuser and not entity.is_verified:
            return False

        # Business rule: Inactive users cannot be verified
        if not entity.is_active and entity.is_verified:
            return False

        return True

    async def apply_business_logic(self, entity: User, **kwargs: Any) -> User:
        """
        Apply business logic to user.

        Args:
            entity: User instance to process
            **kwargs: Additional business logic context

        Returns:
            Processed user instance
        """
        # Apply business logic based on context
        if kwargs.get("is_new_user"):
            # New users start as unverified and active
            entity.is_verified = False
            entity.is_active = True
            entity.is_superuser = False

        if kwargs.get("deactivated"):
            # Deactivated users lose superuser privileges
            entity.is_superuser = False

        if kwargs.get("email_verified"):
            # Email verification might trigger additional business logic
            pass

        if kwargs.get("for_listing"):
            # Remove sensitive information for listing operations
            if hasattr(entity, "hashed_password"):
                entity.hashed_password = None

        return entity

    def _is_valid_email(self, email: str) -> bool:
        """
        Validate email format.

        Args:
            email: Email address to validate

        Returns:
            True if email format is valid, False otherwise
        """
        if not email:
            return False

        # Basic email regex pattern
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def _is_valid_password(self, password: str) -> bool:
        """
        Validate password strength.

        Args:
            password: Password to validate

        Returns:
            True if password meets requirements, False otherwise
        """
        if not password:
            return False

        # Password requirements
        if len(password) < 8:
            return False

        # Must contain at least one uppercase letter, one lowercase letter,
        # and one digit
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        return has_upper and has_lower and has_digit

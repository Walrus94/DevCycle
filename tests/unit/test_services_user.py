"""
Unit tests for user service functionality.

This module tests the UserService class and its user-specific business logic.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from devcycle.core.auth.models import User
from devcycle.core.repositories.user_repository import UserRepository
from devcycle.core.services.user_service import UserService


@pytest.fixture
def mock_user_repository():
    """Create a mock user repository."""
    repository = AsyncMock(spec=UserRepository)
    repository.create = AsyncMock()
    repository.get_by_id = AsyncMock()
    repository.get_by_email = AsyncMock()
    repository.email_exists = AsyncMock()
    repository.update = AsyncMock()
    repository.deactivate_user = AsyncMock()
    repository.activate_user = AsyncMock()
    repository.verify_user = AsyncMock()
    repository.promote_to_superuser = AsyncMock()
    repository.demote_from_superuser = AsyncMock()
    repository.get_active_users = AsyncMock()
    repository.get_all = AsyncMock()
    return repository


@pytest.fixture
def user_service(mock_user_repository):
    """Create a user service instance."""
    return UserService(mock_user_repository)


@pytest.fixture
def sample_user():
    """Create a sample user instance."""
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_verified=False,
        is_superuser=False,
    )


@pytest.fixture
def superuser():
    """Create a superuser instance."""
    return User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_verified=True,
        is_superuser=True,
    )


class TestUserService:
    """Test user service functionality."""

    def test_init(self, mock_user_repository):
        """Test service initialization."""
        service = UserService(mock_user_repository)
        assert service.repository == mock_user_repository
        assert service.user_repository == mock_user_repository

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_user_repository):
        """Test successful user creation."""
        # Arrange
        mock_user = User(
            id=uuid4(),
            email="new@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_verified=False,
            is_superuser=False,
        )
        mock_user_repository.email_exists.return_value = False
        mock_user_repository.create.return_value = mock_user

        # Act
        result = await user_service.create_user("new@example.com", "SecurePass123")

        # Assert
        mock_user_repository.email_exists.assert_called_once_with("new@example.com")
        mock_user_repository.create.assert_called_once()
        assert result == mock_user
        assert result.is_verified is False
        assert result.is_active is True
        assert result.is_superuser is False

    @pytest.mark.asyncio
    async def test_create_user_invalid_email(self, user_service):
        """Test user creation with invalid email."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid email format"):
            await user_service.create_user("invalid-email", "SecurePass123")

    @pytest.mark.asyncio
    async def test_create_user_weak_password(self, user_service):
        """Test user creation with weak password."""
        # Act & Assert
        with pytest.raises(
            ValueError, match="Password does not meet security requirements"
        ):
            await user_service.create_user("valid@email.com", "weak")

    @pytest.mark.asyncio
    async def test_create_user_email_exists(self, user_service, mock_user_repository):
        """Test user creation with existing email."""
        # Arrange
        mock_user_repository.email_exists.return_value = True

        # Act & Assert
        with pytest.raises(ValueError, match="Email address already registered"):
            await user_service.create_user("existing@email.com", "SecurePass123")

    @pytest.mark.asyncio
    async def test_update_user_profile_success(
        self, user_service, mock_user_repository, sample_user
    ):
        """Test successful user profile update."""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.update.return_value = sample_user

        # Act
        result = await user_service.update_user_profile(sample_user.id, name="New Name")

        # Assert
        mock_user_repository.update.assert_called_once_with(
            sample_user.id, name="New Name"
        )
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_update_user_profile_not_found(
        self, user_service, mock_user_repository
    ):
        """Test user profile update when user not found."""
        # Arrange
        mock_user_repository.get_by_id.return_value = None

        # Act
        result = await user_service.update_user_profile(uuid4(), name="New Name")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_user_profile_invalid_email(
        self, user_service, mock_user_repository, sample_user
    ):
        """Test user profile update with invalid email."""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid email format"):
            await user_service.update_user_profile(
                sample_user.id, email="invalid-email"
            )

    @pytest.mark.asyncio
    async def test_update_user_profile_email_conflict(
        self, user_service, mock_user_repository, sample_user
    ):
        """Test user profile update with conflicting email."""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user
        conflicting_user = User(id=uuid4(), email="conflict@email.com")
        mock_user_repository.get_by_email.return_value = conflicting_user

        # Act & Assert
        with pytest.raises(
            ValueError, match="Email address already in use by another user"
        ):
            await user_service.update_user_profile(
                sample_user.id, email="conflict@email.com"
            )

    @pytest.mark.asyncio
    async def test_deactivate_user_success(
        self, user_service, mock_user_repository, sample_user
    ):
        """Test successful user deactivation."""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.deactivate_user.return_value = sample_user

        # Act
        result = await user_service.deactivate_user(
            sample_user.id, reason="Test deactivation"
        )

        # Assert
        mock_user_repository.deactivate_user.assert_called_once_with(sample_user.id)
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_deactivate_user_not_found(self, user_service, mock_user_repository):
        """Test user deactivation when user not found."""
        # Arrange
        mock_user_repository.get_by_id.return_value = None

        # Act
        result = await user_service.deactivate_user(uuid4())

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_deactivate_superuser_forbidden(
        self, user_service, mock_user_repository, superuser
    ):
        """Test that superusers cannot be deactivated."""
        # Arrange
        mock_user_repository.get_by_id.return_value = superuser

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot deactivate superuser accounts"):
            await user_service.deactivate_user(superuser.id)

    @pytest.mark.asyncio
    async def test_activate_user_success(
        self, user_service, mock_user_repository, sample_user
    ):
        """Test successful user activation."""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.activate_user.return_value = sample_user

        # Act
        result = await user_service.activate_user(sample_user.id)

        # Assert
        mock_user_repository.activate_user.assert_called_once_with(sample_user.id)
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_verify_user_email_success(
        self, user_service, mock_user_repository, sample_user
    ):
        """Test successful user email verification."""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.verify_user.return_value = sample_user

        # Act
        result = await user_service.verify_user_email(sample_user.id)

        # Assert
        mock_user_repository.verify_user.assert_called_once_with(sample_user.id)
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_promote_to_superuser_success(
        self, user_service, mock_user_repository, sample_user, superuser
    ):
        """Test successful user promotion to superuser."""
        # Arrange
        mock_user_repository.get_by_id.side_effect = [sample_user, superuser]
        mock_user_repository.promote_to_superuser.return_value = sample_user

        # Act
        result = await user_service.promote_to_superuser(sample_user.id, superuser.id)

        # Assert
        mock_user_repository.promote_to_superuser.assert_called_once_with(
            sample_user.id
        )
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_promote_to_superuser_not_found(
        self, user_service, mock_user_repository
    ):
        """Test user promotion when user not found."""
        # Arrange
        mock_user_repository.get_by_id.return_value = None

        # Act
        result = await user_service.promote_to_superuser(uuid4(), uuid4())

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_promote_to_superuser_unauthorized(
        self, user_service, mock_user_repository, sample_user
    ):
        """Test user promotion by non-superuser."""
        # Arrange
        regular_user = User(id=uuid4(), is_superuser=False)
        mock_user_repository.get_by_id.side_effect = [sample_user, regular_user]

        # Act & Assert
        with pytest.raises(ValueError, match="Only superusers can promote other users"):
            await user_service.promote_to_superuser(sample_user.id, regular_user.id)

    @pytest.mark.asyncio
    async def test_promote_inactive_user_forbidden(
        self, user_service, mock_user_repository, superuser
    ):
        """Test that inactive users cannot be promoted to superuser."""
        # Arrange
        inactive_user = User(id=uuid4(), is_active=False)
        mock_user_repository.get_by_id.side_effect = [inactive_user, superuser]

        # Act & Assert
        with pytest.raises(
            ValueError, match="Cannot promote inactive users to superuser"
        ):
            await user_service.promote_to_superuser(inactive_user.id, superuser.id)

    @pytest.mark.asyncio
    async def test_get_active_users(self, user_service, mock_user_repository):
        """Test getting active users with business logic."""
        # Arrange
        active_users = [
            User(
                id=uuid4(),
                email="user1@example.com",
                hashed_password="hash1",
                is_active=True,
            ),
            User(
                id=uuid4(),
                email="user2@example.com",
                hashed_password="hash2",
                is_active=True,
            ),
        ]
        mock_user_repository.get_active_users.return_value = active_users

        # Act
        result = await user_service.get_active_users(limit=2, offset=1)

        # Assert
        mock_user_repository.get_active_users.assert_called_once()
        # With offset=1, we skip the first user, so we expect 1 user (not 2)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_users(self, user_service, mock_user_repository):
        """Test user search functionality."""
        # Arrange
        all_users = [
            User(id=uuid4(), email="john@example.com"),
            User(id=uuid4(), email="jane@example.com"),
            User(id=uuid4(), email="bob@example.com"),
        ]
        mock_user_repository.get_all.return_value = all_users

        # Act
        result = await user_service.search_users("john", limit=5)

        # Assert
        assert len(result) == 1
        assert result[0].email == "john@example.com"

    @pytest.mark.asyncio
    async def test_validate_business_rules_valid(self, user_service, sample_user):
        """Test business rules validation with valid user."""
        # Act
        result = await user_service.validate_business_rules(sample_user)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_business_rules_invalid_email(self, user_service):
        """Test business rules validation with invalid email."""
        # Arrange
        invalid_user = User(
            id=uuid4(), email="", is_active=True, is_verified=False, is_superuser=False
        )

        # Act
        result = await user_service.validate_business_rules(invalid_user)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_business_rules_superuser_unverified(self, user_service):
        """Test business rules validation with unverified superuser."""
        # Arrange
        invalid_user = User(
            id=uuid4(),
            email="admin@example.com",
            is_active=True,
            is_verified=False,
            is_superuser=True,
        )

        # Act
        result = await user_service.validate_business_rules(invalid_user)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_business_rules_inactive_verified(self, user_service):
        """Test business rules validation with verified inactive user."""
        # Arrange
        invalid_user = User(
            id=uuid4(),
            email="user@example.com",
            is_active=False,
            is_verified=True,
            is_superuser=False,
        )

        # Act
        result = await user_service.validate_business_rules(invalid_user)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_apply_business_logic_new_user(self, user_service, sample_user):
        """Test business logic application for new user."""
        # Act
        result = await user_service.apply_business_logic(sample_user, is_new_user=True)

        # Assert
        assert result.is_verified is False
        assert result.is_active is True
        assert result.is_superuser is False

    @pytest.mark.asyncio
    async def test_apply_business_logic_deactivated(self, user_service, superuser):
        """Test business logic application for deactivated user."""
        # Act
        result = await user_service.apply_business_logic(superuser, deactivated=True)

        # Assert
        assert result.is_superuser is False

    @pytest.mark.asyncio
    async def test_apply_business_logic_for_listing(self, user_service, sample_user):
        """Test business logic application for listing operations."""
        # Act
        result = await user_service.apply_business_logic(sample_user, for_listing=True)

        # Assert
        assert result.hashed_password is None

    def test_is_valid_email_valid(self, user_service):
        """Test email validation with valid email."""
        # Act
        result = user_service._is_valid_email("test@example.com")

        # Assert
        assert result is True

    def test_is_valid_email_invalid(self, user_service):
        """Test email validation with invalid email."""
        # Act & Assert
        assert user_service._is_valid_email("invalid-email") is False
        assert user_service._is_valid_email("") is False
        assert user_service._is_valid_email("@example.com") is False
        assert user_service._is_valid_email("test@") is False

    def test_is_valid_password_valid(self, user_service):
        """Test password validation with valid password."""
        # Act
        result = user_service._is_valid_password("SecurePass123")

        # Assert
        assert result is True

    def test_is_valid_password_invalid(self, user_service):
        """Test password validation with invalid password."""
        # Act & Assert
        assert user_service._is_valid_password("") is False
        assert user_service._is_valid_password("weak") is False
        assert user_service._is_valid_password("nouppercase123") is False
        assert user_service._is_valid_password("NOLOWERCASE123") is False
        assert user_service._is_valid_password("NoDigits") is False

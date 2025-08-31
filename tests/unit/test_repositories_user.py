"""
Unit tests for user repository functionality.

This module tests the UserRepository class and its user-specific operations.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from devcycle.core.auth.models import User
from devcycle.core.repositories.user_repository import UserRepository


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def user_repository(mock_session):
    """Create a user repository instance."""
    return UserRepository(mock_session)


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


class TestUserRepository:
    """Test user repository functionality."""

    def test_init(self, mock_session):
        """Test repository initialization."""
        repo = UserRepository(mock_session)
        assert repo.session == mock_session
        assert repo.model == User

    @pytest.mark.asyncio
    @patch.object(UserRepository, "find_one_by")
    async def test_get_by_email(self, mock_find_one_by, user_repository, sample_user):
        """Test getting user by email."""
        # Arrange
        mock_find_one_by.return_value = sample_user

        # Act
        result = await user_repository.get_by_email("test@example.com")

        # Assert
        assert result == sample_user

    @pytest.mark.asyncio
    @patch.object(UserRepository, "find_one_by")
    async def test_get_by_email_not_found(self, mock_find_one_by, user_repository):
        """Test getting user by email when not found."""
        # Arrange
        mock_find_one_by.return_value = None

        # Act
        result = await user_repository.get_by_email("nonexistent@example.com")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    @patch.object(UserRepository, "find_by")
    async def test_get_active_users(self, mock_find_by, user_repository):
        """Test getting active users."""
        # Arrange
        active_users = [
            User(
                id=uuid4(),
                email="user1@example.com",
                hashed_password="hash",
                is_active=True,
            ),
            User(
                id=uuid4(),
                email="user2@example.com",
                hashed_password="hash",
                is_active=True,
            ),
        ]
        mock_find_by.return_value = active_users

        # Act
        result = await user_repository.get_active_users()

        # Assert
        assert result == active_users
        assert len(result) == 2

    @pytest.mark.asyncio
    @patch.object(UserRepository, "find_by")
    async def test_get_verified_users(self, mock_find_by, user_repository):
        """Test getting verified users."""
        # Arrange
        verified_users = [
            User(
                id=uuid4(),
                email="user1@example.com",
                hashed_password="hash",
                is_verified=True,
            ),
            User(
                id=uuid4(),
                email="user2@example.com",
                hashed_password="hash",
                is_verified=True,
            ),
        ]
        mock_find_by.return_value = verified_users

        # Act
        result = await user_repository.get_verified_users()

        # Assert
        assert result == verified_users
        assert len(result) == 2

    @pytest.mark.asyncio
    @patch.object(UserRepository, "find_by")
    async def test_get_superusers(self, mock_find_by, user_repository):
        """Test getting superusers."""
        # Arrange
        superusers = [
            User(
                id=uuid4(),
                email="admin1@example.com",
                hashed_password="hash",
                is_superuser=True,
            ),
            User(
                id=uuid4(),
                email="admin2@example.com",
                hashed_password="hash",
                is_superuser=True,
            ),
        ]
        mock_find_by.return_value = superusers

        # Act
        result = await user_repository.get_superusers()

        # Assert
        assert result == superusers
        assert len(result) == 2

    @pytest.mark.asyncio
    @patch.object(UserRepository, "find_by")
    async def test_get_users_by_status(self, mock_find_by, user_repository):
        """Test getting users by status filters."""
        # Arrange
        filtered_users = [
            User(
                id=uuid4(),
                email="user@example.com",
                hashed_password="hash",
                is_active=True,
                is_verified=True,
            )
        ]
        mock_find_by.return_value = filtered_users

        # Act
        result = await user_repository.get_users_by_status(
            is_active=True, is_verified=True
        )

        # Assert
        assert result == filtered_users

    @pytest.mark.asyncio
    @patch.object(UserRepository, "find_by")
    async def test_get_users_by_status_no_filters(self, mock_find_by, user_repository):
        """Test getting users by status with no filters."""
        # Arrange
        all_users = [
            User(id=uuid4(), email="user1@example.com", hashed_password="hash"),
            User(id=uuid4(), email="user2@example.com", hashed_password="hash"),
        ]
        mock_find_by.return_value = all_users

        # Act
        result = await user_repository.get_users_by_status()

        # Assert
        assert result == all_users

    @pytest.mark.asyncio
    @patch.object(UserRepository, "count_active_users")
    async def test_count_active_users(self, mock_count, user_repository):
        """Test counting active users."""
        # Arrange
        mock_count.return_value = 2

        # Act
        result = await user_repository.count_active_users()

        # Assert
        assert result == 2

    @pytest.mark.asyncio
    @patch.object(UserRepository, "count_verified_users")
    async def test_count_verified_users(self, mock_count, user_repository):
        """Test counting verified users."""
        # Arrange
        mock_count.return_value = 1

        # Act
        result = await user_repository.count_verified_users()

        # Assert
        assert result == 1

    @pytest.mark.asyncio
    @patch.object(UserRepository, "find_one_by")
    async def test_email_exists_true(self, mock_find_one_by, user_repository):
        """Test checking if email exists when it does."""
        # Arrange
        mock_find_one_by.return_value = User(
            id=uuid4(), email="test@example.com", hashed_password="hash"
        )

        # Act
        result = await user_repository.email_exists("test@example.com")

        # Assert
        assert result is True

    @pytest.mark.asyncio
    @patch.object(UserRepository, "find_one_by")
    async def test_email_exists_false(self, mock_find_one_by, user_repository):
        """Test checking if email exists when it doesn't."""
        # Arrange
        mock_find_one_by.return_value = None

        # Act
        result = await user_repository.email_exists("nonexistent@example.com")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    @patch.object(UserRepository, "update")
    async def test_update_user_status(self, mock_update, user_repository, sample_user):
        """Test updating user status."""
        # Arrange
        mock_update.return_value = sample_user

        # Act
        result = await user_repository.update_user_status(
            sample_user.id, is_active=True, is_verified=True
        )

        # Assert
        assert result == sample_user

    @pytest.mark.asyncio
    @patch.object(UserRepository, "get_by_id")
    async def test_update_user_status_no_changes(
        self, mock_get_by_id, user_repository, sample_user
    ):
        """Test updating user status with no changes."""
        # Arrange
        mock_get_by_id.return_value = sample_user

        # Act
        result = await user_repository.update_user_status(sample_user.id)

        # Assert
        assert result == sample_user

    @pytest.mark.asyncio
    @patch.object(UserRepository, "update")
    async def test_deactivate_user(self, mock_update, user_repository, sample_user):
        """Test deactivating a user."""
        # Arrange
        mock_update.return_value = sample_user

        # Act
        result = await user_repository.deactivate_user(sample_user.id)

        # Assert
        assert result == sample_user

    @pytest.mark.asyncio
    @patch.object(UserRepository, "update")
    async def test_activate_user(self, mock_update, user_repository, sample_user):
        """Test activating a user."""
        # Arrange
        mock_update.return_value = sample_user

        # Act
        result = await user_repository.activate_user(sample_user.id)

        # Assert
        assert result == sample_user

    @pytest.mark.asyncio
    @patch.object(UserRepository, "update")
    async def test_verify_user(self, mock_update, user_repository, sample_user):
        """Test verifying a user."""
        # Arrange
        mock_update.return_value = sample_user

        # Act
        result = await user_repository.verify_user(sample_user.id)

        # Assert
        assert result == sample_user

    @pytest.mark.asyncio
    @patch.object(UserRepository, "update")
    async def test_promote_to_superuser(
        self, mock_update, user_repository, sample_user
    ):
        """Test promoting a user to superuser."""
        # Arrange
        mock_update.return_value = sample_user

        # Act
        result = await user_repository.promote_to_superuser(sample_user.id)

        # Assert
        assert result == sample_user

    @pytest.mark.asyncio
    @patch.object(UserRepository, "update")
    async def test_demote_from_superuser(self, mock_update, user_repository, superuser):
        """Test demoting a user from superuser."""
        # Arrange
        mock_update.return_value = superuser

        # Act
        result = await user_repository.demote_from_superuser(superuser.id)

        # Assert
        assert result == superuser

    @pytest.mark.asyncio
    @patch.object(UserRepository, "update")
    async def test_update_user_status_user_not_found(
        self, mock_update, user_repository
    ):
        """Test updating user status when user not found."""
        # Arrange
        mock_update.return_value = None

        # Act
        result = await user_repository.update_user_status(uuid4(), is_active=False)

        # Assert
        assert result is None

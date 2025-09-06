"""
Tortoise ORM user models for DevCycle authentication.

Simple user model for now - FastAPI Users integration can be added later.
"""

from tortoise import fields
from tortoise.models import Model


class User(Model):
    """User model using Tortoise ORM."""

    id = fields.UUIDField(primary_key=True)
    email = fields.CharField(max_length=255, unique=True)
    hashed_password = fields.CharField(max_length=255)
    is_active = fields.BooleanField(default=True)
    is_superuser = fields.BooleanField(default=False)
    is_verified = fields.BooleanField(default=False)

    # Additional user profile fields
    first_name = fields.CharField(max_length=100, null=True)
    last_name = fields.CharField(max_length=100, null=True)
    role = fields.CharField(max_length=50, default="user", db_index=True)

    class Meta:
        """Meta class for User model."""

        table = "user"

    def __str__(self) -> str:
        """Return string representation of User."""
        return f"User({self.email})"

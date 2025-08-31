"""
FastAPI Users models for DevCycle.

This module defines the user models that extend FastAPI Users base classes,
providing a clean, simple authentication system.
"""

from uuid import uuid4

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from ..database.models import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    """User model extending FastAPI Users base."""

    __tablename__ = "user"

    # These fields are required by FastAPI Users
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_superuser = Column(Boolean, nullable=False, default=False)
    is_verified = Column(Boolean, nullable=False, default=False)

    # Additional user profile fields
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Basic role field for simple authorization
    role = Column(String(50), nullable=False, default="user", index=True)

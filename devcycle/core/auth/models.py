"""
FastAPI Users models for DevCycle.

This module defines the user models that extend FastAPI Users base classes,
providing a clean, simple authentication system.
"""

from typing import Optional
from uuid import UUID, uuid4

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database.models import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    """User model extending FastAPI Users base."""

    __tablename__ = "user"

    # These fields are required by FastAPI Users
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Additional user profile fields
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Basic role field for simple authorization
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default="user", index=True
    )

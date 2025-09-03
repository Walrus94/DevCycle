"""
FastAPI Users models for DevCycle.

This module defines the user models that extend FastAPI Users base classes,
providing a clean, simple authentication system.
"""

from typing import Optional

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ..database.models import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    """User model extending FastAPI Users base."""

    __tablename__ = "user"

    # Additional user profile fields
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Basic role field for simple authorization
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default="user", index=True
    )

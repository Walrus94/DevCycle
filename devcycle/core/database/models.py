"""
Database models for DevCycle.

This module defines SQLAlchemy ORM models for the database schema.
Note: User authentication models are now handled by FastAPI Users in core/auth/models.py
"""

from typing import Any

from sqlalchemy.orm import declarative_base

Base: Any = declarative_base()

# Note: User authentication models are now in core/auth/models.py
# This file contains only non-auth related models


# AuditLog model removed - unused in the codebase
# System uses structlog for logging instead of database audit logs

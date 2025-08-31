"""
Authentication module for DevCycle.

This module provides authentication models, utilities, FastAPI Users integration,
and authorization decorators.
"""

from .decorators import (
    check_user_role,
    get_user_role_level,
    require_admin,
    require_role,
    require_user,
)
from .models import User
from .password import hash_password, verify_password

__all__ = [
    "User",
    "hash_password",
    "verify_password",
    "require_role",
    "require_admin",
    "require_user",
    "check_user_role",
    "get_user_role_level",
]

"""
Authentication module for DevCycle API.

This module provides FastAPI Users-based authentication endpoints
for the DevCycle API system.
"""

from .endpoints import router as auth_router

__all__ = ["auth_router"]

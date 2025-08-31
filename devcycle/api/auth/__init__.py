"""
Authentication package for the DevCycle API.

This package provides session-based authentication using Redis for storage,
with features like session management, rate limiting, and security.
"""

from .sessions import SessionData, SessionManager, get_session_manager

__all__ = [
    "SessionManager",
    "SessionData",
    "get_session_manager",
]

"""
CSRF Protection Middleware for FastAPI.

This module provides CSRF protection for state-changing operations.
"""

import secrets
import time
from typing import Callable, Dict

from fastapi import Request, status
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware for state-changing operations."""

    def __init__(self, app: Starlette, secret_key: str) -> None:
        super().__init__(app)
        self.secret_key = secret_key
        self.csrf_tokens: Dict[str, float] = {}  # token -> timestamp
        self.token_lifetime = 3600  # 1 hour

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """Process request and check CSRF token for state-changing operations."""

        # Skip CSRF check for safe methods
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            response = await call_next(request)
            return response

        # Skip CSRF check for health endpoints
        if request.url.path.startswith("/health"):
            response = await call_next(request)
            return response

        # Check CSRF token for state-changing operations
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token required"},
            )

        # Validate token
        if not self._validate_csrf_token(csrf_token):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Invalid CSRF token"},
            )

        response = await call_next(request)
        return response

    def _validate_csrf_token(self, token: str) -> bool:
        """Validate CSRF token."""
        if token not in self.csrf_tokens:
            return False

        # Check if token has expired
        token_time = self.csrf_tokens[token]
        if time.time() - token_time > self.token_lifetime:
            del self.csrf_tokens[token]
            return False

        return True

    def generate_csrf_token(self) -> str:
        """Generate a new CSRF token."""
        token = secrets.token_urlsafe(32)
        self.csrf_tokens[token] = time.time()
        return token

    def revoke_csrf_token(self, token: str) -> bool:
        """Revoke a CSRF token."""
        if token in self.csrf_tokens:
            del self.csrf_tokens[token]
            return True
        return False

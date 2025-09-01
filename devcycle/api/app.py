"""
Main FastAPI application for DevCycle API.

This module provides the core FastAPI application with middleware,
CORS configuration, and basic endpoints.
"""

import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from ..core.config import get_config
from ..core.logging import get_logger


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers[
            "Permissions-Policy"
        ] = "geolocation=(), microphone=(), camera=()"

        # Remove server information
        if "server" in response.headers:
            del response.headers["server"]

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware for auth endpoints."""

    def __init__(
        self, app: ASGIApp, max_requests: int = 10, window_seconds: int = 60
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only apply rate limiting to auth endpoints
        if request.url.path.startswith("/api/v1/auth"):
            client_ip = request.client.host if request.client else "unknown"
            current_time = time.time()

            # Clean old entries
            self.requests = {
                ip: timestamps
                for ip, timestamps in self.requests.items()
                if current_time - timestamps[-1] < self.window_seconds
            }

            # Initialize client tracking if not exists
            if client_ip not in self.requests:
                self.requests[client_ip] = []

            # Remove old timestamps for this client
            self.requests[client_ip] = [
                ts
                for ts in self.requests[client_ip]
                if current_time - ts < self.window_seconds
            ]

            # Check rate limit
            if len(self.requests[client_ip]) >= self.max_requests:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Rate limit exceeded",
                        "message": (
                            f"Too many requests. Limit: {self.max_requests} "
                            f"per {self.window_seconds} seconds"
                        ),
                    },
                )

            # Record request
            self.requests[client_ip].append(current_time)

        response = await call_next(request)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger = get_logger("api.app")
    logger.info("Starting DevCycle API server...")

    # Load configuration
    config = get_config()
    logger.info(f"Loaded configuration for environment: {config.environment}")

    yield

    # Shutdown
    logger.info("Shutting down DevCycle API server...")


def create_app(environment: Optional[str] = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        environment: Optional environment override. If provided, this will
                    override the environment from config for this app instance.
    """
    config = get_config()

    # Override environment if specified
    if environment:
        config.environment = environment

    app = FastAPI(
        title="DevCycle API",
        description="RESTful API for DevCycle AI agent system",
        version="0.1.0",
        docs_url="/docs" if config.environment != "production" else None,
        redoc_url="/redoc" if config.environment != "production" else None,
        lifespan=lifespan,
    )

    # Add middleware
    _setup_middleware(app, config)

    # Add exception handlers
    _setup_exception_handlers(app)

    # Add routes
    _setup_routes(app)

    return app


def _setup_middleware(app: FastAPI, config: Any) -> None:
    """Setup application middleware."""
    # Security headers middleware (add first to ensure headers are set)
    app.add_middleware(SecurityHeadersMiddleware)

    # Rate limiting middleware for auth endpoints

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_credentials=config.api.cors_credentials,
        allow_methods=config.api.cors_methods,
        allow_headers=config.api.cors_headers,
    )

    # Gzip compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next: Any) -> Any:
        logger = get_logger("api.middleware")
        start_time = time.time()

        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        response = await call_next(request)

        # Log response
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} " f"took {process_time:.4f}s")

        return response


def _setup_exception_handlers(app: FastAPI) -> None:
    """Setup exception handlers."""
    logger = get_logger("api.exceptions")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "errors": exc.errors(),
                "path": request.url.path,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")

        # Special handling for auth endpoints to include success field
        if request.url.path.startswith("/api/v1/auth") and exc.status_code == 401:
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "success": False,
                    "detail": exc.detail,
                    "path": request.url.path,
                    "message": "Authentication failed",
                },
            )

        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "path": request.url.path},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error", "path": request.url.path},
        )


def _setup_routes(app: FastAPI) -> None:
    """Setup application routes."""
    from fastapi_users import schemas

    from ..core.auth.fastapi_users import auth_backend, fastapi_users
    from .auth import auth_router
    from .routes import agents, health, messages

    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(agents.router, prefix="/api/v1", tags=["agents"])
    app.include_router(messages.router, prefix="/api/v1", tags=["messages"])
    app.include_router(auth_router, prefix="/api/v1")

    # Include FastAPI Users routers
    app.include_router(
        fastapi_users.get_auth_router(auth_backend),
        prefix="/api/v1/auth/jwt",
        tags=["auth"],
    )
    # Registration disabled - users must be created by admin
    # app.include_router(
    #     fastapi_users.get_register_router(schemas.BaseUserCreate, schemas.BaseUser),
    #     prefix="/api/v1/auth",
    #     tags=["auth"],
    # )
    app.include_router(
        fastapi_users.get_users_router(schemas.BaseUser, schemas.BaseUserUpdate),
        prefix="/api/v1/auth",
        tags=["auth"],
    )


# Create the main application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run(
        "devcycle.api.app:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.reload and config.environment == "development",
        log_level="info",
    )

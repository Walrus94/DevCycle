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
from .middleware.csrf_protection import CSRFProtectionMiddleware
from .versioning import get_version_info


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

        # CORS-specific security headers
        origin = request.headers.get("origin")
        if origin:
            # Only set CORS headers for actual cross-origin requests
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
            response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
            response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"

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
        logger = get_logger(__name__)
        logger.debug(f"🔍 RateLimitMiddleware processing {request.method} {request.url}")

        # Only apply rate limiting to auth endpoints
        if request.url.path.startswith("/api/v1/auth"):
            logger.debug("🔍 Auth endpoint detected, applying rate limiting...")
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
                logger.warning(f"❌ Rate limit exceeded for {client_ip}")
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
            logger.debug(f"✅ Rate limit check passed for {client_ip}")
        else:
            logger.debug("✅ Non-auth endpoint, skipping rate limiting")

        logger.debug("🔍 RateLimitMiddleware calling next middleware...")
        response = await call_next(request)
        logger.debug(
            f"✅ RateLimitMiddleware completed, response status: {response.status_code}"
        )
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
        from ..core.config import Environment

        config.environment = Environment(environment)

    app = FastAPI(
        title="DevCycle API",
        description="""
        ## DevCycle AI Agent System API

        A comprehensive RESTful API for managing AI agents, handling inter-agent
        communication, and monitoring system health in the DevCycle platform.

        ### Features
        - **Agent Management**: Register, monitor, and manage AI agents
        - **Message Routing**: Send messages between agents with intelligent routing
        - **Health Monitoring**: Comprehensive health checks and system monitoring
        - **Authentication**: Secure JWT-based authentication
        - **Versioning**: API versioning with backward compatibility

        ### Authentication
        Most endpoints require authentication. Use the `/auth/jwt/login` endpoint to
        obtain a JWT token, then include it in the `Authorization` header as
        `Bearer <token>`.

        ### Rate Limiting
        Authentication endpoints are rate-limited to 10 requests per minute per IP
        address.

        ### Support
        For more information, see the [API Documentation](../docs/api-documentation.md).
        """,
        version="0.1.0",
        docs_url="/docs" if config.environment != "production" else None,
        redoc_url="/redoc" if config.environment != "production" else None,
        lifespan=lifespan,
        contact={
            "name": "DevCycle Support",
            "email": "support@devcycle.ai",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
    )

    # Add version information endpoint
    @app.get("/api/version", tags=["version"])
    async def get_api_version_info() -> Dict[str, Any]:
        """Get API version information."""
        return get_version_info()

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

    # XSS Protection middleware - REMOVED: Using FastAPI built-in validation instead
    # app.add_middleware(XSSProtectionMiddleware, strict_mode=True)

    # CSRF Protection middleware (only in production)
    if config.environment == "production":
        app.add_middleware(
            CSRFProtectionMiddleware, secret_key=config.security.secret_key
        )

    # Rate limiting middleware for auth endpoints
    app.add_middleware(RateLimitMiddleware, max_requests=10, window_seconds=60)

    # CORS middleware with environment-specific configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins_resolved,
        allow_credentials=config.cors_credentials_resolved,
        allow_methods=config.cors_methods_resolved,
        allow_headers=config.cors_headers_resolved,
        expose_headers=config.cors_expose_headers_resolved,
        max_age=config.api.cors_max_age,
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

        logger.debug("🔍 LoggingMiddleware calling next middleware...")
        response = await call_next(request)
        logger.debug(f"✅ LoggingMiddleware received response: {response.status_code}")

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

    # Create versioned routers (for future use)
    # health_router = create_versioned_router(APIVersion.V1, tags=["health"])
    # agents_router = create_versioned_router(APIVersion.V1, tags=["agents"])
    # messages_router = create_versioned_router(APIVersion.V1, tags=["messages"])
    # auth_router_v1 = create_versioned_router(APIVersion.V1, tags=["auth"])
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

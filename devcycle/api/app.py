"""
Main FastAPI application for DevCycle API.

This module provides the core FastAPI application with middleware,
CORS configuration, and basic endpoints.
"""

import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..core.config import get_config
from ..core.logging import get_logger


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


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = get_config()

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
    from .auth import auth_router
    from .routes import agents, health, messages

    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(agents.router, prefix="/api/v1", tags=["agents"])
    app.include_router(messages.router, prefix="/api/v1", tags=["messages"])
    app.include_router(auth_router, prefix="/api/v1")


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

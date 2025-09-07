"""
Performance monitoring decorators.

This module provides decorators for automatic performance metrics collection
on Redis operations and ACP service methods.
"""

import asyncio
import functools
import time
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Dict, Optional

from ...logging import get_logger

logger = get_logger(__name__)


def monitor_redis_operation(
    operation_name: Optional[str] = None,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    Monitor Redis operations.

    Args:
        operation_name: Name of the operation (defaults to function name)
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get performance monitor from first argument (usually self)
            monitor = None
            if args and hasattr(args[0], "performance_monitor"):
                monitor = args[0].performance_monitor
            elif "performance_monitor" in kwargs:
                monitor = kwargs["performance_monitor"]

            if not monitor:
                # No monitoring available, just execute function
                return await func(*args, **kwargs)

            # Extract key from arguments (usually first argument after self)
            key = str(args[1]) if len(args) > 1 else "unknown"
            op_name = operation_name or func.__name__

            start_time = time.time()
            success = True
            error = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                monitor.record_redis_operation(
                    op_name, key, duration_ms, success, error
                )

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get performance monitor from first argument (usually self)
            monitor = None
            if args and hasattr(args[0], "performance_monitor"):
                monitor = args[0].performance_monitor
            elif "performance_monitor" in kwargs:
                monitor = kwargs["performance_monitor"]

            if not monitor:
                # No monitoring available, just execute function
                return func(*args, **kwargs)

            # Extract key from arguments (usually first argument after self)
            key = str(args[1]) if len(args) > 1 else "unknown"
            op_name = operation_name or func.__name__

            start_time = time.time()
            success = True
            error = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                monitor.record_redis_operation(
                    op_name, key, duration_ms, success, error
                )

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def monitor_acp_operation(
    service_name: str, operation_name: Optional[str] = None
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    Monitor ACP service operations.

    Args:
        service_name: Name of the ACP service
        operation_name: Name of the operation (defaults to function name)
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get performance monitor from first argument (usually self)
            monitor = None
            if args and hasattr(args[0], "performance_monitor"):
                monitor = args[0].performance_monitor
            elif "performance_monitor" in kwargs:
                monitor = kwargs["performance_monitor"]

            if not monitor:
                # No monitoring available, just execute function
                return await func(*args, **kwargs)

            op_name = operation_name or func.__name__

            start_time = time.time()
            success = True
            error = None
            metadata = {}

            try:
                result = await func(*args, **kwargs)

                # Extract metadata from result if possible
                if hasattr(result, "metadata"):
                    metadata = result.metadata
                elif isinstance(result, dict) and "metadata" in result:
                    metadata = result["metadata"]

                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                monitor.record_acp_operation(
                    service_name, op_name, duration_ms, success, error, metadata
                )

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get performance monitor from first argument (usually self)
            monitor = None
            if args and hasattr(args[0], "performance_monitor"):
                monitor = args[0].performance_monitor
            elif "performance_monitor" in kwargs:
                monitor = kwargs["performance_monitor"]

            if not monitor:
                # No monitoring available, just execute function
                return func(*args, **kwargs)

            op_name = operation_name or func.__name__

            start_time = time.time()
            success = True
            error = None
            metadata = {}

            try:
                result = func(*args, **kwargs)

                # Extract metadata from result if possible
                if hasattr(result, "metadata"):
                    metadata = result.metadata
                elif isinstance(result, dict) and "metadata" in result:
                    metadata = result["metadata"]

                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                monitor.record_acp_operation(
                    service_name, op_name, duration_ms, success, error, metadata
                )

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@asynccontextmanager
async def monitor_operation(
    monitor: Any,
    service: str,
    operation: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Context manager for monitoring operations.

    Args:
        monitor: Performance monitor instance
        service: Service name
        operation: Operation name
        metadata: Optional metadata
    """
    start_time = time.time()
    success = True
    error = None

    try:
        yield
    except Exception as e:
        success = False
        error = str(e)
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        monitor.record_acp_operation(
            service, operation, duration_ms, success, error, metadata
        )


def monitor_method_calls(service_name: str) -> Callable[[type], type]:
    """
    Class decorator to automatically monitor all method calls.

    Args:
        service_name: Name of the service
    """

    def decorator(cls: type) -> type:
        # Get all methods from the class
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)

            # Skip private methods and properties
            if attr_name.startswith("_") or not callable(attr):
                continue

            # Skip if already decorated
            if hasattr(attr, "_monitored"):
                continue

            # Apply monitoring decorator
            monitored_attr = monitor_acp_operation(service_name)(attr)
            # Mark as monitored using a different approach
            setattr(monitored_attr, "_monitored", True)
            setattr(cls, attr_name, monitored_attr)

        return cls

    return decorator

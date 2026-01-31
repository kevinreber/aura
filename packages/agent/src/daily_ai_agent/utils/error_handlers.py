"""Centralized error handling utilities for the Daily AI Agent."""

from typing import Any, Callable, TypeVar, Optional
from functools import wraps
import asyncio
from loguru import logger


# Custom exception types for better error categorization
class APIError(Exception):
    """Base exception for API-related errors."""

    def __init__(self, message: str, status_code: int = 500, details: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class MCPError(APIError):
    """Exception for MCP server communication errors."""

    def __init__(self, message: str, status_code: int = 503, details: Optional[dict] = None):
        super().__init__(f"MCP Server Error: {message}", status_code, details)


class ToolError(APIError):
    """Exception for tool execution errors."""

    def __init__(self, tool_name: str, message: str, details: Optional[dict] = None):
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' error: {message}", 500, details)


class ValidationError(APIError):
    """Exception for input validation errors."""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[dict] = None):
        self.field = field
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(f"Validation error: {message}", 400, error_details)


def handle_api_error(error: Exception) -> tuple[dict, int]:
    """
    Convert an exception to a standardized API error response.

    Args:
        error: The exception to handle

    Returns:
        Tuple of (error_dict, status_code)
    """
    if isinstance(error, APIError):
        return {
            "error": error.message,
            "status_code": error.status_code,
            "details": error.details,
        }, error.status_code
    elif isinstance(error, ValueError):
        return {
            "error": f"Invalid value: {str(error)}",
            "status_code": 400,
            "details": {},
        }, 400
    else:
        logger.error(f"Unhandled error: {type(error).__name__}: {error}")
        return {
            "error": "Internal server error",
            "status_code": 500,
            "details": {"type": type(error).__name__},
        }, 500


T = TypeVar("T")


def safe_async_call(
    func: Callable[..., T],
    *args: Any,
    default: Optional[T] = None,
    error_prefix: str = "Error",
    **kwargs: Any,
) -> T:
    """
    Safely execute an async function and return a default value on error.

    Args:
        func: The async function to call
        *args: Positional arguments for the function
        default: Default value to return on error
        error_prefix: Prefix for error log messages
        **kwargs: Keyword arguments for the function

    Returns:
        The function result or the default value on error
    """
    try:
        if asyncio.iscoroutinefunction(func):
            return asyncio.run(func(*args, **kwargs))
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"{error_prefix}: {e}")
        return default


def log_errors(error_prefix: str = "Error"):
    """
    Decorator to log errors from async functions.

    Args:
        error_prefix: Prefix for error log messages
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{error_prefix} in {func.__name__}: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{error_prefix} in {func.__name__}: {e}")
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator

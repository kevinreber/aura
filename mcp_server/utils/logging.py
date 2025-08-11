"""Structured logging configuration for the MCP server."""

import sys
from loguru import logger
from typing import Dict, Any
import json

from ..config import get_settings


def setup_logging() -> None:
    """Configure structured logging with Loguru."""
    settings = get_settings()
    
    # Remove default handler
    logger.remove()
    
    # Configure format based on environment
    if settings.environment == "development":
        # Pretty format for development
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "{message}"
        )
    else:
        # JSON format for production
        format_string = "{time} | {level} | {name}:{function}:{line} | {message}"
    
    # Add console handler
    logger.add(
        sys.stdout,
        format=format_string,
        level=settings.log_level,
        colorize=settings.environment == "development",
        serialize=settings.environment != "development"
    )
    
    # Add file handler for production
    if settings.environment == "production":
        logger.add(
            "logs/mcp_server.log",
            format=format_string,
            level="INFO",
            rotation="10 MB",
            retention="7 days",
            serialize=True
        )


def get_logger(name: str = "mcp_server"):
    """Get a logger instance with the given name."""
    return logger.bind(name=name)


def log_tool_call(tool_name: str, inputs: Dict[str, Any], duration_ms: float = None) -> None:
    """Log a tool call with structured data."""
    log_data = {
        "event": "tool_call",
        "tool_name": tool_name,
        "inputs": inputs,
    }
    
    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms
    
    logger.info("Tool call executed", extra=log_data)


def log_api_call(url: str, method: str, status_code: int, duration_ms: float) -> None:
    """Log an external API call with structured data."""
    log_data = {
        "event": "api_call",
        "url": url,
        "method": method,
        "status_code": status_code,
        "duration_ms": duration_ms
    }
    
    logger.info("External API call", extra=log_data)

"""LangSmith tracing configuration and utilities."""

import os
from loguru import logger
from typing import Optional


def setup_langsmith_tracing(
    api_key: Optional[str] = None,
    project: str = "aura",
    endpoint: str = "https://api.smith.langchain.com",
    enabled: bool = False,
) -> bool:
    """
    Configure LangSmith tracing via environment variables.

    LangChain automatically picks up these environment variables,
    so we just need to set them before any LangChain imports.

    Args:
        api_key: LangSmith API key (ls_xxx)
        project: Project name in LangSmith
        endpoint: LangSmith API endpoint
        enabled: Whether tracing is enabled

    Returns:
        True if tracing was enabled, False otherwise
    """
    if not enabled:
        logger.debug("LangSmith tracing is disabled")
        return False

    if not api_key:
        logger.warning("LangSmith tracing enabled but no API key provided")
        return False

    # Set environment variables for LangChain to pick up
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGCHAIN_PROJECT"] = project
    os.environ["LANGCHAIN_ENDPOINT"] = endpoint

    logger.info(f"LangSmith tracing enabled for project: {project}")
    logger.debug(f"LangSmith endpoint: {endpoint}")

    return True


def disable_langsmith_tracing() -> None:
    """Disable LangSmith tracing by clearing environment variables."""
    os.environ.pop("LANGCHAIN_TRACING_V2", None)
    os.environ.pop("LANGCHAIN_API_KEY", None)
    os.environ.pop("LANGCHAIN_PROJECT", None)
    os.environ.pop("LANGCHAIN_ENDPOINT", None)

    logger.debug("LangSmith tracing disabled")


def is_tracing_active() -> bool:
    """Check if LangSmith tracing is currently active."""
    return os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true" and bool(
        os.environ.get("LANGCHAIN_API_KEY")
    )

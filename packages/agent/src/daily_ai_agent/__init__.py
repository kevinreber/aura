"""Morning Routine AI Agent - Intelligent orchestration of MCP server tools."""

__version__ = "0.1.0"
__author__ = "Kevin Reber"


def main():
    """Lazy import of main to avoid loading langchain at module level."""
    from .main import main as _main
    return _main()


# Export main entry point
__all__ = ["main"]

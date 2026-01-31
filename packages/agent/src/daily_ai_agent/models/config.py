"""Configuration management for the AI agent."""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List
import os


# Default CORS origins for development
DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
]

# Default CORS origins for production (can be overridden via env)
PRODUCTION_CORS_ORIGINS = [
    "https://daily-agent-ui.vercel.app",
    "https://web-production-66f9.up.railway.app",
    "https://web-production-f80730.up.railway.app",
]


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # AI Model Configuration
    openai_api_key: str = ""
    anthropic_api_key: Optional[str] = None
    default_llm: str = "openai"

    # MCP Server Connection
    mcp_server_url: str = "http://localhost:8000"
    mcp_server_timeout: int = 45

    # Agent Configuration
    log_level: str = "INFO"
    enable_memory: bool = True
    debug: bool = False
    environment: str = "development"

    # Web Server Configuration
    host: str = "0.0.0.0"
    port: int = 8001

    # CORS Configuration - can be set via ALLOWED_ORIGINS env var (comma-separated)
    allowed_origins_env: Optional[str] = None
    rate_limit_per_minute: int = 60

    # User Preferences
    user_name: str = "Kevin"
    user_location: str = "San Francisco"
    default_commute_origin: str = "Home"
    default_commute_destination: str = "Office"

    class Config:
        env_file = ".env"
        case_sensitive = False
        # Map environment variables to field names
        fields = {
            "allowed_origins_env": {"env": "ALLOWED_ORIGINS"},
        }

    @property
    def allowed_origins(self) -> List[str]:
        """
        Get allowed CORS origins.

        Priority:
        1. ALLOWED_ORIGINS environment variable (comma-separated)
        2. Default origins based on environment
        """
        if self.allowed_origins_env:
            # Parse comma-separated origins from environment
            origins = [
                origin.strip()
                for origin in self.allowed_origins_env.split(",")
                if origin.strip()
            ]
            return origins

        # Use default origins based on environment
        if self.environment == "production":
            return PRODUCTION_CORS_ORIGINS + DEFAULT_CORS_ORIGINS
        return DEFAULT_CORS_ORIGINS

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == "testing"

    def __init__(self, **kwargs):
        # Handle environment variables for debug and environment
        if "debug" not in kwargs:
            kwargs["debug"] = os.getenv("DEBUG", "false").lower() == "true"
        if "environment" not in kwargs:
            kwargs["environment"] = os.getenv("ENVIRONMENT", "development")
        if "host" not in kwargs:
            kwargs["host"] = os.getenv("HOST", "0.0.0.0")
        if "port" not in kwargs:
            kwargs["port"] = int(os.getenv("PORT", "8001"))
        if "allowed_origins_env" not in kwargs:
            kwargs["allowed_origins_env"] = os.getenv("ALLOWED_ORIGINS")

        super().__init__(**kwargs)

        # Validate required API keys in production
        if self.is_production:
            if self.default_llm == "openai" and not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when using OpenAI in production")
            if self.default_llm == "anthropic" and not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic in production")


# Global settings instance (lazy initialization)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance (useful for testing)."""
    global _settings
    _settings = None

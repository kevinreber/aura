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

# Default CORS origins for production (can be extended via ALLOWED_ORIGINS env var)
PRODUCTION_CORS_ORIGINS = [
    "https://daily-agent-ui.vercel.app",
    "https://aura-six-sable.vercel.app",
]


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # AI Model Configuration
    openai_api_key: str = ""
    anthropic_api_key: Optional[str] = None
    llm_provider: str = "openai"  # "openai" or "anthropic"
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    llm_temperature: float = 0.1

    # LangSmith Tracing (optional)
    langchain_tracing_v2: bool = False
    langchain_api_key: Optional[str] = None
    langchain_project: str = "aura"
    langchain_endpoint: str = "https://api.smith.langchain.com"

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

    # Auth: shared secret with the UI proxy (the only legitimate caller).
    # If set, requests to protected endpoints must include the matching
    # X-Internal-Auth header. The UI's session layer is the source of truth
    # for the user's verified Google identity, forwarded in X-User-Email.
    internal_auth_secret: Optional[str] = None

    # Auth: allowlist of Google email addresses permitted to use the app.
    # Comma-separated. Empty/unset means fail-closed (nobody allowed) when
    # internal_auth_secret is set, so always configure these together.
    allowed_emails_env: Optional[str] = None

    # User Preferences
    user_name: str = "Kevin"
    user_location: str = "San Francisco"
    default_commute_origin: str = "Home"
    default_commute_destination: str = "Office"
    # Full street address for per-event commute calculations. Sourced from
    # the same HOME_ADDRESS env var the server reads — the briefing builder
    # uses it as the origin for the first located event of the day.
    home_address: str = ""
    # Used to compute "tomorrow" in user-local time. Single-user app, so we
    # default to PT; the agent server itself runs UTC in Docker.
    user_timezone: str = "America/Los_Angeles"

    class Config:
        env_file = ".env"
        case_sensitive = False
        # Map environment variables to field names
        fields = {
            "allowed_origins_env": {"env": "ALLOWED_ORIGINS"},
            "allowed_emails_env": {"env": "ALLOWED_EMAILS"},
            "internal_auth_secret": {"env": "INTERNAL_AUTH_SECRET"},
        }

    @property
    def allowed_origins(self) -> List[str]:
        """
        Get allowed CORS origins.

        In production: includes Vercel defaults + any extras from ALLOWED_ORIGINS env var.
        In development: localhost origins + any extras from ALLOWED_ORIGINS env var.
        """
        if self.environment == "production":
            origins = PRODUCTION_CORS_ORIGINS + DEFAULT_CORS_ORIGINS
        else:
            origins = DEFAULT_CORS_ORIGINS

        # ALLOWED_ORIGINS env var adds extra origins (comma-separated)
        if self.allowed_origins_env:
            extras = [
                origin.strip()
                for origin in self.allowed_origins_env.split(",")
                if origin.strip()
            ]
            origins = origins + extras

        return origins

    @property
    def allowed_emails(self) -> List[str]:
        """Lowercased list of Google emails allowed to use the app."""
        if not self.allowed_emails_env:
            return []
        return [
            email.strip().lower()
            for email in self.allowed_emails_env.split(",")
            if email.strip()
        ]

    @property
    def auth_enabled(self) -> bool:
        """Auth is enforced when a shared secret is configured."""
        return bool(self.internal_auth_secret)

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

    @property
    def is_tracing_enabled(self) -> bool:
        """Check if LangSmith tracing is enabled and configured."""
        return self.langchain_tracing_v2 and bool(self.langchain_api_key)

    @property
    def effective_llm_provider(self) -> str:
        """Get the effective LLM provider based on config and available API keys."""
        # If anthropic is requested but no key, fall back to openai
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            return "openai"
        # If openai is requested but no key, try anthropic
        if self.llm_provider == "openai" and not self.openai_api_key:
            if self.anthropic_api_key:
                return "anthropic"
        return self.llm_provider

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
        if "allowed_emails_env" not in kwargs:
            kwargs["allowed_emails_env"] = os.getenv("ALLOWED_EMAILS")
        if "internal_auth_secret" not in kwargs:
            kwargs["internal_auth_secret"] = os.getenv("INTERNAL_AUTH_SECRET")

        super().__init__(**kwargs)

        # Validate required API keys in production
        if self.is_production:
            if self.llm_provider == "openai" and not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when using OpenAI in production")
            if self.llm_provider == "anthropic" and not self.anthropic_api_key:
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

"""Configuration management for the MCP server."""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Core MCP Server Settings  
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = "INFO"
    host: str = os.getenv("HOST", "0.0.0.0")  # Default to 0.0.0.0 for production compatibility
    port: int = int(os.getenv("PORT", "8000"))  # Railway provides PORT env var
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"  # Default to False for production

    # External API Keys (for tools)
    weather_api_key: str = ""  # OpenWeatherMap API key
    google_maps_api_key: str = ""  # Google Maps API key
    alpha_vantage_api_key: str = ""  # Alpha Vantage API key for financial data
    
    # Google Calendar Integration
    google_calendar_credentials_path: Optional[str] = None
    google_calendar_credentials_json: Optional[str] = None  # For production env var
    
    # Personal Addresses for Commute Routing
    home_address: str = ""  # Full home address for accurate routing
    work_address: str = ""  # Full work address for accurate routing
    
    # Caltrain Stations for Transit Routing
    home_caltrain_station: str = "South San Francisco"  # Nearest Caltrain station to home
    work_caltrain_station: str = "Mountain View"  # Nearest Caltrain station to work
    
    # Optional todo integration (e.g., Todoist, Any.do)
    todoist_api_key: Optional[str] = None

    # Weekend Orchestrator API keys (optional — tools fall back to mock data)
    ticketmaster_api_key: Optional[str] = None  # Concert listings (Discovery API)
    outdooractive_api_key: Optional[str] = None  # Trail data (falls back to Google Places)

    # Brain-vault integration (optional — when unset, vault tools return a
    # "vault not configured" error rather than crashing the server).
    vault_root: Optional[str] = None  # Filesystem path to the markdown vault root
    # Remote vault sync (Phase 2). Both unset = no sync; both set = clone on
    # boot + periodic pull. The token is a GitHub fine-grained PAT scoped to
    # the brain-vault repo with Contents: Read-only.
    vault_git_url: Optional[str] = None  # https://github.com/owner/brain-vault.git
    vault_git_token: Optional[str] = None  # Fine-grained PAT, injected at URL build time

    # Caching (optional)
    redis_url: Optional[str] = None
    cache_ttl: int = 300  # 5 minutes default

    # Security & CORS
    secret_key: str = "your-secret-key-change-in-production"
    # Shared-secret auth for internal callers (Aura's Agent, Navi). When set,
    # every request except /health must present a matching X-Internal-Auth
    # header; unset means open (local dev only). Mirrors the Agent's UI->Agent
    # scheme. BaseSettings reads INTERNAL_AUTH_SECRET from the environment.
    internal_auth_secret: Optional[str] = None
    allowed_origins: List[str] = [
        "http://localhost:3000", 
        "http://localhost:5173", 
        "http://localhost:5174",
        "https://daily-agent-ui.vercel.app",
        "https://web-production-66f9.up.railway.app"
    ]
    
    # Rate limiting
    rate_limit_per_minute: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Validate required API keys and addresses in production
        if self.environment == "production":
            if not self.weather_api_key:
                raise ValueError("WEATHER_API_KEY is required in production")
            if not self.google_maps_api_key:
                raise ValueError("GOOGLE_MAPS_API_KEY is required in production")
            if not self.home_address:
                raise ValueError("HOME_ADDRESS is required in production for accurate commute routing")
            if not self.work_address:
                raise ValueError("WORK_ADDRESS is required in production for accurate commute routing")


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings

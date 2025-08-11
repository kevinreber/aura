"""Configuration management for the MCP server."""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Core MCP Server Settings
    environment: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", "8000"))  # Railway provides PORT env var
    debug: bool = False

    # External API Keys (for tools)
    weather_api_key: str = ""  # OpenWeatherMap API key
    google_maps_api_key: str = ""  # Google Maps API key
    
    # Optional calendar integration
    google_calendar_credentials_path: Optional[str] = None
    
    # Optional todo integration (e.g., Todoist, Any.do)
    todoist_api_key: Optional[str] = None

    # Caching (optional)
    redis_url: Optional[str] = None
    cache_ttl: int = 300  # 5 minutes default

    # Security & CORS
    secret_key: str = "your-secret-key-change-in-production"
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Rate limiting
    rate_limit_per_minute: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Validate required API keys in production
        if self.environment == "production":
            if not self.weather_api_key:
                raise ValueError("WEATHER_API_KEY is required in production")
            if not self.google_maps_api_key:
                raise ValueError("GOOGLE_MAPS_API_KEY is required in production")


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings

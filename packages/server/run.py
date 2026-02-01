#!/usr/bin/env python3
"""Development server entry point for the MCP server."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """Run the development server with uvicorn."""
    import uvicorn

    # Load environment variables from .env file if it exists
    env_file = project_root / ".env"
    if env_file.exists():
        print(f"Loading environment from {env_file}")
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
        except ImportError:
            print("python-dotenv not installed, skipping .env file loading")

    from mcp_server.config import get_settings
    settings = get_settings()

    # Determine public URL for Railway vs local development
    railway_url = os.getenv("RAILWAY_STATIC_URL") or os.getenv("RAILWAY_PUBLIC_DOMAIN")

    if settings.environment == "production" and railway_url:
        # Use Railway-provided URL
        public_url = railway_url if railway_url.startswith(('http://', 'https://')) else f"https://{railway_url}"
        if public_url.endswith(":"):
            public_url = public_url.rstrip(":")
    elif settings.environment == "production":
        # Fallback for production without Railway URL
        public_url = "https://web-production-66f9.up.railway.app"
    else:
        # Local development
        public_url = f"http://{settings.host}:{settings.port}"

    print(f"🚀 Starting MCP Server on {settings.host}:{settings.port}")
    print(f"📊 Environment: {settings.environment}")
    print(f"🔧 Debug mode: {settings.debug}")
    print(f"📝 Log level: {settings.log_level}")
    print()
    print("Available endpoints:")
    print(f"  📋 Health check: {public_url}/health")
    print(f"  📚 Swagger UI:   {public_url}/docs")
    print(f"  📖 ReDoc:        {public_url}/redoc")
    print(f"  🔌 MCP SSE:      {public_url}/mcp/sse")
    print(f"  🛠️  List tools:   {public_url}/tools")
    print(f"  🌤️  Weather:      {public_url}/tools/weather.get_daily")
    print(f"  🚗  Mobility:     {public_url}/tools/mobility.get_commute")
    print(f"  📅  Calendar:     {public_url}/tools/calendar.list_events")
    print(f"  📅+ Create Event: {public_url}/tools/calendar.create_event")
    print(f"  ✅📋 List Todos:  {public_url}/tools/todo.list")
    print(f"  ✅➕ Create Todo: {public_url}/tools/todo.create")
    print(f"  💰  Financial:    {public_url}/tools/financial.get_data")
    print()

    try:
        uvicorn.run(
            "mcp_server.app:app",
            host=settings.host,
            port=settings.port,
            reload=settings.environment == "development",
            log_level=settings.log_level.lower(),
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down MCP Server...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

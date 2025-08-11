#!/usr/bin/env python3
"""Development server entry point for the MCP server."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.app import create_app
from mcp_server.config import get_settings


def main():
    """Run the development server."""
    # Load environment variables from .env file if it exists
    env_file = project_root / ".env"
    if env_file.exists():
        print(f"Loading environment from {env_file}")
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
        except ImportError:
            print("python-dotenv not installed, skipping .env file loading")
    
    # Create the Flask app
    app = create_app()
    settings = get_settings()
    
    print(f"🚀 Starting MCP Server on {settings.host}:{settings.port}")
    print(f"📊 Environment: {settings.environment}")
    print(f"🔧 Debug mode: {settings.debug}")
    print(f"📝 Log level: {settings.log_level}")
    print()
    print("Available endpoints:")
    print(f"  📋 Health check: http://{settings.host}:{settings.port}/health")
    print(f"  🛠️  List tools:   http://{settings.host}:{settings.port}/tools")
    print(f"  🌤️  Weather:      http://{settings.host}:{settings.port}/tools/weather.get_daily")
    print(f"  🚗  Mobility:     http://{settings.host}:{settings.port}/tools/mobility.get_commute")
    print(f"  📅  Calendar:     http://{settings.host}:{settings.port}/tools/calendar.list_events")
    print(f"  ✅  Todos:        http://{settings.host}:{settings.port}/tools/todo.list")
    print(f"  💰  Financial:    http://{settings.host}:{settings.port}/tools/financial.get_data")
    print()
    
    try:
        app.run(
            host=settings.host,
            port=settings.port,
            debug=settings.debug,
            use_reloader=settings.environment == "development"
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down MCP Server...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

"""Entry point for running the AI agent as a web API server."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .api import create_app
from .models.config import get_settings


def main():
    """Run the API server."""
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
    
    print(f"🚀 Starting AI Agent API Server")
    print(f"📊 Environment: {settings.environment}")
    print(f"🔧 Debug mode: {settings.debug}")
    print(f"📝 Log level: {settings.log_level}")
    print(f"🤖 AI Features: {'✅ Enabled' if settings.openai_api_key else '❌ Disabled (no OpenAI key)'}")
    print(f"🌐 MCP Server: {settings.mcp_server_url}")
    print()
    print("Available endpoints:")
    print(f"  📋 Health check:     http://{settings.host}:{settings.port}/health")
    print(f"  📚 Swagger UI:       http://{settings.host}:{settings.port}/docs")
    print(f"  🗂️  List tools:       http://{settings.host}:{settings.port}/tools")
    print(f"  💬 Chat API:         POST http://{settings.host}:{settings.port}/chat")
    print(f"  📅 Briefing API:     http://{settings.host}:{settings.port}/briefing")
    print(f"  🌤️  Weather API:      http://{settings.host}:{settings.port}/tools/weather")
    print(f"  ✅ Todos API:        http://{settings.host}:{settings.port}/tools/todos")
    print(f"  📅 Calendar API:     http://{settings.host}:{settings.port}/tools/calendar")
    print(f"  🚗 Commute API:      http://{settings.host}:{settings.port}/tools/commute")
    print()
    
    try:
        app.run(
            host=settings.host,
            port=settings.port,
            debug=settings.debug,
            use_reloader=settings.environment == "development"
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down AI Agent API Server...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

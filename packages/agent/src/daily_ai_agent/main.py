"""Main entry point for the AI agent CLI."""

import asyncio
import typer
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from loguru import logger

from .services.mcp_client import MCPClient
from .models.config import get_settings
from .agent.orchestrator import AgentOrchestrator

app = typer.Typer(help="🤖 Morning Routine AI Agent")
console = Console()


@app.command()
def health():
    """Check if the MCP server is healthy."""
    async def check():
        client = MCPClient()
        is_healthy = await client.health_check()
        
        if is_healthy:
            console.print("✅ MCP Server is healthy!", style="green")
        else:
            console.print("❌ MCP Server is not responding", style="red")
    
    asyncio.run(check())


@app.command()
def weather(location: str = None):
    """Get weather forecast for a location."""
    async def get_weather():
        settings = get_settings()
        client = MCPClient()
        
        target_location = location or settings.user_location
        
        try:
            weather_data = await client.get_weather(target_location)
            
            # Display weather in a nice format
            table = Table(title=f"🌤️ Weather for {weather_data.get('location', target_location)}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="magenta")
            
            table.add_row("High", f"{weather_data.get('temp_hi')}°F")
            table.add_row("Low", f"{weather_data.get('temp_lo')}°F")
            table.add_row("Precipitation", f"{weather_data.get('precip_chance', 0)}%")
            table.add_row("Summary", weather_data.get('summary', 'N/A'))
            table.add_row("Date", weather_data.get('date', 'N/A'))
            
            console.print(table)
            
        except Exception as e:
            console.print(f"❌ Error getting weather: {e}", style="red")
    
    asyncio.run(get_weather())


@app.command()
def todos(bucket: str = "work"):
    """Get todo items from a bucket."""
    async def get_todos():
        client = MCPClient()
        
        try:
            todos_data = await client.get_todos(bucket)
            
            table = Table(title=f"✅ {bucket.title()} Todos")
            table.add_column("Task", style="cyan")
            table.add_column("Priority", style="yellow")
            table.add_column("Due Date", style="green")
            
            for item in todos_data.get('items', []):
                table.add_row(
                    item.get('title', 'N/A'),
                    item.get('priority', 'N/A'),
                    item.get('due_date', 'N/A')
                )
            
            console.print(table)
            console.print(f"📊 Total: {todos_data.get('total_items', 0)} items, {todos_data.get('pending_count', 0)} pending")
            
        except Exception as e:
            console.print(f"❌ Error getting todos: {e}", style="red")
    
    asyncio.run(get_todos())


@app.command()
def commute(origin: str = None, destination: str = None):
    """Get commute information."""
    async def get_commute():
        settings = get_settings()
        client = MCPClient()
        
        start = origin or settings.default_commute_origin
        end = destination or settings.default_commute_destination
        
        try:
            commute_data = await client.get_commute(start, end)
            
            table = Table(title=f"🚗 Commute: {start} → {end}")
            table.add_column("Mode", style="cyan")
            table.add_column("Duration", style="yellow")
            table.add_column("Distance", style="green")
            
            table.add_row(
                commute_data.get('mode', 'N/A'),
                commute_data.get('duration', 'N/A'),
                commute_data.get('distance', 'N/A')
            )
            
            console.print(table)
            
        except Exception as e:
            console.print(f"❌ Error getting commute: {e}", style="red")
    
    asyncio.run(get_commute())


@app.command()
def briefing(date: str = None):
    """Generate a complete morning briefing."""
    async def generate_briefing():
        client = MCPClient()
        target_date = date or datetime.now().strftime('%Y-%m-%d')
        
        console.print(f"🌅 Generating morning briefing for {target_date}...")
        
        try:
            # Get all data in parallel
            data = await client.get_all_morning_data(target_date)
            
            # Create a comprehensive briefing
            briefing_panel = Panel.fit(
                f"""🌤️ Weather: {data.get('weather', {}).get('summary', 'N/A')} - {data.get('weather', {}).get('temp_hi', 'N/A')}°F
                
🚗 Commute: {data.get('commute', {}).get('duration', 'N/A')} to {data.get('commute', {}).get('destination', 'office')}

📅 Calendar: {data.get('calendar', {}).get('total_events', 0)} events today

✅ Todos: {data.get('todos', {}).get('pending_count', 0)} pending tasks""",
                title="📋 Morning Briefing",
                border_style="blue"
            )
            
            console.print(briefing_panel)
            
        except Exception as e:
            console.print(f"❌ Error generating briefing: {e}", style="red")
    
    asyncio.run(generate_briefing())


@app.command()
def chat(message: str = typer.Option(None, "--message", "-m", help="Single message to send to the assistant")):
    """Have a natural language conversation with your AI assistant."""
    async def chat_session():
        orchestrator = AgentOrchestrator()
        
        if not orchestrator.is_conversational():
            console.print("❌ Conversational features require an OpenAI API key in your .env file", style="red")
            console.print("💡 You can still use individual commands like 'weather', 'todos', etc.", style="yellow")
            return
        
        if message:
            # Single message mode
            console.print(f"You: {message}", style="cyan")
            console.print("🤖 Thinking...", style="yellow")
            
            try:
                response = await orchestrator.chat(message)
                console.print(f"Assistant: {response}", style="green")
            except Exception as e:
                console.print(f"❌ Error: {e}", style="red")
        else:
            # Interactive chat mode
            console.print("🤖 Morning Assistant Chat (type 'quit' to exit)", style="blue")
            console.print("Try asking: 'What's my day looking like?' or 'Should I drive to work?'", style="dim")
            console.print()
            
            while True:
                try:
                    user_input = input("You: ").strip()
                    
                    if user_input.lower() in ['quit', 'exit', 'bye']:
                        console.print("👋 Have a great day!", style="green")
                        break
                    
                    if not user_input:
                        continue
                    
                    console.print("🤖 Thinking...", style="yellow")
                    response = await orchestrator.chat(user_input)
                    console.print(f"Assistant: {response}", style="green")
                    console.print()
                    
                except KeyboardInterrupt:
                    console.print("\\n👋 Have a great day!", style="green")
                    break
                except Exception as e:
                    console.print(f"❌ Error: {e}", style="red")
    
    asyncio.run(chat_session())


@app.command("smart-briefing")
def smart_briefing():
    """Generate an AI-powered conversational morning briefing."""
    async def generate_smart_briefing():
        console.print("🤖 Generating your intelligent morning briefing...", style="blue")
        
        orchestrator = AgentOrchestrator()
        
        try:
            briefing = await orchestrator.get_smart_briefing()
            
            # Display in a beautiful panel
            briefing_panel = Panel.fit(
                briefing,
                title="🌅 AI Morning Briefing",
                border_style="green"
            )
            
            console.print(briefing_panel)
            
        except Exception as e:
            console.print(f"❌ Error generating smart briefing: {e}", style="red")
            console.print("💡 Try the regular 'briefing' command or check your OpenAI API key", style="yellow")
    
    asyncio.run(generate_smart_briefing())


@app.command()
def demo():
    """Run a quick demo of all features."""
    async def run_demo():
        console.print("🎪 Running Morning Routine AI Agent Demo!", style="bold blue")
        console.print()
        
        # Check API key
        settings = get_settings()
        if settings.openai_api_key:
            console.print("✅ OpenAI API key configured - Conversational features available", style="green")
        else:
            console.print("⚠️ No OpenAI API key - Only basic tools available", style="yellow")
        console.print()
        
        # Test MCP server connection
        console.print("🔍 Testing MCP server connection...", style="blue")
        client = MCPClient()
        is_healthy = await client.health_check()
        
        if is_healthy:
            console.print("✅ MCP Server is healthy!", style="green")
        else:
            console.print("❌ MCP Server connection failed", style="red")
            return
        console.print()
        
        # Demo individual tools
        console.print("🌤️ Getting weather...", style="blue")
        try:
            weather = await client.get_weather(settings.user_location)
            console.print(f"Weather: {weather.get('summary')} - {weather.get('temp_hi')}°F", style="green")
        except Exception as e:
            console.print(f"Weather error: {e}", style="red")
        
        console.print("✅ Getting todos...", style="blue")
        try:
            todos = await client.get_todos("work")
            console.print(f"Todos: {todos.get('pending_count')} pending tasks", style="green")
        except Exception as e:
            console.print(f"Todos error: {e}", style="red")
        
        console.print()
        console.print("🎯 Demo complete! Try these commands:", style="bold green")
        console.print("  • uv run daily-ai-agent weather", style="cyan")
        console.print("  • uv run daily-ai-agent briefing", style="cyan")
        console.print("  • uv run daily-ai-agent chat", style="cyan")
        console.print("  • uv run daily-ai-agent smart-briefing", style="cyan")
    
    asyncio.run(run_demo())


def main():
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()

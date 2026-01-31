"""LLM service for conversational AI using OpenAI."""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Dict, Any, List
from loguru import logger

from ..models.config import get_settings


class LLMService:
    """Service for interacting with Large Language Models."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Initialize OpenAI client
        if self.settings.openai_api_key:
            self.llm = ChatOpenAI(
                api_key=self.settings.openai_api_key,
                model="gpt-4o-mini",  # Fast and cost-effective
                temperature=0.1  # Low temperature for consistent responses
            )
        else:
            self.llm = None
            logger.warning("No OpenAI API key configured")
    
    def is_available(self) -> bool:
        """Check if LLM is available."""
        return self.llm is not None
    
    async def generate_morning_briefing(self, data: Dict[str, Any]) -> str:
        """
        Generate a natural language morning briefing from tool data.
        
        Args:
            data: Combined data from all morning tools
            
        Returns:
            Natural language briefing
        """
        if not self.is_available():
            return self._fallback_briefing(data)
        
        # Extract key information
        weather = data.get('weather', {})
        calendar = data.get('calendar', {})
        todos = data.get('todos', {})
        commute = data.get('commute', {})
        
        # Create context for the LLM
        context = f"""
Weather: {weather.get('summary', 'N/A')} - {weather.get('temp_hi', 'N/A')}°F
Calendar: {calendar.get('total_events', 0)} events today
Todos: {todos.get('pending_count', 0)} pending tasks
Commute: {commute.get('duration', 'N/A')} to {commute.get('destination', 'office')}
"""
        
        system_prompt = f"""You are {self.settings.user_name}'s personal morning assistant. 
Generate a friendly, concise morning briefing that highlights the most important information.
Be conversational but informative. Focus on actionable insights.
User location: {self.settings.user_location}"""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Here's my morning data:\n{context}\n\nGenerate my morning briefing:")
            ]
            
            response = await self.llm.ainvoke(messages)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating briefing: {e}")
            return self._fallback_briefing(data)
    
    async def chat_response(self, user_message: str, context: Dict[str, Any] = None) -> str:
        """
        Generate a conversational response to user input.
        
        Args:
            user_message: User's natural language input
            context: Optional context from tool calls
            
        Returns:
            AI assistant response
        """
        if not self.is_available():
            return "I need an OpenAI API key to have conversations. I can still run individual tools though!"
        
        system_prompt = f"""You are {self.settings.user_name}'s personal morning assistant. 
You have access to weather, calendar, todo, and commute information.
Be helpful, friendly, and concise. Provide actionable insights when possible.
User location: {self.settings.user_location}
Current time context: Morning routine assistant"""
        
        context_text = ""
        if context:
            context_text = f"\\n\\nCurrent data: {context}"
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"{user_message}{context_text}")
            ]
            
            response = await self.llm.ainvoke(messages)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            return f"Sorry, I had trouble processing that. Error: {str(e)}"
    
    def _fallback_briefing(self, data: Dict[str, Any]) -> str:
        """Generate a simple text briefing without AI."""
        weather = data.get('weather', {})
        calendar = data.get('calendar', {})
        todos = data.get('todos', {})
        commute = data.get('commute', {})
        
        briefing_parts = [
            f"🌅 Good morning, {self.settings.user_name}!",
            "",
            f"🌤️ Weather: {weather.get('summary', 'N/A')} - {weather.get('temp_hi', 'N/A')}°F",
            f"🚗 Commute: {commute.get('duration', 'N/A')} to {commute.get('destination', 'office')}",
            f"📅 Calendar: {calendar.get('total_events', 0)} events today",
            f"✅ Todos: {todos.get('pending_count', 0)} pending tasks",
            "",
            "Have a great day! 🚀"
        ]
        
        return "\\n".join(briefing_parts)

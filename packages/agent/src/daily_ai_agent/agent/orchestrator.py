"""Main agent orchestrator that handles conversations and tool selection."""

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from typing import Dict, Any, List, Optional
from loguru import logger
from datetime import datetime

from .tools import get_all_tools
from ..models.config import get_settings
from ..services.llm import LLMService
from ..utils.constants import DEFAULT_LLM_MODEL, DEFAULT_LLM_TEMPERATURE

# Module-level tool cache for performance
_cached_tools: Optional[List] = None


def get_cached_tools() -> List:
    """Get cached tools, creating them only once."""
    global _cached_tools
    if _cached_tools is None:
        logger.debug("Initializing tool cache")
        _cached_tools = get_all_tools()
    return _cached_tools


def clear_tool_cache() -> None:
    """Clear the tool cache (useful for testing)."""
    global _cached_tools
    _cached_tools = None
    logger.debug("Tool cache cleared")


class AgentOrchestrator:
    """Main orchestrator for the AI agent."""

    def __init__(self, use_cached_tools: bool = True, enable_memory: Optional[bool] = None) -> None:
        """
        Initialize the agent orchestrator.

        Args:
            use_cached_tools: Whether to use cached tools (True for production)
            enable_memory: Whether to enable conversation memory (defaults to settings.enable_memory)
        """
        self.settings = get_settings()
        self.llm_service = LLMService()

        # Initialize conversation memory based on settings or override
        self.enable_memory = enable_memory if enable_memory is not None else self.settings.enable_memory
        self.chat_history: List[BaseMessage] = []

        if self.enable_memory:
            logger.info("Conversation memory enabled")
        else:
            logger.info("Conversation memory disabled")

        # Use cached tools by default for better performance
        if use_cached_tools:
            self.tools = get_cached_tools()
        else:
            self.tools = get_all_tools()

        # Initialize LangChain agent if OpenAI is available
        if self.settings.openai_api_key:
            self._init_langchain_agent()
        else:
            self.agent: Optional[AgentExecutor] = None
            logger.warning("No OpenAI API key - conversational features disabled")

    def _init_langchain_agent(self) -> None:
        """Initialize the LangChain agent with tools."""
        try:
            # Create the LLM
            llm = ChatOpenAI(
                api_key=self.settings.openai_api_key,
                model=DEFAULT_LLM_MODEL,
                temperature=DEFAULT_LLM_TEMPERATURE,
            )

            # Create the prompt template with current date
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_day = datetime.now().strftime("%A, %B %d, %Y")

            # Build prompt messages - include chat_history placeholder if memory is enabled
            prompt_messages = [
                ("system", f"""You are {self.settings.user_name}'s personal morning assistant.
You help with their daily routine by providing weather, calendar, todo, and commute information.

IMPORTANT: Today's date is {current_date} ({current_day}). When users ask about "today", "this morning", "my schedule", etc., use this date: {current_date}.

User preferences:
- Name: {self.settings.user_name}
- Location: {self.settings.user_location}
- Default commute: {self.settings.default_commute_origin} to {self.settings.default_commute_destination}

You have access to these tools:
- get_weather: Get weather forecasts
- get_calendar: Get calendar events for a single date (use YYYY-MM-DD format, today is {current_date})
- get_calendar_range: Get calendar events for a date range (MUCH more efficient for week queries)
- get_todos: Get todo/task lists
- get_commute: Get basic travel information between any two locations
- get_commute_options: Get comprehensive work commute analysis with driving vs transit (Caltrain + shuttle) options, real-time traffic, and AI recommendations
- get_shuttle_schedule: Get MV Connector shuttle schedules for LinkedIn campus transportation
- get_morning_briefing: Get complete morning summary

IMPORTANT: For week/multi-day queries, ALWAYS use get_calendar_range instead of multiple get_calendar calls.
Use get_calendar_range when users ask about "this week", "next week", "upcoming days", or any date range.

Be helpful, concise, and friendly. When users ask general questions like "What's my day like?",
use the morning briefing tool. For specific questions, use the appropriate individual tools.

IMPORTANT: When users ask about "work schedule" or "work meetings", they mean their job/professional calendar.
Currently only personal calendar, Runna (fitness), and Family calendars are available via API.
If asked about work meetings specifically, explain that work calendar integration requires additional setup.

CONVERSATION MEMORY: You have access to the conversation history. When users say things like "yes", "proceed",
"do it", "go ahead", or reference previous messages, use the chat history to understand what they're referring to.
Always maintain context from earlier in the conversation."""),
            ]

            # Add chat history placeholder if memory is enabled
            if self.enable_memory:
                prompt_messages.append(MessagesPlaceholder(variable_name="chat_history"))

            prompt_messages.extend([
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}")
            ])

            prompt = ChatPromptTemplate.from_messages(prompt_messages)

            # Create the agent
            agent = create_tool_calling_agent(llm, self.tools, prompt)
            self.agent = AgentExecutor(agent=agent, tools=self.tools, verbose=True)

            logger.info("LangChain agent initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing LangChain agent: {e}")
            self.agent = None

    async def chat(self, user_input: str) -> str:
        """
        Handle a conversational input from the user.

        Args:
            user_input: Natural language input from user

        Returns:
            AI assistant response
        """
        if not self.agent:
            return "I need an OpenAI API key to have conversations. Try the specific commands like 'briefing' or 'weather' instead!"

        try:
            logger.info(f"Processing user input: {user_input}")

            # Build the invoke payload
            invoke_payload: Dict[str, Any] = {"input": user_input}

            # Include chat history if memory is enabled
            if self.enable_memory:
                invoke_payload["chat_history"] = self.chat_history
                logger.debug(f"Including {len(self.chat_history)} messages in chat history")

            # Use the agent to process the input
            result = await self.agent.ainvoke(invoke_payload)
            response = result.get("output", "I'm not sure how to help with that.")

            # Store the conversation in memory if enabled
            if self.enable_memory:
                self.chat_history.append(HumanMessage(content=user_input))
                self.chat_history.append(AIMessage(content=response))
                logger.debug(f"Chat history now has {len(self.chat_history)} messages")

            logger.info("Successfully generated response")
            return response

        except Exception as e:
            logger.error(f"Error in chat processing: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    async def get_smart_briefing(self) -> str:
        """
        Get an AI-generated morning briefing.

        Returns:
            Natural language morning briefing
        """
        try:
            # Get all the morning data
            today = datetime.now().strftime('%Y-%m-%d')

            # Use the morning briefing tool through the agent if available
            if self.agent:
                result = await self.agent.ainvoke({
                    "input": "Give me my complete morning briefing with weather, calendar, todos, and commute information. Make it conversational and highlight the most important things."
                })
                return result.get("output", "Error generating briefing")
            else:
                # Fallback to direct tool call
                from ..services.mcp_client import MCPClient
                client = MCPClient()
                data = await client.get_all_morning_data(today)
                return await self.llm_service.generate_morning_briefing(data)

        except Exception as e:
            logger.error(f"Error generating smart briefing: {e}")
            return f"Error generating briefing: {str(e)}"

    def is_conversational(self) -> bool:
        """Check if conversational features are available."""
        return self.agent is not None

    def clear_memory(self) -> None:
        """Clear the conversation history to start a fresh session."""
        self.chat_history.clear()
        logger.info("Conversation memory cleared")

    def get_memory_length(self) -> int:
        """Get the number of messages in conversation history."""
        return len(self.chat_history)

    def get_chat_history(self) -> List[BaseMessage]:
        """Get a copy of the current chat history."""
        return list(self.chat_history)

    def has_memory(self) -> bool:
        """Check if memory is enabled and has messages stored."""
        return self.enable_memory and len(self.chat_history) > 0

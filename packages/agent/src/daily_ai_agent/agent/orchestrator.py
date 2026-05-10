"""Main agent orchestrator that handles conversations and tool selection."""

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from typing import Dict, Any, List, Optional, AsyncIterator
from loguru import logger
from datetime import datetime

from .tools import get_all_tools
from ..models.config import get_settings
from ..services.llm import LLMService
from ..services.preferences import get_enabled_categories
from ..utils.tracing import setup_langsmith_tracing, is_tracing_active

# Map weekend category IDs (from /weekend/categories) to the LangChain tool names
# that implement them. Disabled categories are filtered out before tool selection.
_CATEGORY_TO_TOOL_NAMES = {
    "trails": ["get_weekend_trails"],
    "concerts": ["get_weekend_concerts"],
    "itinerary": ["generate_weekend_itinerary"],
}

# All weekend tool names, regardless of category. Used to identify which tools
# are subject to category-based filtering vs. always-on tools (weather, calendar, etc).
_ALL_WEEKEND_TOOL_NAMES = {
    name for tools in _CATEGORY_TO_TOOL_NAMES.values() for name in tools
}


def _filter_tools_by_enabled_categories(tools: List, enabled: List[str]) -> List:
    """Drop weekend tools whose category isn't in the user's enabled list.

    Non-weekend tools (weather, calendar, todos, etc) pass through unchanged —
    the toggle system only gates the weekend orchestrator's category-mapped tools.
    """
    enabled_tool_names = set()
    for category in enabled:
        enabled_tool_names.update(_CATEGORY_TO_TOOL_NAMES.get(category, []))

    filtered: List = []
    dropped: List[str] = []
    for tool in tools:
        # Always-on tools (everything outside the weekend category map)
        if tool.name not in _ALL_WEEKEND_TOOL_NAMES:
            filtered.append(tool)
            continue
        # Weekend tools — only include if their category is enabled
        if tool.name in enabled_tool_names:
            filtered.append(tool)
        else:
            dropped.append(tool.name)

    if dropped:
        logger.debug(
            f"Weekend prefs filtered out {len(dropped)} disabled tools: {dropped}"
        )
    return filtered

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

        # Set up LangSmith tracing if configured (must be done before LangChain imports)
        self._setup_tracing()

        self.llm_service = LLMService()

        # Initialize conversation memory based on settings or override
        self.enable_memory = enable_memory if enable_memory is not None else self.settings.enable_memory
        self.chat_history: List[BaseMessage] = []

        if self.enable_memory:
            logger.info("Conversation memory enabled")
        else:
            logger.info("Conversation memory disabled")

        # Use cached tools by default for better performance
        self._use_cached_tools = use_cached_tools
        # Track the prefs we last built tools+agent against so we can detect
        # changes and rebuild only when needed (cheap to compare a tuple).
        self._last_enabled_categories: Optional[tuple] = None
        self.tools: List = []
        self._refresh_tools_from_preferences()

        # Determine which LLM provider to use
        self.llm_provider = self.settings.effective_llm_provider

        # Initialize LangChain agent if any LLM is available
        if self._has_llm_credentials():
            self._init_langchain_agent()
        else:
            self.agent: Optional[AgentExecutor] = None
            logger.warning("No LLM API key configured - conversational features disabled")

    def _refresh_tools_from_preferences(self) -> bool:
        """Re-read prefs and rebuild self.tools if enabled categories changed.

        Returns True if a rebuild happened (so callers can also rebuild the
        LangChain agent), False otherwise. Cheap when prefs haven't changed.
        """
        enabled_categories = get_enabled_categories()
        signature = tuple(sorted(enabled_categories))

        if signature == self._last_enabled_categories and self.tools:
            return False  # Already in sync, no work needed

        all_tools = (
            get_cached_tools() if self._use_cached_tools else get_all_tools()
        )
        self.tools = _filter_tools_by_enabled_categories(
            all_tools, enabled_categories
        )
        self._last_enabled_categories = signature
        logger.info(
            f"Agent tools refreshed: {len(self.tools)} available "
            f"(weekend categories enabled: {enabled_categories})"
        )
        return True

    def _setup_tracing(self) -> None:
        """Set up LangSmith tracing if configured."""
        if self.settings.is_tracing_enabled:
            setup_langsmith_tracing(
                api_key=self.settings.langchain_api_key,
                project=self.settings.langchain_project,
                endpoint=self.settings.langchain_endpoint,
                enabled=True,
            )
        else:
            logger.debug("LangSmith tracing not configured")

    def _has_llm_credentials(self) -> bool:
        """Check if any LLM credentials are available."""
        return bool(self.settings.openai_api_key) or bool(self.settings.anthropic_api_key)

    def _create_llm(self, streaming: bool = False) -> BaseChatModel:
        """
        Create the appropriate LLM based on configuration.

        Args:
            streaming: Whether to enable streaming for this LLM instance

        Returns:
            Configured LLM instance (ChatOpenAI or ChatAnthropic)
        """
        if self.llm_provider == "anthropic":
            # Import here to avoid requiring anthropic if not used
            from langchain_anthropic import ChatAnthropic

            logger.info(f"Using Anthropic model: {self.settings.anthropic_model}")
            return ChatAnthropic(
                api_key=self.settings.anthropic_api_key,
                model=self.settings.anthropic_model,
                temperature=self.settings.llm_temperature,
                streaming=streaming,
            )
        else:
            # Default to OpenAI
            logger.info(f"Using OpenAI model: {self.settings.openai_model}")
            return ChatOpenAI(
                api_key=self.settings.openai_api_key,
                model=self.settings.openai_model,
                temperature=self.settings.llm_temperature,
                streaming=streaming,
            )

    def _init_langchain_agent(self) -> None:
        """Initialize the LangChain agent with tools."""
        try:
            # Create the LLM using configured provider
            llm = self._create_llm(streaming=False)

            # Create the prompt template with current date
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_day = datetime.now().strftime("%A, %B %d, %Y")

            # Compute disabled weekend categories so the prompt can tell the agent
            # to short-circuit ("concerts are disabled — suggest enabling them")
            # instead of looping through other tools when asked about a disabled
            # category. See WEEKEND_ORCHESTRATOR_SPEC.md Section 20.
            all_weekend_categories = set(_CATEGORY_TO_TOOL_NAMES.keys())
            enabled_categories = set(get_enabled_categories())
            disabled_categories = sorted(all_weekend_categories - enabled_categories)
            disabled_categories_note = (
                f"\n\nDISABLED WEEKEND CATEGORIES: {', '.join(disabled_categories)}. "
                f"If the user asks about any of these categories, do NOT try to call other "
                f"tools to substitute — instead reply briefly that the category is disabled "
                f"in their preferences and suggest they enable it in settings."
                if disabled_categories
                else ""
            )

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
- get_weekend_trails: Find outdoor trails (hiking/running/cycling) near a location for weekend planning
- get_weekend_concerts: Find upcoming concerts and live music events near a location, optionally filtered by artists
- generate_weekend_itinerary: Generate a multi-day trip itinerary with points of interest grouped by category
- create_calendar_event: Create a new calendar event (used for write-back — see WEEKEND CALENDAR WRITE-BACK below)

WEEKEND PLANNING: When users ask about weekend plans, "things to do this weekend", trip ideas, or
multi-day getaways, combine the weekend tools intelligently. For example, check the weather first
to decide between outdoor trails (good weather) and indoor concerts (rainy). Use get_calendar_range
to find which days are actually free before recommending plans. For multi-day trips, use
generate_weekend_itinerary as the primary tool and supplement with get_weekend_trails or
get_weekend_concerts for richer recommendations.

TRAIL DISTANCE FOLLOW-UPS: After get_weekend_trails returns results, each trail line includes
the trail name AND a 📍 line with the full address (e.g. "Twin Peaks, San Francisco, CA 94114").
If the user asks how far each trail is from somewhere, use get_commute with the FULL ADDRESS
from the 📍 line — NOT the trail name alone. Trail names like "Twin Peaks" or "Mission Peak"
are ambiguous and may match the wrong landmark.

MARKDOWN FORMATTING: When you produce structured responses (multi-day itineraries, lists of
trails, daily plans), use proper markdown with newlines between sections. Put a blank line
before each ATX header (### Day 1, ### Day 2, etc) and start each list item on a new line.
The chat UI parses your output as markdown — headers without leading newlines render as
plain text "###" instead of formatted headers.

WEEKEND CALENDAR WRITE-BACK — IMPORTANT NEW CAPABILITY: After you generate a weekend
itinerary, multi-day plan, or any time-blocked recommendation (e.g. "Saturday: hike at 9am,
lunch at noon, concert at 8pm"), you MUST end your reply with an explicit offer to add
the events to the user's calendar. Use phrasing like:

  "Want me to add these to your calendar with travel time blocked off? Just say yes and
   I'll create the events."

Do NOT proactively create events without explicit confirmation. Wait for the user to say
"yes" / "do it" / "add them" / similar.

When the user confirms, follow this protocol:

1. For each itinerary item, call create_calendar_event with:
   - title: emoji-prefixed and concise. Use 🥾 for hikes/outdoors, 🎵 for concerts,
     🍽️ for restaurants/meals, 🎯 for attractions, 🏨 for lodging, 🚗 for travel/drive
     time blocks. Example: "🥾 Marin Headlands Hike", "🎵 Tycho @ The Fillmore".
   - start_time / end_time in ISO format (YYYY-MM-DDTHH:MM:SS). Use the dates and
     times from your generated plan; if you only suggested rough times like "morning",
     pick concrete defaults (morning=9-11am, lunch=12-1:30pm, afternoon=2-5pm,
     dinner=6:30-8:30pm, evening=8-10:30pm) and mention them in the confirmation.
   - description: include relevant details — full street address (from 📍 lines),
     trail length / difficulty, ticket URL, restaurant rating + price level, drive
     time + distance to the next stop. The description is what the user will see
     when they tap the event.
   - location: the full street address (from 📍 line) — NOT just the place name.
     This makes Google Calendar's "Get Directions" button work correctly.
   - calendar_name: "primary" unless the user has specified otherwise.

2. Insert TRAVEL TIME blocks between consecutive events when the drive between them
   is more than 5 minutes. Use get_commute with FULL addresses to compute drive time.
   Title format: "🚗 Drive to [destination name]" (e.g. "🚗 Drive to Marin Headlands").
   Place this block immediately before the destination event — the travel block's
   start_time equals the previous event's end_time, and its end_time equals
   start_time plus the computed drive minutes.

3. After each create_calendar_event call, check the response for "conflicts" — if
   any are returned, surface them to the user clearly. Don't auto-resolve conflicts;
   tell the user what conflicts exist and ask whether to shift, skip, or keep both.

4. Once all events are created, summarize what you added in the chat:
   "Done — added 8 events to your calendar between Saturday 8am and Sunday 9pm.
    Travel time blocked between each. One conflict found: your existing 'Hiking'
    event at 9am Sunday — I left it as-is and built around it."

If the user says "no" or only wants part of the plan added (e.g. "just the hikes"),
honor that — only create events for the subset they specified.

IMPORTANT: For week/multi-day queries, ALWAYS use get_calendar_range instead of multiple get_calendar calls.
Use get_calendar_range when users ask about "this week", "next week", "upcoming days", or any date range.

Be helpful, concise, and friendly. When users ask general questions like "What's my day like?",
use the morning briefing tool. For specific questions, use the appropriate individual tools.

IMPORTANT: When users ask about "work schedule" or "work meetings", they mean their job/professional calendar.
Currently only personal calendar, Runna (fitness), and Family calendars are available via API.
If asked about work meetings specifically, explain that work calendar integration requires additional setup.

CONVERSATION MEMORY: You have access to the conversation history. When users say things like "yes", "proceed",
"do it", "go ahead", or reference previous messages, use the chat history to understand what they're referring to.
Always maintain context from earlier in the conversation.{disabled_categories_note}"""),
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

            # Log tracing status
            tracing_status = "with LangSmith tracing" if is_tracing_active() else "without tracing"
            logger.info(f"LangChain agent initialized successfully ({self.llm_provider}, {tracing_status})")

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
            return "I need an LLM API key to have conversations. Try the specific commands like 'briefing' or 'weather' instead!"

        # If the user toggled weekend prefs since last chat, rebuild the agent
        # so the LLM sees the new tool list + updated disabled-category note.
        if self._refresh_tools_from_preferences():
            self._init_langchain_agent()

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

    async def _refresh_agent_for_chat(self) -> None:
        """Helper for streaming chat — rebuild LangChain agent if prefs changed."""
        if self._refresh_tools_from_preferences():
            self._init_langchain_agent()

    async def chat_stream(self, user_input: str) -> AsyncIterator[str]:
        """
        Handle a conversational input with streaming response.

        Args:
            user_input: Natural language input from user

        Yields:
            Chunks of the AI assistant response as they're generated.
            Also yields tool events in the format:
            - [TOOL_START] tool_name
            - [TOOL_END] tool_name
        """
        if not self.agent:
            yield "I need an LLM API key to have conversations. Try the specific commands like 'briefing' or 'weather' instead!"
            return

        # If weekend prefs changed since last chat, rebuild the agent so
        # streaming responses pick up the new tool list immediately.
        await self._refresh_agent_for_chat()

        try:
            logger.info(f"Processing user input (streaming): {user_input}")

            # Build the invoke payload
            invoke_payload: Dict[str, Any] = {"input": user_input}

            # Include chat history if memory is enabled
            if self.enable_memory:
                invoke_payload["chat_history"] = self.chat_history
                logger.debug(f"Including {len(self.chat_history)} messages in chat history")

            # Stream the response using astream_events
            full_response = ""
            async for event in self.agent.astream_events(invoke_payload, version="v2"):
                kind = event.get("event")

                # Emit tool start events
                if kind == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    logger.debug(f"Tool started: {tool_name}")
                    yield f"[TOOL_START] {tool_name}"

                # Stream tokens from the LLM
                elif kind == "on_chat_model_stream":
                    content = event.get("data", {}).get("chunk", {})
                    if hasattr(content, "content") and content.content:
                        chunk = content.content
                        full_response += chunk
                        yield chunk

                # Emit tool end events
                elif kind == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    tool_output = event.get("data", {}).get("output")
                    if tool_output:
                        logger.debug(f"Tool completed: {tool_name}")
                    yield f"[TOOL_END] {tool_name}"

            # Store the conversation in memory if enabled
            if self.enable_memory and full_response:
                self.chat_history.append(HumanMessage(content=user_input))
                self.chat_history.append(AIMessage(content=full_response))
                logger.debug(f"Chat history now has {len(self.chat_history)} messages")

            logger.info("Successfully generated streaming response")

        except Exception as e:
            logger.error(f"Error in streaming chat processing: {e}")
            yield f"Sorry, I encountered an error: {str(e)}"

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

    def get_llm_info(self) -> Dict[str, Any]:
        """Get information about the current LLM configuration."""
        return {
            "provider": self.llm_provider,
            "model": (
                self.settings.anthropic_model
                if self.llm_provider == "anthropic"
                else self.settings.openai_model
            ),
            "tracing_enabled": is_tracing_active(),
            "tracing_project": self.settings.langchain_project if is_tracing_active() else None,
        }

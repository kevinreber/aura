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
from ..services.intent_classifier import IntentClassifier
from ..services.embeddings import EmbeddingService
from ..utils.tracing import setup_langsmith_tracing, is_tracing_active

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
        if use_cached_tools:
            self.tools = get_cached_tools()
        else:
            self.tools = get_all_tools()

        # Initialize Hugging Face services (lazy-loaded, won't download until first use)
        self.intent_classifier = IntentClassifier(
            model_name=self.settings.hf_intent_classifier_model,
            confidence_threshold=self.settings.hf_intent_confidence_threshold,
            enabled=self.settings.hf_intent_classifier_enabled,
        )
        self.embedding_service = EmbeddingService(
            model_name=self.settings.hf_embeddings_model,
            enabled=self.settings.hf_embeddings_enabled,
        )
        logger.info(
            f"HF services: intent_classifier={'enabled' if self.intent_classifier.enabled else 'disabled'}, "
            f"embeddings={'enabled' if self.embedding_service.enabled else 'disabled'}"
        )

        # Determine which LLM provider to use
        self.llm_provider = self.settings.effective_llm_provider

        # Initialize LangChain agent if any LLM is available
        if self._has_llm_credentials():
            self._init_langchain_agent()
        else:
            self.agent: Optional[AgentExecutor] = None
            logger.warning("No LLM API key configured - conversational features disabled")

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

            # Log tracing status
            tracing_status = "with LangSmith tracing" if is_tracing_active() else "without tracing"
            logger.info(f"LangChain agent initialized successfully ({self.llm_provider}, {tracing_status})")

        except Exception as e:
            logger.error(f"Error initializing LangChain agent: {e}")
            self.agent = None

    async def _try_direct_tool_call(self, tool_name: str, user_input: str) -> Optional[str]:
        """
        Attempt to call a tool directly based on intent classification,
        bypassing the LLM for simple queries.

        Returns the tool result string, or None if the tool call fails
        and the query should fall through to the full LLM agent.
        """
        tool_map = {t.name: t for t in self.tools}
        tool = tool_map.get(tool_name)
        if not tool:
            return None

        try:
            logger.info(f"Fast path: calling {tool_name} directly (skipping LLM)")

            # For tools with simple defaults, call directly
            if tool_name == "get_morning_briefing":
                return await tool._arun()
            elif tool_name == "get_weather":
                return await tool._arun(location=self.settings.user_location)
            elif tool_name == "get_calendar":
                today = datetime.now().strftime("%Y-%m-%d")
                return await tool._arun(date=today)
            elif tool_name == "get_todos":
                return await tool._arun()
            elif tool_name == "get_financial_data":
                from ..utils.constants import FINANCIAL_SYMBOLS
                return await tool._arun(symbols=FINANCIAL_SYMBOLS, data_type="mixed")
            elif tool_name == "get_commute":
                return await tool._arun(
                    origin=self.settings.default_commute_origin,
                    destination=self.settings.default_commute_destination,
                )
            else:
                # Tool needs parameters we can't infer — fall through to LLM
                return None
        except Exception as e:
            logger.warning(f"Direct tool call failed for {tool_name}: {e}")
            return None

    async def chat(self, user_input: str) -> str:
        """
        Handle a conversational input from the user.

        Uses a two-stage approach:
        1. Fast path: HF intent classifier routes simple queries directly to tools
        2. Full path: LLM agent handles complex/ambiguous queries

        Args:
            user_input: Natural language input from user

        Returns:
            AI assistant response
        """
        if not self.agent:
            return "I need an LLM API key to have conversations. Try the specific commands like 'briefing' or 'weather' instead!"

        try:
            logger.info(f"Processing user input: {user_input}")

            # Stage 1: Try fast intent classification
            intent_tool, confidence = self.intent_classifier.classify(user_input)
            if intent_tool:
                logger.info(f"Intent classified: {intent_tool} (confidence={confidence:.2f})")
                direct_result = await self._try_direct_tool_call(intent_tool, user_input)
                if direct_result:
                    # Store in memory and embeddings
                    self._store_exchange(user_input, direct_result)
                    return direct_result

            # Stage 2: Full LLM agent path
            invoke_payload: Dict[str, Any] = {"input": user_input}

            # Enrich input with semantically relevant context from embeddings
            if self.embedding_service.enabled and self.embedding_service.history_size() > 0:
                relevant = self.embedding_service.get_relevant_context(user_input, top_k=3)
                if relevant:
                    context_block = "\n".join(f"- {msg}" for msg in relevant)
                    invoke_payload["input"] = (
                        f"[Relevant prior context:\n{context_block}]\n\n{user_input}"
                    )
                    logger.debug(f"Enriched input with {len(relevant)} relevant context messages")

            # Include chat history if memory is enabled
            if self.enable_memory:
                invoke_payload["chat_history"] = self.chat_history
                logger.debug(f"Including {len(self.chat_history)} messages in chat history")

            # Use the agent to process the input
            result = await self.agent.ainvoke(invoke_payload)
            response = result.get("output", "I'm not sure how to help with that.")

            # Store in memory and embeddings
            self._store_exchange(user_input, response)

            logger.info("Successfully generated response")
            return response

        except Exception as e:
            logger.error(f"Error in chat processing: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    def _store_exchange(self, user_input: str, response: str) -> None:
        """Store a user/assistant exchange in chat history and embeddings."""
        if self.enable_memory:
            self.chat_history.append(HumanMessage(content=user_input))
            self.chat_history.append(AIMessage(content=response))
            logger.debug(f"Chat history now has {len(self.chat_history)} messages")

        # Store embeddings for semantic retrieval
        self.embedding_service.add_to_history(user_input, {"role": "user"})
        self.embedding_service.add_to_history(response, {"role": "assistant"})

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

            # Store in memory and embeddings
            if full_response:
                self._store_exchange(user_input, full_response)

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
        """Clear the conversation history and embedding history."""
        self.chat_history.clear()
        self.embedding_service.clear()
        logger.info("Conversation memory and embeddings cleared")

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
        """Get information about the current LLM and HF configuration."""
        return {
            "provider": self.llm_provider,
            "model": (
                self.settings.anthropic_model
                if self.llm_provider == "anthropic"
                else self.settings.openai_model
            ),
            "tracing_enabled": is_tracing_active(),
            "tracing_project": self.settings.langchain_project if is_tracing_active() else None,
            "hf_intent_classifier": self.intent_classifier.enabled,
            "hf_embeddings": self.embedding_service.enabled,
            "hf_embeddings_stored": self.embedding_service.history_size(),
        }

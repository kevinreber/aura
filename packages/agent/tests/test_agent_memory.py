"""Tests for agent conversation memory functionality.

These tests verify that the AI agent can:
1. Store conversation history
2. Understand vague references like "yes, proceed"
3. Maintain context across multiple turns
4. Clear memory when requested
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAgentMemoryBasics:
    """Test basic memory functionality without LLM calls."""

    @pytest.fixture
    def mock_orchestrator(self, mock_settings):
        """Create an orchestrator with mocked LLM."""
        with patch("daily_ai_agent.agent.orchestrator.ChatOpenAI") as mock_llm, \
             patch("daily_ai_agent.agent.orchestrator.create_tool_calling_agent") as mock_create_agent, \
             patch("daily_ai_agent.agent.orchestrator.AgentExecutor") as mock_executor, \
             patch("daily_ai_agent.agent.orchestrator.get_cached_tools") as mock_tools:

            mock_tools.return_value = []
            mock_executor_instance = MagicMock()
            mock_executor.return_value = mock_executor_instance

            from daily_ai_agent.agent.orchestrator import AgentOrchestrator
            orchestrator = AgentOrchestrator(use_cached_tools=True, enable_memory=True)
            orchestrator.agent = mock_executor_instance

            yield orchestrator

    def test_memory_enabled_by_default(self, mock_settings):
        """Test that memory is enabled when settings.enable_memory is True."""
        with patch("daily_ai_agent.agent.orchestrator.ChatOpenAI"), \
             patch("daily_ai_agent.agent.orchestrator.create_tool_calling_agent"), \
             patch("daily_ai_agent.agent.orchestrator.AgentExecutor"), \
             patch("daily_ai_agent.agent.orchestrator.get_cached_tools") as mock_tools:

            mock_tools.return_value = []
            from daily_ai_agent.agent.orchestrator import AgentOrchestrator
            orchestrator = AgentOrchestrator()

            assert orchestrator.enable_memory is True
            assert orchestrator.chat_history == []

    def test_memory_can_be_disabled(self, mock_settings):
        """Test that memory can be explicitly disabled."""
        with patch("daily_ai_agent.agent.orchestrator.ChatOpenAI"), \
             patch("daily_ai_agent.agent.orchestrator.create_tool_calling_agent"), \
             patch("daily_ai_agent.agent.orchestrator.AgentExecutor"), \
             patch("daily_ai_agent.agent.orchestrator.get_cached_tools") as mock_tools:

            mock_tools.return_value = []
            from daily_ai_agent.agent.orchestrator import AgentOrchestrator
            orchestrator = AgentOrchestrator(enable_memory=False)

            assert orchestrator.enable_memory is False

    def test_clear_memory(self, mock_orchestrator):
        """Test that clear_memory() empties the chat history."""
        # Import inside test to avoid Pydantic schema generation at module load
        from langchain_core.messages import HumanMessage, AIMessage
        # Add some messages manually
        mock_orchestrator.chat_history.append(HumanMessage(content="Hello"))
        mock_orchestrator.chat_history.append(AIMessage(content="Hi there!"))

        assert mock_orchestrator.get_memory_length() == 2

        mock_orchestrator.clear_memory()

        assert mock_orchestrator.get_memory_length() == 0
        assert mock_orchestrator.chat_history == []

    def test_get_memory_length(self, mock_orchestrator):
        """Test that get_memory_length() returns correct count."""
        from langchain_core.messages import HumanMessage, AIMessage
        assert mock_orchestrator.get_memory_length() == 0

        mock_orchestrator.chat_history.append(HumanMessage(content="Test"))
        assert mock_orchestrator.get_memory_length() == 1

        mock_orchestrator.chat_history.append(AIMessage(content="Response"))
        assert mock_orchestrator.get_memory_length() == 2

    def test_get_chat_history_returns_copy(self, mock_orchestrator):
        """Test that get_chat_history() returns a copy, not the original."""
        from langchain_core.messages import HumanMessage
        mock_orchestrator.chat_history.append(HumanMessage(content="Original"))

        history_copy = mock_orchestrator.get_chat_history()
        history_copy.append(HumanMessage(content="New message"))

        # Original should be unchanged
        assert mock_orchestrator.get_memory_length() == 1

    def test_has_memory_false_when_empty(self, mock_orchestrator):
        """Test has_memory() returns False when no messages stored."""
        assert mock_orchestrator.has_memory() is False

    def test_has_memory_true_when_populated(self, mock_orchestrator):
        """Test has_memory() returns True when messages are stored."""
        from langchain_core.messages import HumanMessage
        mock_orchestrator.chat_history.append(HumanMessage(content="Test"))
        assert mock_orchestrator.has_memory() is True

    def test_has_memory_false_when_disabled(self, mock_settings):
        """Test has_memory() returns False when memory is disabled."""
        with patch("daily_ai_agent.agent.orchestrator.ChatOpenAI"), \
             patch("daily_ai_agent.agent.orchestrator.create_tool_calling_agent"), \
             patch("daily_ai_agent.agent.orchestrator.AgentExecutor"), \
             patch("daily_ai_agent.agent.orchestrator.get_cached_tools") as mock_tools:

            mock_tools.return_value = []
            from daily_ai_agent.agent.orchestrator import AgentOrchestrator
            orchestrator = AgentOrchestrator(enable_memory=False)

            # Even if we add messages, has_memory should return False
            from langchain_core.messages import HumanMessage
            orchestrator.chat_history.append(HumanMessage(content="Test"))
            assert orchestrator.has_memory() is False


class TestAgentMemoryWithChat:
    """Test memory functionality with actual chat calls (mocked LLM)."""

    @pytest.fixture
    def orchestrator_with_mock_agent(self, mock_settings):
        """Create orchestrator with a mock agent that returns predictable responses."""
        with patch("daily_ai_agent.agent.orchestrator.ChatOpenAI"), \
             patch("daily_ai_agent.agent.orchestrator.create_tool_calling_agent"), \
             patch("daily_ai_agent.agent.orchestrator.AgentExecutor") as mock_executor_class, \
             patch("daily_ai_agent.agent.orchestrator.get_cached_tools") as mock_tools:

            mock_tools.return_value = []

            # Create mock agent executor
            mock_agent = AsyncMock()
            mock_executor_class.return_value = mock_agent

            from daily_ai_agent.agent.orchestrator import AgentOrchestrator
            orchestrator = AgentOrchestrator(use_cached_tools=True, enable_memory=True)

            yield orchestrator, mock_agent

    @pytest.mark.asyncio
    async def test_chat_stores_messages_in_history(self, orchestrator_with_mock_agent):
        """Test that chat() stores both user input and AI response in history."""
        orchestrator, mock_agent = orchestrator_with_mock_agent

        # Mock agent response
        mock_agent.ainvoke.return_value = {"output": "The weather is sunny!"}

        response = await orchestrator.chat("What's the weather?")

        assert response == "The weather is sunny!"
        assert orchestrator.get_memory_length() == 2

        history = orchestrator.get_chat_history()
        # Use type name check to avoid Pydantic schema generation issues
        assert type(history[0]).__name__ == "HumanMessage"
        assert history[0].content == "What's the weather?"
        assert type(history[1]).__name__ == "AIMessage"
        assert history[1].content == "The weather is sunny!"

    @pytest.mark.asyncio
    async def test_chat_passes_history_to_agent(self, mock_settings):
        """Test that chat() passes the conversation history to the agent."""
        with patch("daily_ai_agent.agent.orchestrator.ChatOpenAI"), \
             patch("daily_ai_agent.agent.orchestrator.create_tool_calling_agent"), \
             patch("daily_ai_agent.agent.orchestrator.AgentExecutor") as mock_executor_class, \
             patch("daily_ai_agent.agent.orchestrator.get_cached_tools") as mock_tools:

            mock_tools.return_value = []
            mock_agent = AsyncMock()
            mock_executor_class.return_value = mock_agent

            # Track history length at each call
            history_lengths = []

            async def track_history_length(payload):
                if "chat_history" in payload:
                    history_lengths.append(len(payload["chat_history"]))
                else:
                    history_lengths.append(0)
                return {"output": "Response"}

            mock_agent.ainvoke.side_effect = track_history_length

            from daily_ai_agent.agent.orchestrator import AgentOrchestrator
            orchestrator = AgentOrchestrator(use_cached_tools=True, enable_memory=True)

            # First message - should have 0 history
            await orchestrator.chat("Check weather in San Francisco")

            # Second message - should have 2 history items (first exchange)
            await orchestrator.chat("Yes, proceed")

            assert history_lengths[0] == 0  # First call has no history
            assert history_lengths[1] == 2  # Second call has first exchange

    @pytest.mark.asyncio
    async def test_chat_accumulates_history(self, orchestrator_with_mock_agent):
        """Test that multiple chat turns accumulate in history."""
        orchestrator, mock_agent = orchestrator_with_mock_agent

        mock_agent.ainvoke.return_value = {"output": "Response 1"}
        await orchestrator.chat("Message 1")
        assert orchestrator.get_memory_length() == 2

        mock_agent.ainvoke.return_value = {"output": "Response 2"}
        await orchestrator.chat("Message 2")
        assert orchestrator.get_memory_length() == 4

        mock_agent.ainvoke.return_value = {"output": "Response 3"}
        await orchestrator.chat("Message 3")
        assert orchestrator.get_memory_length() == 6

    @pytest.mark.asyncio
    async def test_memory_disabled_does_not_store(self, mock_settings):
        """Test that with memory disabled, chat doesn't store history."""
        with patch("daily_ai_agent.agent.orchestrator.ChatOpenAI"), \
             patch("daily_ai_agent.agent.orchestrator.create_tool_calling_agent"), \
             patch("daily_ai_agent.agent.orchestrator.AgentExecutor") as mock_executor_class, \
             patch("daily_ai_agent.agent.orchestrator.get_cached_tools") as mock_tools:

            mock_tools.return_value = []
            mock_agent = AsyncMock()
            mock_agent.ainvoke.return_value = {"output": "Response"}
            mock_executor_class.return_value = mock_agent

            from daily_ai_agent.agent.orchestrator import AgentOrchestrator
            orchestrator = AgentOrchestrator(enable_memory=False)

            await orchestrator.chat("Hello")
            await orchestrator.chat("How are you?")

            assert orchestrator.get_memory_length() == 0

    @pytest.mark.asyncio
    async def test_memory_disabled_does_not_pass_history(self, mock_settings):
        """Test that with memory disabled, chat_history is not passed to agent."""
        with patch("daily_ai_agent.agent.orchestrator.ChatOpenAI"), \
             patch("daily_ai_agent.agent.orchestrator.create_tool_calling_agent"), \
             patch("daily_ai_agent.agent.orchestrator.AgentExecutor") as mock_executor_class, \
             patch("daily_ai_agent.agent.orchestrator.get_cached_tools") as mock_tools:

            mock_tools.return_value = []
            mock_agent = AsyncMock()
            mock_agent.ainvoke.return_value = {"output": "Response"}
            mock_executor_class.return_value = mock_agent

            from daily_ai_agent.agent.orchestrator import AgentOrchestrator
            orchestrator = AgentOrchestrator(enable_memory=False)

            await orchestrator.chat("Hello")

            # Verify chat_history was NOT passed
            call_args = mock_agent.ainvoke.call_args[0][0]
            assert "chat_history" not in call_args


class TestAgentMemoryContextUnderstanding:
    """
    Tests for verifying the agent understands context from memory.

    These tests validate scenarios like:
    - User says "yes, proceed" and agent understands the reference
    - User asks "what about tomorrow?" after asking about today's weather
    - User references "the first option" from a previous response
    """

    @pytest.mark.asyncio
    async def test_vague_confirmation_has_context(self, mock_settings):
        """Test that 'yes, proceed' gets full conversation context."""
        with patch("daily_ai_agent.agent.orchestrator.ChatOpenAI"), \
             patch("daily_ai_agent.agent.orchestrator.create_tool_calling_agent"), \
             patch("daily_ai_agent.agent.orchestrator.AgentExecutor") as mock_executor_class, \
             patch("daily_ai_agent.agent.orchestrator.get_cached_tools") as mock_tools:

            mock_tools.return_value = []
            mock_agent = AsyncMock()
            mock_executor_class.return_value = mock_agent

            # Track history content at each call
            captured_histories = []

            async def capture_history(payload):
                if "chat_history" in payload:
                    # Deep copy the history content
                    captured_histories.append([
                        (type(m).__name__, m.content) for m in payload["chat_history"]
                    ])
                else:
                    captured_histories.append([])
                return {"output": f"Response to: {payload['input']}"}

            mock_agent.ainvoke.side_effect = capture_history

            from daily_ai_agent.agent.orchestrator import AgentOrchestrator
            orchestrator = AgentOrchestrator(use_cached_tools=True, enable_memory=True)

            # First message establishes context
            await orchestrator.chat("Should I check the weather in San Francisco?")

            # Vague confirmation
            await orchestrator.chat("Yes, proceed")

            # The second call should have the first exchange in history
            assert len(captured_histories[1]) == 2

            # Verify the history contains the original question
            assert "San Francisco" in captured_histories[1][0][1]

    @pytest.mark.asyncio
    async def test_follow_up_question_has_context(self, mock_settings):
        """Test that 'what about tomorrow?' gets previous weather context."""
        with patch("daily_ai_agent.agent.orchestrator.ChatOpenAI"), \
             patch("daily_ai_agent.agent.orchestrator.create_tool_calling_agent"), \
             patch("daily_ai_agent.agent.orchestrator.AgentExecutor") as mock_executor_class, \
             patch("daily_ai_agent.agent.orchestrator.get_cached_tools") as mock_tools:

            mock_tools.return_value = []
            mock_agent = AsyncMock()
            mock_executor_class.return_value = mock_agent

            captured_histories = []

            async def capture_history(payload):
                if "chat_history" in payload:
                    captured_histories.append([
                        (type(m).__name__, m.content) for m in payload["chat_history"]
                    ])
                else:
                    captured_histories.append([])
                return {"output": f"Response to: {payload['input']}"}

            mock_agent.ainvoke.side_effect = capture_history

            from daily_ai_agent.agent.orchestrator import AgentOrchestrator
            orchestrator = AgentOrchestrator(use_cached_tools=True, enable_memory=True)

            await orchestrator.chat("What's the weather in New York?")
            await orchestrator.chat("What about tomorrow?")

            # The follow-up should have access to the New York weather question
            assert "New York" in captured_histories[1][0][1]

    @pytest.mark.asyncio
    async def test_multiple_turns_accumulate_context(self, mock_settings):
        """Test that context accumulates over multiple turns."""
        with patch("daily_ai_agent.agent.orchestrator.ChatOpenAI"), \
             patch("daily_ai_agent.agent.orchestrator.create_tool_calling_agent"), \
             patch("daily_ai_agent.agent.orchestrator.AgentExecutor") as mock_executor_class, \
             patch("daily_ai_agent.agent.orchestrator.get_cached_tools") as mock_tools:

            mock_tools.return_value = []
            mock_agent = AsyncMock()
            mock_executor_class.return_value = mock_agent

            captured_histories = []

            async def capture_history(payload):
                if "chat_history" in payload:
                    captured_histories.append([
                        (type(m).__name__, m.content) for m in payload["chat_history"]
                    ])
                else:
                    captured_histories.append([])
                return {"output": f"Response to: {payload['input']}"}

            mock_agent.ainvoke.side_effect = capture_history

            from daily_ai_agent.agent.orchestrator import AgentOrchestrator
            orchestrator = AgentOrchestrator(use_cached_tools=True, enable_memory=True)

            await orchestrator.chat("Check my calendar")
            await orchestrator.chat("What about my todos?")
            await orchestrator.chat("Give me a summary of both")

            # Third call should have 4 messages (2 exchanges)
            assert len(captured_histories[2]) == 4

            # Verify both previous topics are in history
            full_history_text = " ".join([msg[1] for msg in captured_histories[2]])
            assert "calendar" in full_history_text.lower()
            assert "todos" in full_history_text.lower()

    @pytest.mark.asyncio
    async def test_cleared_memory_loses_context(self, mock_settings):
        """Test that clearing memory removes all context."""
        with patch("daily_ai_agent.agent.orchestrator.ChatOpenAI"), \
             patch("daily_ai_agent.agent.orchestrator.create_tool_calling_agent"), \
             patch("daily_ai_agent.agent.orchestrator.AgentExecutor") as mock_executor_class, \
             patch("daily_ai_agent.agent.orchestrator.get_cached_tools") as mock_tools:

            mock_tools.return_value = []
            mock_agent = AsyncMock()
            mock_executor_class.return_value = mock_agent

            captured_histories = []

            async def capture_history(payload):
                if "chat_history" in payload:
                    captured_histories.append([
                        (type(m).__name__, m.content) for m in payload["chat_history"]
                    ])
                else:
                    captured_histories.append([])
                return {"output": f"Response to: {payload['input']}"}

            mock_agent.ainvoke.side_effect = capture_history

            from daily_ai_agent.agent.orchestrator import AgentOrchestrator
            orchestrator = AgentOrchestrator(use_cached_tools=True, enable_memory=True)

            await orchestrator.chat("Remember this: the secret code is 12345")

            # Clear memory
            orchestrator.clear_memory()

            await orchestrator.chat("What was the secret code?")

            # Second call after clear should have no history
            assert len(captured_histories[1]) == 0


class TestMemoryPersistenceAcrossInstances:
    """Test that memory is instance-specific (no cross-contamination)."""

    def test_separate_instances_have_separate_memory(self, mock_settings):
        """Test that different orchestrator instances have independent memory."""
        with patch("daily_ai_agent.agent.orchestrator.ChatOpenAI"), \
             patch("daily_ai_agent.agent.orchestrator.create_tool_calling_agent"), \
             patch("daily_ai_agent.agent.orchestrator.AgentExecutor"), \
             patch("daily_ai_agent.agent.orchestrator.get_cached_tools") as mock_tools:

            mock_tools.return_value = []

            from daily_ai_agent.agent.orchestrator import AgentOrchestrator
            from langchain_core.messages import HumanMessage

            orchestrator1 = AgentOrchestrator(enable_memory=True)
            orchestrator2 = AgentOrchestrator(enable_memory=True)

            # Add message to first instance
            orchestrator1.chat_history.append(HumanMessage(content="Only in instance 1"))

            # Second instance should be empty
            assert orchestrator1.get_memory_length() == 1
            assert orchestrator2.get_memory_length() == 0

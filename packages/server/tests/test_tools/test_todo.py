"""Tests for the todo tool."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from mcp_server.tools.todo import TodoTool
from mcp_server.schemas.todo import (
    TodoInput, TodoOutput, TodoItem, TodoBucket, TodoPriority,
    TodoCreateInput, TodoCreateOutput,
    TodoUpdateInput, TodoUpdateOutput,
    TodoCompleteInput, TodoCompleteOutput,
    TodoDeleteInput, TodoDeleteOutput
)


class TestTodoTool:
    """Test the TodoTool class."""

    @pytest.fixture
    def todo_tool(self):
        """Create a TodoTool instance."""
        return TodoTool()

    @pytest.mark.asyncio
    async def test_list_todos_work_bucket(self, todo_tool):
        """Test listing todos from work bucket."""
        input_data = TodoInput(bucket=TodoBucket.WORK)

        result = await todo_tool.list_todos(input_data)

        assert isinstance(result, TodoOutput)
        assert result.bucket == TodoBucket.WORK
        assert isinstance(result.items, list)
        assert result.total_items == len(result.items)
        assert result.pending_count + result.completed_count == result.total_items

    @pytest.mark.asyncio
    async def test_list_todos_personal_bucket(self, todo_tool):
        """Test listing todos from personal bucket."""
        input_data = TodoInput(bucket=TodoBucket.PERSONAL)

        result = await todo_tool.list_todos(input_data)

        assert result.bucket == TodoBucket.PERSONAL

    @pytest.mark.asyncio
    async def test_list_todos_home_bucket(self, todo_tool):
        """Test listing todos from home bucket."""
        input_data = TodoInput(bucket=TodoBucket.HOME)

        result = await todo_tool.list_todos(input_data)

        assert result.bucket == TodoBucket.HOME

    @pytest.mark.asyncio
    async def test_list_todos_errands_bucket(self, todo_tool):
        """Test listing todos from errands bucket."""
        input_data = TodoInput(bucket=TodoBucket.ERRANDS)

        result = await todo_tool.list_todos(input_data)

        assert result.bucket == TodoBucket.ERRANDS

    @pytest.mark.asyncio
    async def test_list_todos_all_buckets(self, todo_tool):
        """Test listing todos from all buckets."""
        input_data = TodoInput(bucket=None)

        result = await todo_tool.list_todos(input_data)

        assert result.bucket is None
        assert isinstance(result.items, list)

    @pytest.mark.asyncio
    async def test_list_todos_include_completed(self, todo_tool):
        """Test listing todos including completed ones."""
        input_data = TodoInput(
            bucket=TodoBucket.WORK,
            include_completed=True
        )

        result = await todo_tool.list_todos(input_data)

        # Should include some completed todos in mock data
        assert isinstance(result.items, list)

    @pytest.mark.asyncio
    async def test_list_todos_exclude_completed(self, todo_tool):
        """Test listing todos excluding completed ones."""
        input_data = TodoInput(
            bucket=TodoBucket.WORK,
            include_completed=False
        )

        result = await todo_tool.list_todos(input_data)

        # All items should be incomplete
        for item in result.items:
            assert item.completed is False


class TestTodoCreateOperations:
    """Test todo creation operations."""

    @pytest.fixture
    def todo_tool(self):
        """Create a TodoTool instance."""
        return TodoTool()

    @pytest.mark.asyncio
    async def test_create_todo_basic(self, todo_tool):
        """Test creating a basic todo."""
        input_data = TodoCreateInput(
            title="Test Todo Item",
            bucket=TodoBucket.WORK,
            priority=TodoPriority.MEDIUM
        )

        result = await todo_tool.create_todo(input_data)

        assert isinstance(result, TodoCreateOutput)
        assert result.success is True
        assert result.todo is not None
        assert result.todo.title == "Test Todo Item"
        assert result.todo.bucket == TodoBucket.WORK
        assert result.todo.priority == TodoPriority.MEDIUM
        assert result.todo.completed is False

    @pytest.mark.asyncio
    async def test_create_todo_with_due_date(self, todo_tool):
        """Test creating a todo with due date."""
        input_data = TodoCreateInput(
            title="Task with deadline",
            bucket=TodoBucket.WORK,
            priority=TodoPriority.HIGH,
            due_date="tomorrow"
        )

        result = await todo_tool.create_todo(input_data)

        assert result.success is True
        assert result.todo.due_date is not None

    @pytest.mark.asyncio
    async def test_create_todo_with_description(self, todo_tool):
        """Test creating a todo with description."""
        input_data = TodoCreateInput(
            title="Detailed Task",
            bucket=TodoBucket.PERSONAL,
            priority=TodoPriority.LOW,
            description="This is a detailed description of the task"
        )

        result = await todo_tool.create_todo(input_data)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_create_todo_with_tags(self, todo_tool):
        """Test creating a todo with tags."""
        input_data = TodoCreateInput(
            title="Tagged Task",
            bucket=TodoBucket.HOME,
            priority=TodoPriority.MEDIUM,
            tags=["urgent", "cleaning"]
        )

        result = await todo_tool.create_todo(input_data)

        assert result.success is True
        assert result.todo.tags == ["urgent", "cleaning"]

    @pytest.mark.asyncio
    async def test_create_todo_urgent_priority(self, todo_tool):
        """Test creating an urgent priority todo."""
        input_data = TodoCreateInput(
            title="Urgent Task",
            bucket=TodoBucket.WORK,
            priority=TodoPriority.URGENT
        )

        result = await todo_tool.create_todo(input_data)

        assert result.success is True
        assert result.todo.priority == TodoPriority.URGENT


class TestTodoUpdateOperations:
    """Test todo update operations."""

    @pytest.fixture
    def todo_tool(self):
        """Create a TodoTool instance."""
        return TodoTool()

    @pytest.mark.asyncio
    async def test_update_todo_title(self, todo_tool):
        """Test updating todo title."""
        input_data = TodoUpdateInput(
            id="test_todo_123",
            title="Updated Title"
        )

        result = await todo_tool.update_todo(input_data)

        assert isinstance(result, TodoUpdateOutput)
        assert result.success is True
        assert "title" in result.changes

    @pytest.mark.asyncio
    async def test_update_todo_priority(self, todo_tool):
        """Test updating todo priority."""
        input_data = TodoUpdateInput(
            id="test_todo_456",
            priority=TodoPriority.HIGH
        )

        result = await todo_tool.update_todo(input_data)

        assert result.success is True
        assert "priority" in result.changes

    @pytest.mark.asyncio
    async def test_update_todo_due_date(self, todo_tool):
        """Test updating todo due date."""
        input_data = TodoUpdateInput(
            id="test_todo_789",
            due_date="next friday"
        )

        result = await todo_tool.update_todo(input_data)

        assert result.success is True
        assert "due_date" in result.changes

    @pytest.mark.asyncio
    async def test_update_todo_multiple_fields(self, todo_tool):
        """Test updating multiple todo fields at once."""
        input_data = TodoUpdateInput(
            id="test_todo_multi",
            title="Multi-field Update",
            priority=TodoPriority.LOW,
            due_date="today"
        )

        result = await todo_tool.update_todo(input_data)

        assert result.success is True
        assert len(result.changes) >= 2


class TestTodoCompleteOperations:
    """Test todo completion operations."""

    @pytest.fixture
    def todo_tool(self):
        """Create a TodoTool instance."""
        return TodoTool()

    @pytest.mark.asyncio
    async def test_complete_todo(self, todo_tool):
        """Test completing a todo."""
        input_data = TodoCompleteInput(
            id="test_todo_complete",
            completed=True
        )

        result = await todo_tool.complete_todo(input_data)

        assert isinstance(result, TodoCompleteOutput)
        assert result.success is True
        assert "completed" in result.message

    @pytest.mark.asyncio
    async def test_uncomplete_todo(self, todo_tool):
        """Test marking a todo as incomplete."""
        input_data = TodoCompleteInput(
            id="test_todo_uncomplete",
            completed=False
        )

        result = await todo_tool.complete_todo(input_data)

        assert result.success is True
        assert "uncompleted" in result.message


class TestTodoDeleteOperations:
    """Test todo deletion operations."""

    @pytest.fixture
    def todo_tool(self):
        """Create a TodoTool instance."""
        return TodoTool()

    @pytest.mark.asyncio
    async def test_delete_todo(self, todo_tool):
        """Test deleting a todo."""
        input_data = TodoDeleteInput(id="test_todo_delete")

        result = await todo_tool.delete_todo(input_data)

        assert isinstance(result, TodoDeleteOutput)
        assert result.success is True
        assert result.deleted_todo is not None


class TestTodoHelperMethods:
    """Test helper methods of the TodoTool."""

    @pytest.fixture
    def todo_tool(self):
        """Create a TodoTool instance."""
        return TodoTool()

    def test_parse_natural_date_today(self, todo_tool):
        """Test parsing 'today'."""
        result = todo_tool._parse_natural_date("today")

        assert result is not None
        assert result.date() == datetime.now().date()

    def test_parse_natural_date_tomorrow(self, todo_tool):
        """Test parsing 'tomorrow'."""
        result = todo_tool._parse_natural_date("tomorrow")

        assert result is not None
        expected = datetime.now().date() + timedelta(days=1)
        assert result.date() == expected

    def test_parse_natural_date_next_week(self, todo_tool):
        """Test parsing 'next week'."""
        result = todo_tool._parse_natural_date("next week")

        assert result is not None
        # Should be in the future
        assert result.date() > datetime.now().date()

    def test_parse_natural_date_next_friday(self, todo_tool):
        """Test parsing 'next friday'."""
        result = todo_tool._parse_natural_date("next friday")

        assert result is not None
        assert result.weekday() == 4  # Friday

    def test_parse_natural_date_empty(self, todo_tool):
        """Test parsing empty string."""
        result = todo_tool._parse_natural_date("")

        assert result is None

    def test_parse_natural_date_none(self, todo_tool):
        """Test parsing None."""
        result = todo_tool._parse_natural_date(None)

        assert result is None

    def test_priority_to_todoist(self, todo_tool):
        """Test priority conversion to Todoist format."""
        assert todo_tool._priority_to_todoist(TodoPriority.LOW) == 1
        assert todo_tool._priority_to_todoist(TodoPriority.MEDIUM) == 2
        assert todo_tool._priority_to_todoist(TodoPriority.HIGH) == 3
        assert todo_tool._priority_to_todoist(TodoPriority.URGENT) == 4

    def test_generate_work_todos(self, todo_tool):
        """Test work todo generation."""
        now = datetime.now()
        todos = todo_tool._generate_work_todos(now)

        assert isinstance(todos, list)
        for todo in todos:
            assert isinstance(todo, TodoItem)
            assert todo.bucket == TodoBucket.WORK

    def test_generate_home_todos(self, todo_tool):
        """Test home todo generation."""
        now = datetime.now()
        todos = todo_tool._generate_home_todos(now)

        assert isinstance(todos, list)
        for todo in todos:
            assert todo.bucket == TodoBucket.HOME

    def test_generate_errands_todos(self, todo_tool):
        """Test errands todo generation."""
        now = datetime.now()
        todos = todo_tool._generate_errands_todos(now)

        assert isinstance(todos, list)
        for todo in todos:
            assert todo.bucket == TodoBucket.ERRANDS

    def test_generate_personal_todos(self, todo_tool):
        """Test personal todo generation."""
        now = datetime.now()
        todos = todo_tool._generate_personal_todos(now)

        assert isinstance(todos, list)
        for todo in todos:
            assert todo.bucket == TodoBucket.PERSONAL

    def test_todo_item_structure(self, todo_tool):
        """Test that generated todos have proper structure."""
        now = datetime.now()
        todos = todo_tool._generate_work_todos(now)

        for todo in todos:
            assert todo.id is not None
            assert todo.title is not None
            assert todo.priority in [TodoPriority.LOW, TodoPriority.MEDIUM,
                                    TodoPriority.HIGH, TodoPriority.URGENT]
            assert isinstance(todo.completed, bool)
            assert todo.created_at is not None

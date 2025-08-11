"""Todo tool for listing task items from different buckets."""

import asyncio
from datetime import datetime, timedelta
from typing import List
import random

from ..schemas.todo import TodoInput, TodoOutput, TodoItem, TodoBucket, TodoPriority
from ..utils.logging import get_logger, log_tool_call
from ..config import get_settings

logger = get_logger("todo_tool")


class TodoTool:
    """Tool for listing todo items. Supports mock data and future integration with task management services."""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def list_todos(self, input_data: TodoInput) -> TodoOutput:
        """
        List todo items from a specific bucket.
        
        Args:
            input_data: TodoInput with bucket and filtering options
            
        Returns:
            TodoOutput with list of todo items
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Getting todos from bucket '{input_data.bucket}' (include_completed: {input_data.include_completed})")
            
            # For now, use mock data. In production, this would integrate with Todoist, Any.do, etc.
            todos = await self._get_todos_for_bucket(input_data.bucket, input_data.include_completed)
            
            # Calculate counts
            completed_count = sum(1 for todo in todos if todo.completed)
            pending_count = len(todos) - completed_count
            
            result = TodoOutput(
                bucket=input_data.bucket,
                items=todos,
                total_items=len(todos),
                completed_count=completed_count,
                pending_count=pending_count
            )
            
            # Log the successful tool call
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("todo.list", input_data.dict(), duration_ms)
            
            return result
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("todo.list", input_data.dict(), duration_ms)
            logger.error(f"Error getting todo items: {e}")
            raise
    
    async def _get_todos_for_bucket(self, bucket: TodoBucket, include_completed: bool) -> List[TodoItem]:
        """Get todo items for a specific bucket."""
        
        if self.settings.todoist_api_key:
            # TODO: Implement Todoist API integration
            logger.info("Todoist integration not yet implemented, using mock data")
            return await self._get_mock_todos(bucket, include_completed)
        else:
            logger.info("No todo service configured, using mock data")
            return await self._get_mock_todos(bucket, include_completed)
    
    async def _get_mock_todos(self, bucket: TodoBucket, include_completed: bool) -> List[TodoItem]:
        """Generate realistic mock todo items for the given bucket."""
        
        now = datetime.now()
        todos = []
        
        # Generate different todos based on bucket
        if bucket == TodoBucket.WORK:
            todos.extend(self._generate_work_todos(now))
        elif bucket == TodoBucket.HOME:
            todos.extend(self._generate_home_todos(now))
        elif bucket == TodoBucket.ERRANDS:
            todos.extend(self._generate_errands_todos(now))
        elif bucket == TodoBucket.PERSONAL:
            todos.extend(self._generate_personal_todos(now))
        
        # Filter out completed items if not requested
        if not include_completed:
            todos = [todo for todo in todos if not todo.completed]
        
        # Sort by priority (urgent first) then by due date
        priority_order = {TodoPriority.URGENT: 0, TodoPriority.HIGH: 1, TodoPriority.MEDIUM: 2, TodoPriority.LOW: 3}
        todos.sort(key=lambda x: (priority_order[x.priority], x.due_date or datetime.max))
        
        return todos
    
    def _generate_work_todos(self, base_time: datetime) -> List[TodoItem]:
        """Generate mock work-related todos."""
        work_tasks = [
            ("Review quarterly reports", TodoPriority.HIGH, ["reports", "quarterly"], 1),
            ("Update project documentation", TodoPriority.MEDIUM, ["documentation", "project"], 2),
            ("Prepare for client presentation", TodoPriority.HIGH, ["presentation", "client"], 0),
            ("Code review for PR #123", TodoPriority.MEDIUM, ["code-review", "pr"], 0),
            ("Team meeting prep", TodoPriority.LOW, ["meeting", "prep"], 1),
            ("Submit expense report", TodoPriority.MEDIUM, ["expenses", "admin"], 3),
            ("Update dependencies in project", TodoPriority.LOW, ["maintenance", "deps"], 7),
            ("Plan sprint retrospective", TodoPriority.MEDIUM, ["sprint", "retro"], 5),
        ]
        
        todos = []
        selected_tasks = random.sample(work_tasks, k=random.randint(3, 6))
        
        for i, (title, priority, tags, due_days) in enumerate(selected_tasks):
            completed = random.random() < 0.2  # 20% chance of being completed
            due_date = base_time + timedelta(days=due_days) if due_days >= 0 else None
            
            todos.append(TodoItem(
                id=f"work_todo_{i+1}",
                title=title,
                priority=priority,
                completed=completed,
                created_at=base_time - timedelta(days=random.randint(1, 10)),
                due_date=due_date,
                bucket=TodoBucket.WORK,
                tags=tags
            ))
        
        return todos
    
    def _generate_home_todos(self, base_time: datetime) -> List[TodoItem]:
        """Generate mock home-related todos."""
        home_tasks = [
            ("Clean the garage", TodoPriority.LOW, ["cleaning", "garage"], 14),
            ("Fix leaky faucet", TodoPriority.MEDIUM, ["maintenance", "plumbing"], 3),
            ("Organize home office", TodoPriority.LOW, ["organization", "office"], 7),
            ("Pay utility bills", TodoPriority.HIGH, ["bills", "utilities"], 2),
            ("Schedule HVAC maintenance", TodoPriority.MEDIUM, ["maintenance", "hvac"], 10),
            ("Deep clean kitchen", TodoPriority.MEDIUM, ["cleaning", "kitchen"], 5),
            ("Update home insurance", TodoPriority.LOW, ["insurance", "admin"], 30),
            ("Plant spring garden", TodoPriority.LOW, ["gardening", "spring"], 21),
        ]
        
        todos = []
        selected_tasks = random.sample(home_tasks, k=random.randint(2, 5))
        
        for i, (title, priority, tags, due_days) in enumerate(selected_tasks):
            completed = random.random() < 0.3  # 30% chance of being completed
            due_date = base_time + timedelta(days=due_days) if due_days >= 0 else None
            
            todos.append(TodoItem(
                id=f"home_todo_{i+1}",
                title=title,
                priority=priority,
                completed=completed,
                created_at=base_time - timedelta(days=random.randint(1, 7)),
                due_date=due_date,
                bucket=TodoBucket.HOME,
                tags=tags
            ))
        
        return todos
    
    def _generate_errands_todos(self, base_time: datetime) -> List[TodoItem]:
        """Generate mock errand todos."""
        errand_tasks = [
            ("Grocery shopping", TodoPriority.MEDIUM, ["shopping", "food"], 1),
            ("Pick up dry cleaning", TodoPriority.LOW, ["pickup", "clothes"], 2),
            ("Go to bank", TodoPriority.MEDIUM, ["banking", "finance"], 1),
            ("Buy birthday gift", TodoPriority.HIGH, ["gift", "birthday"], 3),
            ("Post office - mail package", TodoPriority.MEDIUM, ["shipping", "mail"], 2),
            ("Pharmacy pickup", TodoPriority.MEDIUM, ["health", "pharmacy"], 1),
            ("Return library books", TodoPriority.LOW, ["library", "books"], 5),
            ("Hardware store - get screws", TodoPriority.LOW, ["hardware", "supplies"], 7),
        ]
        
        todos = []
        selected_tasks = random.sample(errand_tasks, k=random.randint(2, 4))
        
        for i, (title, priority, tags, due_days) in enumerate(selected_tasks):
            completed = random.random() < 0.4  # 40% chance of being completed (errands get done faster)
            due_date = base_time + timedelta(days=due_days) if due_days >= 0 else None
            
            todos.append(TodoItem(
                id=f"errands_todo_{i+1}",
                title=title,
                priority=priority,
                completed=completed,
                created_at=base_time - timedelta(days=random.randint(1, 5)),
                due_date=due_date,
                bucket=TodoBucket.ERRANDS,
                tags=tags
            ))
        
        return todos
    
    def _generate_personal_todos(self, base_time: datetime) -> List[TodoItem]:
        """Generate mock personal todos."""
        personal_tasks = [
            ("Call mom", TodoPriority.MEDIUM, ["family", "call"], 2),
            ("Read 'The Great Gatsby'", TodoPriority.LOW, ["reading", "books"], 30),
            ("Plan weekend trip", TodoPriority.MEDIUM, ["travel", "planning"], 14),
            ("Update resume", TodoPriority.LOW, ["career", "resume"], 60),
            ("Learn Spanish - Lesson 5", TodoPriority.LOW, ["learning", "spanish"], 7),
            ("Schedule dentist appointment", TodoPriority.MEDIUM, ["health", "dentist"], 10),
            ("Backup photos to cloud", TodoPriority.LOW, ["tech", "backup"], 21),
            ("Write in journal", TodoPriority.LOW, ["writing", "journal"], 1),
        ]
        
        todos = []
        selected_tasks = random.sample(personal_tasks, k=random.randint(3, 5))
        
        for i, (title, priority, tags, due_days) in enumerate(selected_tasks):
            completed = random.random() < 0.25  # 25% chance of being completed
            due_date = base_time + timedelta(days=due_days) if due_days >= 0 else None
            
            todos.append(TodoItem(
                id=f"personal_todo_{i+1}",
                title=title,
                priority=priority,
                completed=completed,
                created_at=base_time - timedelta(days=random.randint(1, 14)),
                due_date=due_date,
                bucket=TodoBucket.PERSONAL,
                tags=tags
            ))
        
        return todos

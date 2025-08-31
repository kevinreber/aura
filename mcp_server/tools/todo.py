"""Todo tool with full CRUD operations using Todoist API integration."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import random
import re
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

try:
    from todoist_api_python.api import TodoistAPI
    TODOIST_AVAILABLE = True
except ImportError:
    TODOIST_AVAILABLE = False

from ..schemas.todo import (
    TodoInput, TodoOutput, TodoItem, TodoBucket, TodoPriority,
    TodoCreateInput, TodoCreateOutput, TodoUpdateInput, TodoUpdateOutput,
    TodoCompleteInput, TodoCompleteOutput, TodoDeleteInput, TodoDeleteOutput
)
from ..utils.logging import get_logger, log_tool_call
from ..config import get_settings

logger = get_logger("todo_tool")


class TodoTool:
    """Tool for full CRUD operations on todo items using Todoist API integration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.api = None
        self._projects = {}  # Cache for project mapping
        
        if self.settings.todoist_api_key and TODOIST_AVAILABLE:
            try:
                self.api = TodoistAPI(self.settings.todoist_api_key)
                logger.info("Todoist API initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Todoist API: {e}")
                self.api = None
        else:
            logger.info("Todoist API not available - using mock data")
    
    async def list_todos(self, input_data: TodoInput) -> TodoOutput:
        """
        List todo items from a specific bucket or all buckets.
        
        Args:
            input_data: TodoInput with optional bucket and filtering options
            
        Returns:
            TodoOutput with list of todo items
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            if input_data.bucket:
                logger.info(f"Getting todos from bucket '{input_data.bucket}' (include_completed: {input_data.include_completed})")
                
                if self.api:
                    todos = await self._get_todoist_todos(input_data.bucket, input_data.include_completed)
                else:
                    todos = await self._get_mock_todos(input_data.bucket, input_data.include_completed)
            else:
                logger.info(f"Getting ALL todos from all projects (include_completed: {input_data.include_completed})")
                
                if self.api:
                    todos = await self._get_all_todoist_todos(input_data.include_completed)
                else:
                    # Get mock todos from all buckets
                    todos = []
                    for bucket in TodoBucket:
                        bucket_todos = await self._get_mock_todos(bucket, input_data.include_completed)
                        todos.extend(bucket_todos)
            
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
    
    async def create_todo(self, input_data: TodoCreateInput) -> TodoCreateOutput:
        """Create a new todo item."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Creating todo: {input_data.title}")
            
            if self.api:
                todo = await self._create_todoist_todo(input_data)
            else:
                # Mock implementation for testing
                todo = self._create_mock_todo(input_data)
            
            result = TodoCreateOutput(
                success=True,
                todo=todo,
                message="Todo created successfully"
            )
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("todo.create", input_data.dict(), duration_ms)
            
            return result
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("todo.create", input_data.dict(), duration_ms)
            logger.error(f"Error creating todo: {e}")
            return TodoCreateOutput(
                success=False,
                todo=None,
                message=f"Failed to create todo: {str(e)}"
            )
    
    async def update_todo(self, input_data: TodoUpdateInput) -> TodoUpdateOutput:
        """Update an existing todo item."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Updating todo: {input_data.id}")
            
            if self.api:
                todo, changes = await self._update_todoist_todo(input_data)
            else:
                # Mock implementation for testing
                todo, changes = self._update_mock_todo(input_data)
            
            result = TodoUpdateOutput(
                success=True,
                todo=todo,
                changes=changes,
                message="Todo updated successfully"
            )
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("todo.update", input_data.dict(), duration_ms)
            
            return result
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("todo.update", input_data.dict(), duration_ms)
            logger.error(f"Error updating todo: {e}")
            return TodoUpdateOutput(
                success=False,
                todo=None,
                changes=[],
                message=f"Failed to update todo: {str(e)}"
            )
    
    async def complete_todo(self, input_data: TodoCompleteInput) -> TodoCompleteOutput:
        """Mark a todo item as completed or uncompleted."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"{'Completing' if input_data.completed else 'Uncompleting'} todo: {input_data.id}")
            
            if self.api:
                todo = await self._complete_todoist_todo(input_data)
            else:
                # Mock implementation for testing
                todo = self._complete_mock_todo(input_data)
            
            action = "completed" if input_data.completed else "uncompleted"
            result = TodoCompleteOutput(
                success=True,
                todo=todo,
                message=f"Todo marked as {action}"
            )
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("todo.complete", input_data.dict(), duration_ms)
            
            return result
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("todo.complete", input_data.dict(), duration_ms)
            logger.error(f"Error completing todo: {e}")
            action = "complete" if input_data.completed else "uncomplete"
            return TodoCompleteOutput(
                success=False,
                todo=None,
                message=f"Failed to {action} todo: {str(e)}"
            )
    
    async def delete_todo(self, input_data: TodoDeleteInput) -> TodoDeleteOutput:
        """Delete a todo item."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Deleting todo: {input_data.id}")
            
            if self.api:
                deleted_todo = await self._delete_todoist_todo(input_data)
            else:
                # Mock implementation for testing  
                deleted_todo = self._delete_mock_todo(input_data)
            
            result = TodoDeleteOutput(
                success=True,
                deleted_todo=deleted_todo,
                message="Todo deleted successfully"
            )
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("todo.delete", input_data.dict(), duration_ms)
            
            return result
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("todo.delete", input_data.dict(), duration_ms)
            logger.error(f"Error deleting todo: {e}")
            return TodoDeleteOutput(
                success=False,
                deleted_todo=None,
                message=f"Failed to delete todo: {str(e)}"
            )
    
    async def _get_todoist_todos(self, bucket: TodoBucket, include_completed: bool) -> List[TodoItem]:
        """Get todo items from Todoist API for a specific bucket."""
        try:
            logger.info(f"Fetching Todoist todos for bucket: {bucket}")
            # Get project ID for bucket
            project_id = await self._get_or_create_project(bucket)
            logger.info(f"Got project ID: {project_id} for bucket: {bucket}")
            
            # Get tasks from Todoist
            tasks = self.api.get_tasks(project_id=project_id)
            logger.info(f"Retrieved {len(tasks)} tasks from Todoist")
            
            todos = []
            for task in tasks:
                # Convert Todoist task to our TodoItem
                todo_item = self._convert_todoist_task(task, bucket)
                
                # Filter completed tasks if needed
                if include_completed or not todo_item.completed:
                    todos.append(todo_item)
            
            # Sort by priority and due date
            priority_order = {TodoPriority.URGENT: 0, TodoPriority.HIGH: 1, TodoPriority.MEDIUM: 2, TodoPriority.LOW: 3}
            todos.sort(key=lambda x: (priority_order[x.priority], x.due_date or datetime.max))
            
            return todos
            
        except Exception as e:
            logger.error(f"Error getting Todoist todos: {e}")
            return await self._get_mock_todos(bucket, include_completed)
    
    async def _get_all_todoist_todos(self, include_completed: bool) -> List[TodoItem]:
        """Get all todo items from all Todoist projects."""
        try:
            logger.info("Fetching all todos from all Todoist projects")
            
            # Get all projects first for efficient bucket mapping
            try:
                projects = self.api.get_projects()
                logger.debug(f"Raw projects from API: {len(projects) if projects else 'None'}")
            except Exception as e:
                logger.error(f"Error getting projects from Todoist API: {e}")
                raise
            
            project_map = {}
            project_names = []
            for project in projects:
                try:
                    logger.debug(f"Processing project: {project}")
                    if hasattr(project, 'id') and hasattr(project, 'name'):
                        project_map[project.id] = project.name.lower()
                        project_names.append(project.name.lower())
                    else:
                        logger.warning(f"Project missing id or name attributes: {dir(project)}")
                except AttributeError as e:
                    logger.warning(f"Project missing expected attributes: {e}")
                    logger.debug(f"Project object type: {type(project)}")
                    logger.debug(f"Project object dir: {dir(project)}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error processing project: {e}")
                    continue
            logger.info(f"Found {len(projects)} projects: {project_names}")
            
            # Get all tasks (without project_id filter to get all tasks)
            try:
                tasks = self.api.get_tasks()
                logger.info(f"Retrieved {len(tasks) if tasks else 0} total tasks from Todoist")
                logger.debug(f"Tasks type: {type(tasks)}")
            except Exception as e:
                logger.error(f"Error getting tasks from Todoist API: {e}")
                raise
            
            todos = []
            for task in tasks:
                try:
                    # Check if task has required attributes
                    if not hasattr(task, 'project_id'):
                        logger.warning(f"Task missing project_id attribute, skipping")
                        continue
                        
                    # Determine bucket from project ID using our map
                    bucket = self._map_project_to_bucket(task.project_id, project_map)
                    
                    # Convert Todoist task to our TodoItem
                    todo_item = self._convert_todoist_task(task, bucket)
                    
                    # Filter completed tasks if needed
                    if include_completed or not todo_item.completed:
                        todos.append(todo_item)
                except AttributeError as e:
                    logger.warning(f"Task object missing expected attributes: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing task: {e}")
                    continue
            
            logger.info(f"Processed {len(todos)} todos from all projects")
            
            # Sort by priority and due date
            priority_order = {TodoPriority.URGENT: 0, TodoPriority.HIGH: 1, TodoPriority.MEDIUM: 2, TodoPriority.LOW: 3}
            todos.sort(key=lambda x: (priority_order[x.priority], x.due_date or datetime.max))
            
            return todos
            
        except KeyError as e:
            if 'can_assign_tasks' in str(e):
                logger.warning("Todoist API response missing 'can_assign_tasks' field - this is a known API inconsistency, falling back to mock data")
            else:
                logger.error(f"Todoist API KeyError: {e}")
            # Fall back to mock todos
            todos = []
            for bucket in TodoBucket:
                bucket_todos = await self._get_mock_todos(bucket, include_completed)
                todos.extend(bucket_todos)
            return todos
        except Exception as e:
            logger.error(f"Error getting all Todoist todos: {e}")
            logger.debug(f"Error type: {type(e).__name__}")
            
            # Fall back to getting mock todos from all buckets
            logger.info("Falling back to mock todos due to Todoist API error")
            todos = []
            for bucket in TodoBucket:
                bucket_todos = await self._get_mock_todos(bucket, include_completed)
                todos.extend(bucket_todos)
            return todos
    
    async def _create_todoist_todo(self, input_data: TodoCreateInput) -> TodoItem:
        """Create a todo in Todoist."""
        try:
            # Get project ID for bucket
            project_id = await self._get_or_create_project(input_data.bucket)
            
            # Parse due date
            due_date = None
            if input_data.due_date:
                due_date = self._parse_natural_date(input_data.due_date)
            
            # Create task in Todoist
            task_data = {
                "content": input_data.title,
                "project_id": project_id,
                "priority": self._priority_to_todoist(input_data.priority),
            }
            
            if due_date:
                task_data["due_string"] = input_data.due_date
            
            if input_data.description:
                task_data["description"] = input_data.description
            
            if input_data.tags:
                task_data["labels"] = input_data.tags
            
            task = self.api.add_task(**task_data)
            
            # Convert back to our format
            return self._convert_todoist_task(task, input_data.bucket)
            
        except Exception as e:
            logger.error(f"Error creating Todoist todo: {e}")
            raise
    
    async def _update_todoist_todo(self, input_data: TodoUpdateInput) -> tuple[TodoItem, List[str]]:
        """Update a todo in Todoist."""
        try:
            # Get the current task
            task = self.api.get_task(input_data.id)
            
            changes = []
            update_data = {}
            
            # Build update data
            if input_data.title:
                update_data["content"] = input_data.title
                changes.append("title")
            
            if input_data.priority:
                update_data["priority"] = self._priority_to_todoist(input_data.priority)
                changes.append("priority")
            
            if input_data.due_date:
                update_data["due_string"] = input_data.due_date
                changes.append("due_date")
            
            if input_data.description:
                update_data["description"] = input_data.description
                changes.append("description")
            
            if input_data.tags:
                update_data["labels"] = input_data.tags
                changes.append("tags")
            
            # Update task in Todoist
            if update_data:
                success = self.api.update_task(task_id=input_data.id, **update_data)
                if not success:
                    raise Exception("Failed to update task in Todoist")
            
            # Get updated task
            updated_task = self.api.get_task(input_data.id)
            
            # Determine bucket from project
            bucket = self._get_bucket_from_project_id(updated_task.project_id)
            
            return self._convert_todoist_task(updated_task, bucket), changes
            
        except Exception as e:
            logger.error(f"Error updating Todoist todo: {e}")
            raise
    
    async def _complete_todoist_todo(self, input_data: TodoCompleteInput) -> TodoItem:
        """Complete or uncomplete a todo in Todoist."""
        try:
            if input_data.completed:
                success = self.api.close_task(task_id=input_data.id)
            else:
                success = self.api.reopen_task(task_id=input_data.id)
            
            if not success:
                raise Exception("Failed to update task completion status")
            
            # Get updated task
            task = self.api.get_task(input_data.id)
            
            # Determine bucket from project
            bucket = self._get_bucket_from_project_id(task.project_id)
            
            return self._convert_todoist_task(task, bucket)
            
        except Exception as e:
            logger.error(f"Error completing Todoist todo: {e}")
            raise
    
    async def _delete_todoist_todo(self, input_data: TodoDeleteInput) -> TodoItem:
        """Delete a todo from Todoist."""
        try:
            # Get task before deletion for audit trail
            task = self.api.get_task(input_data.id)
            bucket = self._get_bucket_from_project_id(task.project_id)
            todo_item = self._convert_todoist_task(task, bucket)
            
            # Delete task
            success = self.api.delete_task(task_id=input_data.id)
            if not success:
                raise Exception("Failed to delete task from Todoist")
            
            return todo_item
            
        except Exception as e:
            logger.error(f"Error deleting Todoist todo: {e}")
            raise
    
    async def _get_or_create_project(self, bucket: TodoBucket) -> str:
        """Get or create Todoist project for bucket."""
        if bucket.value in self._projects:
            logger.info(f"Using cached project ID for bucket {bucket}: {self._projects[bucket.value]}")
            return self._projects[bucket.value]
        
        try:
            logger.info(f"Getting projects from Todoist API for bucket: {bucket}")
            # Get all projects
            projects = self.api.get_projects()
            logger.info(f"Got {len(projects)} projects from Todoist")
            
            # Look for existing project
            project_name = bucket.value.title()
            logger.info(f"Looking for project named: {project_name}")
            for project in projects:
                try:
                    if hasattr(project, 'name') and hasattr(project, 'id'):
                        if project.name.lower() == project_name.lower():
                            logger.info(f"Found existing project: {project.name} (ID: {project.id})")
                            self._projects[bucket.value] = project.id
                            return project.id
                except AttributeError as e:
                    logger.warning(f"Project object missing expected attributes: {e}")
                    continue
            
            # Create new project
            logger.info(f"Creating new project: {project_name}")
            project = self.api.add_project(name=project_name)
            logger.info(f"Created project: {project.name} (ID: {project.id})")
            self._projects[bucket.value] = project.id
            return project.id
            
        except Exception as e:
            logger.error(f"Error getting/creating project: {e}")
            # Return default project ID (Inbox)
            return "2254899858"  # User's actual Inbox project ID
    
    def _convert_todoist_task(self, task: Any, bucket: TodoBucket) -> TodoItem:
        """Convert Todoist task to TodoItem."""
        try:
            # Convert priority
            priority_map = {1: TodoPriority.LOW, 2: TodoPriority.MEDIUM, 3: TodoPriority.HIGH, 4: TodoPriority.URGENT}
            priority = priority_map.get(getattr(task, 'priority', 1), TodoPriority.MEDIUM)
            
            # Parse dates
            created_at = datetime.fromisoformat(getattr(task, 'created_at', '').replace('Z', '+00:00'))
            due_date = None
            if hasattr(task, 'due') and task.due:
                try:
                    if hasattr(task.due, 'datetime') and task.due.datetime:
                        due_date = datetime.fromisoformat(task.due.datetime.replace('Z', '+00:00'))
                    elif hasattr(task.due, 'date') and task.due.date:
                        due_date = datetime.fromisoformat(task.due.date + 'T17:00:00+00:00')
                except Exception as e:
                    logger.debug(f"Could not parse due date: {e}")
            
            # Get labels (tags)
            tags = getattr(task, 'labels', [])
        
            return TodoItem(
                id=getattr(task, 'id', 'unknown'),
                title=getattr(task, 'content', 'Untitled'),
                priority=priority,
                completed=getattr(task, 'is_completed', False),
                created_at=created_at,
                due_date=due_date,
                bucket=bucket,
                tags=tags
            )
        except Exception as e:
            logger.error(f"Error converting Todoist task {getattr(task, 'id', 'unknown')}: {e}")
            # Return a basic TodoItem with available data
            return TodoItem(
                id=getattr(task, 'id', 'unknown'),
                title=getattr(task, 'content', 'Untitled'),
                priority=TodoPriority.MEDIUM,
                completed=getattr(task, 'is_completed', False),
                created_at=datetime.now(),
                due_date=None,
                bucket=bucket,
                tags=[]
            )
    
    def _get_bucket_from_project_id(self, project_id: str) -> TodoBucket:
        """Get bucket from project ID."""
        for bucket_name, cached_project_id in self._projects.items():
            if cached_project_id == project_id:
                return TodoBucket(bucket_name)
        return TodoBucket.PERSONAL  # Default
    
    def _determine_bucket_from_project(self, project_id: str) -> TodoBucket:
        """Determine bucket from project ID by checking project name."""
        try:
            # First check if we have it cached
            if hasattr(self, '_projects'):
                for bucket_name, cached_project_id in self._projects.items():
                    if cached_project_id == project_id:
                        return TodoBucket(bucket_name)
            
            # If not cached, get project info from Todoist
            projects = self.api.get_projects()
            for project in projects:
                if project.id == project_id:
                    project_name = project.name.lower()
                    
                    # Map project names to buckets
                    if project_name in ['work']:
                        return TodoBucket.WORK
                    elif project_name in ['home']:
                        return TodoBucket.HOME
                    elif project_name in ['errands']:
                        return TodoBucket.ERRANDS
                    elif project_name in ['personal']:
                        return TodoBucket.PERSONAL
                    else:
                        # For projects like "Inbox" or others, default to PERSONAL
                        return TodoBucket.PERSONAL
                        
            # Default fallback
            return TodoBucket.PERSONAL
            
        except Exception as e:
            logger.error(f"Error determining bucket from project {project_id}: {e}")
            return TodoBucket.PERSONAL
    
    def _map_project_to_bucket(self, project_id: str, project_map: dict) -> TodoBucket:
        """Efficiently map project ID to bucket using project name map."""
        try:
            project_name = project_map.get(project_id, '').lower()
            
            # Map project names to buckets
            if project_name in ['work']:
                return TodoBucket.WORK
            elif project_name in ['home']:
                return TodoBucket.HOME
            elif project_name in ['errands']:
                return TodoBucket.ERRANDS
            elif project_name in ['personal']:
                return TodoBucket.PERSONAL
            else:
                # For projects like "Inbox" or others, default to PERSONAL
                logger.debug(f"Unknown project name '{project_name}' (ID: {project_id}), defaulting to PERSONAL")
                return TodoBucket.PERSONAL
                
        except Exception as e:
            logger.error(f"Error mapping project {project_id} to bucket: {e}")
            return TodoBucket.PERSONAL
    
    def _priority_to_todoist(self, priority: TodoPriority) -> int:
        """Convert our priority to Todoist priority."""
        priority_map = {
            TodoPriority.LOW: 1,
            TodoPriority.MEDIUM: 2, 
            TodoPriority.HIGH: 3,
            TodoPriority.URGENT: 4
        }
        return priority_map.get(priority, 2)
    
    def _parse_natural_date(self, date_string: str) -> Optional[datetime]:
        """Parse natural language date strings."""
        if not date_string:
            return None
        
        date_string = date_string.lower().strip()
        now = datetime.now()
        
        # Handle common patterns
        if date_string in ['today']:
            return now.replace(hour=17, minute=0, second=0, microsecond=0)
        elif date_string in ['tomorrow']:
            return (now + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
        elif 'next week' in date_string:
            days_ahead = 7 - now.weekday() + 0  # Next Monday
            return (now + timedelta(days=days_ahead)).replace(hour=17, minute=0, second=0, microsecond=0)
        elif 'next friday' in date_string:
            days_ahead = (4 - now.weekday()) % 7
            if days_ahead <= 0:  # If it's Friday or after, go to next Friday
                days_ahead += 7
            return (now + timedelta(days=days_ahead)).replace(hour=17, minute=0, second=0, microsecond=0)
        
        # Try to parse with dateutil
        try:
            parsed_date = date_parser.parse(date_string, default=now)
            return parsed_date
        except:
            return None
    
    # Mock data methods (keep for fallback)
    def _create_mock_todo(self, input_data: TodoCreateInput) -> TodoItem:
        """Create mock todo for testing."""
        now = datetime.now()
        due_date = None
        if input_data.due_date:
            due_date = self._parse_natural_date(input_data.due_date)
        
        return TodoItem(
            id=f"mock_todo_{int(now.timestamp())}",
            title=input_data.title,
            priority=input_data.priority,
            completed=False,
            created_at=now,
            due_date=due_date,
            bucket=input_data.bucket,
            tags=input_data.tags or []
        )
    
    def _update_mock_todo(self, input_data: TodoUpdateInput) -> tuple[TodoItem, List[str]]:
        """Update mock todo for testing."""
        changes = []
        if input_data.title: changes.append("title")
        if input_data.priority: changes.append("priority")  
        if input_data.due_date: changes.append("due_date")
        
        mock_todo = TodoItem(
            id=input_data.id,
            title=input_data.title or "Updated mock todo",
            priority=input_data.priority or TodoPriority.MEDIUM,
            completed=False,
            created_at=datetime.now() - timedelta(days=1),
            due_date=self._parse_natural_date(input_data.due_date) if input_data.due_date else None,
            bucket=TodoBucket.PERSONAL,
            tags=input_data.tags or []
        )
        
        return mock_todo, changes
    
    def _complete_mock_todo(self, input_data: TodoCompleteInput) -> TodoItem:
        """Complete mock todo for testing."""
        return TodoItem(
            id=input_data.id,
            title="Mock todo",
            priority=TodoPriority.MEDIUM,
            completed=input_data.completed,
            created_at=datetime.now() - timedelta(days=1),
            due_date=None,
            bucket=TodoBucket.PERSONAL,
            tags=[]
        )
    
    def _delete_mock_todo(self, input_data: TodoDeleteInput) -> TodoItem:
        """Delete mock todo for testing."""
        return TodoItem(
            id=input_data.id,
            title="Deleted mock todo",
            priority=TodoPriority.MEDIUM,
            completed=False,
            created_at=datetime.now() - timedelta(days=1),
            due_date=None,
            bucket=TodoBucket.PERSONAL,
            tags=[]
        )
    
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

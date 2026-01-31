"""Pydantic schemas for todo tool validation."""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime


class TodoBucket(str, Enum):
    """Valid todo buckets for organization."""
    WORK = "work"
    HOME = "home"  
    ERRANDS = "errands"
    PERSONAL = "personal"


class TodoPriority(str, Enum):
    """Valid priority levels for todo items."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TodoInput(BaseModel):
    """Input schema for todo.list tool."""
    
    bucket: Optional[TodoBucket] = Field(
        default=None,
        description="Category/bucket to list todos from. If not specified, returns all todos from all projects."
    )
    include_completed: bool = Field(
        default=False,
        description="Whether to include completed todo items"
    )


class TodoItem(BaseModel):
    """Schema for a single todo item."""
    
    id: str = Field(description="Unique todo item identifier")
    title: str = Field(description="Todo item title/description")
    priority: TodoPriority = Field(description="Priority level of the todo item")
    completed: bool = Field(default=False, description="Whether the item is completed")
    created_at: datetime = Field(description="When the todo was created")
    due_date: Optional[datetime] = Field(default=None, description="Due date if set")
    bucket: TodoBucket = Field(description="Category/bucket this todo belongs to")
    tags: Optional[List[str]] = Field(default=None, description="Tags associated with the todo")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "todo_123",
                "title": "Review quarterly reports",
                "priority": "medium",
                "completed": False,
                "created_at": "2024-01-10T09:00:00Z",
                "due_date": "2024-01-15T17:00:00Z",
                "bucket": "work",
                "tags": ["reports", "quarterly"]
            }
        }


class TodoOutput(BaseModel):
    """Output schema for todo.list tool."""
    
    bucket: Optional[TodoBucket] = Field(description="Bucket/category queried (null if all buckets)")
    items: List[TodoItem] = Field(description="List of todo items")
    total_items: int = Field(description="Total number of items found")
    completed_count: int = Field(description="Number of completed items")
    pending_count: int = Field(description="Number of pending items")
    
    class Config:
        json_schema_extra = {
            "example": {
                "bucket": "work",
                "items": [
                    {
                        "id": "todo_123",
                        "title": "Review quarterly reports",
                        "priority": "medium",
                        "completed": False,
                        "created_at": "2024-01-10T09:00:00Z",
                        "due_date": "2024-01-15T17:00:00Z",
                        "bucket": "work",
                        "tags": ["reports", "quarterly"]
                    }
                ],
                "total_items": 1,
                "completed_count": 0,
                "pending_count": 1
            }
        }


# CRUD Operation Schemas

class TodoCreateInput(BaseModel):
    """Input schema for todo.create tool."""
    
    title: str = Field(description="Todo item title/description")
    priority: TodoPriority = Field(default=TodoPriority.MEDIUM, description="Priority level")
    bucket: TodoBucket = Field(default=TodoBucket.PERSONAL, description="Category/bucket for the todo")
    due_date: Optional[str] = Field(default=None, description="Due date in natural language (e.g., 'tomorrow', 'next Friday', '2024-01-15')")
    tags: Optional[List[str]] = Field(default=None, description="Tags to associate with the todo")
    description: Optional[str] = Field(default=None, description="Additional description or notes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Review quarterly reports",
                "priority": "high",
                "bucket": "work",
                "due_date": "next Friday",
                "tags": ["reports", "quarterly"],
                "description": "Need to review Q4 financial reports before board meeting"
            }
        }


class TodoCreateOutput(BaseModel):
    """Output schema for todo.create tool."""
    
    success: bool = Field(description="Whether the todo was created successfully")
    todo: Optional[TodoItem] = Field(description="The created todo item")
    message: str = Field(description="Success or error message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "todo": {
                    "id": "todo_123",
                    "title": "Review quarterly reports",
                    "priority": "high",
                    "completed": False,
                    "created_at": "2024-01-10T09:00:00Z",
                    "due_date": "2024-01-15T17:00:00Z",
                    "bucket": "work",
                    "tags": ["reports", "quarterly"]
                },
                "message": "Todo created successfully"
            }
        }


class TodoUpdateInput(BaseModel):
    """Input schema for todo.update tool."""
    
    id: str = Field(description="Unique todo item identifier to update")
    title: Optional[str] = Field(default=None, description="New title/description")
    priority: Optional[TodoPriority] = Field(default=None, description="New priority level")
    due_date: Optional[str] = Field(default=None, description="New due date in natural language")
    tags: Optional[List[str]] = Field(default=None, description="New tags (replaces existing)")
    description: Optional[str] = Field(default=None, description="New description or notes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "todo_123",
                "title": "Review Q4 financial reports (updated)",
                "priority": "urgent",
                "due_date": "tomorrow"
            }
        }


class TodoUpdateOutput(BaseModel):
    """Output schema for todo.update tool."""
    
    success: bool = Field(description="Whether the todo was updated successfully")
    todo: Optional[TodoItem] = Field(description="The updated todo item")
    changes: List[str] = Field(description="List of fields that were changed")
    message: str = Field(description="Success or error message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "todo": {
                    "id": "todo_123",
                    "title": "Review Q4 financial reports (updated)",
                    "priority": "urgent",
                    "completed": False,
                    "created_at": "2024-01-10T09:00:00Z",
                    "due_date": "2024-01-11T17:00:00Z",
                    "bucket": "work",
                    "tags": ["reports", "quarterly"]
                },
                "changes": ["title", "priority", "due_date"],
                "message": "Todo updated successfully"
            }
        }


class TodoCompleteInput(BaseModel):
    """Input schema for todo.complete tool."""
    
    id: str = Field(description="Unique todo item identifier to complete")
    completed: bool = Field(default=True, description="Whether to mark as completed (true) or uncompleted (false)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "todo_123",
                "completed": True
            }
        }


class TodoCompleteOutput(BaseModel):
    """Output schema for todo.complete tool."""
    
    success: bool = Field(description="Whether the todo status was updated successfully")
    todo: Optional[TodoItem] = Field(description="The updated todo item")
    message: str = Field(description="Success or error message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "todo": {
                    "id": "todo_123",
                    "title": "Review quarterly reports",
                    "priority": "high",
                    "completed": True,
                    "created_at": "2024-01-10T09:00:00Z",
                    "due_date": "2024-01-15T17:00:00Z",
                    "bucket": "work",
                    "tags": ["reports", "quarterly"]
                },
                "message": "Todo marked as completed"
            }
        }


class TodoDeleteInput(BaseModel):
    """Input schema for todo.delete tool."""
    
    id: str = Field(description="Unique todo item identifier to delete")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "todo_123"
            }
        }


class TodoDeleteOutput(BaseModel):
    """Output schema for todo.delete tool."""
    
    success: bool = Field(description="Whether the todo was deleted successfully")
    deleted_todo: Optional[TodoItem] = Field(description="The deleted todo item (for audit trail)")
    message: str = Field(description="Success or error message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "deleted_todo": {
                    "id": "todo_123",
                    "title": "Review quarterly reports",
                    "priority": "high",
                    "completed": False,
                    "created_at": "2024-01-10T09:00:00Z",
                    "due_date": "2024-01-15T17:00:00Z",
                    "bucket": "work",
                    "tags": ["reports", "quarterly"]
                },
                "message": "Todo deleted successfully"
            }
        }

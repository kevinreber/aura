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
    
    bucket: TodoBucket = Field(
        default=TodoBucket.WORK,
        description="Category/bucket to list todos from"
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
    
    bucket: TodoBucket = Field(description="Bucket/category queried")
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


from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime


class TaskUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    completed: bool = False
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

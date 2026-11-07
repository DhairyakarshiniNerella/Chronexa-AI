from pydantic import BaseModel
from datetime import datetime


# Model for creating a task
class TaskCreate(BaseModel):
    title: str
    description: str
    start_time: datetime
    end_time: datetime


# Model for updating a task
class TaskUpdate(BaseModel):
    title: str
    description: str
    completed: bool

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# Schema for creating a reminder
class ReminderCreate(BaseModel):

    title: str

    description: Optional[str] = None

    remind_at: datetime


# Schema for updating a reminder
class ReminderUpdate(BaseModel):

    title: str

    description: Optional[str] = None

    remind_at: datetime

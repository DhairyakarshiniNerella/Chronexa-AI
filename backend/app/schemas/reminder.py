
from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional


# Schema for creating a reminder
class ReminderCreate(BaseModel):

    title: str

    description: Optional[str] = None

    remind_at: datetime

    recurrence: Optional[str] = None

    recurrence_end_date: Optional[date] = None


# Schema for updating a reminder
class ReminderUpdate(BaseModel):

    title: str

    description: Optional[str] = None

    remind_at: datetime

    recurrence: Optional[str] = None

    recurrence_end_date: Optional[date] = None

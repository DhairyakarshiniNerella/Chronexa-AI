from pydantic import BaseModel
from datetime import datetime


# Schema for creating a schedule
class ScheduleCreate(BaseModel):
    title: str
    description: str
    start_time: datetime
    end_time: datetime


# Schema for updating a schedule
class ScheduleUpdate(BaseModel):
    title: str
    description: str
    start_time: datetime
    end_time: datetime
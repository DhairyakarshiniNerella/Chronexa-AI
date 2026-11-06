from pydantic import BaseModel


# Model for creating a task
class TaskCreate(BaseModel):
    title: str
    description: str


# Model for updating a task
class TaskUpdate(BaseModel):
    title: str
    description: str
    completed: bool
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# User Registration Schema
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


# User Login Schema
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# User Response Schema
class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# Task Creation Schema
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None


# Task Response Schema
class TaskResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
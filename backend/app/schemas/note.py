from pydantic import BaseModel


# Schema for creating a note
class NoteCreate(BaseModel):
    title: str
    content: str


# Schema for updating a note
class NoteUpdate(BaseModel):
    title: str
    content: str

import os

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from groq import Groq

from database import get_db
from models import Task, Schedule, Reminder, Note
from app.auth_dependencies import get_current_user


router = APIRouter(
    prefix="/ai",
    tags=["AI Assistant"]
)


# Chat request schema
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


# AI Chat endpoint
@router.post("/chat")
def chat_with_ai(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Groq API key is not configured"
        )

    try:
        # Get logged-in user's tasks
        tasks = db.query(Task).filter(
            Task.user_id == current_user.id
        ).all()

        # Get logged-in user's schedules
        schedules = db.query(Schedule).filter(
            Schedule.user_id == current_user.id
        ).all()

        # Get logged-in user's reminders
        reminders = db.query(Reminder).filter(
            Reminder.user_id == current_user.id
        ).all()

        # Get logged-in user's notes
        notes = db.query(Note).filter(
            Note.user_id == current_user.id
        ).all()

        # Prepare personal productivity information
        context = {
            "tasks": [
                {
                    "title": task.title,
                    "description": task.description,
                    "status": task.status
                }
                for task in tasks
            ],

            "schedules": [
                {
                    "title": schedule.title,
                    "start_time": str(schedule.start_time),
                    "end_time": str(schedule.end_time)
                }
                for schedule in schedules
            ],

            "reminders": [
                {
                    "title": reminder.title,
                    "remind_at": str(reminder.remind_at),
                    "is_sent": reminder.is_sent
                }
                for reminder in reminders
            ],

            "notes": [
                {
                    "title": note.title,
                    "content": note.content
                }
                for note in notes
            ]
        }

        client = Groq(api_key=api_key)

        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Chronexa AI, a friendly personal "
                        "productivity assistant.\n\n"

                        "You can help users organize tasks, schedules, "
                        "reminders and notes.\n\n"

                        "Use the following personal productivity data "
                        "to answer questions accurately:\n"
                        f"{context}\n\n"

                        "Only use the provided information. "
                        "Never invent tasks, schedules or reminders. "
                        "If information is unavailable, say so clearly. "
                        "Give simple, clear and useful answers."
                    )
                },

                {
                    "role": "user",
                    "content": request.message
                }
            ],

            temperature=0.5,
            max_completion_tokens=1024
        )

        ai_reply = completion.choices[0].message.content

        return {
            "reply": ai_reply,
            "user": current_user.email
        }

    except HTTPException:
        raise

    except Exception as e:
        print("GROQ ERROR:", str(e))

        raise HTTPException(
            status_code=502,
            detail="Unable to get a response from Chronexa AI"
        )

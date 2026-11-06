
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Reminder, User
from app.schemas.reminder import ReminderCreate, ReminderUpdate
from app.auth_dependencies import get_current_user


# Create Reminder router
router = APIRouter()


# Create a new reminder
@router.post("/reminders", status_code=201)
def create_reminder(
    reminder: ReminderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    new_reminder = Reminder(
        title=reminder.title,
        description=reminder.description,
        remind_at=reminder.remind_at,
        user_id=current_user.id
    )

    db.add(new_reminder)
    db.commit()
    db.refresh(new_reminder)

    return new_reminder


# Get all reminders for the logged-in user
@router.get("/reminders")
def get_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    reminders = db.query(Reminder).filter(
        Reminder.user_id == current_user.id
    ).order_by(Reminder.remind_at.asc()).all()

    return reminders


# Update a reminder
@router.put("/reminders/{reminder_id}")
def update_reminder(
    reminder_id: int,
    reminder: ReminderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    existing_reminder = db.query(Reminder).filter(
        Reminder.id == reminder_id,
        Reminder.user_id == current_user.id
    ).first()

    if not existing_reminder:
        raise HTTPException(
            status_code=404,
            detail="Reminder not found"
        )

    existing_reminder.title = reminder.title
    existing_reminder.description = reminder.description
    existing_reminder.remind_at = reminder.remind_at

    # Reset notification status when reminder is updated
    existing_reminder.is_sent = False

    db.commit()
    db.refresh(existing_reminder)

    return existing_reminder


# Delete a reminder
@router.delete("/reminders/{reminder_id}")
def delete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    existing_reminder = db.query(Reminder).filter(
        Reminder.id == reminder_id,
        Reminder.user_id == current_user.id
    ).first()

    if not existing_reminder:
        raise HTTPException(
            status_code=404,
            detail="Reminder not found"
        )

    db.delete(existing_reminder)
    db.commit()

    return {
        "message": "Reminder deleted successfully"
    }

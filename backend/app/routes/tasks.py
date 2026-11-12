from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Task, User, Schedule, Reminder
from app.schemas.task import TaskCreate, TaskUpdate
from app.auth_dependencies import get_current_user

router = APIRouter()


# GET - View logged-in user's tasks
@router.get("/tasks")
def get_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tasks = db.query(Task).filter(
        Task.user_id == current_user.id
    ).all()

    return {
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "completed": task.status == "Completed",
                "start_time": task.schedule.start_time if task.schedule else None
            }

            for task in tasks
        ]
    }


# POST - Create task with automatic schedule and reminder
@router.post("/tasks", status_code=201)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate selected time
    if task.end_time <= task.start_time:
        raise HTTPException(
            status_code=400,
            detail="End time must be after start time"
        )

    # Check for schedule conflicts
    conflict = db.query(Schedule).filter(
        Schedule.user_id == current_user.id,
        Schedule.start_time < task.end_time,
        Schedule.end_time > task.start_time
    ).first()

    if conflict:
        raise HTTPException(
            status_code=409,
            detail=f"You already have a schedule during this time: {conflict.title}"
        )

    try:
        # 1. Create task
        new_task = Task(
            user_id=current_user.id,
            title=task.title,
            description=task.description,
            status="Pending"
        )

        db.add(new_task)
        db.flush()

        # 2. Automatically create schedule
        new_schedule = Schedule(
            user_id=current_user.id,
            task_id=new_task.id,
            title=task.title,
            description=task.description,
            start_time=task.start_time,
            end_time=task.end_time
        )

        db.add(new_schedule)

        # 3. Automatically create reminder
        new_reminder = Reminder(
            user_id=current_user.id,
            task_id=new_task.id,
            title=task.title,
            description=task.description,
            remind_at=task.start_time
        )

        db.add(new_reminder)

        # Save everything together
        db.commit()

        db.refresh(new_task)
        db.refresh(new_schedule)
        db.refresh(new_reminder)

        return {
            "message": "Task, schedule and reminder created successfully",
            "task": {
                "id": new_task.id,
                "title": new_task.title,
                "description": new_task.description,
                "completed": False
            },
            "schedule": {
                "id": new_schedule.id,
                "start_time": new_schedule.start_time,
                "end_time": new_schedule.end_time
            },
            "reminder": {
                "id": new_reminder.id,
                "remind_at": new_reminder.remind_at
            }
        }

    except Exception:
        db.rollback()
        raise


# PUT - Update a task

@router.put("/tasks/{task_id}")
def update_task(
    task_id: int,
    updated_task: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    start_time = updated_task.start_time
    end_time = updated_task.end_time

    if start_time and end_time and end_time <= start_time:
        raise HTTPException(
            status_code=400,
            detail="End time must be after start time"
        )

    try:
        task.title = updated_task.title
        task.description = updated_task.description
        task.status = (
            "Completed" if updated_task.completed else "Pending"
        )

        if task.schedule:
            task.schedule.title = task.title
            task.schedule.description = task.description

            if start_time:
                task.schedule.start_time = start_time

            if end_time:
                task.schedule.end_time = end_time

            if task.schedule.end_time <= task.schedule.start_time:
                raise HTTPException(
                    status_code=400,
                    detail="End time must be after start time"
                )

        if task.reminder:
            task.reminder.title = task.title
            task.reminder.description = task.description

            if start_time:
                task.reminder.remind_at = start_time
                task.reminder.is_sent = False

        db.commit()
        db.refresh(task)

        return {
            "message": "Task and linked records updated successfully",
            "task": {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "completed": task.status == "Completed"
            }
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

# DELETE - Delete a task
@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    db.delete(task)
    db.commit()

    return {
        "message": "Task deleted successfully"
    }
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Schedule, User
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate
from app.auth_dependencies import get_current_user

router = APIRouter()


# ==========================================
# 1. CREATE SCHEDULE
# ==========================================

@router.post("/schedules", status_code=201)
def create_schedule(
    schedule: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if schedule.end_time <= schedule.start_time:
        raise HTTPException(
            status_code=400,
            detail="End time must be after start time"
        )

    new_schedule = Schedule(
        user_id=current_user.id,
        title=schedule.title,
        description=schedule.description,
        start_time=schedule.start_time,
        end_time=schedule.end_time
    )

    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)

    return {
        "message": "Schedule created successfully",
        "schedule": {
            "id": new_schedule.id,
            "title": new_schedule.title,
            "description": new_schedule.description,
            "start_time": new_schedule.start_time,
            "end_time": new_schedule.end_time
        }
    }


# ==========================================
# 2. GET ALL USER SCHEDULES
# ==========================================

@router.get("/schedules")
def get_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    schedules = db.query(Schedule).filter(
        Schedule.user_id == current_user.id
    ).order_by(Schedule.start_time.asc()).all()

    return {
        "message": "Schedules retrieved successfully",
        "schedules": [
            {
                
"id": schedule.id,
"title": schedule.title,
"description": schedule.description,
"start_time": schedule.start_time,
"end_time": schedule.end_time,
"task_id": schedule.task_id

            }
            for schedule in schedules
        ]
    }


# ==========================================
# 3. UPDATE SCHEDULE
# ==========================================

@router.put("/schedules/{schedule_id}")
def update_schedule(
    schedule_id: int,
    schedule: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    existing_schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.user_id == current_user.id
    ).first()

    if existing_schedule is None:
        raise HTTPException(
            status_code=404,
            detail="Schedule not found"
        )

    if schedule.end_time <= schedule.start_time:
        raise HTTPException(
            status_code=400,
            detail="End time must be after start time"
        )

    existing_schedule.title = schedule.title
    existing_schedule.description = schedule.description
    existing_schedule.start_time = schedule.start_time
    existing_schedule.end_time = schedule.end_time

    db.commit()
    db.refresh(existing_schedule)

    return {
        "message": "Schedule updated successfully",
        "schedule": {
            "id": existing_schedule.id,
            "title": existing_schedule.title,
            "description": existing_schedule.description,
            "start_time": existing_schedule.start_time,
            "end_time": existing_schedule.end_time
        }
    }


# ==========================================
# 4. DELETE SCHEDULE
# ==========================================

@router.delete("/schedules/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    existing_schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.user_id == current_user.id
    ).first()

    if existing_schedule is None:
        raise HTTPException(
            status_code=404,
            detail="Schedule not found"
        )

    db.delete(existing_schedule)
    db.commit()

    return {
        "message": "Schedule deleted successfully"
    }
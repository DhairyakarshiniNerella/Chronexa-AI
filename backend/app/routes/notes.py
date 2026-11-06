from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Note, User
from app.schemas.note import NoteCreate, NoteUpdate
from app.auth_dependencies import get_current_user


# Create Notes router
router = APIRouter()
# Create a new note
@router.post("/notes", status_code=201)
def create_note(
    note: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    new_note = Note(
        user_id=current_user.id,
        title=note.title,
        content=note.content
    )

    db.add(new_note)
    db.commit()
    db.refresh(new_note)

    return {
        "message": "Note created successfully",
        "note": {
            "id": new_note.id,
            "title": new_note.title,
            "content": new_note.content
        }
    }

# Get all notes of the logged-in user
@router.get("/notes")
def get_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    notes = db.query(Note).filter(
        Note.user_id == current_user.id
    ).all()

    return {
        "notes": [
            {
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "created_at": note.created_at,
                "updated_at": note.updated_at
            }
            for note in notes
        ]
    }

# Update an existing note
@router.put("/notes/{note_id}")
def update_note(
    note_id: int,
    note: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    existing_note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == current_user.id
    ).first()

    if not existing_note:
        raise HTTPException(
            status_code=404,
            detail="Note not found"
        )

    existing_note.title = note.title
    existing_note.content = note.content

    db.commit()
    db.refresh(existing_note)

    return {
        "message": "Note updated successfully",
        "note": {
            "id": existing_note.id,
            "title": existing_note.title,
            "content": existing_note.content
        }
    }
# Delete an existing note
@router.delete("/notes/{note_id}")
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    existing_note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == current_user.id
    ).first()

    if not existing_note:
        raise HTTPException(
            status_code=404,
            detail="Note not found"
        )

    db.delete(existing_note)
    db.commit()

    return {
        "message": "Note deleted successfully"
    }

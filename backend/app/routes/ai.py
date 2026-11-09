
import os
import json
import re

from datetime import datetime, date, time

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from groq import Groq

from database import get_db
from models import Task, Schedule, Reminder, Note
from app.auth_dependencies import get_current_user


router = APIRouter(
    prefix="/ai",
    tags=["AI Assistant"]
)


# Temporary conversation storage for each logged-in user
pending_conversations = {}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


# Required information for each creation feature

REQUIRED_FIELDS = {
    "task": ["title", "description", "date", "start_time", "end_time"],
    "schedule": ["title", "description", "date", "start_time", "end_time"],
    "reminder": ["title", "description", "date", "remind_time"],
    "note": ["title", "content"]
}


SKIP_WORDS = {
    "skip",
    "no description",
    "without description",
    "none",
    "not needed",
    "no need",
    "i don't need one",
    "i dont need one",
    "don't need one",
    "dont need one",
    "no thanks"
}


# Normalize task status

def normalize_status(value):

    if value is None:
        return ""

    if hasattr(value, "value"):
        value = value.value

    return str(value).split(".")[-1].lower().replace("_", " ")


# Detect note retrieval directly using Python.
# This prevents Groq from incorrectly classifying
# note retrieval requests as out_of_scope.

def detect_note_listing(message):

    text = message.strip().lower()

    note_words = re.search(r"\bnotes?\b", text)

    action_words = re.search(
        r"\b(show|list|find|get|open|read|display|view|"
        r"retrieve|search|fetch)\b",
        text
    )

    note_question = re.search(
        r"\b(what|which)\b.*\bnote\b",
        text
    )

    if not note_words:
        return None

    if not action_words and not note_question:
        return None

    # Try to identify a specific note title.

    title = None

    patterns = [
        r"\b(?:my|the)\s+(.+?)\s+notes?\b",
        r"\b(?:show|find|get|open|read|display|view|retrieve|"
        r"search|fetch)\s+(?:me\s+)?(?:the\s+)?"
        r"(.+?)\s+notes?\b"
    ]

    for pattern in patterns:

        match = re.search(pattern, text)

        if match:

            candidate = match.group(1).strip()

            if candidate not in {
                "all",
                "all my",
                "all of my",
                "my",
                "the"
            }:

                title = candidate
                break

    if title:

        title = re.sub(
            r"^(my|the)\s+",
            "",
            title
        ).strip()

        title = re.sub(
            r"\s+(please|for me)$",
            "",
            title
        ).strip()

    return {
        "intent": "list_notes",
        "title": title
    }


# Ask Groq to understand the user's message

def understand_message(client, message, pending, context):

    today = date.today().isoformat()

    if pending:

        missing_fields = get_missing_fields(
            pending["intent"],
            pending["fields"]
        )

        next_field = (
            missing_fields[0]
            if missing_fields
            else None
        )

        prompt = f"""
You are extracting information for an existing Chronexa AI request.

Current date: {today}

Existing request:
{json.dumps(pending, default=str)}

New user message:
{message}

The field Chronexa is currently asking the user to provide is:
{next_field}

Interpret the user's short reply as an answer to this field.

Extract only new information.
Do not remove previously collected information.
Do not change the existing request type.

Return ONLY valid JSON:

{{
    "fields": {{
        "title": null,
        "description": null,
        "content": null,
        "date": null,
        "start_time": null,
        "end_time": null,
        "remind_time": null,
        "status": null
    }}
}}

Rules:
- Date must be YYYY-MM-DD.
- Times must be HH:MM in 24-hour format.
- Convert 9:50 PM to 21:50.
- Convert 10 AM to 10:00.
- Recognize time-only answers.
- Map reminder times to remind_time.
- Map starting times to start_time.
- Map ending times to end_time.
- Resolve today, tomorrow and weekdays.
- Do not invent missing information.
- Do not interpret unrelated questions as field values.
"""

    else:

        prompt = f"""
You are Chronexa AI, a personal productivity assistant.

Current date: {today}

User message:
{message}

User productivity information:
{json.dumps(context, default=str)}

Classify the request.

Allowed intents:
- create_task
- create_schedule
- create_reminder
- create_note
- list_tasks
- list_schedules
- list_reminders
- list_notes
- list_productivity
- project_question
- out_of_scope

Return ONLY valid JSON:

{{
    "intent": "create_task",
    "fields": {{
        "title": null,
        "description": null,
        "content": null,
        "date": null,
        "start_time": null,
        "end_time": null,
        "remind_time": null,
        "status": null
    }},
    "reply": ""
}}

Rules:

- Extract all information already provided.
- Date must be YYYY-MM-DD.
- Times must be HH:MM in 24-hour format.
- Convert 9:50 PM to 21:50.
- Convert 10 AM to 10:00.
- Do not invent missing information.
- Only handle Chronexa productivity-related requests.

Listing rules:

- Show/list/find tasks -> list_tasks.
- Show/list/find schedules -> list_schedules.
- Show/list/find reminders -> list_reminders.
- Show/list/find notes -> list_notes.
- Show all three productivity categories -> list_productivity.
- If the user requests all productivity records, include notes too.
- If the user requests one specific note, use list_notes.
- Put a specific requested note title in the title field.
- If the user requests all notes, leave title null.
- Extract requested dates into the date field.
- Resolve today, tomorrow and weekdays.
- Completed records -> status "Completed".
- Pending records -> status "Pending".
- If no status filter is requested, leave status null.
- Apply task status filtering to tasks and schedules.
- Do not apply task status filtering to reminders or notes.

Project question rules:

- Answer questions about Chronexa AI and its features.
- Do not answer unrelated questions.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"},
        temperature=0
    )

    result = json.loads(
        response.choices[0].message.content
    )

    return result


# Check which required fields are missing

def get_missing_fields(intent, fields):

    missing = []

    for field in REQUIRED_FIELDS[intent]:

        value = fields.get(field)

        if field == "description":

            if value is None:
                missing.append(field)

        elif value is None or value == "":

            missing.append(field)

    return missing


# Ask for missing information

def ask_for_missing_detail(field):

    questions = {
        "title": "What should I name it?",
        "description": (
            "Please provide a description. "
            "You can also say 'Skip' if you don't need one."
        ),
        "date": "Which date should I schedule it for?",
        "start_time": "What is the starting time?",
        "end_time": "What is the ending time?",
        "remind_time": "What time should I remind you?",
        "content": "What would you like to write in your note?"
    }

    return questions.get(
        field,
        "Could you provide the missing information?"
    )


# Convert date and time into datetime

def convert_datetime(date_value, time_value):

    try:

        if isinstance(date_value, datetime):
            parsed_date = date_value.date()

        elif isinstance(date_value, date):
            parsed_date = date_value

        else:
            parsed_date = date.fromisoformat(
                str(date_value).strip()
            )

        if isinstance(time_value, datetime):
            parsed_time = time_value.time()

        elif isinstance(time_value, time):
            parsed_time = time_value

        else:

            time_text = str(time_value).strip()

            try:

                parsed_time = time.fromisoformat(time_text)

            except ValueError:

                parsed_time = datetime.strptime(
                    time_text.upper(),
                    "%I:%M %p"
                ).time()

        return datetime.combine(
            parsed_date,
            parsed_time
        )

    except (ValueError, TypeError, AttributeError):

        print("INVALID DATE VALUE:", repr(date_value))
        print("INVALID TIME VALUE:", repr(time_value))

        raise HTTPException(
            status_code=400,
            detail="Invalid date or time. Please provide valid values."
        )


# Save completed requests directly into MySQL

def save_request(intent, fields, db, user_id):

    if intent in ["task", "schedule"]:

        start = convert_datetime(
            fields["date"],
            fields["start_time"]
        )

        end = convert_datetime(
            fields["date"],
            fields["end_time"]
        )

        if end <= start:

            raise HTTPException(
                status_code=400,
                detail="End time must be after start time."
            )

        conflict = db.query(Schedule).filter(
            Schedule.user_id == user_id,
            Schedule.start_time < end,
            Schedule.end_time > start
        ).first()

        if conflict:

            raise HTTPException(
                status_code=409,
                detail=(
                    f"You already have a schedule during this time: "
                    f"{conflict.title}. Please choose another time."
                )
            )

        if intent == "task":

            new_task = Task(
                user_id=user_id,
                title=fields["title"],
                description=fields.get("description") or None,
                status="Pending"
            )

            db.add(new_task)
            db.flush()

            new_schedule = Schedule(
                user_id=user_id,
                task_id=new_task.id,
                title=new_task.title,
                description=new_task.description,
                start_time=start,
                end_time=end
            )

            new_reminder = Reminder(
                user_id=user_id,
                task_id=new_task.id,
                title=new_task.title,
                description=new_task.description,
                remind_at=start,
                is_sent=False
            )

            db.add(new_schedule)
            db.add(new_reminder)

            db.commit()

            return (
                f"Task '{new_task.title}' created successfully!\n"
                "Its schedule and reminder have also been created."
            )

        new_schedule = Schedule(
            user_id=user_id,
            title=fields["title"],
            description=fields.get("description") or None,
            start_time=start,
            end_time=end
        )

        db.add(new_schedule)
        db.commit()

        return (
            f"Schedule '{new_schedule.title}' created successfully!"
        )

    if intent == "reminder":

        remind_at = convert_datetime(
            fields["date"],
            fields["remind_time"]
        )

        new_reminder = Reminder(
            user_id=user_id,
            title=fields["title"],
            description=fields.get("description") or None,
            remind_at=remind_at,
            is_sent=False
        )

        db.add(new_reminder)
        db.commit()

        return (
            f"Reminder '{new_reminder.title}' created successfully!"
        )

    if intent == "note":

        new_note = Note(
            user_id=user_id,
            title=fields["title"],
            content=fields["content"]
        )

        db.add(new_note)
        db.commit()

        return (
            f"Note '{new_note.title}' saved successfully!"
        )


# Retrieve notes from MySQL

def list_notes(db, user_id, title=None):

    query = db.query(Note).filter(
        Note.user_id == user_id
    )

    notes = query.order_by(Note.id.desc()).all()

    # Match a specific note title if requested.

    if title:

        search_title = title.strip().casefold()

        notes = [
            note for note in notes
            if search_title in note.title.casefold()
        ]

    if not notes:

        if title:

            return (
                f"I couldn't find a note matching '{title}'. "
                "Please check the note title."
            )

        return "You don't have any saved notes yet."

    response = [
        "📝 YOUR SAVED NOTES",
        "--------------------",
        ""
    ]

    for index, note in enumerate(notes, 1):

        response.append(
            f"{index}. {note.title}\n"
            f"   Content: {note.content}"
        )

        response.append("")

    return "\n".join(response)


# List tasks, schedules, reminders and notes from MySQL

def list_productivity(
    intent,
    date_value,
    status,
    db,
    user_id
):

    selected_date = None

    if date_value:

        try:

            selected_date = date.fromisoformat(
                str(date_value)
            )

        except ValueError:

            return "I couldn't understand the requested date."

    # Retrieve only the logged-in user's records.

    tasks = db.query(Task).filter(
        Task.user_id == user_id
    ).all()

    schedules = db.query(Schedule).filter(
        Schedule.user_id == user_id
    ).all()

    reminders = db.query(Reminder).filter(
        Reminder.user_id == user_id
    ).all()

    notes = db.query(Note).filter(
        Note.user_id == user_id
    ).order_by(Note.id.desc()).all()

    # Filter by date.

    if selected_date:

        tasks = [
            task for task in tasks
            if task.schedule
            and task.schedule.start_time
            and task.schedule.start_time.date() == selected_date
        ]

        schedules = [
            schedule for schedule in schedules
            if schedule.start_time
            and schedule.start_time.date() == selected_date
        ]

        reminders = [
            reminder for reminder in reminders
            if reminder.remind_at
            and reminder.remind_at.date() == selected_date
        ]

    # Filter by task status.

    if status:

        requested_status = normalize_status(status)

        tasks = [
            task for task in tasks
            if normalize_status(task.status) == requested_status
        ]

        schedules = [
            schedule for schedule in schedules
            if schedule.task
            and normalize_status(schedule.task.status) == requested_status
        ]

    date_label = (
        selected_date.strftime("%d %B %Y")
        if selected_date
        else "All dates"
    )

    response = [
        "YOUR PRODUCTIVITY SUMMARY",
        f"Date: {date_label}",
        ""
    ]

    # Display tasks.

    if intent in ["list_tasks", "list_productivity"]:

        response.append("📋 MY TASKS")
        response.append("--------------------")

        if tasks:

            for index, task in enumerate(tasks, 1):

                response.append(
                    f"{index}. {task.title}\n"
                    f"   Description: {task.description or 'Not provided'}\n"
                    f"   Status: {task.status}"
                )

        else:

            response.append("No tasks found.")

        response.append("")

    # Display schedules.

    if intent in ["list_schedules", "list_productivity"]:

        response.append("📅 MY SCHEDULES")
        response.append("--------------------")

        if schedules:

            for index, schedule in enumerate(schedules, 1):

                response.append(
                    f"{index}. {schedule.title}\n"
                    f"   Description: {schedule.description or 'Not provided'}\n"
                    f"   Start: {schedule.start_time.strftime('%d %b %Y, %I:%M %p')}\n"
                    f"   End: {schedule.end_time.strftime('%I:%M %p')}"
                )

        else:

            response.append("No schedules found.")

        response.append("")

    # Display reminders.

    if intent in ["list_reminders", "list_productivity"]:

        response.append("🔔 MY REMINDERS")
        response.append("--------------------")

        if reminders:

            for index, reminder in enumerate(reminders, 1):

                response.append(
                    f"{index}. {reminder.title}\n"
                    f"   Description: {reminder.description or 'Not provided'}\n"
                    f"   Time: {reminder.remind_at.strftime('%d %b %Y, %I:%M %p')}"
                )

        else:

            response.append("No reminders found.")

        response.append("")

    # Display notes.

    if intent == "list_productivity":

        response.append("📝 MY NOTES")
        response.append("--------------------")

        if notes:

            for index, note in enumerate(notes, 1):

                response.append(
                    f"{index}. {note.title}\n"
                    f"   Content: {note.content}"
                )

        else:

            response.append("No notes found.")

        response.append("")

    return "\n".join(response)


# Chat endpoint

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
            detail="Groq API key is not configured."
        )

    user_id = current_user.id

    try:

        client = Groq(api_key=api_key)

        # Load only the logged-in user's information.

        tasks = db.query(Task).filter(
            Task.user_id == user_id
        ).all()

        schedules = db.query(Schedule).filter(
            Schedule.user_id == user_id
        ).all()

        reminders = db.query(Reminder).filter(
            Reminder.user_id == user_id
        ).all()

        notes = db.query(Note).filter(
            Note.user_id == user_id
        ).all()

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

        # Check for an unfinished request.

        pending = pending_conversations.get(user_id)

        # Detect note retrieval directly before calling Groq.

        # This avoids incorrect out_of_scope classification
        # for requests such as "Show me my Python Revision note".

        if not pending:

            note_request = detect_note_listing(
                request.message
            )

            if note_request:

                reply = list_notes(
                    db,
                    user_id,
                    note_request["title"]
                )

                return {
                    "reply": reply,
                    "pending": False,
                    "completed": True
                }

        # Detect Skip directly using Python.

        normalized_message = (
            request.message.strip().lower().strip(
                " \t\n'\".,!?"
            )
        )

        is_skip = normalized_message in SKIP_WORDS

        if pending:

            missing_fields = get_missing_fields(
                pending["intent"],
                pending["fields"]
            )

            if (
                is_skip
                and missing_fields
                and missing_fields[0] == "description"
            ):

                result = {
                    "fields": {
                        "description": ""
                    }
                }

            else:

                result = understand_message(
                    client,
                    request.message,
                    pending,
                    context
                )

        else:

            result = understand_message(
                client,
                request.message,
                pending,
                context
            )

        # Continue an existing request.

        if pending:

            fields = pending["fields"]

            new_fields = result.get("fields", {})

            for key, value in new_fields.items():

                if value is not None:

                    if value != "" or key == "description":

                        fields[key] = value

            intent = pending["intent"]

        else:

            intent = result.get("intent")

            # Handle unrelated requests.

            if intent == "out_of_scope":

                return {
                    "reply": (
                        "I'm Chronexa AI, your personal productivity "
                        "assistant. I can help with tasks, schedules, "
                        "reminders and notes."
                    )
                }

            # Handle Chronexa questions.

            if intent == "project_question":

                return {
                    "reply": result.get(
                        "reply",
                        "I can help you manage your productivity."
                    )
                }

            # Handle listing requests.

            listing_intents = [
                "list_tasks",
                "list_schedules",
                "list_reminders",
                "list_notes",
                "list_productivity"
            ]

            if intent in listing_intents:

                fields = result.get("fields", {})

                if intent == "list_notes":

                    reply = list_notes(
                        db,
                        user_id,
                        fields.get("title")
                    )

                else:

                    reply = list_productivity(
                        intent,
                        fields.get("date"),
                        fields.get("status"),
                        db,
                        user_id
                    )

                return {
                    "reply": reply,
                    "pending": False,
                    "completed": True
                }

            # Map AI intents to database creation types.

            intent_map = {
                "create_task": "task",
                "create_schedule": "schedule",
                "create_reminder": "reminder",
                "create_note": "note"
            }

            if intent not in intent_map:

                return {
                    "reply": (
                        "I can help you create tasks, schedules, "
                        "reminders and notes. What would you like to do?"
                    )
                }

            intent = intent_map[intent]

            fields = result.get("fields", {})

        # Validate request type.

        if intent not in REQUIRED_FIELDS:

            return {
                "reply": "Please tell me what you would like to create."
            }

        # Check for missing information.

        missing = get_missing_fields(
            intent,
            fields
        )

        if missing:

            pending_conversations[user_id] = {
                "intent": intent,
                "fields": fields
            }

            question = ask_for_missing_detail(
                missing[0]
            )

            return {
                "reply": question,
                "pending": True
            }

        # Save after collecting all required details.

        reply = save_request(
            intent,
            fields,
            db,
            user_id
        )

        pending_conversations.pop(
            user_id,
            None
        )

        return {
            "reply": reply,
            "pending": False,
            "completed": True
        }

    except HTTPException as e:

        db.rollback()

        print(
            "CHRONEXA HTTP ERROR:",
            e.status_code,
            e.detail
        )

        raise

    except Exception as e:

        db.rollback()

        print(
            "CHRONEXA AI ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=502,
            detail="Unable to process your request."
        )


import os
import json
import re
import calendar

from datetime import datetime, date, time, timedelta

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

# Stores pending update/delete confirmations and selections
pending_actions = {}


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


# ==========================================
# GENERAL HELPERS
# ==========================================

def normalize_status(value):

    if value is None:
        return ""

    if hasattr(value, "value"):
        value = value.value

    return str(value).split(".")[-1].lower().replace("_", " ")


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


# Calculate the end date for a recurring reminder.
# The end date is inclusive.

def calculate_recurrence_end_date(start_date, duration):

    duration_text = str(duration).strip().lower()

    duration_text = re.sub(
        r"^for\s+",
        "",
        duration_text
    ).strip()

    month_count = None

    if duration_text in {
        "1 month",
        "one month",
        "a month",
        "month"
    }:
        month_count = 1

    elif duration_text in {
        "2 months",
        "two months"
    }:
        month_count = 2

    if month_count is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "I couldn't understand that reminder duration. "
                "Please provide a specific end date."
            )
        )

    year = start_date.year
    month = start_date.month + month_count

    while month > 12:
        month -= 12
        year += 1

    last_day = calendar.monthrange(year, month)[1]
    day = min(start_date.day, last_day)

    return date(year, month, day)


# ==========================================
# AI UPDATE AND DELETE OPERATIONS
# ==========================================

ACTION_INTENTS = {
    "update_task": "task",
    "update_schedule": "schedule",
    "update_reminder": "reminder",
    "update_note": "note",
    "delete_task": "task",
    "delete_schedule": "schedule",
    "delete_reminder": "reminder",
    "delete_note": "note"
}


def get_entity_model(entity_type):

    models = {
        "task": Task,
        "schedule": Schedule,
        "reminder": Reminder,
        "note": Note
    }

    return models[entity_type]


def find_matching_records(
    db,
    user_id,
    entity_type,
    target_title
):

    model = get_entity_model(entity_type)

    records = db.query(model).filter(
        model.user_id == user_id
    ).all()

    search_text = target_title.strip().casefold()

    exact_matches = [
        record for record in records
        if record.title.casefold() == search_text
    ]

    if exact_matches:
        return exact_matches

    return [
        record for record in records
        if search_text in record.title.casefold()
    ]


def get_record_by_id(
    db,
    user_id,
    entity_type,
    record_id
):

    model = get_entity_model(entity_type)

    return db.query(model).filter(
        model.id == record_id,
        model.user_id == user_id
    ).first()


def format_matching_records(records, entity_type):

    lines = ["I found multiple matching records:"]

    for index, record in enumerate(records, 1):
        lines.append(
            f"{index}. {record.title} (ID: {record.id})"
        )

    lines.append("")
    lines.append(
        "Please reply with the number of the record you mean."
    )

    return "\n".join(lines)


def get_update_changes(fields):

    allowed_fields = [
        "updated_title",
        "description",
        "content",
        "date",
        "start_time",
        "end_time",
        "remind_time",
        "status"
    ]

    return {
        key: fields[key]
        for key in allowed_fields
        if key in fields and fields[key] is not None
    }


def apply_record_update(
    db,
    user_id,
    entity_type,
    record,
    changes
):

    if not changes:
        return (
            "What would you like me to change? "
            "Please specify the new title, description, content, "
            "status or time."
        )

    try:

        new_title = changes.get("updated_title")

        if new_title:
            record.title = new_title.strip()

        if "description" in changes and entity_type != "note":
            record.description = changes["description"]

        if entity_type == "note":

            if "content" in changes:
                record.content = changes["content"]

        elif entity_type == "task":

            if "status" in changes:

                requested_status = normalize_status(
                    changes["status"]
                )

                valid_statuses = {
                    "pending": "Pending",
                    "in progress": "In Progress",
                    "completed": "Completed"
                }

                if requested_status not in valid_statuses:
                    return (
                        "Please choose a valid task status: "
                        "Pending, In Progress or Completed."
                    )

                record.status = valid_statuses[requested_status]

            schedule = record.schedule
            reminder = record.reminder

            time_fields = {
                "date",
                "start_time",
                "end_time"
            }

            if time_fields.intersection(changes):

                if not schedule:
                    return (
                        "This task does not have a linked schedule "
                        "to update."
                    )

                selected_date = changes.get(
                    "date",
                    schedule.start_time.date().isoformat()
                )

                new_start = convert_datetime(
                    selected_date,
                    changes.get(
                        "start_time",
                        schedule.start_time.strftime("%H:%M")
                    )
                )

                new_end = convert_datetime(
                    selected_date,
                    changes.get(
                        "end_time",
                        schedule.end_time.strftime("%H:%M")
                    )
                )

                if new_end <= new_start:
                    return "End time must be after start time."

                conflict = db.query(Schedule).filter(
                    Schedule.user_id == user_id,
                    Schedule.id != schedule.id,
                    Schedule.start_time < new_end,
                    Schedule.end_time > new_start
                ).first()

                if conflict:
                    return (
                        "You already have another schedule during "
                        f"that time: {conflict.title}. "
                        "Please choose another time."
                    )

                schedule.start_time = new_start
                schedule.end_time = new_end

                if reminder:
                    reminder.remind_at = new_start
                    reminder.is_sent = False

            if schedule:
                schedule.title = record.title
                schedule.description = record.description

            if reminder:
                reminder.title = record.title
                reminder.description = record.description

        elif entity_type == "schedule":

            if (
                "date" in changes
                or "start_time" in changes
                or "end_time" in changes
            ):

                selected_date = changes.get(
                    "date",
                    record.start_time.date().isoformat()
                )

                new_start = convert_datetime(
                    selected_date,
                    changes.get(
                        "start_time",
                        record.start_time.strftime("%H:%M")
                    )
                )

                new_end = convert_datetime(
                    selected_date,
                    changes.get(
                        "end_time",
                        record.end_time.strftime("%H:%M")
                    )
                )

                if new_end <= new_start:
                    return "End time must be after start time."

                conflict = db.query(Schedule).filter(
                    Schedule.user_id == user_id,
                    Schedule.id != record.id,
                    Schedule.start_time < new_end,
                    Schedule.end_time > new_start
                ).first()

                if conflict:
                    return (
                        "You already have another schedule during "
                        f"that time: {conflict.title}."
                    )

                record.start_time = new_start
                record.end_time = new_end

            # Keep linked records synchronized.

            if record.task:

                record.task.title = record.title
                record.task.description = record.description

                if record.task.reminder:

                    record.task.reminder.title = record.title
                    record.task.reminder.description = record.description

                    if "start_time" in changes or "date" in changes:
                        record.task.reminder.remind_at = record.start_time
                        record.task.reminder.is_sent = False

        elif entity_type == "reminder":

            if "date" in changes or "remind_time" in changes:

                selected_date = changes.get(
                    "date",
                    record.remind_at.date().isoformat()
                )

                record.remind_at = convert_datetime(
                    selected_date,
                    changes.get(
                        "remind_time",
                        record.remind_at.strftime("%H:%M")
                    )
                )

            record.is_sent = False

            if record.task:

                record.task.title = record.title
                record.task.description = record.description

                if record.task.schedule:
                    record.task.schedule.title = record.title
                    record.task.schedule.description = record.description

        db.commit()
        db.refresh(record)

        return (
            f"{entity_type.capitalize()} "
            f"'{record.title}' updated successfully!"
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def begin_ai_action(
    db,
    user_id,
    intent,
    fields
):

    entity_type = ACTION_INTENTS[intent]

    is_delete = intent.startswith("delete_")
    changes = get_update_changes(fields)

    target_title = fields.get("target_title")

    if not target_title:

        pending_actions[user_id] = {
            "stage": "identify_target",
            "action": "delete" if is_delete else "update",
            "entity_type": entity_type,
            "changes": changes
        }

        return {
            "reply": (
                f"Which {entity_type} would you like to "
                f"{'delete' if is_delete else 'update'}? "
                "Please provide its title."
            ),
            "pending": True
        }

    if not is_delete and not changes:
        return {
            "reply": (
                f"I found that you want to update a {entity_type}. "
                "Please also tell me what you want to change."
            ),
            "pending": False
        }

    records = find_matching_records(
        db,
        user_id,
        entity_type,
        target_title
    )

    if not records:
        return {
            "reply": (
                f"I couldn't find a {entity_type} matching "
                f"'{target_title}'. Please check its title."
            ),
            "pending": False
        }

    if len(records) > 1:

        pending_actions[user_id] = {
            "stage": "select",
            "action": "delete" if is_delete else "update",
            "entity_type": entity_type,
            "record_ids": [record.id for record in records],
            "changes": changes
        }

        return {
            "reply": format_matching_records(
                records,
                entity_type
            ),
            "pending": True
        }

    record = records[0]

    if is_delete:

        pending_actions[user_id] = {
            "stage": "confirm_delete",
            "entity_type": entity_type,
            "record_id": record.id,
            "title": record.title
        }

        return {
            "reply": (
                f"Are you sure you want to delete "
                f"'{record.title}'? "
                "Please reply Yes to confirm or No to cancel."
            ),
            "pending": True
        }

    reply = apply_record_update(
        db,
        user_id,
        entity_type,
        record,
        changes
    )

    return {
        "reply": reply,
        "pending": False,
        "completed": True
    }


def handle_pending_action(db, user_id, message):

    pending = pending_actions.get(user_id)

    if not pending:
        return None

    text = message.strip().casefold()

    # Identify the record to update or delete.

    if pending["stage"] == "identify_target":

        entity_type = pending["entity_type"]
        action = pending["action"]
        changes = pending["changes"]

        target_title = message.strip()

        records = find_matching_records(
            db,
            user_id,
            entity_type,
            target_title
        )

        if not records:
            return {
                "reply": (
                    f"I couldn't find a {entity_type} matching "
                    f"'{target_title}'. Please provide the correct title."
                ),
                "pending": True
            }

        if len(records) > 1:

            pending_actions[user_id] = {
                "stage": "select",
                "action": action,
                "entity_type": entity_type,
                "record_ids": [record.id for record in records],
                "changes": changes
            }

            return {
                "reply": format_matching_records(
                    records,
                    entity_type
                ),
                "pending": True
            }

        record = records[0]

        if action == "delete":

            pending_actions[user_id] = {
                "stage": "confirm_delete",
                "entity_type": entity_type,
                "record_id": record.id,
                "title": record.title
            }

            return {
                "reply": (
                    f"Are you sure you want to delete "
                    f"'{record.title}'? "
                    "Please reply Yes to confirm or No to cancel."
                ),
                "pending": True
            }

        pending_actions.pop(user_id, None)

        reply = apply_record_update(
            db,
            user_id,
            entity_type,
            record,
            changes
        )

        return {
            "reply": reply,
            "pending": False,
            "completed": True
        }

    # Handle delete confirmation.

    if pending["stage"] == "confirm_delete":

        if text in {
            "yes",
            "y",
            "confirm",
            "yes delete",
            "confirm delete"
        }:

            record = get_record_by_id(
                db,
                user_id,
                pending["entity_type"],
                pending["record_id"]
            )

            if not record:

                pending_actions.pop(user_id, None)

                return {
                    "reply": "That record no longer exists.",
                    "pending": False
                }

            title = record.title

            try:

                db.delete(record)
                db.commit()

                pending_actions.pop(user_id, None)

                return {
                    "reply": f"'{title}' deleted successfully!",
                    "pending": False,
                    "completed": True
                }

            except Exception:
                db.rollback()
                raise

        if text in {
            "no",
            "n",
            "cancel",
            "don't delete",
            "do not delete"
        }:

            pending_actions.pop(user_id, None)

            return {
                "reply": "Deletion cancelled. Your record is safe.",
                "pending": False
            }

        return {
            "reply": (
                "Please reply Yes to confirm deletion "
                "or No to cancel."
            ),
            "pending": True
        }

    # Handle duplicate-title selection.

    if pending["stage"] == "select":

        selection_words = {
            "first": 1,
            "second": 2,
            "third": 3,
            "fourth": 4,
            "fifth": 5
        }

        selected_number = None

        number_match = re.search(r"\b(\d+)\b", text)

        if number_match:
            selected_number = int(number_match.group(1))

        else:

            for word, number in selection_words.items():

                if word in text:
                    selected_number = number
                    break

        record_ids = pending["record_ids"]

        if (
            selected_number is None
            or selected_number < 1
            or selected_number > len(record_ids)
        ):

            return {
                "reply": (
                    "Please select a valid record number "
                    "from the list."
                ),
                "pending": True
            }

        record_id = record_ids[selected_number - 1]

        record = get_record_by_id(
            db,
            user_id,
            pending["entity_type"],
            record_id
        )

        if not record:

            pending_actions.pop(user_id, None)

            return {
                "reply": "That record could not be found.",
                "pending": False
            }

        action = pending["action"]
        entity_type = pending["entity_type"]
        changes = pending["changes"]

        if action == "delete":

            pending_actions[user_id] = {
                "stage": "confirm_delete",
                "entity_type": entity_type,
                "record_id": record.id,
                "title": record.title
            }

            return {
                "reply": (
                    f"You selected '{record.title}'. "
                    "Are you sure you want to delete it? "
                    "Reply Yes to confirm or No to cancel."
                ),
                "pending": True
            }

        pending_actions.pop(user_id, None)

        reply = apply_record_update(
            db,
            user_id,
            entity_type,
            record,
            changes
        )

        return {
            "reply": reply,
            "pending": False,
            "completed": True
        }

    return None


# ==========================================
# NOTE RETRIEVAL
# ==========================================

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


# ==========================================
# GROQ MESSAGE UNDERSTANDING
# ==========================================

def understand_message(
    client,
    message,
    pending,
    context
):

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
        "status": null,
        "recurrence": null,
        "recurrence_end_date": null,
        "recurrence_duration": null
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
- Extract recurrence, recurrence_end_date and recurrence_duration
  when the user provides them.
- "Every day", "daily" and "each day" mean recurrence "daily".
- "For one month" or "for a month" means recurrence_duration "1 month".
- "For two months" means recurrence_duration "2 months".
- "Until December 17" means extract the exact end date.
- Do not invent recurrence details.
- Preserve previously collected information.
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
- update_task
- update_schedule
- update_reminder
- update_note
- delete_task
- delete_schedule
- delete_reminder
- delete_note

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
        "status": null,
        "target_title": null,
        "updated_title": null,
        "recurrence": null,
        "recurrence_end_date": null,
        "recurrence_duration": null
    }},
    "reply": ""
}}

General rules:

- Extract all information already provided.
- Date must be YYYY-MM-DD.
- Times must be HH:MM in 24-hour format.
- Convert 9:50 PM to 21:50.
- Convert 10 AM to 10:00.
- Do not invent missing information.
- Only handle Chronexa productivity-related requests.

Creation rules:

- Extract the title and description from the user's message.
- For tasks and schedules, extract date, start_time and end_time.
- For reminders, extract date and remind_time.
- For notes, extract title and content.
- If a description is not provided, leave it null.
- Do not invent a description.

Recurring reminder rules:

- "Every day", "daily" or "each day" means recurrence "daily".
- "For one month" or "for a month" means recurrence_duration "1 month".
- "For two months" means recurrence_duration "2 months".
- "Until December 17" means extract the exact date into recurrence_end_date.
- Extract the recurrence start date into date.
- Extract the reminder time into remind_time.
- One-time reminders must have recurrence null.
- Do not invent an end date when the duration is not provided.
- Do not classify a normal one-time reminder as recurring.
- Recurrence is currently supported only for reminders.

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

Update and delete rules:

- "Update my task..." -> update_task.
- "Update my schedule..." -> update_schedule.
- "Update my reminder..." -> update_reminder.
- "Update my note..." -> update_note.
- "Delete my task..." -> delete_task.
- "Delete my schedule..." -> delete_schedule.
- "Delete my reminder..." -> delete_reminder.
- "Delete my note..." -> delete_note.
- Put the existing record's title in target_title.
- Put a replacement title in updated_title.
- Put the new description in description.
- Put the new note text in content.
- Put the new requested status in status.
- Extract new dates and times when requested.
- Never invent a target title or changes.
- Do not classify a request to update or delete as a creation request.

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


# ==========================================
# REQUIRED FIELD CHECKING
# ==========================================

def get_missing_fields(intent, fields):

    missing = []

    for field in REQUIRED_FIELDS[intent]:

        value = fields.get(field)

        if field == "description":

            if value is None:
                missing.append(field)

        elif value is None or value == "":
            missing.append(field)

    # A daily reminder must have an end date or duration.

    if intent == "reminder" and fields.get("recurrence") == "daily":

        if (
            not fields.get("recurrence_end_date")
            and not fields.get("recurrence_duration")
        ):
            missing.append("recurrence_end_date")

    return missing


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

        "content": "What would you like to write in your note?",

        "recurrence_end_date": (
            "Until which date should I send this daily reminder? "
            "You can also say 'for one month' or 'for two months'."
        )
    }

    return questions.get(
        field,
        "Could you provide the missing information?"
    )


# ==========================================
# SAVE CREATION REQUESTS
# ==========================================

def save_request(
    intent,
    fields,
    db,
    user_id
):

    # --------------------------------------
    # CREATE TASK OR SCHEDULE
    # --------------------------------------

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

    # --------------------------------------
    # CREATE ONE-TIME OR DAILY REMINDER
    # --------------------------------------

    if intent == "reminder":

        remind_at = convert_datetime(
            fields["date"],
            fields["remind_time"]
        )

        recurrence = fields.get("recurrence")
        recurrence_end_date = None

        if recurrence == "daily":

            if fields.get("recurrence_end_date"):

                try:

                    recurrence_end_date = date.fromisoformat(
                        str(fields["recurrence_end_date"])
                    )

                except (ValueError, TypeError):

                    raise HTTPException(
                        status_code=400,
                        detail="Invalid recurrence end date."
                    )

            elif fields.get("recurrence_duration"):

                recurrence_end_date = calculate_recurrence_end_date(
                    remind_at.date(),
                    fields["recurrence_duration"]
                )

            # Defensive validation.

            if recurrence_end_date is None:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Please provide an end date or duration "
                        "for your daily reminder."
                    )
                )

            if recurrence_end_date < remind_at.date():

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "End date cannot be before the reminder "
                        "start date."
                    )
                )

        new_reminder = Reminder(
            user_id=user_id,
            title=fields["title"],
            description=fields.get("description") or None,
            remind_at=remind_at,
            recurrence=recurrence,
            recurrence_end_date=recurrence_end_date,
            is_sent=False
        )

        db.add(new_reminder)
        db.commit()
        db.refresh(new_reminder)

        if recurrence == "daily":

            return (
                f"Daily reminder '{new_reminder.title}' "
                "created successfully!\n"
                f"First reminder: "
                f"{remind_at.strftime('%d %B %Y, %I:%M %p')}\n"
                f"Last reminder: "
                f"{recurrence_end_date.strftime('%d %B %Y')}"
            )

        return (
            f"Reminder '{new_reminder.title}' created successfully!"
        )

    # --------------------------------------
    # CREATE NOTE
    # --------------------------------------

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


# ==========================================
# LIST NOTES
# ==========================================

def list_notes(
    db,
    user_id,
    title=None
):

    query = db.query(Note).filter(
        Note.user_id == user_id
    )

    notes = query.order_by(Note.id.desc()).all()

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


# ==========================================
# LIST PRODUCTIVITY RECORDS
# ==========================================

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
                    f"   Description: "
                    f"{task.description or 'Not provided'}\n"
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
                    f"   Description: "
                    f"{schedule.description or 'Not provided'}\n"
                    f"   Start: "
                    f"{schedule.start_time.strftime('%d %b %Y, %I:%M %p')}\n"
                    f"   End: "
                    f"{schedule.end_time.strftime('%I:%M %p')}"
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

                recurrence_label = (
                    "Daily"
                    if reminder.recurrence == "daily"
                    else "One-time"
                )

                response.append(
                    f"{index}. {reminder.title}\n"
                    f"   Description: "
                    f"{reminder.description or 'Not provided'}\n"
                    f"   Time: "
                    f"{reminder.remind_at.strftime('%d %b %Y, %I:%M %p')}\n"
                    f"   Type: {recurrence_label}"
                )

                if (
                    reminder.recurrence == "daily"
                    and reminder.recurrence_end_date
                ):
                    response.append(
                        f"   Last date: "
                        f"{reminder.recurrence_end_date.strftime('%d %b %Y')}"
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


# ==========================================
# CHAT ENDPOINT
# ==========================================

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
                    "is_sent": reminder.is_sent,
                    "recurrence": reminder.recurrence,
                    "recurrence_end_date": str(
                        reminder.recurrence_end_date
                    ) if reminder.recurrence_end_date else None
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

        # Check for an unfinished creation request.

        pending = pending_conversations.get(user_id)

        # Handle an existing update/delete confirmation or selection.

        pending_action_result = handle_pending_action(
            db,
            user_id,
            request.message
        )

        if pending_action_result is not None:
            return pending_action_result

        # Give new update/delete requests priority over pending creation.

        action_words = re.search(
            r"\b(delete|remove|update|edit|change)\b",
            request.message,
            re.IGNORECASE
        )

        if pending and action_words:

            new_action_result = understand_message(
                client,
                request.message,
                None,
                context
            )

            new_intent = new_action_result.get("intent")

            if new_intent in ACTION_INTENTS:

                pending_conversations.pop(user_id, None)

                return begin_ai_action(
                    db,
                    user_id,
                    new_intent,
                    new_action_result.get("fields", {})
                )

        # Detect note retrieval directly before calling Groq.

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

            # Handle AI update and delete requests.

            if intent in ACTION_INTENTS:

                action_result = begin_ai_action(
                    db,
                    user_id,
                    intent,
                    result.get("fields", {})
                )

                return action_result

            # Handle unrelated requests.

            if intent == "out_of_scope":

                return {
                    "reply": (
                        "I'm Chronexa AI, your personal productivity "
                        "assistant. I can help with tasks, schedules, "
                        "reminders and notes."
                    ),
                    "pending": False
                }

            # Handle Chronexa project questions.

            if intent == "project_question":

                return {
                    "reply": result.get(
                        "reply",
                        "I can help you manage your productivity."
                    ),
                    "pending": False
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
                    ),
                    "pending": False
                }

            intent = intent_map[intent]

            fields = result.get("fields", {})

        # Validate request type.

        if intent not in REQUIRED_FIELDS:

            return {
                "reply": (
                    "Please tell me what you would like to create."
                ),
                "pending": False
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
            "CHRONEX HTTP ERROR:",
            e.status_code,
            e.detail
        )

        raise

    except Exception as e:

        db.rollback()

        print(
            "CHRONEX AI ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=502,
            detail="Unable to process your request."
        )

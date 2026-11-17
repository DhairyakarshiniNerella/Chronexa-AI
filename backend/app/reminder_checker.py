
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from database import SessionLocal
from models import Reminder
from app.email_service import send_reminder_email


def check_due_reminders():

    db = SessionLocal()

    try:
        current_time = datetime.now(
            ZoneInfo("Asia/Kolkata")
        ).replace(tzinfo=None)

        # Find reminders that are due and have not been sent
        due_reminders = db.query(Reminder).filter(
            Reminder.remind_at <= current_time,
            Reminder.is_sent.is_(False)
        ).all()

        for reminder in due_reminders:

            try:
                user_email = reminder.owner.email

                email_sent = send_reminder_email(
                    to_email=user_email,
                    title=reminder.title,
                    description=reminder.description,
                    remind_at=reminder.remind_at
                )

                if email_sent:

                    # Handle daily recurring reminders
                    if (
                        reminder.recurrence == "daily"
                        and reminder.recurrence_end_date
                    ):

                        next_reminder = (
                            reminder.remind_at + timedelta(days=1)
                        )

                        # Skip missed occurrences if the backend
                        # was offline, avoiding multiple emails at once.
                        while (
                            next_reminder <= current_time
                            and next_reminder.date()
                            <= reminder.recurrence_end_date
                        ):
                            next_reminder += timedelta(days=1)

                        # Continue if another occurrence remains
                        if (
                            next_reminder.date()
                            <= reminder.recurrence_end_date
                        ):
                            reminder.remind_at = next_reminder
                            reminder.is_sent = False

                        else:
                            # Final occurrence has been sent
                            reminder.is_sent = True

                    else:
                        # One-time reminder
                        reminder.is_sent = True

                    db.commit()

                    print(
                        f"Reminder processed successfully: "
                        f"{reminder.title}"
                    )

                else:
                    db.rollback()
                    print(
                        f"Reminder email failed: {reminder.title}. "
                        "Will retry."
                    )

            except Exception as error:
                db.rollback()
                print(
                    f"Error processing reminder "
                    f"{reminder.id}: {error}"
                )

    except Exception as error:
        print("Reminder checker error:", error)

    finally:
        db.close()

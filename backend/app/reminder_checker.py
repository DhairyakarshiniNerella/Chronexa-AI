
from datetime import datetime

from database import SessionLocal
from models import Reminder

from app.email_service import send_reminder_email


def check_due_reminders():

    db = SessionLocal()

    try:
        current_time = datetime.now()

        due_reminders = db.query(Reminder).filter(
            Reminder.remind_at <= current_time,
            Reminder.is_sent.is_(False)
        ).all()

        if not due_reminders:
            print("No due reminders found.")
            return

        print(f"Found {len(due_reminders)} due reminder(s).")

        for reminder in due_reminders:

            try:
                print("\n========== CHRONEXA NOTIFICATION ==========")
                print("Reminder:", reminder.title)
                print("Description:", reminder.description)
                print("Scheduled Time:", reminder.remind_at)

                # Get reminder owner's registered email
                user_email = reminder.owner.email

                # Send reminder email
                email_sent = send_reminder_email(
                    to_email=user_email,
                    title=reminder.title,
                    description=reminder.description,
                    remind_at=reminder.remind_at
                )

                if email_sent:

                    reminder.is_sent = True
                    db.commit()

                    print("Email notification completed.")
                    print("Reminder marked as sent.")

                else:
                    db.rollback()
                    print(
                        f"Email failed for reminder: {reminder.title}. "
                        "It will be retried during the next check."
                    )

                print("===========================================\n")

            except Exception as error:

                db.rollback()

                print(
                    f"Error processing reminder "
                    f"'{reminder.title}': {error}"
                )

                # Continue processing other reminders
                continue

    except Exception as error:

        db.rollback()
        print("Reminder checker error:", error)

    finally:
        db.close()


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
            Reminder.is_sent == False
        ).all()

        for reminder in due_reminders:

            print("\n========== CHRONEXA NOTIFICATION ==========")
            print("Reminder:", reminder.title)
            print("Description:", reminder.description)
            print("Scheduled Time:", reminder.remind_at)

            # Get the reminder owner's registered email
            user_email = reminder.owner.email

            # Send reminder email
            email_sent = send_reminder_email(
                to_email=user_email,
                title=reminder.title,
                description=reminder.description,
                remind_at=reminder.remind_at
            )

            # Mark as sent only after successful email delivery
            if email_sent:
                reminder.is_sent = True
                print("Email notification completed.")

            print("===========================================\n")

        db.commit()

    except Exception as error:
        db.rollback()
        print("Reminder checker error:", error)

    finally:
        db.close()

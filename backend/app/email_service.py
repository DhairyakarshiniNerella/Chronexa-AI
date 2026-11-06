
import os
import smtplib

from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()


def send_reminder_email(to_email, title, description, remind_at):

    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_APP_PASSWORD")

    if not smtp_email or not smtp_password:
        print("Email credentials are missing in .env")
        return False

    message = EmailMessage()

    message["Subject"] = f"Chronexa AI Reminder: {title}"
    message["From"] = smtp_email
    message["To"] = to_email

    message.set_content(
        f"""
Hello!

This is your reminder from Chronexa AI.

Reminder: {title}

Description: {description or "No description provided"}

Scheduled Time: {remind_at}

Stay organized with Chronexa AI!

Best regards,
Chronexa AI
"""
    )

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:

            server.login(smtp_email, smtp_password)

            server.send_message(message)

        print(f"Reminder email sent successfully to {to_email}")

        return True

    except Exception as error:

        print("Email sending failed:", error)

        return False

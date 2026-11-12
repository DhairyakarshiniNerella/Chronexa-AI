
import os
import smtplib

from email.message import EmailMessage
from email.utils import formataddr
from dotenv import load_dotenv

load_dotenv()


def send_reminder_email(to_email, title, description, remind_at):

    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_APP_PASSWORD")

    if not smtp_email or not smtp_password:
        print("Email credentials are missing in .env")
        return False

    message = EmailMessage()

    message["Subject"] = f"Reminder: {title} | Chronexa AI"
    message["From"] = formataddr(("Chronexa AI", smtp_email))
    message["To"] = to_email

    description = description or "No description provided"

    # Plain text fallback
    message.set_content(
        f"""
Hello!

You have an upcoming reminder from Chronexa AI.

Reminder: {title}

Description: {description}

Scheduled Time: {remind_at}

Stay organized and make every moment count!

Best regards,
Chronexa AI
Your Personal Productivity Assistant
"""
    )

    # Professional HTML email
    html_content = f"""
    <html>
    <body style="
        margin: 0;
        padding: 30px;
        background-color: #f3f4f8;
        font-family: Arial, sans-serif;
    ">

        <div style="
            max-width: 550px;
            margin: auto;
            background-color: white;
            border-radius: 12px;
            overflow: hidden;
        ">

            <div style="
                background: linear-gradient(135deg, #4338ca, #7c3aed);
                padding: 25px;
                text-align: center;
                color: white;
            ">
                <h1 style="margin: 0;">Chronexa AI</h1>
                <p style="margin-bottom: 0;">
                    Your Personal Productivity Assistant
                </p>
            </div>

            <div style="padding: 30px; color: #333;">

                <h2 style="color: #4338ca;">
                    Reminder Notification
                </h2>

                <p>Hello!</p>

                <p>
                    You have an upcoming reminder.
                    Here are your reminder details:
                </p>

                <div style="
                    background-color: #f5f3ff;
                    padding: 20px;
                    border-radius: 8px;
                    margin-top: 20px;
                ">

                    <p style="color: #777; margin-bottom: 5px;">
                        REMINDER TITLE
                    </p>

                    <h2 style="margin-top: 0; color: #4338ca;">
                        {title}
                    </h2>

                    <p><strong>Description:</strong></p>
                    <p>{description}</p>

                    <p><strong>Scheduled Time:</strong></p>
                    <p>{remind_at}</p>

                </div>

                <p style="margin-top: 25px;">
                    Stay organized and make every moment count!
                </p>

            </div>

            <div style="
                background-color: #f3f4f8;
                padding: 18px;
                text-align: center;
                color: #777;
                font-size: 12px;
            ">
                This is an automated reminder from Chronexa AI.
                <br>
                Thank you for using Chronexa AI!
            </div>

        </div>

    </body>
    </html>
    """

    message.add_alternative(html_content, subtype="html")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:

            server.login(smtp_email, smtp_password)

            server.send_message(message)

        print(f"Reminder email sent successfully to {to_email}")

        return True

    except Exception as error:

        print("Email sending failed:", error)

        return False


import os
import html
import json
import urllib.request
import urllib.error

from dotenv import load_dotenv

load_dotenv()


def send_reminder_email(to_email, title, description, remind_at):

    brevo_api_key = os.getenv("BREVO_API_KEY")
    from_email = os.getenv("BREVO_FROM_EMAIL")

    if not brevo_api_key or not from_email:
        print("Brevo credentials are missing.")
        return False

    description = description or "No description provided"

    safe_title = html.escape(str(title))
    safe_description = html.escape(str(description))
    safe_remind_at = html.escape(str(remind_at))

    plain_text = f"""
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

    html_content = f"""
    <html>
    <body style="margin:0;padding:30px;background:#f3f4f8;
                 font-family:Arial,sans-serif;">

        <div style="max-width:550px;margin:auto;background:white;
                    border-radius:12px;overflow:hidden;">

            <div style="background:linear-gradient(135deg,#4338ca,#7c3aed);
                        padding:25px;text-align:center;color:white;">
                <h1>Chronexa AI</h1>
                <p>Your Personal Productivity Assistant</p>
            </div>

            <div style="padding:30px;color:#333;">
                <h2 style="color:#4338ca;">Reminder Notification</h2>

                <p>Hello!</p>
                <p>You have an upcoming reminder.</p>

                <div style="background:#f5f3ff;padding:20px;
                            border-radius:8px;">

                    <p><strong>Reminder Title</strong></p>
                    <h2 style="color:#4338ca;">{safe_title}</h2>

                    <p><strong>Description:</strong></p>
                    <p>{safe_description}</p>

                    <p><strong>Scheduled Time:</strong></p>
                    <p>{safe_remind_at}</p>
                </div>

                <p>Stay organized and make every moment count!</p>
            </div>

            <div style="background:#f3f4f8;padding:18px;
                        text-align:center;color:#777;font-size:12px;">
                This is an automated reminder from Chronexa AI.
                <br>
                Thank you for using Chronexa AI!
            </div>

        </div>
    </body>
    </html>
    """

    payload = {
        "sender": {
            "name": "Chronexa AI",
            "email": from_email
        },
        "to": [
            {
                "email": to_email
            }
        ],
        "subject": f"Reminder: {title} | Chronexa AI",
        "textContent": plain_text,
        "htmlContent": html_content
    }

    request = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": brevo_api_key,
            "content-type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))

            print(f"Reminder email sent successfully to {to_email}")
            print(f"Brevo response: {result}")

            return True

    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        print("Brevo email sending failed:", details)
        return False

    except Exception as error:
        print("Email sending failed:", error)
        return False

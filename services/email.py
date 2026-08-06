import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY")


def send_email(to: str, subject: str, html: str):
    print("Sending email to:", to, "==========================")
    return resend.Emails.send({
        "from": "testing_ollama@resend.dev",
        "to": [to],
        "subject": subject,
        "html": html,
    })

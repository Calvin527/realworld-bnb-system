
import os
import requests


def send_email(to_email, subject, body, html=None):
    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("MAIL_DEFAULT_SENDER", "Makgobelo Lodge <onboarding@resend.dev>")

    if not api_key:
        return False, "RESEND_API_KEY is not configured."

    payload = {
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "text": body,
    }

    if html:
        payload["html"] = html

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )

        if response.status_code in [200, 201, 202]:
            return True, "Email sent successfully."

        return False, response.text

    except Exception as exc:
        return False, str(exc)
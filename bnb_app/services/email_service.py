
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
    

def send_reset_code_email(user_email, full_name, code):
    subject = "Reset your Makgobelo Lodge password"

    body = f"""Hello {full_name},

We received a request to reset your password.

Your password reset code is: {code}

Use this code on the reset password page.

If you did not request a password reset, please ignore this email.

Makgobelo Lodge
"""

    html = f"""
    <h2>Password Reset Request</h2>
    <p>Hello {full_name},</p>
    <p>Your password reset code is:</p>
    <p style="font-size:24px;font-weight:bold;letter-spacing:2px;">{code}</p>
    <p>Use this code on the reset password page.</p>
    <p>If you did not request a password reset, please ignore this email.</p>
    <p><strong>Makgobelo Lodge</strong></p>
    """

    return send_email(user_email, subject, body, html)
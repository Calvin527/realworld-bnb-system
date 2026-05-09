
import os
import requests


def send_email(to_email, subject, body, html=None):
    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv(
        "MAIL_DEFAULT_SENDER",
        "Makgobelo Lodge <onboarding@resend.dev>"
    )

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


def send_verification_email(user_email, full_name, code):
    subject = "Verify your Makgobelo Lodge account"
    body = f"""Hello {full_name},

Your verification code is: {code}

Makgobelo Lodge
"""
    html = f"""
    <h2>Verify your account</h2>
    <p>Hello {full_name},</p>
    <p>Your verification code is:</p>
    <h1>{code}</h1>
    <p>Makgobelo Lodge</p>
    """
    return send_email(user_email, subject, body, html)


def send_reset_code_email(user_email, full_name, code):
    subject = "Reset your Makgobelo Lodge password"
    body = f"""Hello {full_name},

Your password reset code is: {code}

Makgobelo Lodge
"""
    html = f"""
    <h2>Password Reset</h2>
    <p>Hello {full_name},</p>
    <p>Your reset code is:</p>
    <h1>{code}</h1>
    <p>Makgobelo Lodge</p>
    """
    return send_email(user_email, subject, body, html)


def send_booking_confirmation_email(user_email, full_name, booking):
    subject = "Booking Confirmation - Makgobelo Lodge"
    body = f"""Hello {full_name},

Your booking has been confirmed.

Room: {booking['room_name']}
Check-in: {booking['check_in']}
Check-out: {booking['check_out']}
Guests: {booking['guests']}
Total Price: R{float(booking['total_price']):.2f}

Makgobelo Lodge
"""
    html = f"""
    <h2>Booking Confirmed</h2>
    <p>Hello {full_name},</p>
    <p>Your booking has been confirmed.</p>
    <ul>
      <li>Room: {booking['room_name']}</li>
      <li>Check-in: {booking['check_in']}</li>
      <li>Check-out: {booking['check_out']}</li>
      <li>Guests: {booking['guests']}</li>
      <li>Total: R{float(booking['total_price']):.2f}</li>
    </ul>
    """
    return send_email(user_email, subject, body, html)


def send_booking_cancellation_email(to_email, full_name, room_name, check_in, check_out):
    subject = "Booking Cancelled - Makgobelo Lodge"
    body = f"""Hello {full_name},

Your booking has been cancelled.

Room: {room_name}
Check-in: {check_in}
Check-out: {check_out}

Please note: No refund applies after cancelling.

Makgobelo Lodge
"""
    html = f"""
    <h2>Booking Cancelled</h2>
    <p>Hello {full_name},</p>
    <p>Your booking has been cancelled.</p>
    <ul>
      <li>Room: {room_name}</li>
      <li>Check-in: {check_in}</li>
      <li>Check-out: {check_out}</li>
    </ul>
    <p><strong>No refund applies after cancelling.</strong></p>
    """
    return send_email(to_email, subject, body, html)


def send_admin_booking_cancellation_email(
    to_email, full_name, room_name, check_in, check_out, refund_message
):
    subject = "Booking Cancelled by Administration - Makgobelo Lodge"
    body = f"""Hello {full_name},

Your booking has been cancelled by administration.

Room: {room_name}
Check-in: {check_in}
Check-out: {check_out}

Refund status:
{refund_message}

Makgobelo Lodge
"""
    html = f"""
    <h2>Booking Cancelled by Administration</h2>
    <p>Hello {full_name},</p>
    <ul>
      <li>Room: {room_name}</li>
      <li>Check-in: {check_in}</li>
      <li>Check-out: {check_out}</li>
    </ul>
    <p><strong>Refund status:</strong> {refund_message}</p>
    """
    return send_email(to_email, subject, body, html)


def send_admin_notification_email(subject, body):
    admin_email = os.getenv("ADMIN_EMAIL")

    if not admin_email:
        return False, "ADMIN_EMAIL is not configured."

    return send_email(admin_email, subject, body)


def send_breakfast_purchase_email(to_email, full_name, booking):
    subject = "Breakfast Updated - Makgobelo Lodge"
    body = f"""Hello {full_name},

Your breakfast selection has been updated.

Room: {booking['room_name']}
Check-in: {booking['check_in']}
Check-out: {booking['check_out']}
Breakfast: {booking['breakfast_name']}
Breakfast Cost: R{float(booking['breakfast_cost']):.2f}
Updated Total Price: R{float(booking['total_price']):.2f}

Makgobelo Lodge
"""
    html = f"""
    <h2>Breakfast Updated</h2>
    <p>Hello {full_name},</p>
    <ul>
      <li>Room: {booking['room_name']}</li>
      <li>Check-in: {booking['check_in']}</li>
      <li>Check-out: {booking['check_out']}</li>
      <li>Breakfast: {booking['breakfast_name']}</li>
      <li>Breakfast Cost: R{float(booking['breakfast_cost']):.2f}</li>
      <li>Updated Total: R{float(booking['total_price']):.2f}</li>
    </ul>
    """
    return send_email(to_email, subject, body, html)
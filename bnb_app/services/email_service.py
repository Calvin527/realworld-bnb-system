
import smtplib
from email.message import EmailMessage
from flask import current_app


def _get_mail_config():
    return {
        "enabled": current_app.config.get("MAIL_ENABLED", False),
        "server": current_app.config.get("MAIL_SERVER"),
        "port": current_app.config.get("MAIL_PORT", 587),
        "use_tls": current_app.config.get("MAIL_USE_TLS", True),
        "username": current_app.config.get("MAIL_USERNAME"),
        "password": current_app.config.get("MAIL_PASSWORD"),
        "default_sender": current_app.config.get("MAIL_DEFAULT_SENDER"),
    }


def send_email(to_email, subject, body, html=None):
    config = _get_mail_config()

    if not config["enabled"]:
        return False, "Email sending is disabled. Set MAIL_ENABLED=True in your .env file."

    missing = [
        key for key in ["server", "port", "username", "password", "default_sender"]
        if not config.get(key)
    ]
    if missing:
        return False, f"Email configuration is incomplete: {', '.join(missing)}"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config["default_sender"]
    msg["To"] = to_email
    msg.set_content(body)

    if html:
        msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(config["server"], config["port"]) as smtp:
            if config["use_tls"]:
                smtp.starttls()
            smtp.login(config["username"], config["password"])
            smtp.send_message(msg)
        return True, "Email sent successfully."
    except Exception as exc:
        return False, str(exc)


def send_verification_email(user_email, full_name, code):
    subject = "Verify your Makgobelo Lodge account"
    body = f"""Hello {full_name},

Welcome to Makgobelo Lodge.
Your email verification code is: {code}

Enter this code on the verification page to activate your account.

If you did not create this account, please ignore this email.

Makgobelo Lodge
"""
    html = f"""
    <h2>Welcome to Makgobelo Lodge</h2>
    <p>Hello {full_name},</p>
    <p>Your email verification code is:</p>
    <p style="font-size:24px;font-weight:bold;letter-spacing:2px;">{code}</p>
    <p>Enter this code on the verification page to activate your account.</p>
    <p>If you did not create this account, please ignore this email.</p>
    <p><strong>Makgobelo Lodge</strong></p>
    """
    return send_email(user_email, subject, body, html)


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


def send_booking_confirmation_email(user_email, full_name, booking):
    subject = f"Booking Confirmation - {booking['room_name']}"
    body = f"""Hello {full_name},

Your booking has been confirmed.

Booking details:
- Room: {booking['room_name']} ({booking['room_type']})
- Check-in: {booking['check_in']}
- Check-out: {booking['check_out']}
- Guests: {booking['guests']}
- Total Price: R{float(booking['total_price']):.2f}
- Breakfast: {booking['breakfast_name']}

Thank you for choosing Makgobelo Lodge.
"""
    html = f"""
    <h2>Booking Confirmed</h2>
    <p>Hello {full_name},</p>
    <p>Your booking has been confirmed.</p>
    <ul>
      <li><strong>Room:</strong> {booking['room_name']} ({booking['room_type']})</li>
      <li><strong>Check-in:</strong> {booking['check_in']}</li>
      <li><strong>Check-out:</strong> {booking['check_out']}</li>
      <li><strong>Guests:</strong> {booking['guests']}</li>
      <li><strong>Total Price:</strong> R{float(booking['total_price']):.2f}</li>
      <li><strong>Breakfast:</strong> {booking['breakfast_name']}</li>
    </ul>
    <p>Thank you for choosing <strong>Makgobelo Lodge</strong>.</p>
    """
    return send_email(user_email, subject, body, html)


def send_booking_cancellation_email(to_email, full_name, room_name, check_in, check_out):
    subject = "Booking Cancelled - Makgobelo Lodge"

    body = f"""Hello {full_name},

Your booking at Makgobelo Lodge has been cancelled successfully.

Booking details:
Room: {room_name}
Check-in: {check_in}
Check-out: {check_out}

Please note: No refund applies after cancelling.

If you did not make this request, please contact Makgobelo Lodge immediately.

Regards,
Makgobelo Lodge
"""

    html = f"""
    <h2>Booking Cancelled</h2>
    <p>Hello {full_name},</p>
    <p>Your booking at <strong>Makgobelo Lodge</strong> has been cancelled successfully.</p>
    <ul>
      <li><strong>Room:</strong> {room_name}</li>
      <li><strong>Check-in:</strong> {check_in}</li>
      <li><strong>Check-out:</strong> {check_out}</li>
    </ul>
    <p><strong>No refund applies after cancelling.</strong></p>
    <p>If you did not make this request, please contact Makgobelo Lodge immediately.</p>
    <p>Regards,<br>Makgobelo Lodge</p>
    """
    return send_email(to_email, subject, body, html)
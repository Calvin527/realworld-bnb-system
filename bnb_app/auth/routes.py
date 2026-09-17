
import os
import re
import secrets
import string

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import execute_db, query_db
from ..utils import inject_common


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
auth_bp.context_processor(inject_common)


MAX_LOGIN_ATTEMPTS = 5


def generate_recovery_code():
    """
    Creates a secret recovery code like: A7K9-P2MX
    The plain code is shown to the user once after registration.
    Only the hashed version is stored in the database.
    """
    characters = string.ascii_uppercase + string.digits
    first_part = "".join(secrets.choice(characters) for _ in range(4))
    second_part = "".join(secrets.choice(characters) for _ in range(4))
    return f"{first_part}-{second_part}"


def normalize_recovery_code(code):
    """
    Accepts codes like A7K9-P2MX or A7K9P2MX and normalizes them.
    """
    clean_code = (code or "").strip().upper().replace(" ", "")

    if "-" not in clean_code and len(clean_code) == 8:
        clean_code = f"{clean_code[:4]}-{clean_code[4:]}"

    return clean_code


def get_admin_contact():
    return os.getenv("ADMIN_EMAIL", "the administrator")


def is_valid_name(name):
    return bool(re.fullmatch(r"[A-Za-zÀ-ÿ\s'-]{2,120}", name or ""))


def is_valid_gmail(email):
    return bool(re.fullmatch(r"[a-zA-Z0-9._%+-]+@gmail\.com", email or ""))


def is_valid_phone(phone):
    if not phone:
        return True
    return bool(re.fullmatch(r"(\+27|0)[0-9]{9}", phone))


def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character."
    return True, ""


def row_value(row, key, default=None):
    if hasattr(row, "get"):
        return row.get(key, default)

    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return default


@auth_bp.route("/resend-verification/<email>", methods=["POST"])
def resend_verification(email):
    # Email verification is removed. Users confirm registration using their secret recovery code.
    flash(
        "Email verification is disabled. Registration is confirmed using your secret recovery code.",
        "info",
    )
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        if session.get("role") == "admin":
            return redirect(url_for("system.admin_dashboard"))
        return redirect(url_for("system.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("auth/login.html")

        if not is_valid_gmail(email):
            flash("Please enter a valid Gmail address.", "danger")
            return render_template("auth/login.html")

        user = query_db(
            """
            SELECT *
            FROM users
            WHERE email = %s
            """,
            [email],
            one=True,
        )

        if not user:
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")

        if row_value(user, "is_locked", False):
            flash(
                f"Your account is locked because of too many failed login attempts. "
                f"Please send an email to {get_admin_contact()} so your secret recovery code can be reset.",
                "danger",
            )
            return render_template("auth/login.html")

        if row_value(user, "is_active", True) is False:
            flash(
                f"Your account has been deactivated. Please send an email to {get_admin_contact()} for assistance.",
                "danger",
            )
            return render_template("auth/login.html")

        if check_password_hash(user["password_hash"], password):
            execute_db(
                """
                UPDATE users
                SET failed_login_attempts = 0,
                    is_locked = FALSE
                WHERE user_id = %s
                """,
                [user["user_id"]],
            )

            session.clear()
            session["user_id"] = user["user_id"]
            session["full_name"] = user["full_name"]
            session["email"] = user["email"]
            session["role"] = user["role"]

            flash("Login successful.", "success")

            if user["role"] == "admin":
                return redirect(url_for("system.admin_dashboard"))

            return redirect(url_for("system.dashboard"))

        failed_attempts = int(row_value(user, "failed_login_attempts", 0) or 0) + 1

        if failed_attempts >= MAX_LOGIN_ATTEMPTS:
            execute_db(
                """
                UPDATE users
                SET failed_login_attempts = %s,
                    is_locked = TRUE
                WHERE user_id = %s
                """,
                [failed_attempts, user["user_id"]],
            )

            flash(
                f"Too many failed login attempts. Your account has been locked. "
                f"Please send an email to {get_admin_contact()} so your account and secret recovery code can be reset.",
                "danger",
            )
            return render_template("auth/login.html")

        execute_db(
            """
            UPDATE users
            SET failed_login_attempts = %s
            WHERE user_id = %s
            """,
            [failed_attempts, user["user_id"]],
        )

        remaining_attempts = MAX_LOGIN_ATTEMPTS - failed_attempts

        flash(
            f"Invalid email or password. You have {remaining_attempts} attempt(s) left.",
            "danger",
        )

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        if session.get("role") == "admin":
            return redirect(url_for("system.admin_dashboard"))
        return redirect(url_for("system.dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not full_name or not email or not password or not confirm_password:
            flash("Full name, email, password, and confirm password are required.", "danger")
            return render_template("auth/register.html")

        if not is_valid_name(full_name):
            flash("Full name must contain letters only and be between 2 and 120 characters.", "danger")
            return render_template("auth/register.html")

        if not is_valid_gmail(email):
            flash("Please enter a valid Gmail address.", "danger")
            return render_template("auth/register.html")

        if not is_valid_phone(phone):
            flash("Phone number must be valid. Use format 0712345678 or +27712345678.", "danger")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")

        password_ok, password_message = validate_password(password)
        if not password_ok:
            flash(password_message, "danger")
            return render_template("auth/register.html")

        existing = query_db(
            """
            SELECT user_id
            FROM users
            WHERE email = %s
            """,
            [email],
            one=True,
        )

        if existing:
            flash("That email is already registered.", "danger")
            return render_template("auth/register.html")

        password_hash = generate_password_hash(password)
        recovery_code = generate_recovery_code()
        recovery_code_hash = generate_password_hash(recovery_code)

        execute_db(
            """
            INSERT INTO users
                (
                    full_name,
                    email,
                    phone,
                    password_hash,
                    role,
                    is_email_verified,
                    verification_code,
                    recovery_code_hash,
                    failed_login_attempts,
                    is_locked,
                    is_active
                )
            VALUES
                (%s, %s, %s, %s, 'guest', TRUE, NULL, %s, 0, FALSE, TRUE)
            """,
            [
                full_name,
                email,
                phone or None,
                password_hash,
                recovery_code_hash,
            ],
        )

        session["new_recovery_code"] = recovery_code
        session["new_recovery_email"] = email

        flash("Account created successfully. Please save your secret recovery code.", "success")
        return redirect(url_for("auth.registration_success"))

    return render_template("auth/register.html")


@auth_bp.route("/registration-success")
def registration_success():
    recovery_code = session.get("new_recovery_code")
    email = session.get("new_recovery_email")

    if not recovery_code or not email:
        flash("Please register first to receive your secret recovery code.", "warning")
        return redirect(url_for("auth.register"))

    return render_template(
        "auth/registration_success.html",
        recovery_code=recovery_code,
        email=email,
    )


@auth_bp.route("/finish-registration", methods=["POST"])
def finish_registration():
    session.pop("new_recovery_code", None)
    session.pop("new_recovery_email", None)

    flash("You can now log in. Keep your secret recovery code safe.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    # Email verification is removed. Registration is confirmed using the secret recovery code page.
    flash(
        "Email verification is disabled. Please log in using your account password.",
        "info",
    )
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        recovery_code = normalize_recovery_code(request.form.get("recovery_code", ""))
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email or not recovery_code or not password or not confirm_password:
            flash("Email, secret recovery code, password, and confirm password are required.", "danger")
            return render_template("auth/forgot_password.html")

        if not is_valid_gmail(email):
            flash("Please enter a valid Gmail address.", "danger")
            return render_template("auth/forgot_password.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/forgot_password.html")

        password_ok, password_message = validate_password(password)
        if not password_ok:
            flash(password_message, "danger")
            return render_template("auth/forgot_password.html")

        user = query_db(
            """
            SELECT *
            FROM users
            WHERE email = %s
            """,
            [email],
            one=True,
        )

        if not user:
            flash("Invalid email or secret recovery code.", "danger")
            return render_template("auth/forgot_password.html")

        recovery_code_hash = row_value(user, "recovery_code_hash")

        if not recovery_code_hash:
            flash(
                f"This account does not have a secret recovery code yet. "
                f"Please send an email to {get_admin_contact()} for assistance.",
                "warning",
            )
            return render_template("auth/forgot_password.html")

        if not check_password_hash(recovery_code_hash, recovery_code):
            flash(
                f"Invalid email or secret recovery code. "
                f"If you forgot your secret code, please send an email to {get_admin_contact()} for assistance.",
                "danger",
            )
            return render_template("auth/forgot_password.html")

        execute_db(
            """
            UPDATE users
            SET password_hash = %s,
                failed_login_attempts = 0,
                is_locked = FALSE
            WHERE user_id = %s
            """,
            [generate_password_hash(password), user["user_id"]],
        )

        flash("Password reset successfully. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    # Old email reset route is kept only to prevent broken links.
    # The real reset process now happens through /auth/forgot-password using the secret recovery code.
    flash("Password reset now uses your secret recovery code instead of email reset codes.", "info")
    return redirect(url_for("auth.forgot_password"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("system.homepage"))

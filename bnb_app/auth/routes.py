
import random
import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import execute_db, query_db
from ..services.email_service import send_reset_code_email
from ..utils import inject_common


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
auth_bp.context_processor(inject_common)


def generate_verification_code():
    return f"{random.randint(100000, 999999)}"


def is_valid_name(name):
    return bool(re.fullmatch(r"[A-Za-zÀ-ÿ\s'-]{2,120}", name))


def is_valid_gmail(email):
    return bool(re.fullmatch(r"[a-zA-Z0-9._%+-]+@gmail\.com", email))


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
    # Email verification is disabled for public demo mode.
    flash("Email verification is disabled. Please log in with your account.", "info")
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

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")

        if row_value(user, "is_active", True) is False:
            flash("Your account has been deactivated. Please contact admin.", "danger")
            return render_template("auth/login.html")

        # Email verification is disabled for public demo mode.
        session.clear()
        session["user_id"] = user["user_id"]
        session["full_name"] = user["full_name"]
        session["email"] = user["email"]
        session["role"] = user["role"]

        flash("Login successful.", "success")

        if user["role"] == "admin":
            return redirect(url_for("system.admin_dashboard"))
        return redirect(url_for("system.dashboard"))

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

        execute_db(
            """
            INSERT INTO users
                (full_name, email, phone, password_hash, role, is_email_verified, verification_code, is_active)
            VALUES
                (%s, %s, %s, %s, 'guest', TRUE, NULL, TRUE)
            """,
            [full_name, email, phone or None, password_hash],
        )

        flash("Account created successfully. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    # Email verification is disabled for public demo mode.
    flash("Email verification is disabled. Please log in with your account.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email:
            flash("Email is required.", "danger")
            return render_template("auth/forgot_password.html")

        if not is_valid_gmail(email):
            flash("Please enter a valid Gmail address.", "danger")
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
            flash("No account exists for that email.", "danger")
            return render_template("auth/forgot_password.html")

        code = generate_verification_code()

        execute_db(
            """
            UPDATE users
            SET reset_code = %s
            WHERE user_id = %s
            """,
            [code, user["user_id"]],
        )

        sent, message = send_reset_code_email(email, user["full_name"], code)

        if not sent:
            flash(f"Could not send reset email. Reason: {message}", "danger")
            return render_template("auth/forgot_password.html")

        flash("A password reset code has been sent to your email address.", "success")
        return redirect(url_for("auth.reset_password", email=email))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = request.args.get("email", request.form.get("email", "")).strip().lower()

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        code = request.form.get("code", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email or not code or not password or not confirm_password:
            flash("Email, reset code, password, and confirm password are required.", "danger")
            return render_template("auth/reset_password.html", email=email)

        if not is_valid_gmail(email):
            flash("Please enter a valid Gmail address.", "danger")
            return render_template("auth/reset_password.html", email=email)

        if not re.fullmatch(r"[0-9]{6}", code):
            flash("Reset code must be exactly 6 digits.", "danger")
            return render_template("auth/reset_password.html", email=email)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/reset_password.html", email=email)

        password_ok, password_message = validate_password(password)
        if not password_ok:
            flash(password_message, "danger")
            return render_template("auth/reset_password.html", email=email)

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
            flash("Account not found.", "danger")
        elif user["reset_code"] != code:
            flash("Reset code is incorrect.", "danger")
        else:
            execute_db(
                """
                UPDATE users
                SET password_hash = %s,
                    reset_code = NULL
                WHERE user_id = %s
                """,
                [generate_password_hash(password), user["user_id"]],
            )
            flash("Password updated successfully. You can now log in.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", email=email)


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("system.homepage"))

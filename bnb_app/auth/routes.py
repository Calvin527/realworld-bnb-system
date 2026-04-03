import random
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import execute_db, query_db
from ..services.email_service import send_reset_code_email, send_verification_email
from ..utils import inject_common


auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
auth_bp.context_processor(inject_common)



def generate_verification_code():
    return f"{random.randint(100000, 999999)}"


@auth_bp.route('/resend-verification/<email>', methods=['POST'])
def resend_verification(email):
    email = email.strip().lower()

    user = query_db(
        """
        SELECT user_id, full_name, email, is_verified
        FROM users
        WHERE email = %s
        """,
        [email],
        one=True,
    )

    if not user:
        flash('User account not found.', 'danger')
        return redirect(url_for('auth.register'))

    if user['is_verified']:
        flash('This account is already verified. Please log in.', 'info')
        return redirect(url_for('auth.login'))

    code = generate_verification_code()
    execute_db(
        """
        UPDATE users
        SET verification_code = %s
        WHERE email = %s
        """,
        [code, email],
    )

    sent, message = send_verification_email(user['email'], user['full_name'], code)
    if not sent:
        flash(f'Could not resend verification email. Reason: {message}', 'danger')
        return redirect(url_for('auth.verify_email', email=email))

    flash('A new verification code has been sent to your email address.', 'success')
    return redirect(url_for('auth.verify_email', email=email))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        if session.get('role') == 'admin':
            return redirect(url_for('system.admin_dashboard'))
        return redirect(url_for('system.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = query_db('SELECT * FROM users WHERE email = %s', [email], one=True)

        if user and user.get('is_active') is False:
            flash('This account has been deactivated. Please contact the administrator.', 'danger')
            return render_template('auth/login.html')

        if user and check_password_hash(user['password_hash'], password):
            if not user['is_verified']:
                flash('Please verify your email before logging in.', 'warning')
                return redirect(url_for('auth.verify_email', email=user['email']))

            session['user_id'] = user['user_id']
            session['full_name'] = user['full_name']
            session['email'] = user['email']
            session['role'] = user['role']

            flash('Login successful.', 'success')
            if user['role'] == 'admin':
                return redirect(url_for('system.admin_dashboard'))
            return redirect(url_for('system.dashboard'))

        flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not full_name or not email or not password:
            flash('Full name, email, and password are required.', 'danger')
            return render_template('auth/register.html')

        if not email.endswith('@gmail.com'):
            flash('Email must be a @gmail.com address.', 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        existing = query_db('SELECT user_id FROM users WHERE email = %s', [email], one=True)
        if existing:
            flash('That email is already registered.', 'danger')
            return render_template('auth/register.html')

        password_hash = generate_password_hash(password)
        code = generate_verification_code()

        execute_db(
            """
            INSERT INTO users (full_name, email, phone, password_hash, verification_code, is_verified, role, is_active)
            VALUES (%s, %s, %s, %s, %s, FALSE, 'user', TRUE)
            """,
            [full_name, email, phone or None, password_hash, code],
        )

        sent, message = send_verification_email(email, full_name, code)
        if not sent:
            execute_db('DELETE FROM users WHERE email = %s', [email])
            flash(
                f'Account could not be created because the verification email was not sent. Reason: {message}',
                'danger',
            )
            return render_template('auth/register.html')

        flash('Account created successfully. A verification code has been sent to your email address.', 'success')
        return redirect(url_for('auth.verify_email', email=email))

    return render_template('auth/register.html')


@auth_bp.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    email = request.args.get('email', request.form.get('email', '')).strip().lower()

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        code = request.form.get('code', '').strip()
        user = query_db('SELECT * FROM users WHERE email = %s', [email], one=True)

        if not user:
            flash('Account not found.', 'danger')
        elif user['verification_code'] != code:
            flash('Verification code is incorrect.', 'danger')
        else:
            execute_db(
                'UPDATE users SET is_verified = TRUE, verification_code = NULL WHERE user_id = %s',
                [user['user_id']],
            )
            flash('Email verified. You can now log in.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/verify_email.html', email=email)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = query_db('SELECT * FROM users WHERE email = %s', [email], one=True)

        if not user:
            flash('No account exists for that email.', 'danger')
        else:
            code = generate_verification_code()
            execute_db('UPDATE users SET reset_code = %s WHERE user_id = %s', [code, user['user_id']])
            sent, message = send_reset_code_email(email, user['full_name'], code)
            if sent:
                flash('A password reset code has been sent to your email address.', 'success')
            else:
                flash(f'Could not send reset email. Reason: {message}', 'danger')
            return redirect(url_for('auth.reset_password', email=email))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = request.args.get('email', request.form.get('email', '')).strip().lower()

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        code = request.form.get('code', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        user = query_db('SELECT * FROM users WHERE email = %s', [email], one=True)

        if not user:
            flash('Account not found.', 'danger')
        elif user['reset_code'] != code:
            flash('Reset code is incorrect.', 'danger')
        elif password != confirm_password:
            flash('Passwords do not match.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
        else:
            execute_db(
                'UPDATE users SET password_hash = %s, reset_code = NULL WHERE user_id = %s',
                [generate_password_hash(password), user['user_id']],
            )
            flash('Password updated successfully. You can now log in.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', email=email)


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('system.homepage'))

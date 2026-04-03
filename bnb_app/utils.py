from datetime import date
from functools import wraps
from flask import flash, redirect, session, url_for
from .db import query_db



def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in first.', 'warning')
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)

    return wrapped



def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in first.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('Administrator access is required.', 'danger')
            return redirect(url_for('system.dashboard'))
        return view(*args, **kwargs)

    return wrapped



def current_user():
    if not session.get('user_id'):
        return None
    return query_db('SELECT * FROM users WHERE user_id = %s', [session['user_id']], one=True)



def inject_common():
    return {'current_user': current_user(), 'today': date.today()}

from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..db import execute_db, query_db
from ..services.email_service import (
    send_booking_cancellation_email,
    send_booking_confirmation_email,
)
from ..utils import admin_required, inject_common, login_required


system_bp = Blueprint('system', __name__)
system_bp.context_processor(inject_common)


@system_bp.route('/')
def homepage():
    rooms = query_db(
        'SELECT * FROM rooms WHERE is_active = TRUE ORDER BY room_id LIMIT 3'
    )
    breakfasts = query_db(
        'SELECT * FROM breakfast_options WHERE is_active = TRUE ORDER BY price'
    )
    return render_template('system/homepage.html', rooms=rooms, breakfasts=breakfasts)


@system_bp.route('/dashboard')
@login_required
def dashboard():
    if session.get('role') == 'admin':
        return redirect(url_for('system.admin_dashboard'))

    total_rooms_row = query_db(
        'SELECT COUNT(*) AS total_rooms FROM rooms WHERE is_active = TRUE', one=True
    )
    total_rooms = total_rooms_row['total_rooms'] if total_rooms_row else 0

    occupied_rooms_row = query_db(
        """
        SELECT COUNT(DISTINCT room_id) AS occupied_rooms
        FROM bookings
        WHERE status = 'confirmed'
          AND check_in <= CURRENT_DATE
          AND check_out > CURRENT_DATE
        """,
        one=True,
    )
    occupied_rooms = occupied_rooms_row['occupied_rooms'] if occupied_rooms_row else 0
    available_rooms = total_rooms - occupied_rooms

    total_guests_row = query_db(
        """
        SELECT COALESCE(SUM(guests), 0) AS total_guests
        FROM bookings
        WHERE status = 'confirmed'
          AND check_in <= CURRENT_DATE
          AND check_out > CURRENT_DATE
        """,
        one=True,
    )
    total_guests = total_guests_row['total_guests'] if total_guests_row else 0

    total_reservations_row = query_db(
        'SELECT COUNT(*) AS total_reservations FROM bookings', one=True
    )
    total_reservations = (
        total_reservations_row['total_reservations'] if total_reservations_row else 0
    )

    pending_row = query_db(
        "SELECT COUNT(*) AS total FROM bookings WHERE status = 'pending'", one=True
    )
    pending_reservations = pending_row['total'] if pending_row else 0

    confirmed_row = query_db(
        "SELECT COUNT(*) AS total FROM bookings WHERE status = 'confirmed'", one=True
    )
    confirmed_reservations = confirmed_row['total'] if confirmed_row else 0

    cancelled_row = query_db(
        "SELECT COUNT(*) AS total FROM bookings WHERE status = 'cancelled'", one=True
    )
    cancelled_reservations = cancelled_row['total'] if cancelled_row else 0

    occupancy_rate = round((occupied_rooms / total_rooms) * 100, 1) if total_rooms else 0

    room_statuses = query_db(
        """
        SELECT
            r.room_id,
            r.room_name,
            r.room_type,
            r.capacity,
            r.price_per_night,
            CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM bookings b
                    WHERE b.room_id = r.room_id
                      AND b.status = 'confirmed'
                      AND b.check_in <= CURRENT_DATE
                      AND b.check_out > CURRENT_DATE
                )
                THEN 'Occupied'
                ELSE 'Available'
            END AS current_status
        FROM rooms r
        WHERE r.is_active = TRUE
        ORDER BY r.room_id
        """
    )

    recent_reservations = query_db(
        """
        SELECT
            b.booking_id,
            u.full_name,
            r.room_name,
            r.room_type,
            b.check_in,
            b.check_out,
            b.guests,
            b.total_price,
            b.status
        FROM bookings b
        JOIN users u ON b.user_id = u.user_id
        JOIN rooms r ON b.room_id = r.room_id
        ORDER BY b.created_at DESC
        LIMIT 5
        """
    )

    reservation_types = query_db(
        """
        SELECT r.room_type, COUNT(*) AS total
        FROM bookings b
        JOIN rooms r ON b.room_id = r.room_id
        GROUP BY r.room_type
        ORDER BY total DESC
        """
    )

    user_bookings = query_db(
        """
        SELECT
            b.booking_id,
            r.room_name,
            r.room_type,
            b.check_in,
            b.check_out,
            b.guests,
            b.total_price,
            b.status,
            CASE
                WHEN b.status IN ('pending', 'confirmed') AND b.check_out > CURRENT_DATE THEN TRUE
                ELSE FALSE
            END AS can_cancel
        FROM bookings b
        JOIN rooms r ON b.room_id = r.room_id
        WHERE b.user_id = %s
        ORDER BY b.created_at DESC
        """,
        [session['user_id']],
    )

    return render_template(
        'system/dashboard.html',
        total_rooms=total_rooms,
        occupied_rooms=occupied_rooms,
        available_rooms=available_rooms,
        total_guests=total_guests,
        total_reservations=total_reservations,
        occupancy_rate=occupancy_rate,
        pending_reservations=pending_reservations,
        confirmed_reservations=confirmed_reservations,
        cancelled_reservations=cancelled_reservations,
        room_statuses=room_statuses,
        recent_reservations=recent_reservations,
        reservation_types=reservation_types,
        user_bookings=user_bookings,
    )


@system_bp.route('/system/rooms')
@login_required
def rooms():
    room_rows = query_db('SELECT * FROM rooms WHERE is_active = TRUE ORDER BY price_per_night')
    breakfasts = query_db('SELECT * FROM breakfast_options WHERE is_active = TRUE ORDER BY price')
    return render_template('system/rooms.html', rooms=room_rows, breakfasts=breakfasts)


@system_bp.route('/system/book/<int:room_id>', methods=['GET', 'POST'])
@login_required
def book(room_id):
    if session.get('role') == 'admin':
        flash('Admins cannot make guest bookings from this page.', 'warning')
        return redirect(url_for('system.admin_dashboard'))

    room = query_db(
        'SELECT * FROM rooms WHERE room_id = %s AND is_active = TRUE',
        [room_id],
        one=True,
    )
    if not room:
        flash('Room not found.', 'danger')
        return redirect(url_for('system.rooms'))

    breakfasts = query_db('SELECT * FROM breakfast_options WHERE is_active = TRUE ORDER BY price')

    if request.method == 'POST':
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')
        guests = int(request.form.get('guests', room['capacity']))
        special_requests = request.form.get('special_requests', '').strip()
        breakfast_id = request.form.get('breakfast_id') or None

        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        except Exception:
            flash('Please provide valid dates.', 'danger')
            return render_template('system/book.html', room=room, breakfasts=breakfasts)

        if check_out_date <= check_in_date:
            flash('Check-out date must be after check-in date.', 'danger')
            return render_template('system/book.html', room=room, breakfasts=breakfasts)
        if guests < 1 or guests > room['capacity']:
            flash('Number of guests must fit the selected room.', 'danger')
            return render_template('system/book.html', room=room, breakfasts=breakfasts)

        overlap = query_db(
            """
            SELECT booking_id FROM bookings
            WHERE room_id = %s
              AND status IN ('pending', 'confirmed')
              AND NOT (%s >= check_out OR %s <= check_in)
            """,
            [room_id, check_in_date, check_out_date],
            one=True,
        )
        if overlap:
            flash('This room is not available for those dates.', 'danger')
            return render_template('system/book.html', room=room, breakfasts=breakfasts)

        nights = (check_out_date - check_in_date).days
        breakfast_price = 0.0
        breakfast_name = 'No breakfast'
        if breakfast_id:
            breakfast = query_db(
                'SELECT * FROM breakfast_options WHERE breakfast_id = %s',
                [breakfast_id],
                one=True,
            )
            if breakfast:
                breakfast_price = float(breakfast['price'])
                breakfast_name = breakfast['name']

        total_price = float(room['price_per_night']) * nights + breakfast_price * guests * nights

        execute_db(
            """
            INSERT INTO bookings
            (user_id, room_id, breakfast_id, check_in, check_out, guests, special_requests, total_price, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'confirmed')
            """,
            [
                session['user_id'],
                room_id,
                breakfast_id,
                check_in_date,
                check_out_date,
                guests,
                special_requests,
                total_price,
            ],
        )

        booking = query_db(
            """
            SELECT
                u.email,
                u.full_name,
                r.room_name,
                r.room_type,
                b.check_in,
                b.check_out,
                b.guests,
                b.total_price,
                COALESCE(bo.name, 'No breakfast') AS breakfast_name
            FROM bookings b
            JOIN users u ON b.user_id = u.user_id
            JOIN rooms r ON b.room_id = r.room_id
            LEFT JOIN breakfast_options bo ON b.breakfast_id = bo.breakfast_id
            WHERE b.user_id = %s AND b.room_id = %s
            ORDER BY b.booking_id DESC
            LIMIT 1
            """,
            [session['user_id'], room_id],
            one=True,
        )

        email_sent = False
        if booking:
            email_sent, email_message = send_booking_confirmation_email(
                booking['email'], booking['full_name'], booking
            )
            if not email_sent:
                flash(
                    f'Booking confirmed, but confirmation email was not sent. Reason: {email_message}',
                    'warning',
                )

        if email_sent:
            flash(
                f'Booking confirmed. A confirmation email has been sent. Total price: R{total_price:.2f}',
                'success',
            )
        else:
            flash(f'Booking confirmed. Total price: R{total_price:.2f}', 'success')
        return redirect(url_for('system.dashboard'))

    return render_template('system/book.html', room=room, breakfasts=breakfasts)


@system_bp.route('/system/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = query_db(
        """
        SELECT
            b.booking_id,
            b.status,
            b.check_in,
            b.check_out,
            r.room_name,
            u.email,
            u.full_name
        FROM bookings b
        JOIN rooms r ON b.room_id = r.room_id
        JOIN users u ON b.user_id = u.user_id
        WHERE b.booking_id = %s AND b.user_id = %s
        """,
        [booking_id, session['user_id']],
        one=True,
    )

    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('system.dashboard'))
    if booking['status'] == 'cancelled':
        flash('This booking is already cancelled.', 'warning')
        return redirect(url_for('system.dashboard'))
    if booking['check_out'] <= datetime.today().date():
        flash('This booking can no longer be cancelled because the stay has ended.', 'warning')
        return redirect(url_for('system.dashboard'))

    execute_db('UPDATE bookings SET status = %s WHERE booking_id = %s', ['cancelled', booking_id])

    sent, message = send_booking_cancellation_email(
        booking['email'],
        booking['full_name'],
        booking['room_name'],
        booking['check_in'],
        booking['check_out'],
    )

    if sent:
        flash('Booking cancelled successfully. A cancellation email has been sent.', 'info')
    else:
        flash(
            f'Booking cancelled successfully, but cancellation email was not sent. Reason: {message}',
            'warning',
        )
    return redirect(url_for('system.dashboard'))


@system_bp.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    total_users_row = query_db('SELECT COUNT(*) AS total_users FROM users', one=True)
    total_users = total_users_row['total_users'] if total_users_row else 0

    total_rooms_row = query_db(
        'SELECT COUNT(*) AS total_rooms FROM rooms WHERE is_active = TRUE', one=True
    )
    total_rooms = total_rooms_row['total_rooms'] if total_rooms_row else 0

    occupied_rooms_row = query_db(
        """
        SELECT COUNT(DISTINCT room_id) AS occupied_rooms
        FROM bookings
        WHERE status = 'confirmed'
          AND check_in <= CURRENT_DATE
          AND check_out > CURRENT_DATE
        """,
        one=True,
    )
    occupied_rooms = occupied_rooms_row['occupied_rooms'] if occupied_rooms_row else 0
    available_rooms = total_rooms - occupied_rooms

    total_bookings_row = query_db('SELECT COUNT(*) AS total_bookings FROM bookings', one=True)
    total_bookings = total_bookings_row['total_bookings'] if total_bookings_row else 0

    pending_row = query_db("SELECT COUNT(*) AS total FROM bookings WHERE status = 'pending'", one=True)
    pending_bookings = pending_row['total'] if pending_row else 0

    confirmed_row = query_db("SELECT COUNT(*) AS total FROM bookings WHERE status = 'confirmed'", one=True)
    confirmed_bookings = confirmed_row['total'] if confirmed_row else 0

    cancelled_row = query_db("SELECT COUNT(*) AS total FROM bookings WHERE status = 'cancelled'", one=True)
    cancelled_bookings = cancelled_row['total'] if cancelled_row else 0

    users = query_db(
        """
        SELECT user_id, full_name, email, role, is_verified, is_active, created_at
        FROM users
        ORDER BY created_at DESC
        """
    )

    bookings = query_db(
        """
        SELECT
            b.booking_id,
            u.full_name,
            u.email,
            r.room_name,
            r.room_type,
            b.check_in,
            b.check_out,
            b.guests,
            b.total_price,
            b.status
        FROM bookings b
        JOIN users u ON b.user_id = u.user_id
        JOIN rooms r ON b.room_id = r.room_id
        ORDER BY b.created_at DESC
        """
    )

    rooms = query_db(
        """
        SELECT room_id, room_name, room_type, capacity, price_per_night, is_active
        FROM rooms
        ORDER BY room_id
        """
    )

    return render_template(
        'system/admin_dashboard.html',
        total_users=total_users,
        total_rooms=total_rooms,
        occupied_rooms=occupied_rooms,
        available_rooms=available_rooms,
        total_bookings=total_bookings,
        pending_bookings=pending_bookings,
        confirmed_bookings=confirmed_bookings,
        cancelled_bookings=cancelled_bookings,
        users=users,
        bookings=bookings,
        rooms=rooms,
    )


@system_bp.route('/admin/booking/<int:booking_id>/confirm', methods=['POST'])
@login_required
@admin_required
def admin_confirm_booking(booking_id):
    booking = query_db('SELECT booking_id, status FROM bookings WHERE booking_id = %s', [booking_id], one=True)
    if not booking:
        flash('Booking not found.', 'danger')
    elif booking['status'] == 'confirmed':
        flash('Booking is already confirmed.', 'warning')
    else:
        execute_db('UPDATE bookings SET status = %s WHERE booking_id = %s', ['confirmed', booking_id])
        flash('Booking confirmed successfully.', 'success')
    return redirect(url_for('system.admin_dashboard'))


@system_bp.route('/admin/booking/<int:booking_id>/cancel', methods=['POST'])
@login_required
@admin_required
def admin_cancel_booking(booking_id):
    booking = query_db('SELECT booking_id, status FROM bookings WHERE booking_id = %s', [booking_id], one=True)
    if not booking:
        flash('Booking not found.', 'danger')
    elif booking['status'] == 'cancelled':
        flash('Booking is already cancelled.', 'warning')
    else:
        execute_db('UPDATE bookings SET status = %s WHERE booking_id = %s', ['cancelled', booking_id])
        flash('Booking cancelled successfully by admin.', 'info')
    return redirect(url_for('system.admin_dashboard'))


@system_bp.route('/admin/booking/<int:booking_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_booking(booking_id):
    booking = query_db('SELECT booking_id FROM bookings WHERE booking_id = %s', [booking_id], one=True)
    if not booking:
        flash('Booking not found.', 'danger')
    else:
        execute_db('DELETE FROM bookings WHERE booking_id = %s', [booking_id])
        flash('Booking history deleted successfully.', 'success')
    return redirect(url_for('system.admin_dashboard'))


@system_bp.route('/admin/users/make-admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def make_admin(user_id):
    user = query_db('SELECT user_id, role FROM users WHERE user_id = %s', [user_id], one=True)
    if not user:
        flash('User not found.', 'danger')
    elif user['role'] == 'admin':
        flash('User is already an admin.', 'warning')
    else:
        execute_db("UPDATE users SET role = 'admin' WHERE user_id = %s", [user_id])
        flash('User promoted to admin successfully.', 'success')
    return redirect(url_for('system.admin_dashboard'))


@system_bp.route('/admin/users/deactivate/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def deactivate_user(user_id):
    user = query_db('SELECT user_id, role FROM users WHERE user_id = %s', [user_id], one=True)
    if not user:
        flash('User not found.', 'danger')
    elif user['role'] == 'admin':
        flash('Admin accounts cannot be deactivated from this page.', 'warning')
    else:
        execute_db('UPDATE users SET is_active = FALSE WHERE user_id = %s', [user_id])
        flash('User deactivated successfully.', 'info')
    return redirect(url_for('system.admin_dashboard'))


@system_bp.route('/admin/users/activate/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def activate_user(user_id):
    user = query_db('SELECT user_id FROM users WHERE user_id = %s', [user_id], one=True)
    if not user:
        flash('User not found.', 'danger')
    else:
        execute_db('UPDATE users SET is_active = TRUE WHERE user_id = %s', [user_id])
        flash('User activated successfully.', 'success')
    return redirect(url_for('system.admin_dashboard'))


@system_bp.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = query_db('SELECT user_id, role FROM users WHERE user_id = %s', [user_id], one=True)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('system.admin_dashboard'))
    if user['role'] == 'admin':
        flash('Admin accounts cannot be deleted from this page.', 'warning')
        return redirect(url_for('system.admin_dashboard'))

    existing_booking = query_db('SELECT booking_id FROM bookings WHERE user_id = %s LIMIT 1', [user_id], one=True)
    if existing_booking:
        flash(
            'This user cannot be deleted because they have booking history. Delete their bookings first or deactivate the account.',
            'warning',
        )
        return redirect(url_for('system.admin_dashboard'))

    execute_db('DELETE FROM users WHERE user_id = %s', [user_id])
    flash('User deleted successfully.', 'success')
    return redirect(url_for('system.admin_dashboard'))


@system_bp.route('/admin/rooms/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_room():
    if request.method == 'POST':
        room_name = request.form.get('room_name', '').strip()
        room_type = request.form.get('room_type', '').strip()
        capacity = request.form.get('capacity', '').strip()
        price_per_night = request.form.get('price_per_night', '').strip()

        if not room_name or not room_type or not capacity or not price_per_night:
            flash('All room fields are required.', 'danger')
            return render_template('system/add_room.html')

        execute_db(
            """
            INSERT INTO rooms (room_name, room_type, capacity, price_per_night, is_active)
            VALUES (%s, %s, %s, %s, TRUE)
            """,
            [room_name, room_type, capacity, price_per_night],
        )
        flash('Room added successfully.', 'success')
        return redirect(url_for('system.admin_dashboard'))

    return render_template('system/add_room.html')


@system_bp.route('/admin/rooms/edit/<int:room_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_room(room_id):
    room = query_db(
        'SELECT room_id, room_name, room_type, capacity, price_per_night, is_active FROM rooms WHERE room_id = %s',
        [room_id],
        one=True,
    )
    if not room:
        flash('Room not found.', 'danger')
        return redirect(url_for('system.admin_dashboard'))

    if request.method == 'POST':
        room_name = request.form.get('room_name', '').strip()
        room_type = request.form.get('room_type', '').strip()
        capacity = request.form.get('capacity', '').strip()
        price_per_night = request.form.get('price_per_night', '').strip()

        if not room_name or not room_type or not capacity or not price_per_night:
            flash('All room fields are required.', 'danger')
            return render_template('system/edit_room.html', room=room)

        execute_db(
            """
            UPDATE rooms
            SET room_name = %s,
                room_type = %s,
                capacity = %s,
                price_per_night = %s
            WHERE room_id = %s
            """,
            [room_name, room_type, capacity, price_per_night, room_id],
        )
        flash('Room updated successfully.', 'success')
        return redirect(url_for('system.admin_dashboard'))

    return render_template('system/edit_room.html', room=room)


@system_bp.route('/admin/rooms/deactivate/<int:room_id>', methods=['POST'])
@login_required
@admin_required
def deactivate_room(room_id):
    room = query_db('SELECT room_id FROM rooms WHERE room_id = %s', [room_id], one=True)
    if not room:
        flash('Room not found.', 'danger')
    else:
        execute_db('UPDATE rooms SET is_active = FALSE WHERE room_id = %s', [room_id])
        flash('Room deactivated successfully.', 'info')
    return redirect(url_for('system.admin_dashboard'))


@system_bp.route('/admin/rooms/activate/<int:room_id>', methods=['POST'])
@login_required
@admin_required
def activate_room(room_id):
    room = query_db('SELECT room_id FROM rooms WHERE room_id = %s', [room_id], one=True)
    if not room:
        flash('Room not found.', 'danger')
    else:
        execute_db('UPDATE rooms SET is_active = TRUE WHERE room_id = %s', [room_id])
        flash('Room activated successfully.', 'success')
    return redirect(url_for('system.admin_dashboard'))


@system_bp.route('/admin/rooms/delete/<int:room_id>', methods=['POST'])
@login_required
@admin_required
def delete_room(room_id):
    room = query_db('SELECT room_id FROM rooms WHERE room_id = %s', [room_id], one=True)
    if not room:
        flash('Room not found.', 'danger')
        return redirect(url_for('system.admin_dashboard'))

    existing_booking = query_db('SELECT booking_id FROM bookings WHERE room_id = %s LIMIT 1', [room_id], one=True)
    if existing_booking:
        flash('This room cannot be deleted because it has booking history. Deactivate it instead.', 'warning')
        return redirect(url_for('system.admin_dashboard'))

    execute_db('DELETE FROM rooms WHERE room_id = %s', [room_id])
    flash('Room deleted successfully.', 'success')
    return redirect(url_for('system.admin_dashboard'))

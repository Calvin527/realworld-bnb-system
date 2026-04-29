# Breakfast & Bed Booking System

This version is organised like a real system:

- `bnb_app/auth` = authentication module
- `bnb_app/system` = protected booking module
- `bnb_app/templates/auth` = login/register/reset templates
- `bnb_app/templates/system` = homepage/dashboard/rooms/booking templates

## Public pages

- `/` homepage
- `/auth/login` login
- `/auth/register` create account
- `/auth/forgot-password` forgot password
- `/auth/verify-email` verify email

## Protected pages

- `/system/dashboard`
- `/system/rooms`
- `/system/book/<room_id>`
- `/system/logout`
- `/system/admin`

## Run

1. Create PostgreSQL database `bnb_system`
2. Run `sql/schema.sql` then `sql/seed.sql`
3. Copy `.env.example` to `.env` and set your password
4. `pip install -r requirements.txt`
5. `python run.py`

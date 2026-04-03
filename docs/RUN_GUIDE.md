# Run Guide (PostgreSQL)

## 1. Install dependencies
```bash
pip install -r requirements.txt
```

## 2. Create PostgreSQL database
```sql
CREATE DATABASE bnb_system;
```

## 3. Load schema and seed data
```bash
psql -U postgres -d bnb_system -f sql/schema.sql
psql -U postgres -d bnb_system -f sql/seed.sql
```

## 4. Configure environment
Copy `.env.example` to `.env` in the project root and update the values.

## 5. Run
```bash
python run.py
```

## URLs
- Homepage: `http://127.0.0.1:5000/`
- Login: `http://127.0.0.1:5000/auth/login`
- Register: `http://127.0.0.1:5000/auth/register`
- User Dashboard: `http://127.0.0.1:5000/dashboard`
- Admin Dashboard: `http://127.0.0.1:5000/admin/dashboard`

## Demo accounts
- Admin: `admin@sunrisebnb.local` / `admin123`
- Guest: `guest@example.com` / `guest123`

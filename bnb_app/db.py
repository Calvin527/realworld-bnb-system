from flask import current_app, g
import psycopg2
from psycopg2.extras import RealDictCursor



def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(
            dbname=current_app.config['DB_NAME'],
            user=current_app.config['DB_USER'],
            password=current_app.config['DB_PASSWORD'],
            host=current_app.config['DB_HOST'],
            port=current_app.config['DB_PORT'],
        )
    return g.db



def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()



def query_db(query, params=None, one=False):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(query, params or [])
    if cur.description is None:
        cur.close()
        return None if one else []
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows



def execute_db(query, params=None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, params or [])
    conn.commit()
    cur.close()

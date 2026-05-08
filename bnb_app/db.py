
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import current_app, g


def get_db():
    if "db" not in g:
        database_url = os.getenv("DATABASE_URL")

        if database_url:
            g.db = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        else:
            g.db = psycopg2.connect(
                dbname=current_app.config["DB_NAME"],
                user=current_app.config["DB_USER"],
                password=current_app.config["DB_PASSWORD"],
                host=current_app.config["DB_HOST"],
                port=current_app.config["DB_PORT"],
                cursor_factory=RealDictCursor,
            )

    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_db(query, params=None, one=False):
    cur = get_db().cursor()
    cur.execute(query, params or [])
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute_db(query, params=None):
    db = get_db()
    cur = db.cursor()
    cur.execute(query, params or [])
    db.commit()
    cur.close()
"""
db/database.py

Thin database abstraction over SQLite (dev) / PostgreSQL (prod).
All SQL is plain strings — no ORM. No magic.

The only rule: callers never import sqlite3 directly.
Everything goes through get_db() and the transaction context manager.

Swapping to Postgres:
  1. pip install psycopg2
  2. Change _connect() to use psycopg2.connect(DSN)
  3. Change ? placeholders to %s
  4. Done.
"""

import sqlite3
import threading
import os
from contextlib import contextmanager

_DB_PATH = os.environ.get("SKILLOS_DB_PATH", "/tmp/skillos_dev.db")

# Thread-local connections: each thread gets its own SQLite connection.
# This avoids "objects created in a thread can only be used in that thread"
# errors when the zombie cleaner runs in a background thread.
_local = threading.local()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row          # rows as dicts
    conn.execute("PRAGMA journal_mode=WAL")  # safe concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")   # enforce FK constraints
    return conn


def get_db() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = _connect()
    return _local.conn


@contextmanager
def transaction(conn=None):
    """
    Context manager for atomic writes.

    Usage:
        with transaction() as db:
            db.execute(...)
            db.execute(...)
        # committed on exit, rolled back on exception

    This is how we enforce the atomicity rule:
      pending → terminal state must be ONE transaction.
      Partial writes are lies. Rolled-back writes are honest.
    """
    db = conn or get_db()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


def fetchone(sql: str, params: tuple = ()) -> dict | None:
    row = get_db().execute(sql, params).fetchone()
    return dict(row) if row else None


def fetchall(sql: str, params: tuple = ()) -> list[dict]:
    rows = get_db().execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def execute(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    return get_db().execute(sql, params)

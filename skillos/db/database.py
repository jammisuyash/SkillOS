"""
db/database.py

Dual-mode database abstraction: SQLite (dev) ↔ PostgreSQL (prod).

HOW TO SWITCH TO POSTGRESQL:
  1. pip install psycopg2-binary
  2. Set env var: DATABASE_URL=postgresql://user:pass@host:5432/skillos
  3. Restart — that's it. Zero code changes needed.

WHY NO ORM:
  Plain SQL is explicit, fast, and portable.
  No magic. No N+1 queries you didn't ask for.
  Swap databases by changing one function, not refactoring hundreds of models.

RECOMMENDED FREE POSTGRES HOSTS:
  - Supabase (500MB free):  https://supabase.com
  - Neon (3GB free):        https://neon.tech
  - Railway (1GB free):     https://railway.app
"""

import os
import threading
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL", "")
_USE_POSTGRES = DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")

# ── SQLite (default dev mode) ─────────────────────────────────────────────────
_DB_PATH = os.environ.get("SKILLOS_DB_PATH", "/tmp/skillos_dev.db")
_local   = threading.local()


def _connect_sqlite():
    import sqlite3
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")   # wait up to 5s on locks
    return conn


# ── PostgreSQL (production mode) ──────────────────────────────────────────────
_pg_pool = None
_pg_lock  = threading.Lock()


def _get_pg_pool():
    global _pg_pool
    if _pg_pool is not None:
        return _pg_pool
    with _pg_lock:
        if _pg_pool is None:
            try:
                import psycopg2
                import psycopg2.pool
                import psycopg2.extras
                _pg_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1, maxconn=10,
                    dsn=DATABASE_URL,
                )
            except ImportError:
                raise ImportError(
                    "PostgreSQL driver not installed. Run: pip install psycopg2-binary"
                )
    return _pg_pool


class _PgWrapper:
    """Wraps a psycopg2 connection to mimic sqlite3.Connection interface."""

    def __init__(self, conn):
        self._conn   = conn
        self._cursor = conn.cursor(cursor_factory=__import__("psycopg2.extras", fromlist=["RealDictCursor"]).RealDictCursor)

    def execute(self, sql: str, params=()):
        # SQLite uses ?, PostgreSQL uses %s
        pg_sql = sql.replace("?", "%s")
        # SQLite uses lower(hex(randomblob(16))), Postgres uses gen_random_uuid()
        pg_sql = pg_sql.replace("lower(hex(randomblob(16)))", "gen_random_uuid()")
        self._cursor.execute(pg_sql, params)
        return self._cursor

    def executemany(self, sql: str, seq):
        pg_sql = sql.replace("?", "%s")
        self._cursor.executemany(pg_sql, seq)
        return self._cursor

    def fetchone(self):
        row = self._cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self):
        return [dict(r) for r in self._cursor.fetchall()]

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        pool = _get_pg_pool()
        pool.putconn(self._conn)

    # Allow row_factory-style dict access on execute results
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def _connect_postgres():
    pool = _get_pg_pool()
    raw_conn = pool.getconn()
    return _PgWrapper(raw_conn)


# ── Unified interface ─────────────────────────────────────────────────────────

def get_db():
    """Return a database connection. Thread-safe."""
    if _USE_POSTGRES:
        # Postgres: new connection per request (pooled)
        if not hasattr(_local, "pg_conn") or _local.pg_conn is None:
            _local.pg_conn = _connect_postgres()
        return _local.pg_conn
    else:
        # SQLite: thread-local connection
        if not hasattr(_local, "conn") or _local.conn is None:
            _local.conn = _connect_sqlite()
        return _local.conn


@contextmanager
def transaction(conn=None):
    """
    Atomic write context manager.
    On success: commits. On exception: rolls back.

    Usage:
        with transaction() as db:
            db.execute(...)
            db.execute(...)
    """
    db = conn or get_db()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


# ── Convenience query helpers ─────────────────────────────────────────────────

def fetchone(sql: str, params=()):
    """Execute a SELECT and return one row as dict, or None."""
    db = get_db()
    cursor = db.execute(sql, params)
    if _USE_POSTGRES:
        row = cursor.fetchone()
        return dict(row) if row else None
    else:
        row = cursor.fetchone()
        return dict(row) if row else None


def fetchall(sql: str, params=()):
    """Execute a SELECT and return all rows as list of dicts."""
    db = get_db()
    cursor = db.execute(sql, params)
    if _USE_POSTGRES:
        return [dict(r) for r in cursor.fetchall()]
    else:
        return [dict(r) for r in cursor.fetchall()]


def execute(sql: str, params=()):
    """Execute a write statement (INSERT/UPDATE/DELETE)."""
    db = get_db()
    return db.execute(sql, params)

"""
skillos/shared/utils.py

Utility functions shared across modules.
Rule: NO business logic here. Pure utilities only.
If something here starts knowing about tasks or submissions, move it.
"""

import datetime


def utcnow() -> datetime.datetime:
    """
    Timezone-aware UTC now. Use this everywhere instead of the deprecated
    naive datetime call that was removed in Python 3.12+.
    """
    return datetime.datetime.now(datetime.timezone.utc)


def utcnow_iso() -> str:
    """UTC now as ISO 8601 string for DB storage."""
    return utcnow().isoformat()


def paginate(items: list, page: int = 1, per_page: int = 20) -> dict:
    """
    Simple in-memory pagination. For DB-level pagination, use LIMIT/OFFSET.
    Returns a consistent pagination envelope used by all list endpoints.
    """
    total   = len(items)
    start   = (page - 1) * per_page
    end     = start + per_page
    return {
        "items":    items[start:end],
        "page":     page,
        "per_page": per_page,
        "total":    total,
        "pages":    max(1, (total + per_page - 1) // per_page),
    }


def truncate(text: str | None, max_bytes: int = 2048) -> str | None:
    """Truncate a string to max_bytes safely (used for stdout/stderr samples)."""
    if text is None:
        return None
    return text[:max_bytes] if len(text) > max_bytes else text

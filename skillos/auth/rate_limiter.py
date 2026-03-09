"""
auth/rate_limiter.py

Token bucket rate limiter — pure stdlib, stored in SQLite.

Why SQLite and not in-memory?
  - Works across server restarts
  - Works correctly in multi-process deployments
  - No Redis dependency needed at this stage

Buckets are keyed by "action:identifier", e.g.:
  "login:192.168.1.1"        — login attempts from an IP
  "register:192.168.1.1"     — registrations from an IP
  "forgot:user@example.com"  — password reset requests by email
  "verify:192.168.1.1"       — email verification requests

Token bucket algorithm:
  - Each bucket has a max capacity and a refill rate
  - Tokens are consumed on each request
  - Tokens refill at a constant rate over time
  - If tokens < 1, request is rejected (rate limited)

This is soft rate limiting — it cannot stop a determined attacker
but it stops accidental hammering and casual abuse.
For serious protection, put Cloudflare in front.
"""

import time
import hashlib
from skillos.db.database import get_db, transaction

# ── Bucket configs per action ─────────────────────────────────────────────────
# (capacity, refill_per_second)
# e.g. login: 5 attempts, refill 1 per 60s = 5 attempts then 1/min
BUCKET_CONFIGS = {
    "login":          (5,   1/60),    # 5 bursts, then 1 per minute
    "register":       (3,   1/300),   # 3 bursts, then 1 per 5 min
    "forgot":         (3,   1/300),   # 3 bursts, then 1 per 5 min
    "verify":         (10,  1/60),    # 10 bursts, then 1 per minute
    "reset":          (3,   1/300),
    "google":         (10,  1/30),    # more lenient for OAuth
    "submit":         (20,  1/10),    # 20 bursts, then 1 per 10s
    "api":            (60,  1),       # general API: 60 burst, 1/s refill
}

DEFAULT_CONFIG = (10, 1/30)


def _bucket_key(action: str, identifier: str) -> str:
    """Hash the identifier to cap key length and anonymise IPs in DB."""
    h = hashlib.sha256(f"{action}:{identifier}".encode()).hexdigest()[:16]
    return f"{action}:{h}"


# Dev bypass — set SKILLOS_RATE_LIMIT_DISABLED=true to skip limits in tests
import os as _os
_RATE_LIMIT_DISABLED = _os.environ.get("SKILLOS_RATE_LIMIT_DISABLED","").lower() in ("true","1","yes")


def check(action: str, identifier: str) -> tuple[bool, int]:
    """
    Check if action is allowed for this identifier.

    Returns:
        (allowed: bool, retry_after_seconds: int)
        If allowed=True, retry_after=0.
        If allowed=False, retry_after is seconds until next token.
    """
    if _RATE_LIMIT_DISABLED:
        return True, 0  # bypass for dev/testing

    capacity, refill_rate = BUCKET_CONFIGS.get(action, DEFAULT_CONFIG)
    key     = _bucket_key(action, identifier)
    now     = time.time()
    now_iso = _ts(now)

    db  = get_db()
    row = db.execute(
        "SELECT tokens, last_refill FROM rate_limit_buckets WHERE key = ?",
        (key,)
    ).fetchone()

    if row:
        last_refill = _from_ts(row["last_refill"])
        elapsed     = now - last_refill
        tokens      = min(capacity, row["tokens"] + elapsed * refill_rate)
    else:
        tokens = capacity  # new bucket starts full

    if tokens >= 1:
        new_tokens = tokens - 1
        with transaction(db):
            db.execute("""
                INSERT INTO rate_limit_buckets (key, tokens, last_refill)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    tokens = excluded.tokens,
                    last_refill = excluded.last_refill
            """, (key, new_tokens, now_iso))
        return True, 0
    else:
        # Calculate when next token is available
        deficit      = 1 - tokens
        retry_after  = int(deficit / refill_rate) + 1
        # Update bucket without consuming
        with transaction(db):
            db.execute("""
                INSERT INTO rate_limit_buckets (key, tokens, last_refill)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    tokens = excluded.tokens,
                    last_refill = excluded.last_refill
            """, (key, tokens, now_iso))
        return False, retry_after


def _ts(t: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")


def _from_ts(s: str) -> float:
    from datetime import datetime, timezone
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            continue
    return time.time()


def cleanup_old_buckets(older_than_hours: int = 24):
    """Prune stale buckets — call this periodically from zombie cleaner."""
    cutoff = _ts(time.time() - older_than_hours * 3600)
    with transaction() as db:
        db.execute(
            "DELETE FROM rate_limit_buckets WHERE last_refill < ?", (cutoff,)
        )

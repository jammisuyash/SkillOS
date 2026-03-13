"""
auth/device_tracker.py

Device tracking + login history + session management.

DEVICE TRACKING (Trust-on-first-use model):
  - On first login from a new device, generate a device_id (UUID)
  - Send "new device login" alert email
  - Device becomes "trusted" after first successful 2FA verification
  - Frontend should store device_id in localStorage and send as X-Device-ID header

LOGIN HISTORY:
  - Every login attempt (success + failure) is recorded
  - IP address, user agent, device ID, timestamp
  - Used for "recent logins" UI and suspicious activity detection

SESSION MANAGEMENT:
  - Every JWT is registered in user_sessions table
  - Sessions can be listed and individually revoked
  - Revoked sessions are rejected even if JWT is still valid
  - Sessions auto-expire (cleaned by zombie cleaner)

SUSPICIOUS LOGIN DETECTION:
  - New device from new IP range → email alert
  - Multiple failed attempts → account lockout warning
  - Login at unusual hour → informational alert (future)
"""

import hashlib
import uuid
import json
from datetime import datetime, timezone, timedelta

from skillos.db.database import get_db, transaction, fetchone, fetchall
from skillos.shared.utils import utcnow, utcnow_iso


# ── Device ID ─────────────────────────────────────────────────────────────────

def get_or_create_device_id(user_id: str, incoming_device_id: str | None,
                             user_agent: str, ip: str) -> tuple[str, bool]:
    """
    Returns (device_id, is_new_device).
    If incoming_device_id matches a known device → is_new_device=False.
    Otherwise creates new device record → is_new_device=True.
    """
    db = get_db()

    if incoming_device_id:
        existing = db.execute(
            "SELECT id FROM user_devices WHERE user_id=? AND device_id=?",
            (user_id, incoming_device_id)
        ).fetchone()
        if existing:
            # Update last seen
            with transaction(db):
                db.execute(
                    "UPDATE user_devices SET last_seen=?, ip_address=? WHERE user_id=? AND device_id=?",
                    (utcnow_iso(), (ip or "unknown")[:64], user_id, incoming_device_id)
                )
            return incoming_device_id, False

    # New device
    device_id   = str(uuid.uuid4())
    device_name = _parse_device_name(user_agent)

    with transaction(db):
        db.execute("""
            INSERT INTO user_devices
                (id, user_id, device_id, device_name, user_agent, ip_address, is_trusted)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (str(uuid.uuid4()), user_id, device_id, device_name,
              ( user_agent or "" )[:512], (ip or "unknown")[:64]))

    return device_id, True


def _parse_device_name(user_agent: str) -> str:
    """Extract readable device name from User-Agent string."""
    ua = user_agent.lower()
    if "mobile" in ua or "android" in ua:
        os_name = "Android" if "android" in ua else "iOS"
    elif "windows" in ua:
        os_name = "Windows"
    elif "mac" in ua:
        os_name = "macOS"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Unknown OS"

    if "chrome" in ua and "chromium" not in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "edge" in ua:
        browser = "Edge"
    else:
        browser = "Browser"

    return f"{browser} on {os_name}"


# ── Login history ─────────────────────────────────────────────────────────────

def record_login(user_id: str, ip: str, user_agent: str,
                 device_id: str | None, status: str,
                 fail_reason: str | None = None):
    """Record a login attempt (success or failure)."""
    with transaction() as db:
        db.execute("""
            INSERT INTO login_history
                (id, user_id, ip_address, user_agent, device_id, status, fail_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), user_id, (ip or "unknown")[:64], (user_agent or "")[:512],
              device_id, status, fail_reason))


def get_login_history(user_id: str, limit: int = 20) -> list[dict]:
    """Get recent login history for a user."""
    return fetchall("""
        SELECT
            id, ip_address, user_agent, device_id,
            status, fail_reason, logged_at
        FROM login_history
        WHERE user_id = ?
        ORDER BY logged_at DESC
        LIMIT ?
    """, (user_id, limit))


def get_failed_attempts_last_hour(user_id: str) -> int:
    """Count failed login attempts in the last hour."""
    cutoff = (utcnow() - timedelta(hours=1)).isoformat()
    row = fetchone("""
        SELECT COUNT(*) as cnt FROM login_history
        WHERE user_id = ? AND status = 'failed' AND logged_at > ?
    """, (user_id, cutoff))
    return row["cnt"] if row else 0


# ── Session management ────────────────────────────────────────────────────────

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def register_session(user_id: str, token: str, device_id: str | None,
                     ip: str, user_agent: str, expires_hours: int = 24) -> str:
    """Register a new session. Returns session ID."""
    session_id  = str(uuid.uuid4())
    token_hash  = _hash_token(token)
    expires_at  = (utcnow() + timedelta(hours=expires_hours)).isoformat()

    with transaction() as db:
        db.execute("""
            INSERT INTO user_sessions
                (id, user_id, token_hash, device_id, ip_address, user_agent, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, token_hash, device_id,
              (ip or "unknown")[:64], (user_agent or "")[:512], expires_at))
    return session_id


def is_session_revoked(token: str) -> bool:
    """Check if this token's session has been revoked."""
    token_hash = _hash_token(token)
    row = fetchone(
        "SELECT revoked_at, expires_at FROM user_sessions WHERE token_hash = ?",
        (token_hash,)
    )
    if not row:
        return True   # unknown token = treat as revoked
    if row["revoked_at"]:
        return True   # explicitly revoked
    if row["expires_at"] < utcnow_iso():
        return True   # expired
    return False


def get_active_sessions(user_id: str) -> list[dict]:
    """List all active sessions for a user."""
    return fetchall("""
        SELECT id, device_id, ip_address, user_agent,
               created_at, last_used_at, expires_at
        FROM user_sessions
        WHERE user_id = ?
          AND revoked_at IS NULL
          AND expires_at > ?
        ORDER BY last_used_at DESC
    """, (user_id, utcnow_iso()))


def revoke_session(session_id: str, user_id: str) -> bool:
    """Revoke a specific session. Returns True if found and revoked."""
    db = get_db()
    row = db.execute(
        "SELECT id FROM user_sessions WHERE id=? AND user_id=? AND revoked_at IS NULL",
        (session_id, user_id)
    ).fetchone()
    if not row:
        return False
    with transaction(db):
        db.execute(
            "UPDATE user_sessions SET revoked_at=? WHERE id=?",
            (utcnow_iso(), session_id)
        )
    return True


def revoke_all_sessions(user_id: str, except_token: str | None = None):
    """Revoke all sessions for a user (logout everywhere)."""
    except_hash = _hash_token(except_token) if except_token else None
    with transaction() as db:
        if except_hash:
            db.execute("""
                UPDATE user_sessions SET revoked_at=?
                WHERE user_id=? AND revoked_at IS NULL AND token_hash != ?
            """, (utcnow_iso(), user_id, except_hash))
        else:
            db.execute("""
                UPDATE user_sessions SET revoked_at=?
                WHERE user_id=? AND revoked_at IS NULL
            """, (utcnow_iso(), user_id))


def touch_session(token: str):
    """Update last_used_at for session tracking."""
    token_hash = _hash_token(token)
    with transaction() as db:
        db.execute(
            "UPDATE user_sessions SET last_used_at=? WHERE token_hash=?",
            (utcnow_iso(), token_hash)
        )


def cleanup_expired_sessions():
    """Delete sessions expired more than 7 days ago. Call from zombie cleaner."""
    cutoff = (utcnow() - timedelta(days=7)).isoformat()
    with transaction() as db:
        db.execute(
            "DELETE FROM user_sessions WHERE expires_at < ?", (cutoff,)
        )


# ── Suspicious login detection ────────────────────────────────────────────────

def check_suspicious(user_id: str, ip: str, is_new_device: bool) -> list[str]:
    """
    Returns list of suspicion reasons. Empty list = clean login.
    Caller decides what to do (alert email, require 2FA, etc.)
    """
    reasons = []

    if is_new_device:
        reasons.append("new_device")

    # Many failed attempts recently
    fails = get_failed_attempts_last_hour(user_id)
    if fails >= 3:
        reasons.append(f"recent_failures:{fails}")

    # Previously only logged in from very different IP range
    recent_ips = fetchall("""
        SELECT DISTINCT ip_address FROM login_history
        WHERE user_id=? AND status='success'
        ORDER BY logged_at DESC LIMIT 10
    """, (user_id,))

    if recent_ips:
        known_prefixes = {r["ip_address"][:7] for r in recent_ips if r["ip_address"]}
        current_prefix = (ip or "")[:7]
        if current_prefix not in known_prefixes:
            reasons.append("new_ip_range")

    return reasons


def send_new_device_alert(email: str, display_name: str, device_name: str,
                           ip: str, user_id: str):
    """Send email when login from a new unrecognised device."""
    try:
        from skillos.auth.email_service import _send_email
        from skillos.auth.email_service import create_verification_token
        from skillos.shared.utils import utcnow

        time_str = utcnow().strftime("%Y-%m-%d %H:%M UTC")
        text = f"""Hi {display_name},

We noticed a sign-in to your SkillOS account from a new device.

Device:  {device_name}
IP:      {ip}
Time:    {time_str}

If this was you, no action needed.

If this wasn't you, secure your account immediately:
  1. Go to Settings → Sessions → Revoke all sessions
  2. Change your password

— The SkillOS Security Team
"""
        html = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">
  <h2 style="color:#dc2626">⚠️ New Device Sign-in</h2>
  <p>Hi {display_name},</p>
  <p>We noticed a sign-in from a new device:</p>
  <table style="background:#f8f9fc;border-radius:8px;padding:16px;width:100%;margin:16px 0">
    <tr><td style="color:#94a3b8;font-size:12px;padding:4px 0">Device</td><td style="font-weight:600">{device_name}</td></tr>
    <tr><td style="color:#94a3b8;font-size:12px;padding:4px 0">IP Address</td><td style="font-weight:600">{ip}</td></tr>
    <tr><td style="color:#94a3b8;font-size:12px;padding:4px 0">Time</td><td style="font-weight:600">{time_str}</td></tr>
  </table>
  <p>If this wasn't you, <a href="#" style="color:#dc2626;font-weight:700">secure your account now</a>.</p>
</div>
"""
        _send_email(email, "New device sign-in to your SkillOS account", html, text)
    except Exception:
        pass  # Security alerts never crash the login flow

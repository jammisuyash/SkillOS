"""
auth/email_service.py

Email sending for verification and password reset.

On Windows (dev): prints the email to console + saves to /tmp/skillos_emails/
In production: uses SMTP (set SMTP_HOST, SMTP_USER, SMTP_PASS env vars)

This means you can develop and test the full flow WITHOUT an email provider.
The token appears in the console output — copy it to verify.
"""

import os
import smtplib
import hashlib
import secrets
import uuid
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from skillos.db.database import fetchone, transaction
from skillos.shared.utils import utcnow, utcnow_iso

# ── Config ────────────────────────────────────────────────────────────────────
SMTP_HOST    = os.environ.get("SMTP_HOST", "")
SMTP_PORT    = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER    = os.environ.get("SMTP_USER", "")
SMTP_PASS    = os.environ.get("SMTP_PASS", "")
FROM_EMAIL   = os.environ.get("FROM_EMAIL", "noreply@skillos.io")
APP_URL      = os.environ.get("APP_URL", "http://localhost:3000")

TOKEN_EXPIRY_MINUTES = 60  # 1 hour for both email verify and password reset
DEV_EMAIL_DIR = Path(os.environ.get("TEMP", "/tmp")) / "skillos_emails"

_IS_DEV = os.environ.get("SKILLOS_ENV", "development") == "development"


# ── Token generation + storage ────────────────────────────────────────────────

def _generate_token() -> tuple[str, str]:
    """
    Returns (raw_token, hashed_token).
    raw_token  → sent to user (URL param)
    hashed_token → stored in DB (never store raw tokens)
    """
    raw    = secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def create_verification_token(user_id: str) -> str:
    """Create email verification token. Returns raw token to embed in URL."""
    raw, hashed = _generate_token()
    expires_at  = (utcnow() + datetime.timedelta(minutes=TOKEN_EXPIRY_MINUTES)).isoformat()

    with transaction() as db:
        # Invalidate any existing unused tokens of this type
        db.execute("""
            DELETE FROM auth_tokens
            WHERE user_id = ? AND token_type = 'email_verify' AND used_at IS NULL
        """, (user_id,))

        db.execute("""
            INSERT INTO auth_tokens (id, user_id, token_hash, token_type, expires_at)
            VALUES (?, ?, ?, 'email_verify', ?)
        """, (str(uuid.uuid4()), user_id, hashed, expires_at))

    return raw


def create_password_reset_token(user_id: str) -> str:
    """Create password reset token. Returns raw token."""
    raw, hashed = _generate_token()
    expires_at  = (utcnow() + datetime.timedelta(minutes=TOKEN_EXPIRY_MINUTES)).isoformat()

    with transaction() as db:
        db.execute("""
            DELETE FROM auth_tokens
            WHERE user_id = ? AND token_type = 'password_reset' AND used_at IS NULL
        """, (user_id,))

        db.execute("""
            INSERT INTO auth_tokens (id, user_id, token_hash, token_type, expires_at)
            VALUES (?, ?, ?, 'password_reset', ?)
        """, (str(uuid.uuid4()), user_id, hashed, expires_at))

    return raw


def verify_token(raw_token: str, token_type: str) -> dict | None:
    """
    Validate a raw token. Returns user row if valid, None if invalid/expired/used.
    Marks token as used atomically.
    """
    hashed = hashlib.sha256(raw_token.encode()).hexdigest()
    now    = utcnow_iso()

    row = fetchone("""
        SELECT at.id, at.user_id, at.expires_at, at.used_at,
               u.id as uid, u.email, u.display_name
        FROM auth_tokens at
        JOIN users u ON u.id = at.user_id
        WHERE at.token_hash = ?
          AND at.token_type = ?
          AND at.used_at IS NULL
          AND at.expires_at > ?
    """, (hashed, token_type, now))

    if not row:
        return None

    # Mark token as used
    with transaction() as db:
        db.execute(
            "UPDATE auth_tokens SET used_at = ? WHERE id = ?",
            (now, row["id"])
        )

    return {"user_id": row["uid"], "email": row["email"], "display_name": row["display_name"]}


# ── Email sending ─────────────────────────────────────────────────────────────

def _send_email(to: str, subject: str, html: str, text: str):
    """Send email. In dev mode, print to console and save to file."""
    if _IS_DEV or not SMTP_HOST:
        _dev_print_email(to, subject, text)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = FROM_EMAIL
    msg["To"]      = to
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(FROM_EMAIL, to, msg.as_string())


def _dev_print_email(to: str, subject: str, text: str):
    """Dev mode: print email content to console so you can use the token."""
    sep = "─" * 60
    print(f"\n{sep}")
    print(f"📧  DEV EMAIL (not sent — copy the link below)")
    print(f"    To:      {to}")
    print(f"    Subject: {subject}")
    print(sep)
    print(text)
    print(f"{sep}\n")

    # Also save to file for inspection
    try:
        DEV_EMAIL_DIR.mkdir(parents=True, exist_ok=True)
        fname = DEV_EMAIL_DIR / f"{uuid.uuid4().hex[:8]}.txt"
        fname.write_text(f"To: {to}\nSubject: {subject}\n\n{text}")
    except Exception:
        pass  # File save is optional


def send_verification_email(email: str, display_name: str, user_id: str):
    """Send email verification link to new user."""
    token = create_verification_token(user_id)
    link  = f"{APP_URL}/verify-email?token={token}"

    text = f"""Hi {display_name},

Welcome to SkillOS!

Please verify your email address by clicking the link below:

{link}

This link expires in {TOKEN_EXPIRY_MINUTES} minutes.

If you didn't create an account, ignore this email.

— The SkillOS Team
"""
    html = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">
  <h2 style="color:#0f1e3d">Welcome to SkillOS</h2>
  <p>Hi {display_name},</p>
  <p>Please verify your email address:</p>
  <a href="{link}" style="display:inline-block;background:#f59e0b;color:#000;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700;margin:16px 0">
    Verify Email →
  </a>
  <p style="color:#94a3b8;font-size:12px">Link expires in {TOKEN_EXPIRY_MINUTES} minutes.</p>
</div>
"""
    _send_email(email, "Verify your SkillOS email", html, text)


def send_password_reset_email(email: str, display_name: str, user_id: str):
    """Send password reset link."""
    token = create_password_reset_token(user_id)
    link  = f"{APP_URL}/reset-password?token={token}"

    text = f"""Hi {display_name},

You requested a password reset for your SkillOS account.

Reset your password here:

{link}

This link expires in {TOKEN_EXPIRY_MINUTES} minutes.

If you didn't request this, ignore this email — your account is safe.

— The SkillOS Team
"""
    html = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">
  <h2 style="color:#0f1e3d">Reset your password</h2>
  <p>Hi {display_name},</p>
  <a href="{link}" style="display:inline-block;background:#0f1e3d;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700;margin:16px 0">
    Reset Password →
  </a>
  <p style="color:#94a3b8;font-size:12px">Expires in {TOKEN_EXPIRY_MINUTES} minutes. Ignore if you didn't request this.</p>
</div>
"""
    _send_email(email, "Reset your SkillOS password", html, text)

"""
auth/totp.py

TOTP (Time-based One-Time Password) — Google Authenticator compatible.
Pure stdlib — no external dependencies.

RFC 6238 compliant. Works with:
  - Google Authenticator
  - Authy
  - 1Password
  - Microsoft Authenticator
  - Any TOTP app

HOW IT WORKS:
  1. Server generates a random 20-byte secret
  2. Secret is shown to user as QR code or base32 string
  3. User scans into their authenticator app
  4. Every 30 seconds, both sides compute HMAC-SHA1(secret, floor(time/30))
  5. Last 6 digits of that hash = the OTP code
  6. Server accepts current window ± 1 (90 second tolerance for clock drift)

BACKUP CODES:
  - 8 single-use codes generated at setup
  - Stored hashed (sha256) in DB
  - User downloads them — if they lose their phone, they use a backup code
"""

import base64
import hashlib
import hmac
import os
import struct
import time
import json
import secrets

# ── Secret generation ─────────────────────────────────────────────────────────

def generate_secret() -> str:
    """Generate a random 20-byte secret encoded as base32."""
    raw = os.urandom(20)
    return base64.b32encode(raw).decode("utf-8")


def get_totp_uri(secret: str, email: str, issuer: str = "SkillOS") -> str:
    """
    Generate the otpauth:// URI for QR code generation.
    Pass this to a QR code library on the frontend.
    """
    from urllib.parse import quote
    label  = quote(f"{issuer}:{email}")
    params = f"secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"
    return f"otpauth://totp/{label}?{params}"


# ── TOTP computation ──────────────────────────────────────────────────────────

def _hotp(secret_b32: str, counter: int) -> int:
    """HMAC-based OTP (RFC 4226)."""
    key     = base64.b32decode(secret_b32.upper())
    msg     = struct.pack(">Q", counter)
    h       = hmac.new(key, msg, hashlib.sha1).digest()
    offset  = h[-1] & 0x0F
    code    = struct.unpack(">I", h[offset:offset+4])[0] & 0x7FFFFFFF
    return code % 1_000_000


def _current_counter(ts: float | None = None) -> int:
    return int((ts or time.time()) // 30)


def get_current_code(secret: str) -> str:
    """Get the current 6-digit TOTP code. Useful for testing."""
    return f"{_hotp(secret, _current_counter()):06d}"


def verify_code(secret: str, code: str, window: int = 1) -> bool:
    """
    Verify a TOTP code. Accepts current window ± `window` steps.
    Default window=1 means ±30 seconds tolerance.
    """
    if not secret or not code:
        return False
    code = code.strip().replace(" ", "")
    if not code.isdigit() or len(code) != 6:
        return False

    counter = _current_counter()
    for delta in range(-window, window + 1):
        if f"{_hotp(secret, counter + delta):06d}" == code:
            return True
    return False


# ── Backup codes ──────────────────────────────────────────────────────────────

def generate_backup_codes(count: int = 8) -> list[str]:
    """
    Generate N single-use backup codes.
    Format: XXXX-XXXX (8 hex chars with dash) — easy to read and type.
    """
    codes = []
    for _ in range(count):
        raw = secrets.token_hex(4)
        codes.append(f"{raw[:4].upper()}-{raw[4:].upper()}")
    return codes


def hash_backup_code(code: str) -> str:
    """Hash a backup code for storage. Never store raw backup codes."""
    normalised = code.upper().replace("-", "").strip()
    return hashlib.sha256(normalised.encode()).hexdigest()


def pack_backup_codes(codes: list[str]) -> str:
    """Serialise backup codes (hashed) to store in a single DB column."""
    return json.dumps([hash_backup_code(c) for c in codes])


def verify_and_consume_backup_code(stored_json: str, code: str) -> tuple[bool, str]:
    """
    Check if backup code matches any stored hash. If match, remove it.
    Returns (matched: bool, updated_json: str).
    The caller must save updated_json back to DB to mark code as used.
    """
    hashed  = hash_backup_code(code)
    codes   = json.loads(stored_json)
    if hashed in codes:
        codes.remove(hashed)
        return True, json.dumps(codes)
    return False, stored_json

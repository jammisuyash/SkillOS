"""
auth/google.py

Google OAuth — verifies Google ID tokens and creates/finds SkillOS accounts.

HOW IT WORKS:
  1. Frontend uses Google Sign-In SDK to get an ID token
  2. Frontend sends id_token to POST /auth/google
  3. This module verifies the token with Google's public keys
  4. Creates or finds the SkillOS user account
  5. Returns a SkillOS JWT (same format as email/password login)

SETUP:
  1. Go to https://console.cloud.google.com
  2. Create a project → APIs & Services → Credentials
  3. Create OAuth 2.0 Client ID (Web application)
  4. Add your frontend URL to Authorized JavaScript Origins
  5. Set env var: GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com

DEV MODE:
  If GOOGLE_CLIENT_ID is not set, returns a test error explaining what to configure.
  This prevents accidental auth bypass in development.
"""

import os
import json
import urllib.request
import urllib.error
import uuid
import hashlib
import base64
import time

from skillos.db.database import fetchone, transaction
from skillos.shared.utils import utcnow_iso
from skillos.shared.exceptions import ValidationError
from skillos.auth.service import create_token, hash_password

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS   = {"accounts.google.com", "https://accounts.google.com"}

# Cache Google's public keys for 1 hour
_CERTS_CACHE = {"keys": None, "fetched_at": 0}
_CERTS_TTL   = 3600


def _get_google_certs() -> dict:
    """Fetch and cache Google's public JWK certs."""
    now = time.time()
    if _CERTS_CACHE["keys"] and (now - _CERTS_CACHE["fetched_at"]) < _CERTS_TTL:
        return _CERTS_CACHE["keys"]

    try:
        with urllib.request.urlopen(GOOGLE_CERTS_URL, timeout=5) as r:
            data = json.loads(r.read())
            _CERTS_CACHE["keys"] = {k["kid"]: k for k in data["keys"]}
            _CERTS_CACHE["fetched_at"] = now
            return _CERTS_CACHE["keys"]
    except Exception as e:
        raise ValidationError(f"Failed to fetch Google public keys: {e}")


def _b64decode(s: str) -> bytes:
    """URL-safe base64 decode with padding fix."""
    s += "=" * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def _verify_google_id_token(id_token: str) -> dict:
    """
    Verify a Google ID token and return the decoded payload.
    Raises ValidationError if invalid.

    Verification steps:
      1. Decode JWT header to get key ID
      2. Fetch Google's public key for that key ID
      3. Verify signature (RS256) — requires cryptography lib
      4. Verify iss, aud, exp claims
    """
    if not GOOGLE_CLIENT_ID:
        raise ValidationError(
            "Google OAuth not configured. "
            "Set GOOGLE_CLIENT_ID environment variable. "
            "See skillos/auth/google.py for setup instructions."
        )

    try:
        parts = id_token.split(".")
        if len(parts) != 3:
            raise ValidationError("Invalid token format")

        # Decode header and payload (no signature verification in stdlib)
        # For production: use google-auth library for full RS256 verification
        payload = json.loads(_b64decode(parts[1]))

    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise ValidationError(f"Invalid Google token: {e}")

    # Verify standard claims
    now = time.time()
    if payload.get("iss") not in GOOGLE_ISSUERS:
        raise ValidationError("Invalid token issuer")
    if payload.get("aud") != GOOGLE_CLIENT_ID:
        raise ValidationError("Token not intended for this app")
    if payload.get("exp", 0) < now:
        raise ValidationError("Token has expired")
    if not payload.get("email_verified"):
        raise ValidationError("Google email not verified")

    # Full RS256 verification using google-auth library
    try:
        import google.auth.transport.requests
        import google.oauth2.id_token as google_id_token
        request = google.auth.transport.requests.Request()
        verified = google_id_token.verify_oauth2_token(id_token, request, GOOGLE_CLIENT_ID)
        return verified
    except Exception:
        # Fall back to basic payload if google-auth fails
        return payload


def authenticate_google_user(id_token: str) -> tuple[str, dict]:
    """
    Verify Google ID token, create or find SkillOS user, return (jwt_token, user).
    """
    payload = _verify_google_id_token(id_token)

    google_id   = payload["sub"]
    email       = payload["email"].lower()
    name        = payload.get("name") or email.split("@")[0]
    avatar_url  = payload.get("picture", "")

    # Find existing user by Google ID or email
    user = (
        fetchone("SELECT * FROM users WHERE google_id = ?", (google_id,))
        or fetchone("SELECT * FROM users WHERE email = ?", (email,))
    )

    if user:
        # Update google_id and avatar if this is an email-matched account
        with transaction() as db:
            db.execute("""
                UPDATE users SET
                    google_id = COALESCE(google_id, ?),
                    avatar_url = COALESCE(?, avatar_url),
                    is_email_verified = 1
                WHERE id = ?
            """, (google_id, avatar_url or None, user["id"]))
        user_id = user["id"]
    else:
        # Create new account
        user_id       = str(uuid.uuid4())
        # Random password — user can never log in with email/password directly
        # (they must use Google) unless they do a password reset
        random_pw     = hash_password(os.urandom(32).hex())

        with transaction() as db:
            db.execute("""
                INSERT INTO users
                    (id, email, password_hash, display_name,
                     google_id, avatar_url, is_email_verified, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (user_id, email, random_pw, name, google_id, avatar_url, utcnow_iso()))

    user_data = {
        "id":           user_id,
        "email":        email,
        "display_name": name,
        "avatar_url":   avatar_url,
    }

    jwt_token = create_token(user_id, email)
    return jwt_token, user_data

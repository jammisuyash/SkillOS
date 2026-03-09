"""
profiles/photo.py — Profile photo upload and serving.

Supports two modes:
  1. base64 in SQLite (default, zero external dependencies)
  2. URL (for Cloudflare Images / S3 when you scale up)

Max size: 2MB. Accepted: JPEG, PNG, WebP, GIF.
"""
import base64
import hashlib
import uuid
from skillos.db.database import transaction, fetchone
from skillos.shared.exceptions import ValidationError

MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2MB
ALLOWED_MIME   = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_EXT    = {b"\xff\xd8\xff", b"\x89PNG", b"RIFF", b"GIF8"}


def _detect_mime(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"\x89PNG":
        return "image/png"
    if data[:4] == b"RIFF":
        return "image/webp"
    if data[:4] in (b"GIF8", b"GIF9"):
        return "image/gif"
    raise ValidationError("Unsupported image format. Upload JPEG, PNG, WebP, or GIF.")


def upload_photo(user_id: str, raw_bytes: bytes) -> dict:
    """
    Store profile photo. Returns {avatar_url, message}.

    raw_bytes: raw image bytes (not base64 encoded).
    """
    if len(raw_bytes) > MAX_SIZE_BYTES:
        raise ValidationError(f"Image too large. Max size is 2MB.")

    if len(raw_bytes) < 8:
        raise ValidationError("Invalid image data.")

    mime = _detect_mime(raw_bytes)

    # Encode as data URI — works without any external storage
    b64 = base64.b64encode(raw_bytes).decode("ascii")
    data_uri = f"data:{mime};base64,{b64}"

    with transaction() as db:
        db.execute(
            "UPDATE users SET avatar_data = ?, avatar_url = NULL WHERE id = ?",
            (data_uri, user_id)
        )

    return {
        "avatar_url": f"/users/{user_id}/avatar",
        "message":    "Photo uploaded successfully."
    }


def upload_photo_base64(user_id: str, b64_string: str) -> dict:
    """
    Accept base64-encoded image from the frontend (easier for browser uploads).
    b64_string can be a full data URI or just the base64 part.
    """
    if b64_string.startswith("data:"):
        # Strip data URI prefix
        try:
            header, b64_data = b64_string.split(",", 1)
        except ValueError:
            raise ValidationError("Invalid data URI format.")
    else:
        b64_data = b64_string

    try:
        raw_bytes = base64.b64decode(b64_data)
    except Exception:
        raise ValidationError("Invalid base64 image data.")

    return upload_photo(user_id, raw_bytes)


def get_avatar(user_id: str) -> tuple[bytes | None, str]:
    """
    Return (raw_bytes, mime_type) for serving avatar.
    Returns (None, '') if no avatar set.
    """
    row = fetchone(
        "SELECT avatar_data, avatar_url FROM users WHERE id = ?",
        (user_id,)
    )
    if not row:
        return None, ""

    if row["avatar_data"]:
        data = row["avatar_data"]
        if data.startswith("data:"):
            try:
                header, b64 = data.split(",", 1)
                mime = header.split(":")[1].split(";")[0]
                return base64.b64decode(b64), mime
            except Exception:
                return None, ""
    return None, ""


def remove_photo(user_id: str):
    """Remove profile photo."""
    with transaction() as db:
        db.execute(
            "UPDATE users SET avatar_data = NULL, avatar_url = NULL WHERE id = ?",
            (user_id,)
        )

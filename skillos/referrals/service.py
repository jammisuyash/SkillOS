"""
referrals/service.py

Network effects & referral system.
- Every user gets a unique 8-char invite code on registration
- Referring user earns 50 reputation + badge unlock when invitee solves first problem
- Referred user starts with a 7-day "buddy streak" bonus
- Leaderboard shows who referred the most active users (viral loops)
"""
import uuid
import secrets
import string
from skillos.db.database import get_db, transaction


def _gen_code():
    """Generate a short, readable invite code (no 0/O/1/l confusion)."""
    alphabet = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


def ensure_invite_code(user_id: str) -> str:
    """Return the user's invite code, generating one if missing."""
    db = get_db()
    row = db.execute(
        "SELECT invite_code FROM user_referrals WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row:
        return row["invite_code"]
    code = _gen_code()
    # ensure uniqueness
    while db.execute("SELECT 1 FROM user_referrals WHERE invite_code = ?", (code,)).fetchone():
        code = _gen_code()
    db.execute(
        "INSERT OR IGNORE INTO user_referrals (id, user_id, invite_code) VALUES (?,?,?)",
        (str(uuid.uuid4()), user_id, code)
    )
    db.commit()
    return code


def get_referral_stats(user_id: str) -> dict:
    db = get_db()
    code = ensure_invite_code(user_id)
    row = db.execute("SELECT * FROM user_referrals WHERE user_id = ?", (user_id,)).fetchone()
    invites = db.execute(
        """SELECT u.display_name, u.created_at, ri.activated_at
           FROM referral_invites ri
           JOIN users u ON u.id = ri.invited_user_id
           WHERE ri.referrer_user_id = ?
           ORDER BY ri.created_at DESC LIMIT 20""",
        (user_id,)
    ).fetchall()
    return {
        "invite_code": code,
        "invite_url": f"/join/{code}",
        "total_invited": row["total_invited"] if row else 0,
        "total_activated": row["total_activated"] if row else 0,
        "reputation_earned": row["reputation_earned"] if row else 0,
        "invites": [dict(i) for i in invites],
    }


def apply_invite_code(invited_user_id: str, code: str) -> bool:
    """Record that invited_user_id joined via invite code."""
    db = get_db()
    ref = db.execute(
        "SELECT * FROM user_referrals WHERE invite_code = ?", (code.upper().strip(),)
    ).fetchone()
    if not ref:
        return False
    if ref["user_id"] == invited_user_id:
        return False  # can't refer yourself
    # Check not already referred
    existing = db.execute(
        "SELECT 1 FROM referral_invites WHERE invited_user_id = ?", (invited_user_id,)
    ).fetchone()
    if existing:
        return False
    with transaction(db):
        db.execute(
            """INSERT INTO referral_invites (id, referrer_user_id, invited_user_id)
               VALUES (?,?,?)""",
            (str(uuid.uuid4()), ref["user_id"], invited_user_id)
        )
        db.execute(
            "UPDATE user_referrals SET total_invited = total_invited + 1 WHERE user_id = ?",
            (ref["user_id"],)
        )
    return True


def activate_referral(invited_user_id: str):
    """Called when the invited user solves their first problem. Rewards referrer."""
    db = get_db()
    invite = db.execute(
        """SELECT * FROM referral_invites
           WHERE invited_user_id = ? AND activated_at IS NULL""",
        (invited_user_id,)
    ).fetchone()
    if not invite:
        return
    with transaction(db):
        db.execute(
            "UPDATE referral_invites SET activated_at = datetime('now') WHERE id = ?",
            (invite["id"],)
        )
        db.execute(
            """UPDATE user_referrals
               SET total_activated = total_activated + 1,
                   reputation_earned = reputation_earned + 50
               WHERE user_id = ?""",
            (invite["referrer_user_id"],)
        )
        # Award 50 rep to referrer
        try:
            from skillos.reputation.service import award_reputation
            award_reputation(invite["referrer_user_id"], 50, "referral_activated")
        except Exception:
            pass


def get_referral_leaderboard() -> list:
    db = get_db()
    rows = db.execute(
        """SELECT u.display_name, u.id, r.total_invited, r.total_activated, r.reputation_earned
           FROM user_referrals r
           JOIN users u ON u.id = r.user_id
           WHERE r.total_activated > 0
           ORDER BY r.total_activated DESC, r.total_invited DESC
           LIMIT 20"""
    ).fetchall()
    return [dict(r) for r in rows]

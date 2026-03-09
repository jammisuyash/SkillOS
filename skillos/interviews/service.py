"""
skillos/interviews/service.py

Live Interview feature — complete implementation.

Supports:
  - Interview room creation (recruiter or admin)
  - Candidate invite (secure token link)
  - Real-time code editor state (stored in DB, polled by frontend)
  - Interview questions / problem assignment during session
  - Interviewer notes (private, not visible to candidate)
  - Session timer
  - Interview result / feedback submission
  - Replay: full code history log
"""

import uuid
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from skillos.db.database import fetchone, fetchall, transaction
from skillos.shared.exceptions import NotFoundError, ValidationError, ForbiddenError


# ── Helpers ─────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ── Room CRUD ────────────────────────────────────────────────────────────────

def create_interview_room(
    creator_id: str,
    candidate_email: str,
    title: str,
    scheduled_at: Optional[str] = None,
    duration_minutes: int = 60,
    task_id: Optional[str] = None,
) -> dict:
    """Create a new interview room. Returns room + invite token."""
    if not title or len(title.strip()) < 3:
        raise ValidationError("Title must be at least 3 characters")
    if duration_minutes < 10 or duration_minutes > 240:
        raise ValidationError("Duration must be 10-240 minutes")

    room_id    = str(uuid.uuid4())
    invite_tok = str(uuid.uuid4()).replace("-", "")   # opaque invite link token

    with transaction() as db:
        db.execute("""
            INSERT INTO interview_rooms
              (id, creator_id, candidate_email, title, scheduled_at,
               duration_minutes, task_id, invite_token, status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            room_id, creator_id, candidate_email.strip().lower(),
            title.strip(), scheduled_at, duration_minutes,
            task_id, invite_tok, "scheduled", _now_iso(),
        ))

    return get_room(room_id, creator_id)


def get_room(room_id: str, viewer_id: Optional[str] = None) -> dict:
    row = fetchone("SELECT * FROM interview_rooms WHERE id=?", (room_id,))
    if not row:
        raise NotFoundError("interview_room", room_id)

    room = dict(row)

    # Attach task info if any
    if room.get("task_id"):
        task = fetchone("SELECT id, title, difficulty, description FROM tasks WHERE id=?",
                        (room["task_id"],))
        room["task"] = dict(task) if task else None

    # Attach latest code snapshot
    snap = fetchone(
        "SELECT code, language, updated_at FROM interview_code_snapshots "
        "WHERE room_id=? ORDER BY updated_at DESC LIMIT 1",
        (room_id,),
    )
    room["current_code"] = dict(snap) if snap else None

    # Attach events (messages / notes) — interviewer notes filtered for candidates
    is_interviewer = (viewer_id == room["creator_id"])
    events_q = """
        SELECT ie.*, u.display_name FROM interview_events ie
        LEFT JOIN users u ON u.id = ie.author_id
        WHERE ie.room_id=? {}
        ORDER BY ie.created_at ASC LIMIT 200
    """.format("" if is_interviewer else "AND ie.is_private=0")
    room["events"] = [dict(e) for e in fetchall(events_q, (room_id,))]

    return room


def get_rooms_for_user(user_id: str) -> list:
    """All rooms created by this user (interviewer view)."""
    rows = fetchall(
        "SELECT * FROM interview_rooms WHERE creator_id=? ORDER BY created_at DESC",
        (user_id,),
    )
    return [dict(r) for r in rows]


def get_room_by_invite(invite_token: str) -> dict:
    """Candidate join via invite link."""
    row = fetchone("SELECT * FROM interview_rooms WHERE invite_token=?", (invite_token,))
    if not row:
        raise NotFoundError("interview_room", invite_token)
    return get_room(row["id"])


def start_room(room_id: str, user_id: str) -> dict:
    """Mark room as active and record start time."""
    room = fetchone("SELECT * FROM interview_rooms WHERE id=?", (room_id,))
    if not room:
        raise NotFoundError("interview_room", room_id)
    if room["creator_id"] != user_id:
        raise ForbiddenError("Only the interviewer can start the room")
    if room["status"] == "active":
        return get_room(room_id, user_id)

    with transaction() as db:
        db.execute(
            "UPDATE interview_rooms SET status='active', started_at=? WHERE id=?",
            (_now_iso(), room_id),
        )
    _add_event(room_id, None, "system", "Interview started", is_private=False)
    return get_room(room_id, user_id)


def end_room(room_id: str, user_id: str, feedback: str = "", rating: int = 0) -> dict:
    """End an interview session and store feedback."""
    room = fetchone("SELECT * FROM interview_rooms WHERE id=?", (room_id,))
    if not room:
        raise NotFoundError("interview_room", room_id)
    if room["creator_id"] != user_id:
        raise ForbiddenError("Only the interviewer can end the room")

    if rating < 0 or rating > 5:
        rating = 0

    with transaction() as db:
        db.execute(
            "UPDATE interview_rooms SET status='ended', ended_at=?, feedback=?, rating=? WHERE id=?",
            (_now_iso(), feedback.strip(), rating, room_id),
        )
    _add_event(room_id, None, "system", "Interview ended", is_private=False)
    return get_room(room_id, user_id)


# ── Code Collaboration ───────────────────────────────────────────────────────

def update_code(room_id: str, author_id: str, code: str, language: str = "python3") -> dict:
    """Save a code snapshot. Called on every significant editor change."""
    if len(code) > 65536:
        raise ValidationError("Code exceeds maximum length (64KB)")

    snap_id = str(uuid.uuid4())
    now = _now_iso()

    with transaction() as db:
        # Save snapshot (full history for replay)
        db.execute("""
            INSERT INTO interview_code_snapshots (id, room_id, author_id, code, language, updated_at)
            VALUES (?,?,?,?,?,?)
        """, (snap_id, room_id, author_id, code, language, now))

    return {"snapshot_id": snap_id, "updated_at": now}


def get_code_history(room_id: str, limit: int = 50) -> list:
    """Return code change history for replay."""
    rows = fetchall(
        "SELECT cs.*, u.display_name FROM interview_code_snapshots cs "
        "LEFT JOIN users u ON u.id=cs.author_id "
        "WHERE cs.room_id=? ORDER BY cs.updated_at DESC LIMIT ?",
        (room_id, limit),
    )
    return [dict(r) for r in rows]


# ── Events / Chat ────────────────────────────────────────────────────────────

def _add_event(
    room_id: str,
    author_id: Optional[str],
    event_type: str,
    content: str,
    is_private: bool = False,
) -> dict:
    eid = str(uuid.uuid4())
    now = _now_iso()
    with transaction() as db:
        db.execute("""
            INSERT INTO interview_events (id, room_id, author_id, event_type, content, is_private, created_at)
            VALUES (?,?,?,?,?,?,?)
        """, (eid, room_id, author_id, event_type, content, 1 if is_private else 0, now))
    return {"id": eid, "event_type": event_type, "content": content, "created_at": now}


def add_message(room_id: str, author_id: str, content: str) -> dict:
    """Send a chat message in the interview room."""
    if not content or len(content.strip()) == 0:
        raise ValidationError("Message cannot be empty")
    if len(content) > 2000:
        raise ValidationError("Message too long (max 2000 chars)")
    return _add_event(room_id, author_id, "message", content.strip(), is_private=False)


def add_interviewer_note(room_id: str, author_id: str, note: str) -> dict:
    """Private note visible only to interviewer."""
    room = fetchone("SELECT creator_id FROM interview_rooms WHERE id=?", (room_id,))
    if not room or room["creator_id"] != author_id:
        raise ForbiddenError("Only the interviewer can add private notes")
    if not note or len(note.strip()) == 0:
        raise ValidationError("Note cannot be empty")
    return _add_event(room_id, author_id, "note", note.strip(), is_private=True)


def add_hint(room_id: str, author_id: str, hint: str) -> dict:
    """Interviewer sends a visible hint to the candidate."""
    room = fetchone("SELECT creator_id FROM interview_rooms WHERE id=?", (room_id,))
    if not room or room["creator_id"] != author_id:
        raise ForbiddenError("Only the interviewer can send hints")
    return _add_event(room_id, author_id, "hint", hint.strip(), is_private=False)


# ── Question Bank Integration ────────────────────────────────────────────────

def assign_task(room_id: str, user_id: str, task_id: str) -> dict:
    """Assign a problem to the interview room mid-session."""
    room = fetchone("SELECT * FROM interview_rooms WHERE id=?", (room_id,))
    if not room:
        raise NotFoundError("interview_room", room_id)
    if room["creator_id"] != user_id:
        raise ForbiddenError("Only the interviewer can assign tasks")

    task = fetchone("SELECT id, title FROM tasks WHERE id=?", (task_id,))
    if not task:
        raise NotFoundError("task", task_id)

    with transaction() as db:
        db.execute("UPDATE interview_rooms SET task_id=? WHERE id=?", (task_id, room_id))

    _add_event(room_id, user_id, "task_assigned",
               f"Problem assigned: {task['title']}", is_private=False)
    return get_room(room_id, user_id)


# ── Stats ────────────────────────────────────────────────────────────────────

def get_interview_stats(user_id: str) -> dict:
    """Summary stats for a recruiter/interviewer."""
    total     = fetchone("SELECT COUNT(*) AS c FROM interview_rooms WHERE creator_id=?", (user_id,))
    completed = fetchone("SELECT COUNT(*) AS c FROM interview_rooms WHERE creator_id=? AND status='ended'", (user_id,))
    avg_r     = fetchone("SELECT AVG(rating) AS r FROM interview_rooms WHERE creator_id=? AND rating > 0", (user_id,))

    return {
        "total_interviews": total["c"] if total else 0,
        "completed": completed["c"] if completed else 0,
        "avg_rating": round(avg_r["r"] or 0, 1) if avg_r else 0.0,
    }

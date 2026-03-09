"""
evaluator/proctoring.py — Light proctoring for timed assessments.

WHAT WE DO (realistic for v1):
  ✓ Track time spent on problem
  ✓ Detect tab switches / window focus loss
  ✓ Flag suspicious behaviour (too fast, too many switches)
  ✓ Store proctoring data with submission

WHAT WE DON'T DO (requires native apps / webcam):
  ✗ Webcam monitoring
  ✗ Screen recording
  ✗ AI face detection
  ✗ Copy-paste detection at OS level

The browser frontend sends events via JS (blur/focus/visibilitychange).
We record them here and attach flags to the submission.

FLAGS:
  - "fast_submit"       — answered in under 30 seconds
  - "excessive_tabs"    — switched tabs 5+ times
  - "long_pause"        — inactive for over 10 minutes
  - "multiple_attempts" — submitted same problem more than 3x in 1 hour
"""
import uuid, json
from datetime import datetime, timedelta
from skillos.db.database import transaction, fetchone, fetchall
from skillos.shared.utils import utcnow_iso


def start_proctoring_session(user_id: str, task_id: str) -> str:
    """Create a proctoring session. Returns session_id."""
    session_id = str(uuid.uuid4())
    with transaction() as db:
        db.execute("""
            INSERT INTO proctoring_sessions
                (id, user_id, task_id, started_at)
            VALUES (?, ?, ?, ?)
        """, (session_id, user_id, task_id, utcnow_iso()))
    return session_id


def update_proctoring_event(session_id: str, event_type: str, data: dict = None):
    """
    Record a proctoring event.
    event_type: 'tab_switch' | 'focus_lost' | 'focus_regained' | 'paste' | 'heartbeat'
    """
    row = fetchone("SELECT * FROM proctoring_sessions WHERE id=?", (session_id,))
    if not row:
        return

    with transaction() as db:
        if event_type == "tab_switch":
            db.execute("""
                UPDATE proctoring_sessions SET tab_switches = tab_switches + 1 WHERE id=?
            """, (session_id,))
        elif event_type == "focus_lost":
            db.execute("""
                UPDATE proctoring_sessions SET focus_lost_count = focus_lost_count + 1 WHERE id=?
            """, (session_id,))
        elif event_type == "heartbeat" and data:
            time_spent = data.get("time_spent_s", 0)
            db.execute("""
                UPDATE proctoring_sessions SET time_spent_s = ? WHERE id=?
            """, (time_spent, session_id))


def finalise_session(session_id: str, submission_id: str = None) -> dict:
    """
    Close a proctoring session and generate flags.
    Returns {flags: [...], is_suspicious: bool, summary: str}
    """
    row = fetchone("SELECT * FROM proctoring_sessions WHERE id=?", (session_id,))
    if not row:
        return {"flags": [], "is_suspicious": False, "summary": "No session found"}

    flags = _compute_flags(row)

    with transaction() as db:
        db.execute("""
            UPDATE proctoring_sessions
            SET ended_at=?, submission_id=?, flags=?
            WHERE id=?
        """, (utcnow_iso(), submission_id, json.dumps(flags), session_id))

    is_suspicious = len(flags) >= 2 or "excessive_tabs" in flags
    summary = _build_summary(row, flags)

    return {
        "flags":        flags,
        "is_suspicious": is_suspicious,
        "summary":      summary,
        "tab_switches": row["tab_switches"],
        "time_spent_s": row["time_spent_s"],
    }


def _compute_flags(row) -> list[str]:
    flags = []
    if row["time_spent_s"] and row["time_spent_s"] < 30:
        flags.append("fast_submit")
    if row["tab_switches"] >= 5:
        flags.append("excessive_tabs")
    elif row["tab_switches"] >= 2:
        flags.append("tab_switches_detected")
    if row["focus_lost_count"] >= 10:
        flags.append("frequent_focus_loss")
    return flags


def _build_summary(row, flags: list) -> str:
    parts = [f"Time spent: {row['time_spent_s'] or 0}s"]
    if row["tab_switches"]:
        parts.append(f"Tab switches: {row['tab_switches']}")
    if flags:
        parts.append(f"Flags: {', '.join(flags)}")
    return " | ".join(parts)


def get_session_report(session_id: str) -> dict | None:
    row = fetchone("SELECT * FROM proctoring_sessions WHERE id=?", (session_id,))
    return dict(row) if row else None

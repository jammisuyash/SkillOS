"""
skills/history.py — Skill score history tracking + chart data.

Every time a user's skill score changes, we record a snapshot here.
This powers the "History of Improvement" chart on the profile page.
"""
import uuid
from skillos.db.database import fetchall, fetchone, transaction
from skillos.shared.utils import utcnow_iso


def record_score_snapshot(user_id: str, skill_id: str, new_score: float,
                           old_score: float, reason: str = "submission"):
    """Record a skill score change. Called by skills/scoring.py after every evaluation."""
    delta = round(new_score - old_score, 2)
    with transaction() as db:
        db.execute("""
            INSERT INTO skill_score_history (id, user_id, skill_id, score, delta, reason)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), user_id, skill_id, round(new_score, 2), delta, reason))


def get_skill_history(user_id: str, skill_id: str, limit: int = 30) -> list[dict]:
    """Get score history for one skill — used to draw a line chart."""
    rows = fetchall("""
        SELECT score, delta, reason, recorded_at
        FROM skill_score_history
        WHERE user_id = ? AND skill_id = ?
        ORDER BY recorded_at ASC
        LIMIT ?
    """, (user_id, skill_id, limit))
    return [dict(r) for r in rows]


def get_all_skills_history(user_id: str, days: int = 30) -> list[dict]:
    """
    Get aggregated history across all skills for the past N days.
    Returns daily max scores per skill — good for a multi-line chart.
    """
    rows = fetchall("""
        SELECT
            ssh.skill_id,
            s.name AS skill_name,
            s.domain,
            date(ssh.recorded_at) AS day,
            MAX(ssh.score) AS score
        FROM skill_score_history ssh
        JOIN skills s ON s.id = ssh.skill_id
        WHERE ssh.user_id = ?
          AND ssh.recorded_at >= datetime('now', ? || ' days')
        GROUP BY ssh.skill_id, day
        ORDER BY day ASC
    """, (user_id, f"-{days}"))
    return [dict(r) for r in rows]


def get_overall_progress(user_id: str) -> dict:
    """Summary stats for the profile page."""
    total = fetchone("""
        SELECT COUNT(*) as cnt, MAX(score) as peak, AVG(score) as avg_score
        FROM skill_score_history WHERE user_id = ?
    """, (user_id,))

    best_day = fetchone("""
        SELECT date(recorded_at) as day, SUM(delta) as total_delta
        FROM skill_score_history
        WHERE user_id = ? AND delta > 0
        GROUP BY day ORDER BY total_delta DESC LIMIT 1
    """, (user_id,))

    recent_gains = fetchall("""
        SELECT s.name as skill_name, SUM(ssh.delta) as total_gain
        FROM skill_score_history ssh JOIN skills s ON s.id = ssh.skill_id
        WHERE ssh.user_id = ? AND ssh.recorded_at >= datetime('now', '-7 days') AND ssh.delta > 0
        GROUP BY ssh.skill_id ORDER BY total_gain DESC LIMIT 3
    """, (user_id,))

    return {
        "total_snapshots": total["cnt"] if total else 0,
        "peak_score":      round(total["peak"] or 0, 1) if total else 0,
        "best_day":        dict(best_day) if best_day else None,
        "recent_gains":    [dict(r) for r in recent_gains],
    }

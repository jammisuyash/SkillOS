"""contests/service.py — Contest lifecycle, registration, scoring, leaderboard."""
import uuid
from datetime import datetime, timedelta, timezone
from skillos.db.database import fetchone, fetchall, transaction
from skillos.shared.exceptions import ValidationError
from skillos.shared.utils import utcnow_iso


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def list_contests(status=None) -> list:
    if status:
        rows = fetchall("SELECT * FROM contests WHERE status=? ORDER BY starts_at DESC", (status,))
    else:
        rows = fetchall("SELECT * FROM contests ORDER BY starts_at DESC")
    result = []
    for r in rows:
        d = dict(r)
        d["problem_count"] = fetchone(
            "SELECT COUNT(*) AS c FROM contest_problems WHERE contest_id=?", (r["id"],))["c"]
        d["participant_count"] = fetchone(
            "SELECT COUNT(*) AS c FROM contest_entries WHERE contest_id=?", (r["id"],))["c"]
        result.append(d)
    return result


def get_contest(contest_id: str) -> dict | None:
    c = fetchone("SELECT * FROM contests WHERE id=?", (contest_id,))
    if not c:
        return None
    problems = fetchall("""
        SELECT t.id, t.title, t.difficulty, cp.points, cp.ordinal
        FROM contest_problems cp JOIN tasks t ON t.id=cp.task_id
        WHERE cp.contest_id=? ORDER BY cp.ordinal
    """, (contest_id,))
    return {**dict(c), "problems": [dict(p) for p in problems],
            "leaderboard": get_contest_leaderboard(contest_id, limit=20)}


def create_contest(title: str, description: str, starts_at: str,
                   ends_at: str, task_ids: list) -> dict:
    contest_id = str(uuid.uuid4())
    with transaction() as db:
        db.execute("""
            INSERT INTO contests (id, title, description, starts_at, ends_at)
            VALUES (?, ?, ?, ?, ?)
        """, (contest_id, title, description, starts_at, ends_at))
        for i, task_id in enumerate(task_ids):
            db.execute("""
                INSERT INTO contest_problems (id, contest_id, task_id, ordinal, points)
                VALUES (?, ?, ?, ?, 100)
            """, (str(uuid.uuid4()), contest_id, task_id, i + 1))
    return {"contest_id": contest_id}


def register_for_contest(user_id: str, contest_id: str) -> dict:
    c = fetchone("SELECT * FROM contests WHERE id=?", (contest_id,))
    if not c:
        raise ValidationError("Contest not found")
    if c["status"] == "ended":
        raise ValidationError("Contest has ended")
    existing = fetchone(
        "SELECT id FROM contest_entries WHERE contest_id=? AND user_id=?",
        (contest_id, user_id)
    )
    if existing:
        raise ValidationError("Already registered")
    entry_id = str(uuid.uuid4())
    with transaction() as db:
        db.execute("INSERT INTO contest_entries (id,contest_id,user_id) VALUES (?,?,?)",
                   (entry_id, contest_id, user_id))
    return {"entry_id": entry_id, "contest_id": contest_id}


def get_contest_leaderboard(contest_id: str, limit=100) -> list:
    rows = fetchall("""
        SELECT ce.user_id, u.display_name, u.username, u.avatar_url,
               ce.total_score, ce.problems_solved, ce.rank, ce.registered_at
        FROM contest_entries ce JOIN users u ON u.id=ce.user_id
        WHERE ce.contest_id=?
        ORDER BY ce.total_score DESC, ce.problems_solved DESC
        LIMIT ?
    """, (contest_id, limit))
    return [dict(r, position=i + 1) for i, r in enumerate(rows)]


def update_contest_score(contest_id: str, user_id: str, task_id: str, points: int):
    entry = fetchone("SELECT * FROM contest_entries WHERE contest_id=? AND user_id=?",
                     (contest_id, user_id))
    if not entry:
        return
    already = fetchone("""
        SELECT COUNT(*) AS c FROM submissions s
        WHERE s.user_id=? AND s.task_id=? AND s.status='accepted'
    """, (user_id, task_id))
    if already and already["c"] > 1:
        return
    with transaction() as db:
        db.execute("""
            UPDATE contest_entries
            SET total_score=total_score+?, problems_solved=problems_solved+1
            WHERE contest_id=? AND user_id=?
        """, (points, contest_id, user_id))
    _refresh_ranks(contest_id)


def _refresh_ranks(contest_id: str):
    entries = fetchall("""
        SELECT id FROM contest_entries WHERE contest_id=?
        ORDER BY total_score DESC, problems_solved DESC
    """, (contest_id,))
    with transaction() as db:
        for i, e in enumerate(entries):
            db.execute("UPDATE contest_entries SET rank=? WHERE id=?", (i + 1, e["id"]))


def sync_contest_statuses():
    now = _now()
    with transaction() as db:
        db.execute("UPDATE contests SET status='active' WHERE status='upcoming' AND starts_at<=?", (now,))
        db.execute("UPDATE contests SET status='ended'  WHERE status='active'   AND ends_at<=?",   (now,))


def seed_daily_challenge():
    from datetime import date
    today = date.today().isoformat()
    existing = fetchone("SELECT id FROM daily_challenges WHERE date=?", (today,))
    if existing:
        return
    task = fetchone("SELECT id FROM tasks WHERE is_published=1 ORDER BY RANDOM() LIMIT 1")
    if task:
        with transaction() as db:
            db.execute("INSERT OR IGNORE INTO daily_challenges (id, task_id, date) VALUES (?,?,?)",
                       (str(uuid.uuid4()), task["id"], today))


def seed_sample_contests():
    if fetchone("SELECT id FROM contests LIMIT 1"):
        return
    tasks = fetchall("SELECT id FROM tasks WHERE is_published=1 ORDER BY difficulty LIMIT 6")
    if len(tasks) < 3:
        return
    task_ids = [t["id"] for t in tasks]
    now = datetime.now(timezone.utc)
    for title, desc, start_delta, end_delta, task_slice in [
        ("Weekly Challenge #1 — Fundamentals",
         "Solve algorithm problems and climb the leaderboard!",
         timedelta(hours=-2), timedelta(hours=22), task_ids[:3]),
        ("Weekend Hackathon — Arrays & Search",
         "Two-day sprint. Top 3 win SkillOS certificates.",
         timedelta(days=2), timedelta(days=4), task_ids[1:4]),
        ("Monthly Open — March 2026",
         "Monthly open competition. All levels welcome.",
         timedelta(days=7), timedelta(days=9), task_ids[3:6]),
    ]:
        create_contest(title, desc,
                       (now + start_delta).isoformat(),
                       (now + end_delta).isoformat(),
                       task_slice)

"""analytics/service.py — Platform analytics: skill trends, demand, developer performance."""
from skillos.db.database import fetchall, fetchone

def get_platform_stats() -> dict:
    return {
        "total_users":       fetchone("SELECT COUNT(*) AS c FROM users", ())["c"],
        "total_submissions": fetchone("SELECT COUNT(*) AS c FROM submissions", ())["c"],
        "accepted_rate":     _acceptance_rate(),
        "total_companies":   fetchone("SELECT COUNT(*) AS c FROM companies", ())["c"],
        "active_today":      _active_today(),
    }

def _acceptance_rate() -> float:
    row = fetchone("""SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN status='accepted' THEN 1 ELSE 0 END) AS accepted
        FROM submissions""", ())
    if not row or not row["total"]: return 0.0
    return round(row["accepted"] / row["total"] * 100, 1)

def _active_today() -> int:
    from datetime import date
    today = date.today().isoformat()
    row = fetchone("SELECT COUNT(DISTINCT user_id) AS c FROM submissions WHERE submitted_at>=?", (today,))
    return row["c"] if row else 0

def get_skill_demand() -> list:
    """Which skills recruiters filter for most (most contact requests with high skill scores)."""
    rows = fetchall("""
        SELECT s.name, COUNT(uss.user_id) AS developer_count,
               AVG(uss.current_score) AS avg_score,
               MAX(uss.current_score) AS top_score
        FROM skills s LEFT JOIN user_skill_scores uss ON uss.skill_id=s.id
        GROUP BY s.id ORDER BY developer_count DESC
    """, ())
    return [dict(r) for r in rows]

def get_top_problems() -> list:
    rows = fetchall("""
        SELECT t.id, t.title, t.difficulty, s.name AS skill_name,
               COUNT(sub.id) AS total_attempts,
               SUM(CASE WHEN sub.status='accepted' THEN 1 ELSE 0 END) AS accepted,
               AVG(sub.max_runtime_ms) AS avg_runtime_ms
        FROM tasks t
        LEFT JOIN submissions sub ON sub.task_id=t.id
        LEFT JOIN skills s ON s.id=t.skill_id
        WHERE t.is_published=1
        GROUP BY t.id ORDER BY total_attempts DESC LIMIT 20
    """, ())
    result = []
    for r in rows:
        d = dict(r)
        d["acceptance_rate"] = round(d["accepted"]/(d["total_attempts"] or 1)*100, 1)
        result.append(d)
    return result

def get_user_activity_trend(days=30) -> list:
    rows = fetchall("""
        SELECT DATE(submitted_at) AS day, COUNT(*) AS submissions,
               COUNT(DISTINCT user_id) AS active_users,
               SUM(CASE WHEN status='accepted' THEN 1 ELSE 0 END) AS accepted
        FROM submissions
        WHERE submitted_at >= DATE('now', ? || ' days')
        GROUP BY day ORDER BY day ASC
    """, (f"-{days}",))
    return [dict(r) for r in rows]

def get_leaderboard_snapshot(period="alltime", limit=100) -> list:
    """Snapshot-based leaderboard (updated periodically)."""
    rows = fetchall("""
        SELECT ls.rank, ls.score, u.display_name, u.username, u.avatar_url
        FROM leaderboard_snapshots ls JOIN users u ON u.id=ls.user_id
        WHERE ls.period=? ORDER BY ls.rank ASC LIMIT ?
    """, (period, limit))
    return [dict(r) for r in rows]

def refresh_leaderboard_snapshots():
    """Recompute and store leaderboard snapshots. Run periodically (e.g. hourly)."""
    import uuid
    from skillos.db.database import transaction
    rows = fetchall("""
        SELECT user_id, SUM(current_score) AS score
        FROM user_skill_scores GROUP BY user_id
        ORDER BY score DESC
    """, ())
    with transaction() as db:
        db.execute("DELETE FROM leaderboard_snapshots WHERE period='alltime'")
        for i, r in enumerate(rows):
            db.execute("""INSERT INTO leaderboard_snapshots (id,user_id,period,score,rank)
                          VALUES (?,?,'alltime',?,?)""",
                       (str(uuid.uuid4()), r["user_id"], r["score"], i+1))

"""leaderboard/service.py — Global, domain, weekly, monthly leaderboards."""
from skillos.db.database import fetchall, fetchone, transaction
from skillos.shared.utils import utcnow_iso
import uuid

def get_global_leaderboard(limit=50, offset=0, college_filter=None) -> list:
    """Global leaderboard. Pass college_filter='IIT Bombay' to filter by institution."""
    if college_filter:
        rows = fetchall("""
            SELECT u.id, u.display_name, u.username, u.avatar_url, u.reputation,
                   u.streak_current, u.college,
                   COALESCE(SUM(uss.current_score),0) AS total_score,
                   COALESCE(SUM(uss.tasks_passed),0)  AS total_solved,
                   COUNT(DISTINCT uss.skill_id)        AS skills_active
            FROM users u
            LEFT JOIN user_skill_scores uss ON uss.user_id=u.id
            WHERE u.is_public=1 AND u.college=?
            GROUP BY u.id ORDER BY total_score DESC, total_solved DESC
            LIMIT ? OFFSET ?
        """, (college_filter, limit, offset))
    else:
        rows = fetchall("""
            SELECT u.id, u.display_name, u.username, u.avatar_url, u.reputation,
                   u.streak_current, u.college,
                   COALESCE(SUM(uss.current_score),0) AS total_score,
                   COALESCE(SUM(uss.tasks_passed),0)  AS total_solved,
                   COUNT(DISTINCT uss.skill_id)        AS skills_active
            FROM users u
            LEFT JOIN user_skill_scores uss ON uss.user_id=u.id
            WHERE u.is_public=1
            GROUP BY u.id ORDER BY total_score DESC, total_solved DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
    return [dict(r, rank=i+offset+1) for i,r in enumerate(rows)]


def get_college_leaderboard(college: str, limit=50) -> list:
    """Leaderboard scoped to a single college/institution."""
    return get_global_leaderboard(limit=limit, college_filter=college)


def get_all_colleges() -> list:
    """Return list of colleges with developer counts."""
    rows = fetchall("""
        SELECT college, COUNT(*) AS developer_count,
               MAX(COALESCE((SELECT SUM(current_score) FROM user_skill_scores WHERE user_id=u.id),0)) AS top_score
        FROM users u
        WHERE u.college IS NOT NULL AND u.college != '' AND u.is_public=1
        GROUP BY college ORDER BY developer_count DESC LIMIT 100
    """, ())
    return [dict(r) for r in rows]

def get_domain_leaderboard(skill_id: str, limit=50) -> list:
    rows = fetchall("""
        SELECT u.id, u.display_name, u.username, u.avatar_url,
               uss.current_score AS score, uss.tasks_passed
        FROM user_skill_scores uss
        JOIN users u ON u.id=uss.user_id
        WHERE uss.skill_id=? AND u.is_public=1
        ORDER BY uss.current_score DESC LIMIT ?
    """, (skill_id, limit))
    return [dict(r, rank=i+1) for i,r in enumerate(rows)]

def get_weekly_leaderboard(limit=50) -> list:
    from datetime import datetime, timedelta
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    rows = fetchall("""
        SELECT u.id, u.display_name, u.username, u.avatar_url,
               COUNT(DISTINCT s.task_id)   AS solved_this_week,
               COUNT(s.id)                 AS submissions_this_week
        FROM submissions s JOIN users u ON u.id=s.user_id
        WHERE s.status='accepted' AND s.submitted_at > ? AND u.is_public=1
        GROUP BY u.id ORDER BY solved_this_week DESC, submissions_this_week ASC
        LIMIT ?
    """, (week_ago, limit))
    return [dict(r, rank=i+1) for i,r in enumerate(rows)]

def get_user_rank(user_id: str) -> dict:
    total = fetchone("SELECT COUNT(*) AS cnt FROM users WHERE is_public=1", ())
    user_score = fetchone("""
        SELECT COALESCE(SUM(current_score),0) AS score FROM user_skill_scores WHERE user_id=?
    """, (user_id,))
    rank = fetchone("""
        SELECT COUNT(*)+1 AS rank FROM (
            SELECT user_id, SUM(current_score) AS s FROM user_skill_scores GROUP BY user_id
        ) WHERE s > ?
    """, (user_score["score"],))
    return {"rank": rank["rank"], "total_users": total["cnt"], "score": user_score["score"]}

def get_monthly_leaderboard(year_month: str = None, limit: int = 50) -> list:
    """
    Monthly leaderboard — problems solved in a calendar month.
    year_month format: "2026-03" (defaults to current month)
    """
    from datetime import datetime
    if not year_month:
        year_month = datetime.utcnow().strftime("%Y-%m")

    # Get first and last day of month
    year, month = int(year_month.split("-")[0]), int(year_month.split("-")[1])
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    start = f"{year:04d}-{month:02d}-01"
    end   = f"{next_year:04d}-{next_month:02d}-01"

    rows = fetchall("""
        SELECT
            u.id, u.display_name, u.username, u.avatar_url,
            COUNT(DISTINCT s.task_id)         AS solved_this_month,
            COUNT(s.id)                        AS total_submissions,
            COUNT(DISTINCT t.skill_id)         AS skills_practiced,
            SUM(CASE WHEN t.difficulty='hard' THEN 1 ELSE 0 END) AS hard_solved
        FROM submissions s
        JOIN users u ON u.id = s.user_id
        JOIN tasks t ON t.id = s.task_id
        WHERE s.status = 'accepted'
          AND s.submitted_at >= ?
          AND s.submitted_at < ?
          AND u.is_public = 1
        GROUP BY u.id
        ORDER BY solved_this_month DESC, hard_solved DESC, total_submissions ASC
        LIMIT ?
    """, (start, end, limit))

    return [dict(r, rank=i+1, year_month=year_month) for i, r in enumerate(rows)]


def get_available_months() -> list[str]:
    """Return list of months that have leaderboard data."""
    rows = fetchall("""
        SELECT DISTINCT strftime('%Y-%m', submitted_at) AS ym
        FROM submissions WHERE status='accepted'
        ORDER BY ym DESC LIMIT 12
    """, ())
    return [r["ym"] for r in rows if r["ym"]]

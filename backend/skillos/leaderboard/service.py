"""leaderboard/service.py — Global, domain, weekly, monthly leaderboards."""
from skillos.db.database import fetchall, fetchone, transaction
from skillos.shared.utils import utcnow_iso
import uuid

def get_global_leaderboard(limit=50, offset=0) -> list:
    rows = fetchall("""
        SELECT u.id, u.display_name, u.username, u.avatar_url, u.reputation,
               u.streak_current,
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

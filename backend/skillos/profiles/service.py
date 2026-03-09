"""profiles/service.py — User profile CRUD, public profile, streak tracking."""
import re, uuid
from datetime import date, timedelta
from skillos.db.database import fetchone, fetchall, transaction
from skillos.shared.exceptions import ValidationError
from skillos.shared.utils import utcnow_iso

_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]{3,30}$')
_URL_RE      = re.compile(r'^https?://.+')

def _validate_url(url, field):
    if url and not _URL_RE.match(url):
        raise ValidationError(f"{field} must start with http:// or https://")

def get_profile(user_id: str) -> dict | None:
    return fetchone("""
        SELECT u.id, u.email, u.display_name, u.username, u.bio, u.location,
               u.education, u.experience_years, u.github_url, u.portfolio_url,
               u.linkedin_url, u.avatar_url, u.is_public, u.reputation,
               u.streak_current, u.streak_best, u.created_at, u.role,
               u.is_email_verified,
               (SELECT COUNT(*) FROM submissions
                WHERE user_id=u.id AND status='accepted') AS problems_solved,
               (SELECT COUNT(DISTINCT task_id) FROM submissions
                WHERE user_id=u.id AND status='accepted') AS unique_solved
        FROM users u WHERE u.id=?
    """, (user_id,))

def get_public_profile(username: str) -> dict | None:
    user = fetchone("""
        SELECT u.id, u.display_name, u.username, u.bio, u.location,
               u.education, u.experience_years, u.github_url, u.portfolio_url,
               u.linkedin_url, u.avatar_url, u.reputation,
               u.streak_current, u.streak_best, u.created_at,
               (SELECT COUNT(*) FROM submissions
                WHERE user_id=u.id AND status='accepted') AS problems_solved
        FROM users u WHERE u.username=? AND u.is_public=1
    """, (username,))
    if not user: return None
    skills = fetchall("""
        SELECT s.name, uss.current_score, uss.tasks_passed
        FROM user_skill_scores uss JOIN skills s ON s.id=uss.skill_id
        WHERE uss.user_id=? ORDER BY uss.current_score DESC
    """, (user["id"],))
    return {**dict(user), "skills": [dict(s) for s in skills]}

def update_profile(user_id: str, data: dict) -> dict:
    allowed = {"display_name","username","bio","location","education",
               "experience_years","github_url","portfolio_url","linkedin_url","is_public"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates: raise ValidationError("No valid fields to update")

    if "username" in updates:
        u = str(updates["username"]).strip()
        if not _USERNAME_RE.match(u): raise ValidationError("Username: 3-30 chars, letters/numbers/underscore only")
        existing = fetchone("SELECT id FROM users WHERE username=? AND id!=?", (u, user_id))
        if existing: raise ValidationError("Username already taken")
        updates["username"] = u

    if "display_name" in updates:
        n = str(updates["display_name"]).strip()
        if not n or len(n) > 64: raise ValidationError("Display name must be 1-64 chars")
        updates["display_name"] = n

    for field in ("github_url","portfolio_url","linkedin_url"):
        if field in updates: _validate_url(updates[field], field)

    sets = ", ".join(f"{k}=?" for k in updates)
    with transaction() as db:
        db.execute(f"UPDATE users SET {sets} WHERE id=?", (*updates.values(), user_id))
    return get_profile(user_id)

def update_streak(user_id: str):
    today = date.today().isoformat()
    user  = fetchone("SELECT last_active_date, streak_current, streak_best FROM users WHERE id=?", (user_id,))
    if not user: return
    last  = user["last_active_date"]
    cur   = user["streak_current"] or 0
    best  = user["streak_best"] or 0
    if last == today: return
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    new_streak = cur + 1 if last == yesterday else 1
    new_best   = max(best, new_streak)
    with transaction() as db:
        db.execute("UPDATE users SET streak_current=?, streak_best=?, last_active_date=? WHERE id=?",
                   (new_streak, new_best, today, user_id))

def get_skill_graph(user_id: str) -> list:
    return fetchall("""
        SELECT s.id, s.name, s.description,
               COALESCE(uss.current_score, 0)   AS score,
               COALESCE(uss.tasks_attempted, 0) AS attempted,
               COALESCE(uss.tasks_passed, 0)    AS passed,
               (SELECT COUNT(*) FROM user_skill_scores
                WHERE skill_id=s.id AND current_score <= COALESCE(uss.current_score,0)) AS rank_below,
               (SELECT COUNT(*) FROM user_skill_scores WHERE skill_id=s.id) AS total_ranked
        FROM skills s
        LEFT JOIN user_skill_scores uss ON uss.skill_id=s.id AND uss.user_id=?
        ORDER BY score DESC
    """, (user_id,))

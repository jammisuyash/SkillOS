"""reputation/service.py — Reputation points, badges, history."""
import uuid
from skillos.db.database import fetchone, fetchall, transaction
from skillos.shared.utils import utcnow_iso

POINTS = {
    "solve_easy":            10,
    "solve_medium":          25,
    "solve_hard":            60,
    "first_solve":           15,   # bonus for first time solving a problem
    "contest_top10":        100,
    "contest_top3":         250,
    "contest_win":          500,
    "post_discussion":        2,
    "post_reply":             1,
    "reply_accepted":        15,
    "discussion_upvoted":     5,
    "path_step_complete":     5,
    "path_complete":         50,
    "cert_earned":          200,
    "streak_7":              25,
    "streak_30":            100,
    "streak_100":           500,
}

def award_reputation(user_id: str, event_type: str, points: int,
                     ref_id: str = None, ref_type: str = None):
    """Award reputation points and persist the event."""
    with transaction() as db:
        db.execute("""INSERT INTO reputation_events (id,user_id,event_type,points,ref_id,ref_type)
                      VALUES (?,?,?,?,?,?)""",
                   (str(uuid.uuid4()), user_id, event_type, points, ref_id, ref_type))
        db.execute("UPDATE users SET reputation=reputation+? WHERE id=?", (points, user_id))

def award_for_submission(user_id: str, task_id: str, difficulty: str, status: str):
    """Award rep when a submission is accepted. Check for first-solve bonus."""
    if status != "accepted": return
    event = f"solve_{difficulty}"
    pts   = POINTS.get(event, 10)
    # First time solving this specific task?
    prev = fetchone("""SELECT COUNT(*) AS c FROM submissions
                       WHERE user_id=? AND task_id=? AND status='accepted'""", (user_id, task_id))
    is_first = prev and prev["c"] <= 1
    if is_first:
        pts += POINTS["first_solve"]
        award_reputation(user_id, "first_solve", POINTS["first_solve"], task_id, "task")
    award_reputation(user_id, event, POINTS.get(event, 10), task_id, "task")

def get_reputation_history(user_id: str, limit=50) -> list:
    return fetchall("""SELECT event_type, points, ref_type, created_at
                       FROM reputation_events WHERE user_id=?
                       ORDER BY created_at DESC LIMIT ?""", (user_id, limit))

def check_streak_milestones(user_id: str):
    """Award rep for streak milestones. Call after updating streak."""
    user = fetchone("SELECT streak_current FROM users WHERE id=?", (user_id,))
    if not user: return
    streak = user["streak_current"]
    milestones = {7:"streak_7", 30:"streak_30", 100:"streak_100"}
    for days, event in milestones.items():
        if streak == days:
            already = fetchone("""SELECT id FROM reputation_events
                                  WHERE user_id=? AND event_type=? LIMIT 1""", (user_id, event))
            if not already:
                award_reputation(user_id, event, POINTS[event])

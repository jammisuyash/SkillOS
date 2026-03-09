"""community/service.py — Discussion forums, replies, upvotes, mentorship."""
import uuid
from skillos.db.database import fetchone, fetchall, transaction
from skillos.shared.exceptions import ValidationError
from skillos.shared.utils import utcnow_iso

MAX_TITLE = 200
MAX_BODY  = 10000

def list_discussions(task_id=None, limit=30, offset=0) -> list:
    if task_id:
        rows = fetchall("""
            SELECT d.*, u.display_name, u.username, u.avatar_url,
                   (SELECT COUNT(*) FROM discussion_replies WHERE discussion_id=d.id) AS reply_count
            FROM discussions d JOIN users u ON u.id=d.user_id
            WHERE d.task_id=? ORDER BY d.is_pinned DESC, d.upvotes DESC, d.created_at DESC
            LIMIT ? OFFSET ?
        """, (task_id, limit, offset))
    else:
        rows = fetchall("""
            SELECT d.*, u.display_name, u.username, u.avatar_url,
                   (SELECT COUNT(*) FROM discussion_replies WHERE discussion_id=d.id) AS reply_count
            FROM discussions d JOIN users u ON u.id=d.user_id
            ORDER BY d.is_pinned DESC, d.created_at DESC LIMIT ? OFFSET ?
        """, (limit, offset))
    return [dict(r) for r in rows]

def get_discussion(disc_id: str) -> dict | None:
    d = fetchone("""
        SELECT d.*, u.display_name, u.username, u.avatar_url
        FROM discussions d JOIN users u ON u.id=d.user_id WHERE d.id=?
    """, (disc_id,))
    if not d: return None
    replies = fetchall("""
        SELECT r.*, u.display_name, u.username, u.avatar_url
        FROM discussion_replies r JOIN users u ON u.id=r.user_id
        WHERE r.discussion_id=? ORDER BY r.is_accepted DESC, r.upvotes DESC, r.created_at ASC
    """, (disc_id,))
    return {**dict(d), "replies": [dict(r) for r in replies]}

def create_discussion(user_id: str, title: str, body: str, task_id=None, is_solution=False) -> dict:
    title = title.strip(); body = body.strip()
    if not title or len(title) > MAX_TITLE: raise ValidationError(f"Title must be 1-{MAX_TITLE} chars")
    if not body  or len(body)  > MAX_BODY:  raise ValidationError(f"Body must be 1-{MAX_BODY} chars")
    disc_id = str(uuid.uuid4())
    with transaction() as db:
        db.execute("""INSERT INTO discussions (id,user_id,task_id,title,body,is_solution)
                      VALUES (?,?,?,?,?,?)""",
                   (disc_id, user_id, task_id, title, body, 1 if is_solution else 0))
    try:
        from skillos.reputation.service import award_reputation
        award_reputation(user_id, "post_discussion", 2, disc_id, "discussion")
    except Exception: pass
    return get_discussion(disc_id)

def add_reply(user_id: str, disc_id: str, body: str) -> dict:
    body = body.strip()
    if not body or len(body) > MAX_BODY: raise ValidationError(f"Reply must be 1-{MAX_BODY} chars")
    d = fetchone("SELECT id, is_locked FROM discussions WHERE id=?", (disc_id,))
    if not d:           raise ValidationError("Discussion not found")
    if d["is_locked"]:  raise ValidationError("This discussion is locked")
    reply_id = str(uuid.uuid4())
    with transaction() as db:
        db.execute("INSERT INTO discussion_replies (id,discussion_id,user_id,body) VALUES (?,?,?,?)",
                   (reply_id, disc_id, user_id, body))
    try:
        from skillos.reputation.service import award_reputation
        award_reputation(user_id, "post_reply", 1, reply_id, "reply")
    except Exception: pass
    return fetchone("SELECT * FROM discussion_replies WHERE id=?", (reply_id,))

def vote(user_id: str, target_type: str, target_id: str, vote: int):
    if target_type not in ("discussion","reply"): raise ValidationError("Invalid target type")
    if vote not in (1,-1): raise ValidationError("Vote must be 1 or -1")
    existing = fetchone("SELECT id, vote FROM discussion_votes WHERE user_id=? AND target_type=? AND target_id=?",
                        (user_id, target_type, target_id))
    with transaction() as db:
        if existing:
            if existing["vote"] == vote:
                db.execute("DELETE FROM discussion_votes WHERE id=?", (existing["id"],))
                delta = -vote
            else:
                db.execute("UPDATE discussion_votes SET vote=? WHERE id=?", (vote, existing["id"]))
                delta = vote * 2
        else:
            db.execute("INSERT INTO discussion_votes (id,user_id,target_type,target_id,vote) VALUES (?,?,?,?,?)",
                       (str(uuid.uuid4()), user_id, target_type, target_id, vote))
            delta = vote
        table = "discussions" if target_type == "discussion" else "discussion_replies"
        db.execute(f"UPDATE {table} SET upvotes=upvotes+? WHERE id=?", (delta, target_id))

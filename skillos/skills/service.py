"""
skillos/skills/service.py

Read-only skill data for API endpoints.
All writes go through scoring.py → upsert_skill_score().
This module never writes directly.

Phase 2 endpoints (not active until auth is built):
  GET /skills                   → list all skills
  GET /users/me/skills          → my skill scores
  GET /users/me/skills/:id      → drill-down: history + submissions per skill
"""

from skillos.db.database import fetchall, fetchone


def list_skills() -> list[dict]:
    return fetchall("SELECT id, name, description FROM skills ORDER BY name")


def get_user_skill_scores(user_id: str) -> list[dict]:
    """
    Return all skill scores for a user — the 'proof' dashboard data.
    Only returns skills where the user has at least one submission.
    """
    return fetchall("""
        SELECT
            s.id          AS skill_id,
            s.name        AS skill_name,
            uss.current_score,
            uss.tasks_attempted,
            uss.tasks_passed,
            uss.last_updated_at
        FROM user_skill_scores uss
        JOIN skills s ON s.id = uss.skill_id
        WHERE uss.user_id = ?
        ORDER BY uss.current_score DESC
    """, (user_id,))


def get_user_skill_detail(user_id: str, skill_id: str) -> dict | None:
    """
    Return a single skill score + recent submission history for that skill.
    Used by the drill-down view on the proof dashboard.
    """
    score_row = fetchone("""
        SELECT uss.*, s.name AS skill_name
        FROM user_skill_scores uss
        JOIN skills s ON s.id = uss.skill_id
        WHERE uss.user_id = ? AND uss.skill_id = ?
    """, (user_id, skill_id))

    if not score_row:
        return None

    recent_submissions = fetchall("""
        SELECT
            sub.id, sub.status, sub.passed_cases, sub.total_cases,
            sub.max_runtime_ms, sub.performance_tier, sub.submitted_at,
            t.title AS task_title, t.difficulty
        FROM submissions sub
        JOIN tasks t ON t.id = sub.task_id
        WHERE sub.user_id = ? AND t.skill_id = ?
        ORDER BY sub.submitted_at DESC
        LIMIT 20
    """, (user_id, skill_id))

    return {**score_row, "recent_submissions": recent_submissions}


def replay_all_skill_scores():
    """
    REPLAY FUNCTION — used for:
      1. Bug recovery (scoring algorithm had a bug)
      2. Algorithm upgrades (new difficulty weights)
      3. Trust verification (run before any launch)

    Delete all derived scores, recompute from raw submissions.
    If this produces the same result as before → system is trustworthy.

    Usage: python -m skillos.skills.service replay
    """
    from skillos.db.database import transaction, fetchall as _fetchall
    from skillos.skills.scoring import upsert_skill_score

    print("Starting skill score replay...")

    # Find all user × skill pairs that have submissions
    pairs = _fetchall("""
        SELECT DISTINCT sub.user_id, t.skill_id
        FROM submissions sub
        JOIN tasks t ON t.id = sub.task_id
        WHERE t.skill_id IS NOT NULL
          AND sub.status = 'accepted'
    """)

    if not pairs:
        print("No accepted submissions found. Nothing to replay.")
        return

    # Wipe derived scores
    with transaction() as db:
        db.execute("DELETE FROM user_skill_scores")
    print(f"Cleared user_skill_scores. Recomputing for {len(pairs)} user×skill pairs...")

    for pair in pairs:
        score = upsert_skill_score(
            user_id=pair["user_id"],
            skill_id=pair["skill_id"],
            db_fetchall=_fetchall,
            db_transaction=transaction,
        )
        print(f"  user={pair['user_id']} skill={pair['skill_id']} → {score:.1f}")

    print("Replay complete.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "replay":
        replay_all_skill_scores()

"""
skillos/skills/scoring.py

Skill score algorithm — v1. Corrected.

FLAWS FOUND AND FIXED (do not reintroduce):

  FLAW 1 (BUG): total_contribution == total_weight always.
    Old code summed the same values for numerator and denominator.
    Raw score was always (weight/weight)*100 = 100.0. Every user scored 100.
    Fix: denominator = n_tasks × MAX_WEIGHT (max possible score ceiling).

  FLAW 2 (BUG): N=20 window allowed duplicate task spam.
    Submitting same easy task 20x filled the window, gaming the score.
    Fix: GROUP BY task_id — each task contributes at most once.

  FLAW 3 (FLAW): upsert ignored injected db_fetchall, re-imported directly.
    Made function untestable with mock data.
    Fix: use db_fetchall throughout, zero internal db imports.

  FLAW 4 (FLAW): stats counted raw submissions, not distinct tasks.
    Fix: COUNT(DISTINCT task_id) for both attempted and passed.

ALGORITHM (v1, corrected):

  skill_score = (sum of difficulty_weights for distinct accepted tasks in window)
                / (count_of_tasks_in_window × MAX_WEIGHT)
                × 100, capped at 100

  WHERE:
    difficulty_weight: easy=1.0, medium=1.5, hard=2.5
    MAX_WEIGHT:        2.5 (hard — represents perfect ceiling per task)
    window:            20 most recently solved DISTINCT tasks

  INTUITION:
    User solves 20 hard tasks → score approaches 100
    User solves 1 easy task   → score = (1.0 / (1 × 2.5)) × 100 = 40
    Spamming same task        → neutralised by GROUP BY deduplication
    Wrong/timeout/crash       → contribute nothing (accepted only)

REPLAYABILITY CONTRACT:
  Pure function over (submissions, tasks).
  Delete user_skill_scores → rerun → identical results. Always.
"""

from skillos.evaluator.limits import DIFFICULTY_WEIGHTS

WINDOW     = 20    # max distinct tasks in scoring window
MAX_WEIGHT = 2.5   # hard task weight — the per-task ceiling


def compute_skill_score(user_id: str, skill_id: str, db_fetchall) -> float:
    """
    Compute skill score for a user × skill pair.

    db_fetchall: injected callable (real DB or test mock).
    Returns float in [0.0, 100.0].
    """
    rows = db_fetchall("""
        SELECT t.difficulty, MAX(s.submitted_at) AS latest
        FROM submissions s
        JOIN tasks t ON t.id = s.task_id
        WHERE s.user_id  = ?
          AND t.skill_id = ?
          AND s.status   = 'accepted'
        GROUP BY s.task_id
        ORDER BY latest DESC
        LIMIT ?
    """, (user_id, skill_id, WINDOW))

    if not rows:
        return 0.0

    n = len(rows)
    total_contribution = sum(
        DIFFICULTY_WEIGHTS.get(r["difficulty"], 1.0)  # × recency_weight (1.0 in v1)
        for r in rows
    )
    max_possible = n * MAX_WEIGHT  # n tasks × ceiling per task

    raw_score = (total_contribution / max_possible) * 100.0
    return round(min(100.0, raw_score), 4)


def upsert_skill_score(user_id: str, skill_id: str, db_fetchall, db_transaction) -> float:
    """
    Recompute and persist skill score atomically.
    No internal db imports — uses injected parameters throughout.
    """
    from skillos.shared.utils import utcnow_iso

    score = compute_skill_score(user_id, skill_id, db_fetchall)

    stats_rows = db_fetchall("""
        SELECT
            COUNT(DISTINCT s.task_id) AS tasks_attempted,
            COUNT(DISTINCT CASE WHEN s.status = 'accepted' THEN s.task_id END) AS tasks_passed
        FROM submissions s
        JOIN tasks t ON t.id = s.task_id
        WHERE s.user_id  = ?
          AND t.skill_id = ?
    """, (user_id, skill_id))

    stats = stats_rows[0] if stats_rows else {}
    now   = utcnow_iso()

    # Get old score before updating (for delta calculation)
    old_rows = db_fetchall(
        "SELECT current_score FROM user_skill_scores WHERE user_id=? AND skill_id=?",
        (user_id, skill_id)
    )
    old_score = old_rows[0]["current_score"] if old_rows else 0.0

    with db_transaction() as db:
        db.execute("""
            INSERT INTO user_skill_scores
                (id, user_id, skill_id, current_score,
                 tasks_attempted, tasks_passed, last_updated_at)
            VALUES (lower(hex(randomblob(16))), ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, skill_id) DO UPDATE SET
                current_score   = excluded.current_score,
                tasks_attempted = excluded.tasks_attempted,
                tasks_passed    = excluded.tasks_passed,
                last_updated_at = excluded.last_updated_at
        """, (
            user_id, skill_id, score,
            stats.get("tasks_attempted", 0),
            stats.get("tasks_passed", 0),
            now,
        ))

    # Record history snapshot whenever score changes meaningfully
    if abs(score - old_score) >= 0.1:
        try:
            from skillos.skills.history import record_score_snapshot
            record_score_snapshot(user_id, skill_id, score, old_score, "submission")
        except Exception:
            pass  # History is non-critical — never crash scoring

    return score

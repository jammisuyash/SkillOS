"""
submissions/service.py

The submission lifecycle. This is Phase 1's only job.

STATE MACHINE:
    pending → accepted
    pending → wrong_answer
    pending → runtime_error
    pending → timeout
    pending → crash

Rules:
  - pending is a transition state, not a resting state
  - Terminal states are immutable (WHERE status = 'pending' guard)
  - All writes to submissions go through this module
  - No other module may write submission state directly
"""

import uuid
import datetime
from skillos.shared.utils import utcnow_iso, utcnow
from skillos.shared.logger import get_logger
_log = get_logger("submissions")
from skillos.db.database import get_db, transaction, fetchone, fetchall, execute
from skillos.shared.exceptions import ValidationError, TaskNotPublishedError, UnsupportedLanguageError


# ─────────────────────────────────────────────────────────────────────────────
# READ
# ─────────────────────────────────────────────────────────────────────────────

def get_submission(submission_id: str) -> dict | None:
    """
    Fetch a submission by ID.
    Returns the full row including status, results, samples.
    Used by GET /submission/{id} for polling.
    """
    return fetchone(
        "SELECT * FROM submissions WHERE id = ?",
        (submission_id,)
    )


def get_task_with_test_cases(task_id: str) -> tuple[dict | None, list[dict]]:
    """
    Fetch task metadata + all test cases ordered by ordinal.
    Returns (task, test_cases) — both needed before evaluation.
    """
    task = fetchone(
        "SELECT * FROM tasks WHERE id = ? AND is_published = 1",
        (task_id,)
    )
    if not task:
        return None, []

    test_cases = fetchall(
        "SELECT * FROM test_cases WHERE task_id = ? ORDER BY ordinal ASC",
        (task_id,)
    )
    return task, test_cases


# ─────────────────────────────────────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────────────────────────────────────

def create_submission(user_id: str, task_id: str, code: str, language: str = "python") -> dict:
    """
    Create a submission record in 'pending' state.
    Returns the created submission dict immediately.

    The caller (API handler) returns this to the client as 202 Accepted.
    The evaluator worker picks it up asynchronously.

    NOTE: We validate the task exists here before creating the record.
    A pending submission for a non-existent task is an inconsistent state.
    """
    task, _ = get_task_with_test_cases(task_id)
    if not task:
        raise TaskNotPublishedError(task_id)

    if language != "python":
        raise UnsupportedLanguageError(language)

    MAX_CODE_BYTES = 64 * 1024  # 64KB — mirrors api/app.py guard
    if len(code.encode("utf-8")) > MAX_CODE_BYTES:
        raise ValidationError(f"Code exceeds maximum length ({MAX_CODE_BYTES // 1024}KB)")

    submission_id   = str(uuid.uuid4())
    submitted_at    = utcnow_iso()

    with transaction() as db:
        db.execute("""
            INSERT INTO submissions
                (id, user_id, task_id, code, language, status, submitted_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, (submission_id, user_id, task_id, code, language, submitted_at))

    return get_submission(submission_id)


# ─────────────────────────────────────────────────────────────────────────────
# PERSIST EVALUATION RESULT — THE ATOMIC CORE
# ─────────────────────────────────────────────────────────────────────────────

def persist_evaluation(submission_id: str, eval_result: dict) -> bool:
    """
    Atomically transition submission from pending → terminal state.

    ATOMICITY RULE:
        All fields (status, metrics, samples, evaluated_at) are written
        in a single transaction. There is no partial state.

    IDEMPOTENCY GUARD:
        WHERE status = 'pending' ensures:
          - Double evaluation cannot overwrite a terminal state
          - If zombie cleaner already marked it 'crash', this no-ops
          - Returns False to signal the write was skipped

    INVARIANT:
        After this function returns (True or False), the submission
        is in a terminal state or was already in one. Never pending.

    Returns:
        True  → written successfully
        False → skipped (already in terminal state)
    """
    evaluated_at = utcnow_iso()

    with transaction() as db:
        cursor = db.execute("""
            UPDATE submissions SET
                status           = ?,
                passed_cases     = ?,
                total_cases      = ?,
                max_runtime_ms   = ?,
                max_memory_kb    = ?,
                performance_tier = ?,
                stdout_sample    = ?,
                stderr_sample    = ?,
                evaluated_at     = ?
            WHERE id = ?
              AND status = 'pending'
        """, (
            eval_result["status"],
            eval_result["passed_cases"],
            eval_result["total_cases"],
            eval_result["max_runtime_ms"],
            eval_result["max_memory_kb"],
            eval_result["performance_tier"],
            eval_result["stdout_sample"][:2048] if eval_result["stdout_sample"] else None,
            eval_result["stderr_sample"][:2048] if eval_result["stderr_sample"] else None,
            evaluated_at,
            submission_id,
        ))
        written = cursor.rowcount == 1

    return written


# ─────────────────────────────────────────────────────────────────────────────
# ZOMBIE CLEANER
# ─────────────────────────────────────────────────────────────────────────────

ZOMBIE_THRESHOLD_SECONDS = 60

def clean_zombie_submissions(logger=None) -> int:
    """
    Find submissions stuck in 'pending' and mark them 'crash'.

    RULES (non-negotiable):
      1. Never re-evaluates — retries hide bugs
      2. Only writes 'crash' — never infers a result
      3. Only touches submissions older than ZOMBIE_THRESHOLD_SECONDS
      4. The idempotency guard (AND status = 'pending') makes this safe
         to run concurrently if needed

    Returns count of zombies found (for monitoring).
    A burst of zombies = evaluator is crashing. Investigate immediately.
    One occasional zombie = normal edge case (server restart, etc.)
    """
    cutoff = (
        utcnow() -
        datetime.timedelta(seconds=ZOMBIE_THRESHOLD_SECONDS)
    ).isoformat()

    zombies = fetchall("""
        SELECT id, user_id, task_id, submitted_at
        FROM submissions
        WHERE status = 'pending'
          AND submitted_at < ?
    """, (cutoff,))

    if not zombies:
        return 0

    evaluated_at = utcnow_iso()

    for z in zombies:
        if logger:
            logger(f"ZOMBIE_SUBMISSION id={z['id']} user={z['user_id']} "
                   f"task={z['task_id']} submitted_at={z['submitted_at']}")
        _log.warning("zombie.found",
                         submission_id=z['id'],
                         user_id=z['user_id'],
                         task_id=z['task_id'],
                         submitted_at=z['submitted_at'])

    zombie_ids = [z["id"] for z in zombies]

    with transaction() as db:
        for zid in zombie_ids:
            db.execute("""
                UPDATE submissions SET
                    status        = 'crash',
                    evaluated_at  = ?,
                    stderr_sample = 'Evaluation timed out — system error. Please resubmit.'
                WHERE id = ?
                  AND status = 'pending'
            """, (evaluated_at, zid))
            # AND status = 'pending': idempotency guard
            # If something else already resolved it, this no-ops cleanly

    return len(zombies)

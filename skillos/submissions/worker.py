"""
submissions/worker.py

The evaluator worker: polls pending submissions, evaluates, persists.

DESIGN:
  - Single background thread (MVP — no queue infrastructure needed)
  - Polls every POLL_INTERVAL_S seconds
  - Can be killed at any point without corrupting DB:
      If killed after evaluate() but before persist_evaluation():
          → submission stays pending
          → zombie cleaner marks it crash after 60s
          → honest outcome, no partial state
  - If killed mid-evaluate():
      → subprocess is in a separate process, sandbox cleanup runs in finally
      → submission stays pending
      → zombie cleaner catches it

PROCESS MODEL:
    API process                Worker thread (same process, MVP)
         │                           │
    POST /submit                     │
    creates pending record ──────────┤
    returns 202                      │
                                     │ polls every N seconds
                                     │ fetches pending submissions
                                     │ calls evaluator.runner.evaluate()
                                     │ calls persist_evaluation() atomically
                                     │ emits submission_evaluated event
                                     │ (skills module reacts)
"""

import time
import threading
import traceback

from skillos.shared.logger import get_logger
log = get_logger("worker")

from skillos.submissions.service import (
    get_task_with_test_cases,
    persist_evaluation,
    fetchall,
)
from skillos.submissions import events
from skillos.evaluator.runner import evaluate

POLL_INTERVAL_S = 2    # check for pending submissions every 2 seconds
MAX_BATCH_SIZE  = 5    # process at most 5 submissions per poll cycle


def _fetch_pending_batch() -> list[dict]:
    """
    Fetch a batch of pending submissions, oldest first.
    FIFO ordering: earlier submissions are evaluated first.
    Batch limit prevents a burst from monopolising the worker.
    """
    return fetchall("""
        SELECT id, user_id, task_id, code, language, mcq_answer
        FROM submissions
        WHERE status = 'pending'
        ORDER BY submitted_at ASC
        LIMIT ?
    """, (MAX_BATCH_SIZE,))


def _process_one(submission: dict):
    """
    Evaluate a single submission and persist the result atomically.

    If anything throws here (bug in evaluator, DB error, etc.):
      - Exception is caught at the worker loop level
      - Submission stays pending
      - Zombie cleaner handles it
      - Worker continues with next submission

    This function NEVER raises to the caller.
    """
    task, test_cases = get_task_with_test_cases(submission["task_id"])
    if not task:
        # Task was unpublished between submission and evaluation.
        # Mark crash — honest outcome.
        persist_evaluation(submission["id"], {
            "status": "crash",
            "passed_cases": 0,
            "total_cases": 0,
            "max_runtime_ms": 0,
            "max_memory_kb": 0,
            "performance_tier": None,
            "stdout_sample": "",
            "stderr_sample": "Task no longer available.",
        })
        return

    # ── Route by problem type ──────────────────────────────────────────────
    problem_type = task.get("problem_type", "coding")

    if problem_type == "mcq":
        from skillos.evaluator.multi_type import evaluate_mcq
        try:
            mcq_answer = int(submission["code"])
        except (ValueError, TypeError):
            mcq_answer = -1
        eval_result = evaluate_mcq(task, mcq_answer)

    elif problem_type == "system_design":
        from skillos.evaluator.multi_type import evaluate_system_design
        eval_result = evaluate_system_design(task, submission["code"])

    else:
        # coding + debugging both go through sandbox
        eval_result = evaluate(
            code=submission["code"],
            language=submission["language"],
            test_cases=[dict(tc) for tc in test_cases],
            limits={
                "time_ms":    task["time_limit_ms"],
                "memory_kb":  task["memory_limit_kb"],
            },
        )

    written = persist_evaluation(submission["id"], eval_result)

    if written:
        # Only emit event if we actually wrote — don't double-emit
        events.emit_submission_evaluated({
            "submission_id": submission["id"],
            "user_id":       submission["user_id"],
            "task_id":       submission["task_id"],
            "skill_id":      task.get("skill_id"),
            "status":        eval_result["status"],
            "passed_cases":  eval_result["passed_cases"],
            "total_cases":   eval_result["total_cases"],
        })


def _worker_loop(stop_event: threading.Event, logger=None):
    """
    Main worker loop. Runs until stop_event is set.
    Errors on individual submissions are caught and logged — they never
    stop the worker from processing subsequent submissions.
    """
    from skillos.shared.logger import get_logger
    _log = get_logger("worker")

    def log(event, **kwargs):
        _log.info(event, **kwargs)

    log("worker.started")
    while not stop_event.is_set():
        try:
            batch = _fetch_pending_batch()
            for submission in batch:
                if stop_event.is_set():
                    break
                try:
                    _process_one(submission)
                except Exception as e:
                    log(f"ERROR processing submission {submission['id']}: "
                        f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
                    # Submission stays pending → zombie cleaner handles it
        except Exception as e:
            _log.error('worker.poll_error', error=type(e).__name__, detail=str(e))

        stop_event.wait(timeout=POLL_INTERVAL_S)

    log("Worker stopped")


class EvaluatorWorker:
    """
    Manages the background worker thread lifecycle.

    Usage:
        worker = EvaluatorWorker()
        worker.start()
        # ... app runs ...
        worker.stop()
    """

    def __init__(self, logger=None):
        self._stop_event = threading.Event()
        self._thread     = None
        self._logger     = logger

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=_worker_loop,
            args=(self._stop_event, self._logger),
            daemon=True,   # dies when main process dies (no orphan threads)
            name="evaluator-worker",
        )
        self._thread.start()

    def stop(self, timeout: float = 10.0):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

"""
submissions/events.py

The event dispatcher. This is the only place in the codebase where
submissions is coupled to downstream consumers.

PATTERN:
    submissions emits → skills (and future: badges, analytics) reacts

    submissions never imports skills.
    skills registers itself at startup.
    This file is the seam.

USAGE:
    # At app startup (main.py):
    from skillos.submissions import events
    from skillos.skills.handlers import handle_submission_evaluated
    events.register(handle_submission_evaluated)

    # In evaluator worker, after persist_evaluation():
    events.emit_submission_evaluated({ submission_id, user_id, ... })

MVP NOTE:
    Handlers are called synchronously. This is fine — skill score
    recalculation is fast (one small SQL query).
    Future: move to async queue when handler latency matters.
"""

_handlers: list = []


def register(handler_fn):
    """Register a function to be called on submission_evaluated events."""
    _handlers.append(handler_fn)


def emit_submission_evaluated(event: dict):
    """
    Dispatch submission_evaluated to all registered handlers.

    EVENT SHAPE:
        submission_id:  str
        user_id:        str
        task_id:        str
        skill_id:       str | None
        status:         str  (accepted | wrong_answer | timeout | runtime_error | crash)
        passed_cases:   int
        total_cases:    int

    Handler errors are caught individually — one failing handler
    must not prevent others from running.
    """
    for handler in _handlers:
        try:
            handler(event)
        except Exception as e:
            # Log but never propagate — submission lifecycle is unaffected
            print(f"[events] handler {handler.__name__} failed: {e}")

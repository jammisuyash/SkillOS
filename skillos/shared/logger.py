"""
skillos/shared/logger.py

Structured logger for SkillOS. Replaces all print() calls.

WHY STRUCTURED LOGGING:
  print("Worker started") → useless in production
  log.info("worker.started", submission_id=sid) → searchable, filterable, alertable

FORMAT:
  [TIMESTAMP] LEVEL  component  message  key=value key=value

USAGE:
  from skillos.shared.logger import get_logger
  log = get_logger("worker")
  log.info("submission.evaluating", submission_id=sub_id, task_id=task_id)
  log.error("submission.failed", submission_id=sub_id, error=str(e))

THREAD SAFETY: Python's logging module is thread-safe. All handlers use locks.

PRODUCTION UPGRADE (Phase 4):
  Replace StreamHandler with a JSON handler:
    import json
    class JsonHandler(logging.StreamHandler):
        def emit(self, record):
            print(json.dumps({...record fields...}))
  This makes logs ingestible by Datadog, Grafana Loki, CloudWatch.
"""

import logging
import sys
from datetime import datetime, timezone

_LOGGERS: dict = {}

LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def _setup_root():
    root = logging.getLogger("skillos")
    if root.handlers:
        return  # already configured
    root.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root.addHandler(handler)
    root.propagate = False


def get_logger(component: str) -> "StructuredLogger":
    """
    Get a named logger for a component.
    Usage: log = get_logger("worker")
    """
    _setup_root()
    if component not in _LOGGERS:
        _LOGGERS[component] = StructuredLogger(component)
    return _LOGGERS[component]


class StructuredLogger:
    """
    Thin wrapper over stdlib logging that supports key=value context.

    log.info("worker.started")
    log.info("submission.evaluating", submission_id="abc-123", task_id="task-001")
    log.error("sandbox.failed", submission_id="abc", error="OOM", exit_code=-9)
    log.warning("zombie.found", submission_id="abc", age_seconds=90)
    """

    def __init__(self, component: str):
        self._logger = logging.getLogger(f"skillos.{component}")

    def _fmt(self, event: str, **kwargs) -> str:
        if not kwargs:
            return event
        pairs = " ".join(f"{k}={v!r}" for k, v in kwargs.items())
        return f"{event}  {pairs}"

    def debug(self, event: str, **kwargs):
        self._logger.debug(self._fmt(event, **kwargs))

    def info(self, event: str, **kwargs):
        self._logger.info(self._fmt(event, **kwargs))

    def warning(self, event: str, **kwargs):
        self._logger.warning(self._fmt(event, **kwargs))

    def error(self, event: str, **kwargs):
        self._logger.error(self._fmt(event, **kwargs))

    def critical(self, event: str, **kwargs):
        self._logger.critical(self._fmt(event, **kwargs))

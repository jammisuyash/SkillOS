"""
skillos/main.py

Application entrypoint. Wires all modules together.

STARTUP SEQUENCE:
  1. Validate config (SECRET_KEY guard for non-dev)
  2. Run DB migrations (idempotent)
  3. Register event handlers (based on phase flags)
  4. Start evaluator worker (background thread)
  5. Start zombie cleaner (background thread)
  6. Start HTTP server

SHUTDOWN: SIGINT / SIGTERM → graceful: stop worker, close server.
"""

import sys
import signal
import threading

from skillos.config import config
from skillos.shared.logger import get_logger

log = get_logger("main")


def _run_migrations():
    from skillos.db.migrations import run_migrations
    log.info("startup.migrations_start")
    run_migrations()
    log.info("startup.migrations_done")
    # Seed task library — idempotent, runs every startup
    from skillos.db.seed import seed
    seed()
    log.info("startup.tasks_seeded")

    # Seed supplementary content — idempotent
    try:
        from skillos.learning.service import seed_learning_paths
        seed_learning_paths()
        log.info("startup.learning_paths_seeded")
    except Exception as e:
        log.warning("startup.learning_paths_seed_failed", error=str(e))

    try:
        from skillos.projects.service import seed_project_templates
        seed_project_templates()
        log.info("startup.project_templates_seeded")
    except Exception as e:
        log.warning("startup.project_templates_seed_failed", error=str(e))

    try:
        from skillos.contests.service import seed_daily_challenge, sync_contest_statuses, seed_sample_contests
        seed_sample_contests()
        seed_daily_challenge()
        sync_contest_statuses()
        log.info("startup.contests_seeded")
    except Exception as e:
        log.warning("startup.contests_seed_failed", error=str(e))


def _register_event_handlers():
    from skillos.submissions import events
    if config.PHASE_SKILLS_ENABLED:
        from skillos.skills.handlers import handle_submission_evaluated
        events.register(handle_submission_evaluated)
        log.info("startup.handler_registered", handler="skills.handle_submission_evaluated")
    else:
        log.info("startup.skills_disabled",
                 reason="PHASE_SKILLS not enabled — skill scoring inactive")


def _start_worker():
    from skillos.submissions.worker import EvaluatorWorker
    worker = EvaluatorWorker()  # worker now uses its own structured logger
    worker.start()
    log.info("startup.worker_started")
    return worker


def _start_zombie_cleaner(stop_event: threading.Event):
    from skillos.submissions.service import clean_zombie_submissions

    def loop():
        while not stop_event.is_set():
            stop_event.wait(timeout=config.ZOMBIE_INTERVAL_S)
            if stop_event.is_set():
                break
            count = clean_zombie_submissions()
            if count > 0:
                log.warning("zombie.cleaned", count=count)

    t = threading.Thread(target=loop, daemon=True, name="zombie-cleaner")
    t.start()
    log.info("startup.zombie_cleaner_started",
             interval_s=config.ZOMBIE_INTERVAL_S,
             threshold_s=config.ZOMBIE_THRESHOLD_S)
    return t


def main():
    log.info("startup.begin",
             host=config.HOST,
             port=config.PORT,
             phase_auth=config.PHASE_AUTH_ENABLED,
             phase_skills=config.PHASE_SKILLS_ENABLED)

    _run_migrations()
    _register_event_handlers()

    stop_event = threading.Event()
    worker     = _start_worker()
    _start_zombie_cleaner(stop_event)

    from http.server import HTTPServer
    from skillos.api.app import SkillOSHandler

    server = HTTPServer((config.HOST, config.PORT), SkillOSHandler)

    log.info("startup.ready",
             url=f"http://{config.HOST}:{config.PORT}",
             endpoints=["GET /health",
                        "POST /auth/register",
                        "POST /auth/login",
                        "POST /submit",
                        "GET /submission/{id}",
                        "GET /users/me/skills",
                        "GET /users/me/skills/{id}"])

    def shutdown(signum, frame):
        log.info("shutdown.begin", signal=signum)
        stop_event.set()
        worker.stop(timeout=10)
        server.server_close()
        log.info("shutdown.complete")
        sys.exit(0)

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    server.serve_forever()


if __name__ == "__main__":
    main()

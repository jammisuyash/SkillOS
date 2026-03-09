"""
jobs/queue.py

Async job queue abstraction.

Dev mode:  in-process thread pool (current behaviour, zero deps)
Prod mode: Redis + Celery (set REDIS_URL env var)

MIGRATION TO REDIS/CELERY:
  1. pip install celery[redis]
  2. Set REDIS_URL=redis://localhost:6379/0
  3. Run worker: celery -A skillos.jobs.queue worker --loglevel=info
  4. Done — same .enqueue() API, jobs run in separate processes

JOB TYPES:
  - code_execution   (already works in thread; Redis allows horizontal scaling)
  - ranking_update   (recalculate leaderboard after contest)
  - notification     (send push/email notifications)
  - ai_review        (async AI code review — don't block the request)
  - cert_check       (check if user has earned a certification)
  - analytics_sync   (batch write analytics events)
"""
import os, json, threading, queue, traceback
from skillos.shared.logger import get_logger

log = get_logger("jobs")

REDIS_URL   = os.environ.get("REDIS_URL", "")
_USE_REDIS  = bool(REDIS_URL)

# ── In-process queue (dev / single-server mode) ───────────────────────────────
_q: queue.Queue = queue.Queue(maxsize=500)
_handlers: dict = {}


def register(job_type: str, handler):
    """Register a handler function for a job type."""
    _handlers[job_type] = handler
    log.info("jobs.handler_registered", job_type=job_type)


def enqueue(job_type: str, payload: dict, delay_seconds: int = 0) -> str:
    """
    Enqueue a background job.
    Returns a job_id string.

    In dev mode:  runs in a thread pool immediately.
    In prod mode: sends to Redis queue for Celery worker.
    """
    import uuid
    job_id = str(uuid.uuid4())
    job    = {"id": job_id, "type": job_type, "payload": payload}

    if _USE_REDIS:
        return _enqueue_redis(job, delay_seconds)
    else:
        return _enqueue_local(job, delay_seconds)


def _enqueue_local(job: dict, delay_seconds: int = 0) -> str:
    """Run job in a background thread."""
    def run():
        if delay_seconds:
            import time
            time.sleep(delay_seconds)
        handler = _handlers.get(job["type"])
        if not handler:
            log.warning("jobs.no_handler", job_type=job["type"])
            return
        try:
            handler(job["payload"])
            log.info("jobs.done", job_id=job["id"], job_type=job["type"])
        except Exception as e:
            log.error("jobs.failed", job_id=job["id"], error=str(e), tb=traceback.format_exc())

    t = threading.Thread(target=run, daemon=True, name=f"job-{job['type']}-{job['id'][:8]}")
    t.start()
    return job["id"]


def _enqueue_redis(job: dict, delay_seconds: int = 0) -> str:
    """Send job to Redis for Celery processing."""
    try:
        import redis
        r = redis.from_url(REDIS_URL)
        if delay_seconds:
            # Use Redis ZADD with future timestamp for delayed jobs
            import time
            r.zadd("skillos:delayed_jobs", {json.dumps(job): time.time() + delay_seconds})
        else:
            r.lpush(f"skillos:jobs:{job['type']}", json.dumps(job))
        log.info("jobs.enqueued_redis", job_id=job["id"], job_type=job["type"])
    except Exception as e:
        log.error("jobs.redis_enqueue_failed", error=str(e))
        # Fallback to local
        return _enqueue_local(job)
    return job["id"]


# ── Built-in job handlers ─────────────────────────────────────────────────────

def _handle_ranking_update(payload: dict):
    """Recalculate contest rankings after a submission."""
    contest_id = payload.get("contest_id")
    if not contest_id:
        return
    try:
        from skillos.contests.service import sync_contest_statuses
        sync_contest_statuses()
        log.info("jobs.ranking_updated", contest_id=contest_id)
    except Exception as e:
        log.warning("jobs.ranking_failed", error=str(e))


def _handle_cert_check(payload: dict):
    """Check if a user has earned a certification after a submission."""
    user_id = payload.get("user_id")
    if not user_id:
        return
    try:
        from skillos.certifications.service import auto_check_certifications
        issued = auto_check_certifications(user_id)
        if issued:
            log.info("jobs.certs_issued", user_id=user_id, count=len(issued))
    except Exception as e:
        log.warning("jobs.cert_check_failed", error=str(e))


def _handle_notification(payload: dict):
    """Create an in-app notification."""
    user_id = payload.get("user_id")
    title   = payload.get("title", "New notification")
    body    = payload.get("body", "")
    ntype   = payload.get("type", "system")
    if not user_id:
        return
    try:
        import uuid
        from skillos.db.database import get_db
        db = get_db()
        db.execute(
            "INSERT INTO notifications (id, user_id, type, title, body) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), user_id, ntype, title, body)
        )
        db.commit()
    except Exception as e:
        log.warning("jobs.notification_failed", error=str(e))


def _handle_analytics_event(payload: dict):
    """Batch-write an analytics event (future: stream to ClickHouse/BigQuery)."""
    log.info("jobs.analytics_event", event_type=payload.get("event_type"))


# Register default handlers
register("ranking_update",   _handle_ranking_update)
register("cert_check",       _handle_cert_check)
register("notification",     _handle_notification)
register("analytics_event",  _handle_analytics_event)

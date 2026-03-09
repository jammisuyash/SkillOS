"""
worker_celery.py

Celery task queue for background job processing.

REPLACES: threading-based EvaluatorWorker
ADVANTAGES:
  - Distributed across multiple machines
  - Retry on failure
  - Rate limiting
  - Priority queues
  - Real-time monitoring with Flower

SETUP:
  1. Start Redis: docker run -d -p 6379:6379 redis:alpine
  2. Start worker: celery -A skillos.worker_celery worker --loglevel=info
  3. Monitor: celery -A skillos.worker_celery flower (http://localhost:5555)

QUEUES:
  - evaluation: Code submission evaluation (high priority)
  - analytics:  Background analytics aggregation (low priority)
  - emails:     Notification emails (medium priority)
  - awards:     Badge/cert checking (low priority)
"""

import os
from celery import Celery
from celery.utils.log import get_task_logger

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# ── App ────────────────────────────────────────────────────────────────────────
celery_app = Celery(
    "skillos",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["skillos.worker_celery"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Queues
    task_queues={
        "evaluation": {"exchange": "evaluation", "routing_key": "evaluation"},
        "analytics":  {"exchange": "analytics",  "routing_key": "analytics"},
        "emails":     {"exchange": "emails",      "routing_key": "emails"},
        "awards":     {"exchange": "awards",      "routing_key": "awards"},
    },
    task_default_queue="evaluation",
    # Retry policy
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Rate limits
    task_annotations={
        "skillos.worker_celery.evaluate_submission": {"rate_limit": "100/m"},
        "skillos.worker_celery.send_notification_email": {"rate_limit": "60/m"},
    },
    # Result expiry
    result_expires=3600,  # 1 hour
    # Worker concurrency
    worker_prefetch_multiplier=1,  # Fair task distribution
)

log = get_task_logger(__name__)


# ── TASK: Evaluate code submission ─────────────────────────────────────────────
@celery_app.task(
    bind=True,
    name="skillos.worker_celery.evaluate_submission",
    max_retries=3,
    queue="evaluation",
    soft_time_limit=30,   # 30s soft kill (raises SoftTimeLimitExceeded)
    time_limit=35,        # 35s hard kill
)
def evaluate_submission(self, submission_id: str):
    """
    Evaluate a submitted code solution.
    Runs in isolated Docker container via EvaluatorWorker.
    """
    log.info(f"evaluate_submission.start sub_id={submission_id}")
    try:
        from skillos.submissions.worker import EvaluatorWorker
        worker = EvaluatorWorker()
        result = worker._process_one(submission_id)
        log.info(f"evaluate_submission.done sub_id={submission_id} status={result.get('status')}")
        return result
    except Exception as exc:
        log.error(f"evaluate_submission.failed sub_id={submission_id} error={exc}")
        # Retry with exponential backoff: 5s, 25s, 125s
        raise self.retry(exc=exc, countdown=5 ** (self.request.retries + 1))


# ── TASK: Award certifications ─────────────────────────────────────────────────
@celery_app.task(
    name="skillos.worker_celery.check_certifications",
    queue="awards",
    max_retries=2,
)
def check_certifications(user_id: str):
    """
    Check if user has unlocked any new certifications after a submission.
    Runs asynchronously to avoid blocking the submission response.
    """
    try:
        from skillos.certifications.service import check_and_award_certifications
        new_certs = check_and_award_certifications(user_id)
        if new_certs:
            log.info(f"check_certifications.awarded user_id={user_id} certs={[c['name'] for c in new_certs]}")
            # Queue notification email for each new cert
            for cert in new_certs:
                send_cert_notification.delay(user_id, cert["name"])
        return {"awarded": len(new_certs)}
    except Exception as exc:
        log.error(f"check_certifications.failed user_id={user_id} error={exc}")
        return {"error": str(exc)}


# ── TASK: Send notification email ──────────────────────────────────────────────
@celery_app.task(
    name="skillos.worker_celery.send_notification_email",
    queue="emails",
    max_retries=3,
)
def send_notification_email(user_id: str, subject: str, body: str):
    """Send a notification email to a user."""
    try:
        from skillos.db.database import fetchone
        user = fetchone("SELECT email, display_name FROM users WHERE id=?", (user_id,))
        if not user:
            return {"error": "User not found"}
        from skillos.auth.email_service import send_email
        send_email(user["email"], subject, body)
        log.info(f"send_notification_email.sent user_id={user_id} subject={subject}")
        return {"ok": True}
    except Exception as exc:
        log.error(f"send_notification_email.failed user_id={user_id} error={exc}")
        raise


@celery_app.task(name="skillos.worker_celery.send_cert_notification", queue="emails")
def send_cert_notification(user_id: str, cert_name: str):
    """Notify user they earned a new certification."""
    send_notification_email.delay(
        user_id,
        f"🎓 New Certification Earned: {cert_name}",
        f"Congratulations! You've earned the {cert_name} certification on SkillOS.\n\n"
        f"This verifies your skills to recruiters and companies on the platform.\n\n"
        f"View your profile to share your certification badge.\n\n"
        f"Keep coding! 🚀\n\n— The SkillOS Team"
    )


# ── TASK: Update analytics aggregates ─────────────────────────────────────────
@celery_app.task(
    name="skillos.worker_celery.update_analytics",
    queue="analytics",
)
def update_analytics():
    """
    Aggregate daily analytics data.
    Schedule with Celery Beat every hour.
    """
    try:
        from skillos.analytics.service import get_platform_stats
        stats = get_platform_stats()
        log.info(f"update_analytics.done users={stats.get('total_users')} subs={stats.get('total_submissions')}")
        return stats
    except Exception as exc:
        log.error(f"update_analytics.failed error={exc}")
        return {"error": str(exc)}


# ── TASK: Recalculate leaderboard ──────────────────────────────────────────────
@celery_app.task(
    name="skillos.worker_celery.recalculate_leaderboard",
    queue="analytics",
)
def recalculate_leaderboard():
    """Refresh leaderboard rankings. Run every 15 minutes."""
    try:
        from skillos.leaderboard.service import get_global_leaderboard
        lb = get_global_leaderboard(limit=100)
        log.info(f"recalculate_leaderboard.done entries={len(lb)}")
        return {"entries": len(lb)}
    except Exception as exc:
        log.error(f"recalculate_leaderboard.failed error={exc}")
        return {"error": str(exc)}


# ── TASK: Clean expired sessions ───────────────────────────────────────────────
@celery_app.task(
    name="skillos.worker_celery.cleanup_expired_sessions",
    queue="analytics",
)
def cleanup_expired_sessions():
    """Remove expired auth sessions. Run daily."""
    try:
        from skillos.db.database import get_db
        db = get_db()
        result = db.execute(
            "DELETE FROM user_sessions WHERE expires_at < datetime('now')"
        )
        db.commit()
        log.info("cleanup_expired_sessions.done")
        return {"ok": True}
    except Exception as exc:
        log.error(f"cleanup_expired_sessions.failed error={exc}")
        return {"error": str(exc)}


# ── Celery Beat schedule (periodic tasks) ────────────────────────────────────
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "update-analytics-hourly": {
        "task": "skillos.worker_celery.update_analytics",
        "schedule": crontab(minute=0),  # Every hour
    },
    "recalculate-leaderboard": {
        "task": "skillos.worker_celery.recalculate_leaderboard",
        "schedule": 900,  # Every 15 minutes
    },
    "cleanup-sessions-daily": {
        "task": "skillos.worker_celery.cleanup_expired_sessions",
        "schedule": crontab(hour=2, minute=0),  # 2 AM daily
    },
}

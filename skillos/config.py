"""
skillos/config.py

All configuration in one place. No config leaks into business logic.

Usage:
    from skillos.config import config
    db_path = config.DB_PATH

Twelve-Factor App principle: config comes from environment, not code.
Defaults are for local development only — never for production.
"""

import os


class Config:
    # ── Database ─────────────────────────────────────────────────────────────
    DB_PATH: str = os.environ.get("SKILLOS_DB_PATH", "/tmp/skillos_dev.db")

    # ── Server ────────────────────────────────────────────────────────────────
    HOST: str = os.environ.get("SKILLOS_HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("SKILLOS_PORT", "8000"))
    DEBUG: bool = os.environ.get("SKILLOS_DEBUG", "false").lower() == "true"

    # ── Evaluator ─────────────────────────────────────────────────────────────
    EVALUATOR_USER: str = os.environ.get("SKILLOS_EVAL_USER", "")
    # Empty = run as current user (dev only).
    # Production: set to a non-root username e.g. "skillos-eval"

    # ── Worker ────────────────────────────────────────────────────────────────
    WORKER_POLL_INTERVAL_S: int = int(os.environ.get("SKILLOS_POLL_INTERVAL", "2"))
    WORKER_BATCH_SIZE: int      = int(os.environ.get("SKILLOS_BATCH_SIZE", "5"))

    # ── Zombie Cleaner ────────────────────────────────────────────────────────
    ZOMBIE_THRESHOLD_S: int = int(os.environ.get("SKILLOS_ZOMBIE_THRESHOLD", "60"))
    ZOMBIE_INTERVAL_S: int  = int(os.environ.get("SKILLOS_ZOMBIE_INTERVAL", "60"))

    # ── Phase flags (what is intentionally not built yet) ────────────────────
    # These gates prevent accidentally enabling unbuilt features.
    PHASE_AUTH_ENABLED: bool        = os.environ.get("PHASE_AUTH", "true").lower() == "true"
    PHASE_SKILLS_ENABLED: bool      = os.environ.get("PHASE_SKILLS", "true").lower() == "true"
    PHASE_FRONTEND_ENABLED: bool    = os.environ.get("PHASE_FRONTEND", "true").lower() == "true"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # In production: set to your frontend domain e.g. "https://app.skillos.io"
    CORS_ORIGIN: str = os.environ.get("SKILLOS_CORS_ORIGIN", "*")


config = Config()

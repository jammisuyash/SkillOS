"""
skillos/api/app.py

HTTP API — Phase 2 hardened.

HARDENING APPLIED (from flaw audit):
  - Max body size: 512KB cap on all POST requests (prevents infinite body attacks)
  - Code length cap: 64KB max code string (enforced in create_submission too)
  - Request-ID header on every response (correlation for debugging)
  - /health endpoint (liveness probe for load balancers / uptime monitors)
  - Structured logging via shared.logger (replaces all print())

ENDPOINTS:
  Public:
    GET  /health
    POST /auth/register
    POST /auth/login

  Protected:
    POST /submit
    GET  /submission/{id}
    GET  /users/me/skills
    GET  /users/me/skills/{skill_id}
"""

import json
import re
import uuid
import threading

from skillos.config import config
from skillos.shared.logger import get_logger
from skillos.shared.exceptions import SkillOSError, ValidationError
from skillos.submissions.service import create_submission, get_submission
from skillos.submissions.worker import EvaluatorWorker

log = get_logger("api")

# ── Limits ────────────────────────────────────────────────────────────────────
MAX_BODY_BYTES = 512 * 1024   # 512 KB — largest legitimate submit is code + metadata
MAX_CODE_BYTES = 64  * 1024   # 64 KB  — no real solution needs more

# ── Route patterns (canonical — single source of truth) ────────────────────────
_HEALTH          = re.compile(r"^/health$")
_REGISTER        = re.compile(r"^/auth/register$")
_LOGIN           = re.compile(r"^/auth/login$")
_SUBMIT          = re.compile(r"^/submit$")
_SUBMISSION      = re.compile(r"^/submission/([a-f0-9-]{36})$")
_MY_SKILLS       = re.compile(r"^/users/me/skills$")
_MY_SKILL        = re.compile(r"^/users/me/skills/([a-zA-Z0-9_-]{1,64})$")
_MY_SUBS         = re.compile(r"^/users/me/submissions$")
_TASKS           = re.compile(r"^/tasks$")
_VERIFY_EMAIL    = re.compile(r"^/auth/verify-email$")
_FORGOT_PASSWORD = re.compile(r"^/auth/forgot-password$")
_RESET_PASSWORD  = re.compile(r"^/auth/reset-password$")
_GOOGLE_AUTH     = re.compile(r"^/auth/google$")
_CERT_CHECK      = re.compile(r"^/certifications/check$")
_MY_CERTS        = re.compile(r"^/users/me/certifications$")
_CERT_TYPES      = re.compile(r"^/certifications/types$")
_CERT_VERIFY     = re.compile(r"^/cert/([a-f0-9-]{36})$")
_SESSIONS        = re.compile(r"^/auth/sessions$")
_REVOKE_SESSION  = re.compile(r"^/auth/sessions/([a-f0-9-]{36})/revoke$")
_REVOKE_ALL      = re.compile(r"^/auth/sessions/revoke-all$")
_LOGIN_HISTORY   = re.compile(r"^/auth/login-history$")
_VERIFY_2FA      = re.compile(r"^/auth/2fa/verify$")
_SETUP_2FA_BEGIN = re.compile(r"^/auth/2fa/setup$")
_SETUP_2FA_DONE  = re.compile(r"^/auth/2fa/confirm$")
_DISABLE_2FA     = re.compile(r"^/auth/2fa/disable$")
# ── New features ──────────────────────────────────────────────────────────────
_PROFILE_ME      = re.compile(r"^/users/me/profile$")
_PROFILE_PUB     = re.compile(r"^/users/([a-zA-Z0-9_]{3,30})$")
_LEADERBOARD_G   = re.compile(r"^/leaderboard$")
_LEADERBOARD_W   = re.compile(r"^/leaderboard/weekly$")
_LEADERBOARD_D   = re.compile(r"^/leaderboard/skill/([a-zA-Z0-9_-]{1,64})$")
_CONTESTS        = re.compile(r"^/contests$")
_CONTEST         = re.compile(r"^/contests/([a-f0-9-]{36})$")
_CONTEST_JOIN    = re.compile(r"^/contests/([a-f0-9-]{36})/register$")
_PATHS           = re.compile(r"^/paths$")
_PATH            = re.compile(r"^/paths/([a-zA-Z0-9_-]{1,64})$")
_PATH_STEP_DONE  = re.compile(r"^/paths/([a-zA-Z0-9_-]{1,64})/steps/([a-zA-Z0-9_-]{1,64})/complete$")
_MY_PATH_PROG    = re.compile(r"^/users/me/paths$")
_COACH           = re.compile(r"^/users/me/coaching$")
_BADGES          = re.compile(r"^/users/me/badges$")
_REP_HISTORY     = re.compile(r"^/users/me/reputation$")
_DISCUSSIONS     = re.compile(r"^/discussions$")
_DISCUSSION      = re.compile(r"^/discussions/([a-f0-9-]{36})$")
_DISC_REPLY      = re.compile(r"^/discussions/([a-f0-9-]{36})/replies$")
_DISC_VOTE       = re.compile(r"^/discussions/([a-f0-9-]{36})/vote$")
_TASK_DISC       = re.compile(r"^/tasks/([a-zA-Z0-9_-]{1,64})/discussions$")
_ANALYTICS       = re.compile(r"^/analytics$")
_ANALYTICS_SKILL = re.compile(r"^/analytics/skills$")
_ANALYTICS_TREND = re.compile(r"^/analytics/trends$")
_COMPANY_ME      = re.compile(r"^/company$")
_COMPANY_JOBS    = re.compile(r"^/company/jobs$")
_PIPELINE        = re.compile(r"^/company/pipeline$")
_CONTACT         = re.compile(r"^/company/contact$")
_CANDIDATES      = re.compile(r"^/candidates$")
_JOBS_PUBLIC     = re.compile(r"^/jobs$")
_PAYMENT_ORDER   = re.compile(r"^/payments/create-order$")
_PAYMENT_VERIFY  = re.compile(r"^/payments/verify$")
_PAYMENT_WEBHOOK = re.compile(r"^/payments/webhook$")
_PROJECTS_TPL    = re.compile(r"^/projects$")
_MY_PROJECTS     = re.compile(r"^/users/me/projects$")
_PROJECT_START   = re.compile(r"^/projects/([a-zA-Z0-9_-]{1,64})/start$")
_PROJECT_SUBMIT  = re.compile(r"^/users/me/projects/([a-f0-9-]{36})/submit$")
_DAILY_CHALLENGE = re.compile(r"^/daily$")

# ── HTTP Base ─────────────────────────────────────────────────────────────────
from http.server import BaseHTTPRequestHandler


class SkillOSHandler(BaseHTTPRequestHandler):

    def setup(self):
        super().setup()
        self._request_id = str(uuid.uuid4())[:8]  # short ID for log correlation

    def log_message(self, fmt, *args):
        status = args[1] if len(args) > 1 else "?"
        log.info("http.request",
                 method=self.command,
                 path=self.path,
                 status=status,
                 request_id=self._request_id)

    def _read_body(self) -> bytes | None:
        """
        Read request body with a hard size cap.
        Returns None and sends 413 if body exceeds MAX_BODY_BYTES.
        """
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_BODY_BYTES:
            _json(self, 413, {
                "error": f"Request body too large (max {MAX_BODY_BYTES // 1024}KB)"
            }, self._request_id)
            return None
        return self.rfile.read(length)

    def _read_json(self) -> dict | None:
        raw = self._read_body()
        if raw is None:
            return None  # 413 already sent
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            _json(self, 400, {"error": "Invalid JSON"}, self._request_id)
            return None

    def do_OPTIONS(self):
        """Handle CORS preflight requests — browser sends this before every cross-origin call."""
        self.send_response(204)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        p = self.path.split("?")[0]  # strip query string for matching
        # ── Static routes ──────────────────────────────────────────────────
        if _HEALTH.match(p):            self._handle_health(); return
        if _TASKS.match(p):             self._handle_tasks(); return
        if _MY_SKILLS.match(p):         self._handle_my_skills(); return
        if _MY_SUBS.match(p):           self._handle_my_submissions(); return
        if _MY_CERTS.match(p):          self._handle_my_certifications(); return
        if _CERT_TYPES.match(p):        self._handle_cert_types(); return
        if _SESSIONS.match(p):          self._handle_get_sessions(); return
        if _LOGIN_HISTORY.match(p):     self._handle_login_history(); return
        # ── New feature routes ─────────────────────────────────────────────
        if _PROFILE_ME.match(p):        self._handle_profile_me(); return
        if _LEADERBOARD_G.match(p):     self._handle_leaderboard_global(); return
        if _LEADERBOARD_W.match(p):     self._handle_leaderboard_weekly(); return
        if _CONTESTS.match(p):          self._handle_contests(); return
        if _PATHS.match(p):             self._handle_paths(); return
        if _MY_PATH_PROG.match(p):      self._handle_my_paths(); return
        if _COACH.match(p):             self._handle_coaching(); return
        if _DISCUSSIONS.match(p):       self._handle_discussions(); return
        if _REP_HISTORY.match(p):       self._handle_reputation(); return
        if _BADGES.match(p):            self._handle_badges(); return
        if _ANALYTICS.match(p):         self._handle_analytics(); return
        if _ANALYTICS_SKILL.match(p):   self._handle_analytics_skills(); return
        if _ANALYTICS_TREND.match(p):   self._handle_analytics_trends(); return
        if _COMPANY_ME.match(p):        self._handle_company_me(); return
        if _COMPANY_JOBS.match(p):      self._handle_company_jobs(); return
        if _JOBS_PUBLIC.match(p):       self._handle_public_jobs(); return
        if _CANDIDATES.match(p):        self._handle_candidates(); return
        if _PIPELINE.match(p):          self._handle_pipeline(); return
        if _PROJECTS_TPL.match(p):      self._handle_project_templates(); return
        if _MY_PROJECTS.match(p):       self._handle_my_projects(); return
        if _DAILY_CHALLENGE.match(p):   self._handle_daily_challenge(); return
        # ── Dynamic routes ─────────────────────────────────────────────────
        m = _SUBMISSION.match(p)
        if m: self._handle_get_submission(m.group(1)); return
        m = _MY_SKILL.match(p)
        if m: self._handle_my_skill_detail(m.group(1)); return
        m = _CERT_VERIFY.match(p)
        if m: self._handle_cert_verify(m.group(1)); return
        m = _CONTEST.match(p)
        if m: self._handle_contest_detail(m.group(1)); return
        m = _PATH.match(p)
        if m: self._handle_path_detail(m.group(1)); return
        m = _DISCUSSION.match(p)
        if m: self._handle_discussion_detail(m.group(1)); return
        m = _TASK_DISC.match(p)
        if m: self._handle_task_discussions(m.group(1)); return
        m = _LEADERBOARD_D.match(p)
        if m: self._handle_leaderboard_domain(m.group(1)); return
        m = _PROFILE_PUB.match(p)
        if m: self._handle_public_profile(m.group(1)); return
        m = _REVOKE_SESSION.match(p)
        if m: _json(self, 405, {"error": "use POST to revoke"}, self._request_id); return
        _json(self, 404, {"error": "not found"}, self._request_id)

    def do_POST(self):
        p = self.path.split("?")[0]
        # ── Auth routes ────────────────────────────────────────────────────
        if _REGISTER.match(p):          self._handle_register(); return
        if _LOGIN.match(p):             self._handle_login(); return
        if _SUBMIT.match(p):            self._handle_submit(); return
        if _VERIFY_EMAIL.match(p):      self._handle_verify_email(); return
        if _FORGOT_PASSWORD.match(p):   self._handle_forgot_password(); return
        if _RESET_PASSWORD.match(p):    self._handle_reset_password(); return
        if _GOOGLE_AUTH.match(p):       self._handle_google_auth(); return
        if _CERT_CHECK.match(p):        self._handle_cert_check(); return
        if _SETUP_2FA_BEGIN.match(p):   self._handle_setup_2fa_begin(); return
        if _SETUP_2FA_DONE.match(p):    self._handle_setup_2fa_confirm(); return
        if _VERIFY_2FA.match(p):        self._handle_verify_2fa(); return
        if _DISABLE_2FA.match(p):       self._handle_disable_2fa(); return
        if _REVOKE_ALL.match(p):        self._handle_revoke_all_sessions(); return
        # ── New feature routes ─────────────────────────────────────────────
        if _PROFILE_ME.match(p):        self._handle_update_profile(); return
        if _DISCUSSIONS.match(p):       self._handle_create_discussion(); return
        if _COMPANY_ME.match(p):        self._handle_company_create(); return
        if _CONTACT.match(p):           self._handle_send_contact(); return
        if _PAYMENT_ORDER.match(p):     self._handle_payment_order(); return
        if _PAYMENT_VERIFY.match(p):    self._handle_payment_verify(); return
        if _PAYMENT_WEBHOOK.match(p):   self._handle_payment_webhook(); return
        # ── Dynamic POST routes ────────────────────────────────────────────
        m = _REVOKE_SESSION.match(p)
        if m: self._handle_revoke_session(m.group(1)); return
        m = _CONTEST_JOIN.match(p)
        if m: self._handle_contest_join(m.group(1)); return
        m = _PATH_STEP_DONE.match(p)
        if m: self._handle_step_complete(m.group(1), m.group(2)); return
        m = _DISC_REPLY.match(p)
        if m: self._handle_disc_reply(m.group(1)); return
        m = _DISC_VOTE.match(p)
        if m: self._handle_disc_vote(m.group(1)); return
        m = _PROJECT_START.match(p)
        if m: self._handle_project_start(m.group(1)); return
        m = _PROJECT_SUBMIT.match(p)
        if m: self._handle_project_submit(m.group(1)); return
        _json(self, 404, {"error": "not found"}, self._request_id)

    # ── GET /tasks ────────────────────────────────────────────────────────────

    def _handle_tasks(self):
        """
        Return all published tasks with their metadata.
        Does NOT include test case content — just what the UI needs to render
        the task list and problem description.
        """
        from skillos.db.database import fetchall
        rows = fetchall("""
            SELECT
                t.id, t.title, t.description, t.difficulty,
                t.skill_id, t.time_limit_ms, t.memory_limit_kb,
                s.name AS skill_name,
                COUNT(tc.id)                                           AS total_cases,
                COUNT(CASE WHEN tc.is_hidden = 0 THEN 1 END)          AS visible_cases
            FROM tasks t
            LEFT JOIN skills s    ON s.id  = t.skill_id
            LEFT JOIN test_cases tc ON tc.task_id = t.id
            WHERE t.is_published = 1
            GROUP BY t.id
            ORDER BY
                CASE t.difficulty WHEN 'easy' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                t.title
        """)
        _json(self, 200, {"tasks": [dict(r) for r in rows]}, self._request_id)

    # ── GET /health ───────────────────────────────────────────────────────────

    def _handle_health(self):
        from skillos.db.database import get_db
        db_ok = False
        try:
            get_db().execute("SELECT 1").fetchone()
            db_ok = True
        except Exception:
            pass
        status = 200 if db_ok else 503
        _json(self, status, {
            "status": "ok" if db_ok else "degraded",
            "db": "ok" if db_ok else "error",
        }, self._request_id)

    # ── POST /auth/register ───────────────────────────────────────────────────

    def _handle_register(self):
        body = self._read_json()
        if body is None:
            return
        ip = self.headers.get("X-Forwarded-For", "unknown")
        # Rate limit registrations by IP
        from skillos.auth.rate_limiter import check as rl_check
        allowed, retry_after = rl_check("register", ip)
        if not allowed:
            _json(self, 429, {
                "error": f"Too many registrations from this IP. Try again in {retry_after}s."
            }, self._request_id)
            return
        try:
            from skillos.auth.service import register
            user = register(
                email=body.get("email", ""),
                password=body.get("password", ""),
                display_name=body.get("display_name", ""),
                role=body.get("role", "user"),
            )
            log.info("auth.registered", user_id=user["id"],
                     request_id=self._request_id)
            _json(self, 201, {"user": user}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ── POST /auth/login ──────────────────────────────────────────────────────

    def _handle_login(self):
        body = self._read_json()
        if body is None:
            return
        ip         = self.headers.get("X-Forwarded-For", "unknown")
        user_agent = self.headers.get("User-Agent", "unknown")
        device_id  = self.headers.get("X-Device-ID")
        try:
            from skillos.auth.service import login
            result = login(
                email=body.get("email", ""),
                password=body.get("password", ""),
                ip=ip, user_agent=user_agent, device_id=device_id,
            )
            _json(self, 200, result, self._request_id)
        except SkillOSError as e:
            log.warning("auth.login_failed", request_id=self._request_id)
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ── POST /submit ──────────────────────────────────────────────────────────

    def _handle_submit(self):
        if config.PHASE_AUTH_ENABLED:
            user = _require_auth(self)
            if not user:
                return
            user_id = user["id"]
        else:
            user_id = "user-dev-001"

        body = self._read_json()
        if body is None:
            return

        task_id  = str(body.get("task_id", "")).strip()
        code     = str(body.get("code", "")).strip()
        language = str(body.get("language", "python")).strip()

        # Validate before hitting the DB
        if not task_id or not code:
            _json(self, 400, {"error": "task_id and code are required"},
                  self._request_id)
            return

        if len(code.encode("utf-8")) > MAX_CODE_BYTES:
            _json(self, 400, {
                "error": f"Code too long (max {MAX_CODE_BYTES // 1024}KB)"
            }, self._request_id)
            return

        # task_id format guard — only allow printable non-whitespace, max 64 chars
        if not re.match(r"^[a-zA-Z0-9_\-]{1,64}$", task_id):
            _json(self, 400, {"error": "Invalid task_id format"}, self._request_id)
            return

        try:
            sub = create_submission(user_id=user_id, task_id=task_id,
                                    code=code, language=language)
            log.info("submission.created",
                     submission_id=sub["id"],
                     user_id=user_id,
                     task_id=task_id,
                     request_id=self._request_id)
            _json(self, 202, {
                "submission_id": sub["id"],
                "status":        sub["status"],
                "poll_url":      f"/submission/{sub['id']}",
            }, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)
        except ValueError as e:
            _json(self, 400, {"error": str(e)}, self._request_id)

    # ── GET /submission/{id} ──────────────────────────────────────────────────

    def _handle_get_submission(self, submission_id: str):
        sub = get_submission(submission_id)
        if not sub:
            _json(self, 404, {"error": "submission not found"}, self._request_id)
            return

        # OWNERSHIP CHECK: authenticated users can only see their own submissions.
        # Unauthenticated requests (dev mode) bypass this check.
        if config.PHASE_AUTH_ENABLED:
            user = _require_auth(self)
            if not user:
                return
            if sub["user_id"] != user["id"]:
                # Return 404, not 403 — don't reveal that the submission exists
                _json(self, 404, {"error": "submission not found"}, self._request_id)
                return

        _json(self, 200, {
            "id":               sub["id"],
            "status":           sub["status"],
            "passed_cases":     sub["passed_cases"],
            "total_cases":      sub["total_cases"],
            "max_runtime_ms":   sub["max_runtime_ms"],
            "performance_tier": sub["performance_tier"],
            "stdout_sample":    sub["stdout_sample"],
            "stderr_sample":    sub["stderr_sample"],
            "submitted_at":     sub["submitted_at"],
            "evaluated_at":     sub["evaluated_at"],
        }, self._request_id)

    # ── GET /users/me/submissions ─────────────────────────────────────────────

    def _handle_my_submissions(self):
        user = _require_auth(self)
        if not user:
            return
        from skillos.db.database import fetchall
        rows = fetchall("""
            SELECT
                s.id, s.task_id, s.status,
                s.passed_cases, s.total_cases,
                s.max_runtime_ms, s.performance_tier,
                s.submitted_at,
                t.title AS task_title,
                t.difficulty,
                sk.name AS skill_name
            FROM submissions s
            JOIN tasks t  ON t.id  = s.task_id
            LEFT JOIN skills sk ON sk.id = t.skill_id
            WHERE s.user_id = ?
            ORDER BY s.submitted_at DESC
            LIMIT 100
        """, (user["id"],))
        _json(self, 200, {"submissions": [dict(r) for r in rows]}, self._request_id)

    # ── GET /users/me/skills ──────────────────────────────────────────────────

    def _handle_my_skills(self):
        if not config.PHASE_SKILLS_ENABLED:
            _json(self, 404, {"error": "skills not yet available"}, self._request_id)
            return
        user = _require_auth(self)
        if not user:
            return
        from skillos.skills.service import get_user_skill_scores
        scores = get_user_skill_scores(user["id"])
        _json(self, 200, {"skills": scores}, self._request_id)

    # ── GET /users/me/skills/{skill_id} ───────────────────────────────────────

    def _handle_my_skill_detail(self, skill_id: str):
        if not config.PHASE_SKILLS_ENABLED:
            _json(self, 404, {"error": "skills not yet available"}, self._request_id)
            return
        user = _require_auth(self)
        if not user:
            return
        from skillos.skills.service import get_user_skill_detail
        detail = get_user_skill_detail(user["id"], skill_id)
        if not detail:
            _json(self, 404, {"error": "skill not found"}, self._request_id)
            return
        _json(self, 200, detail, self._request_id)

    # ── POST /auth/verify-email ───────────────────────────────────────────────

    def _handle_verify_email(self):
        body = self._read_json()
        if body is None:
            return
        token = str(body.get("token", "")).strip()
        if not token:
            _json(self, 400, {"error": "token is required"}, self._request_id)
            return
        try:
            from skillos.auth.service import verify_email
            result = verify_email(token)
            log.info("auth.email_verified", user_id=result["user_id"],
                     request_id=self._request_id)
            _json(self, 200, {"message": "Email verified successfully", "user": result},
                  self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ── POST /auth/forgot-password ────────────────────────────────────────────

    def _handle_forgot_password(self):
        body = self._read_json()
        if body is None:
            return
        email = str(body.get("email", "")).strip()
        if not email:
            _json(self, 400, {"error": "email is required"}, self._request_id)
            return
        # Always return 200 — never reveal if email exists (anti-enumeration)
        try:
            from skillos.auth.service import request_password_reset
            request_password_reset(email)
        except Exception:
            pass  # Swallow all errors — never reveal account existence
        _json(self, 200, {
            "message": "If that email exists, a reset link has been sent"
        }, self._request_id)

    # ── POST /auth/reset-password ─────────────────────────────────────────────

    def _handle_reset_password(self):
        body = self._read_json()
        if body is None:
            return
        token    = str(body.get("token", "")).strip()
        password = str(body.get("password", ""))
        if not token or not password:
            _json(self, 400, {"error": "token and password are required"},
                  self._request_id)
            return
        try:
            from skillos.auth.service import reset_password
            result = reset_password(token, password)
            log.info("auth.password_reset", user_id=result["user_id"],
                     request_id=self._request_id)
            _json(self, 200, {"message": "Password reset successfully"},
                  self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ── POST /auth/google ─────────────────────────────────────────────────────
    # Google OAuth — client sends the Google ID token, server verifies it.
    # Requires GOOGLE_CLIENT_ID environment variable in production.

    def _handle_google_auth(self):
        body = self._read_json()
        if body is None:
            return
        id_token = str(body.get("id_token", "")).strip()
        if not id_token:
            _json(self, 400, {"error": "id_token is required"}, self._request_id)
            return
        try:
            from skillos.auth.google import authenticate_google_user
            token, user = authenticate_google_user(id_token)
            _json(self, 200, {"token": token, "user": user}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)
        except Exception as e:
            log.error("auth.google_error", error=str(e),
                      request_id=self._request_id)
            _json(self, 500, {"error": "Google authentication failed"},
                  self._request_id)


    # ── GET /users/me/certifications ──────────────────────────────────────────

    def _handle_my_certifications(self):
        user = _require_auth(self)
        if not user:
            return
        from skillos.certifications.service import get_user_certifications
        certs = get_user_certifications(user["id"])
        _json(self, 200, {"certifications": certs}, self._request_id)

    # ── GET /certifications/types ─────────────────────────────────────────────

    def _handle_cert_types(self):
        from skillos.certifications.service import get_all_cert_types
        types = get_all_cert_types()
        _json(self, 200, {"cert_types": types}, self._request_id)

    # ── GET /cert/{code} — public verification ────────────────────────────────

    def _handle_cert_verify(self, cert_code: str):
        from skillos.certifications.service import verify_certificate
        cert = verify_certificate(cert_code)
        if not cert:
            _json(self, 404, {"error": "Certificate not found or has been revoked"},
                  self._request_id)
            return
        _json(self, 200, {"certificate": cert, "valid": True}, self._request_id)

    # ── POST /certifications/check ────────────────────────────────────────────
    # Manually trigger a cert check for the logged-in user.
    # Useful after solving a batch of problems.

    def _handle_cert_check(self):
        user = _require_auth(self)
        if not user:
            return
        from skillos.certifications.service import check_and_award_certifications
        new_certs = check_and_award_certifications(user["id"])
        _json(self, 200, {
            "newly_awarded": new_certs,
            "count": len(new_certs),
            "message": f"{len(new_certs)} new certificate(s) awarded" if new_certs else "No new certificates earned yet",
        }, self._request_id)

    # ── POST /auth/2fa/setup ──────────────────────────────────────────────────
    def _handle_setup_2fa_begin(self):
        user = _require_auth(self)
        if not user: return
        try:
            from skillos.auth.service import setup_2fa_begin
            result = setup_2fa_begin(user["id"])
            _json(self, 200, result, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ── POST /auth/2fa/confirm ────────────────────────────────────────────────
    def _handle_setup_2fa_confirm(self):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.auth.service import setup_2fa_confirm
            result = setup_2fa_confirm(user["id"], str(body.get("code", "")))
            log.info("auth.2fa_enabled", user_id=user["id"],
                     request_id=self._request_id)
            _json(self, 200, result, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ── POST /auth/2fa/verify ─────────────────────────────────────────────────
    def _handle_verify_2fa(self):
        body = self._read_json()
        if body is None: return
        ip         = self.headers.get("X-Forwarded-For", self.client_address[0] if hasattr(self, "client_address") else "unknown")
        user_agent = self.headers.get("User-Agent", "unknown")
        device_id  = self.headers.get("X-Device-ID")
        try:
            from skillos.auth.service import verify_2fa
            result = verify_2fa(
                partial_token=str(body.get("partial_token", "")),
                code=str(body.get("code", "")),
                ip=ip, user_agent=user_agent, device_id=device_id,
            )
            _json(self, 200, result, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ── POST /auth/2fa/disable ────────────────────────────────────────────────
    def _handle_disable_2fa(self):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.auth.service import disable_2fa
            result = disable_2fa(user["id"], str(body.get("code", "")))
            _json(self, 200, result, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ── GET /auth/sessions ────────────────────────────────────────────────────
    def _handle_get_sessions(self):
        user = _require_auth(self)
        if not user: return
        from skillos.auth.device_tracker import get_active_sessions
        sessions = get_active_sessions(user["id"])
        _json(self, 200, {"sessions": sessions}, self._request_id)

    # ── POST /auth/sessions/{id}/revoke ───────────────────────────────────────
    def _handle_revoke_session(self, session_id: str):
        user = _require_auth(self)
        if not user: return
        from skillos.auth.device_tracker import revoke_session
        ok = revoke_session(session_id, user["id"])
        if not ok:
            _json(self, 404, {"error": "session not found"}, self._request_id)
        else:
            _json(self, 200, {"revoked": True}, self._request_id)

    # ── POST /auth/sessions/revoke-all ────────────────────────────────────────
    def _handle_revoke_all_sessions(self):
        user = _require_auth(self)
        if not user: return
        body       = self._read_json() or {}
        keep_current = body.get("keep_current", True)
        auth       = self.headers.get("Authorization", "")
        token      = auth[7:].strip() if auth.startswith("Bearer ") else None
        from skillos.auth.device_tracker import revoke_all_sessions
        revoke_all_sessions(user["id"], except_token=token if keep_current else None)
        log.info("auth.sessions_revoked_all", user_id=user["id"],
                 request_id=self._request_id)
        _json(self, 200, {"revoked": True}, self._request_id)

    # ── GET /auth/login-history ───────────────────────────────────────────────
    def _handle_login_history(self):
        user = _require_auth(self)
        if not user: return
        from skillos.auth.device_tracker import get_login_history
        history = get_login_history(user["id"], limit=20)
        _json(self, 200, {"history": history}, self._request_id)


    # ═══════════════════════════════════════════════════════════════════════════
    # PROFILE ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _handle_get_my_profile(self):
        user = _require_auth(self)
        if not user: return
        from skillos.profiles.service import get_profile, get_skill_graph
        profile = get_profile(user["id"])
        graph   = get_skill_graph(user["id"])
        _json(self, 200, {"profile": dict(profile) if profile else {}, "skill_graph": graph}, self._request_id)

    def _handle_update_profile(self):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.profiles.service import update_profile
            updated = update_profile(user["id"], body)
            _json(self, 200, {"profile": dict(updated)}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_public_profile(self, username: str):
        from skillos.profiles.service import get_public_profile
        profile = get_public_profile(username)
        if not profile:
            _json(self, 404, {"error": "Profile not found or private"}, self._request_id)
            return
        _json(self, 200, {"profile": profile}, self._request_id)

    # ═══════════════════════════════════════════════════════════════════════════
    # LEADERBOARD ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _handle_leaderboard_global(self):
        from skillos.leaderboard.service import get_global_leaderboard
        rows = get_global_leaderboard(limit=50)
        _json(self, 200, {"leaderboard": rows}, self._request_id)

    def _handle_leaderboard_domain(self, skill_id: str):
        from skillos.leaderboard.service import get_domain_leaderboard
        rows = get_domain_leaderboard(skill_id)
        _json(self, 200, {"leaderboard": rows, "skill_id": skill_id}, self._request_id)

    def _handle_leaderboard_weekly(self):
        from skillos.leaderboard.service import get_weekly_leaderboard
        rows = get_weekly_leaderboard()
        _json(self, 200, {"leaderboard": rows}, self._request_id)

    def _handle_my_rank(self):
        user = _require_auth(self)
        if not user: return
        from skillos.leaderboard.service import get_user_rank
        rank = get_user_rank(user["id"])
        _json(self, 200, rank, self._request_id)

    # ═══════════════════════════════════════════════════════════════════════════
    # CONTEST ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _handle_list_contests(self):
        from skillos.contests.service import list_contests, sync_contest_statuses
        sync_contest_statuses()
        status = self.path.split("status=")[-1] if "status=" in self.path else None
        rows = list_contests(status)
        _json(self, 200, {"contests": rows}, self._request_id)

    def _handle_get_contest(self, contest_id: str):
        from skillos.contests.service import get_contest
        c = get_contest(contest_id)
        if not c:
            _json(self, 404, {"error": "Contest not found"}, self._request_id)
            return
        _json(self, 200, {"contest": c}, self._request_id)

    def _handle_contest_register(self, contest_id: str):
        user = _require_auth(self)
        if not user: return
        try:
            from skillos.contests.service import register_for_contest
            result = register_for_contest(user["id"], contest_id)
            _json(self, 201, result, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_contest_leaderboard(self, contest_id: str):
        from skillos.contests.service import get_contest_leaderboard
        rows = get_contest_leaderboard(contest_id)
        _json(self, 200, {"leaderboard": rows}, self._request_id)

    # ═══════════════════════════════════════════════════════════════════════════
    # LEARNING PATH ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _handle_list_paths(self):
        from skillos.learning.service import list_paths
        domain = self.path.split("domain=")[-1] if "domain=" in self.path else None
        rows = list_paths(domain)
        _json(self, 200, {"paths": rows}, self._request_id)

    def _handle_get_path(self, path_id: str):
        from skillos.learning.service import get_path
        p = get_path(path_id)
        if not p:
            _json(self, 404, {"error": "Path not found"}, self._request_id)
            return
        _json(self, 200, {"path": p}, self._request_id)

    def _handle_path_progress(self, path_id: str):
        user = _require_auth(self)
        if not user: return
        from skillos.learning.service import get_user_progress
        try:
            prog = get_user_progress(user["id"], path_id)
            _json(self, 200, prog, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_complete_step(self, path_id: str):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        step_id = str(body.get("step_id","")).strip()
        if not step_id:
            _json(self, 400, {"error": "step_id required"}, self._request_id)
            return
        try:
            from skillos.learning.service import complete_step
            complete_step(user["id"], path_id, step_id)
            _json(self, 200, {"message": "Step marked complete"}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ═══════════════════════════════════════════════════════════════════════════
    # AI COACHING ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _handle_coach_analysis(self):
        user = _require_auth(self)
        if not user: return
        from skillos.coaching.service import analyse_performance
        analysis = analyse_performance(user["id"])
        _json(self, 200, analysis, self._request_id)

    def _handle_daily_challenge(self):
        from skillos.coaching.service import get_daily_challenge, seed_daily_challenge
        seed_daily_challenge()
        challenge = get_daily_challenge()
        if not challenge:
            _json(self, 404, {"error": "No daily challenge today"}, self._request_id)
            return
        _json(self, 200, {"challenge": challenge}, self._request_id)

    # ═══════════════════════════════════════════════════════════════════════════
    # COMMUNITY ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _handle_list_discussions(self):
        task_id = self.path.split("task_id=")[-1] if "task_id=" in self.path else None
        from skillos.community.service import list_discussions
        rows = list_discussions(task_id)
        _json(self, 200, {"discussions": rows}, self._request_id)

    def _handle_get_discussion(self, disc_id: str):
        from skillos.community.service import get_discussion
        d = get_discussion(disc_id)
        if not d:
            _json(self, 404, {"error": "Discussion not found"}, self._request_id)
            return
        _json(self, 200, {"discussion": d}, self._request_id)

    def _handle_create_discussion(self):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.community.service import create_discussion
            d = create_discussion(user["id"], body.get("title",""),
                body.get("body",""), body.get("task_id"), body.get("is_solution",False))
            _json(self, 201, {"discussion": d}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_add_reply(self, disc_id: str):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.community.service import add_reply
            r = add_reply(user["id"], disc_id, body.get("body",""))
            _json(self, 201, {"reply": dict(r)}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_vote(self, target_type: str, target_id: str):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.community.service import vote
            vote(user["id"], target_type, target_id, int(body.get("vote", 1)))
            _json(self, 200, {"message": "Vote recorded"}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ═══════════════════════════════════════════════════════════════════════════
    # REPUTATION ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _handle_reputation_history(self):
        user = _require_auth(self)
        if not user: return
        from skillos.reputation.service import get_reputation_history
        history = get_reputation_history(user["id"])
        total = self._get_user_rep(user["id"])
        _json(self, 200, {"reputation": total, "history": history}, self._request_id)

    def _get_user_rep(self, user_id: str) -> int:
        from skillos.db.database import fetchone
        row = fetchone("SELECT reputation FROM users WHERE id=?", (user_id,))
        return row["reputation"] if row else 0

    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYTICS ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _handle_analytics_platform(self):
        user = _require_auth(self)
        if not user: return
        from skillos.analytics.service import get_platform_stats, get_skill_demand, get_top_problems
        _json(self, 200, {
            "stats":        get_platform_stats(),
            "skill_demand": get_skill_demand(),
            "top_problems": get_top_problems(),
        }, self._request_id)

    def _handle_analytics_activity(self):
        from skillos.analytics.service import get_user_activity_trend
        rows = get_user_activity_trend(30)
        _json(self, 200, {"trend": rows}, self._request_id)

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPANY / RECRUITER ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _handle_create_company(self):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.companies.service import create_company
            co = create_company(user["id"], body.get("name",""),
                                body.get("domain"), body.get("description"))
            _json(self, 201, {"company": dict(co)}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_my_company(self):
        user = _require_auth(self)
        if not user: return
        from skillos.companies.service import get_user_company
        co = get_user_company(user["id"])
        if not co:
            _json(self, 404, {"error": "No company found. Create one first."}, self._request_id)
            return
        _json(self, 200, {"company": co}, self._request_id)

    def _handle_create_job(self):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        from skillos.companies.service import get_user_company, create_job
        co = get_user_company(user["id"])
        if not co:
            _json(self, 403, {"error": "No company account"}, self._request_id)
            return
        try:
            job = create_job(co["id"], body)
            _json(self, 201, {"job": dict(job)}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_list_jobs(self):
        from skillos.companies.service import list_jobs
        _json(self, 200, {"jobs": list_jobs()}, self._request_id)

    def _handle_pipeline(self):
        user = _require_auth(self)
        if not user: return
        from skillos.companies.service import get_user_company, get_pipeline
        co = get_user_company(user["id"])
        if not co:
            _json(self, 403, {"error": "No company account"}, self._request_id)
            return
        rows = get_pipeline(co["id"])
        _json(self, 200, {"pipeline": rows}, self._request_id)

    def _handle_contact_candidate(self):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        from skillos.companies.service import get_user_company, send_contact_request
        co = get_user_company(user["id"])
        if not co:
            _json(self, 403, {"error": "No company account"}, self._request_id)
            return
        try:
            req = send_contact_request(co["id"], user["id"],
                body.get("candidate_id",""), body.get("message",""),
                body.get("job_id"))
            _json(self, 201, {"request": dict(req)}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_my_contact_requests(self):
        """Candidate sees incoming contact requests."""
        user = _require_auth(self)
        if not user: return
        from skillos.db.database import fetchall
        rows = fetchall("""
            SELECT cr.*, c.name AS company_name, c.logo_url,
                   jp.title AS job_title
            FROM contact_requests cr
            JOIN companies c ON c.id=cr.company_id
            LEFT JOIN job_postings jp ON jp.id=cr.job_id
            WHERE cr.candidate_id=? ORDER BY cr.created_at DESC
        """, (user["id"],))
        _json(self, 200, {"requests": [dict(r) for r in rows]}, self._request_id)

    def _handle_respond_contact(self, req_id: str):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.companies.service import respond_to_contact
            respond_to_contact(user["id"], req_id, bool(body.get("accept", True)))
            _json(self, 200, {"message": "Response recorded"}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ═══════════════════════════════════════════════════════════════════════════
    # PAYMENT ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _handle_create_payment_order(self):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        plan = str(body.get("plan","")).strip()
        if not plan:
            _json(self, 400, {"error": "plan required"}, self._request_id)
            return
        from skillos.companies.service import get_user_company
        from skillos.payments.service import create_order
        co = get_user_company(user["id"])
        co_id = co["id"] if co else None
        try:
            order = create_order(co_id, user["id"], plan)
            _json(self, 201, order, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_verify_payment(self):
        body = self._read_json()
        if body is None: return
        try:
            from skillos.payments.service import verify_payment
            result = verify_payment(
                body.get("order_id",""),
                body.get("razorpay_payment_id",""),
                body.get("razorpay_signature",""),
            )
            _json(self, 200, result, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ═══════════════════════════════════════════════════════════════════════════
    # PROJECTS ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _handle_list_project_templates(self):
        from skillos.projects.service import list_templates
        _json(self, 200, {"templates": list_templates()}, self._request_id)

    def _handle_start_project(self):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.projects.service import start_project
            proj = start_project(user["id"], body.get("template_id",""))
            _json(self, 201, {"project": dict(proj)}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_submit_project(self, project_id: str):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.projects.service import submit_project
            proj = submit_project(user["id"], project_id, body.get("repo_url",""))
            _json(self, 200, {"project": dict(proj)}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_my_projects(self):
        user = _require_auth(self)
        if not user: return
        from skillos.projects.service import get_user_projects
        _json(self, 200, {"projects": get_user_projects(user["id"])}, self._request_id)


    # ─────────────────────────────────────────────────────────────────────────
    # PROFILE
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_profile_me(self):
        user = _require_auth(self)
        if not user: return
        from skillos.profiles.service import get_profile
        profile = get_profile(user["id"])
        _json(self, 200, {"profile": profile}, self._request_id)

    def _handle_update_profile(self):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.profiles.service import update_profile
            profile = update_profile(user["id"], body)
            _json(self, 200, {"profile": profile}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_public_profile(self, username: str):
        from skillos.profiles.service import get_public_profile
        profile = get_public_profile(username)
        if not profile:
            _json(self, 404, {"error": "Profile not found or is private"}, self._request_id)
            return
        _json(self, 200, {"profile": profile}, self._request_id)

    # ─────────────────────────────────────────────────────────────────────────
    # LEADERBOARD
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_leaderboard_global(self):
        from skillos.leaderboard.service import get_global_leaderboard
        _json(self, 200, {"leaderboard": get_global_leaderboard()}, self._request_id)

    def _handle_leaderboard_weekly(self):
        from skillos.leaderboard.service import get_weekly_leaderboard
        _json(self, 200, {"leaderboard": get_weekly_leaderboard()}, self._request_id)

    def _handle_leaderboard_domain(self, skill_id: str):
        from skillos.leaderboard.service import get_domain_leaderboard
        _json(self, 200, {"leaderboard": get_domain_leaderboard(skill_id)}, self._request_id)

    # ─────────────────────────────────────────────────────────────────────────
    # CONTESTS
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_contests(self):
        from skillos.contests.service import get_all_contests
        _json(self, 200, {"contests": get_all_contests()}, self._request_id)

    def _handle_contest_detail(self, contest_id: str):
        from skillos.contests.service import get_contest
        c = get_contest(contest_id)
        if not c:
            _json(self, 404, {"error": "Contest not found"}, self._request_id); return
        _json(self, 200, {"contest": c}, self._request_id)

    def _handle_contest_join(self, contest_id: str):
        user = _require_auth(self)
        if not user: return
        try:
            from skillos.contests.service import register_for_contest
            result = register_for_contest(contest_id, user["id"])
            _json(self, 201, result, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ─────────────────────────────────────────────────────────────────────────
    # LEARNING PATHS
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_paths(self):
        from skillos.learning.service import get_all_paths
        _json(self, 200, {"paths": get_all_paths()}, self._request_id)

    def _handle_path_detail(self, path_id: str):
        user = _require_auth(self)
        from skillos.learning.service import get_path_with_steps
        p = get_path_with_steps(path_id, user["id"] if user else None)
        if not p:
            _json(self, 404, {"error": "Path not found"}, self._request_id); return
        _json(self, 200, {"path": p}, self._request_id)

    def _handle_my_paths(self):
        user = _require_auth(self)
        if not user: return
        from skillos.learning.service import get_user_progress
        _json(self, 200, {"paths": get_user_progress(user["id"])}, self._request_id)

    def _handle_step_complete(self, path_id: str, step_id: str):
        user = _require_auth(self)
        if not user: return
        try:
            from skillos.learning.service import mark_step_complete
            path = mark_step_complete(user["id"], path_id, step_id)
            _json(self, 200, {"path": path}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ─────────────────────────────────────────────────────────────────────────
    # AI COACHING
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_coaching(self):
        user = _require_auth(self)
        if not user: return
        from skillos.coaching.service import get_coaching_report
        report = get_coaching_report(user["id"])
        _json(self, 200, {"report": report}, self._request_id)

    # ─────────────────────────────────────────────────────────────────────────
    # COMMUNITY / DISCUSSIONS
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_discussions(self):
        from skillos.community.service import get_discussions
        _json(self, 200, {"discussions": get_discussions()}, self._request_id)

    def _handle_task_discussions(self, task_id: str):
        from skillos.community.service import get_discussions
        _json(self, 200, {"discussions": get_discussions(task_id=task_id)}, self._request_id)

    def _handle_discussion_detail(self, disc_id: str):
        user = _require_auth(self)
        from skillos.community.service import get_discussion
        d = get_discussion(disc_id, user["id"] if user else None)
        if not d:
            _json(self, 404, {"error": "Discussion not found"}, self._request_id); return
        _json(self, 200, {"discussion": d}, self._request_id)

    def _handle_create_discussion(self):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.community.service import create_discussion
            d = create_discussion(user["id"], body.get("title",""),
                                  body.get("body",""), body.get("task_id"),
                                  body.get("is_solution", False))
            _json(self, 201, {"discussion": d}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_disc_reply(self, disc_id: str):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.community.service import create_reply
            replies = create_reply(disc_id, user["id"], body.get("body",""))
            _json(self, 201, {"replies": replies}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_disc_vote(self, disc_id: str):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.community.service import vote
            result = vote(user["id"], "discussion", disc_id, body.get("vote", 1))
            _json(self, 200, result, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ─────────────────────────────────────────────────────────────────────────
    # REPUTATION & BADGES
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_reputation(self):
        user = _require_auth(self)
        if not user: return
        from skillos.reputation.service import get_reputation_history
        _json(self, 200, {"history": get_reputation_history(user["id"])}, self._request_id)

    def _handle_badges(self):
        user = _require_auth(self)
        if not user: return
        from skillos.reputation.service import get_badges
        _json(self, 200, {"badges": get_badges(user["id"])}, self._request_id)

    # ─────────────────────────────────────────────────────────────────────────
    # ANALYTICS
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_analytics(self):
        from skillos.analytics.service import get_platform_stats
        _json(self, 200, get_platform_stats(), self._request_id)

    def _handle_analytics_skills(self):
        from skillos.analytics.service import get_skill_demand
        _json(self, 200, {"skills": get_skill_demand()}, self._request_id)

    def _handle_analytics_trends(self):
        from skillos.analytics.service import get_submission_trends
        _json(self, 200, {"trends": get_submission_trends()}, self._request_id)

    # ─────────────────────────────────────────────────────────────────────────
    # COMPANIES & RECRUITER
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_company_me(self):
        user = _require_auth(self)
        if not user: return
        from skillos.companies.service import get_company_for_user
        c = get_company_for_user(user["id"])
        if not c:
            _json(self, 404, {"error": "No company found. Create one first."}, self._request_id)
            return
        _json(self, 200, {"company": c}, self._request_id)

    def _handle_company_create(self):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.companies.service import get_or_create_company
            c = get_or_create_company(user["id"], body.get("name","My Company"),
                                      body.get("domain"))
            _json(self, 201, {"company": c}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_company_jobs(self):
        user = _require_auth(self)
        if not user: return
        from skillos.companies.service import get_company_for_user, get_company_jobs
        c = get_company_for_user(user["id"])
        if not c:
            _json(self, 404, {"error": "No company"}, self._request_id); return
        _json(self, 200, {"jobs": get_company_jobs(c["id"])}, self._request_id)

    def _handle_public_jobs(self):
        from skillos.companies.service import get_public_jobs
        _json(self, 200, {"jobs": get_public_jobs()}, self._request_id)

    def _handle_candidates(self):
        user = _require_auth(self)
        if not user: return
        import urllib.parse
        params = {}
        if "?" in self.path:
            params = dict(urllib.parse.parse_qsl(self.path.split("?",1)[1]))
        from skillos.companies.service import search_candidates
        candidates = search_candidates(params)
        _json(self, 200, {"candidates": candidates}, self._request_id)

    def _handle_send_contact(self):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.companies.service import get_company_for_user, send_contact_request
            c = get_company_for_user(user["id"])
            if not c:
                _json(self, 400, {"error": "Create a company first"}, self._request_id); return
            result = send_contact_request(c["id"], user["id"],
                                          body.get("candidate_id",""),
                                          body.get("message",""),
                                          body.get("job_id"))
            _json(self, 201, result, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_pipeline(self):
        user = _require_auth(self)
        if not user: return
        from skillos.companies.service import get_company_for_user, get_pipeline
        c = get_company_for_user(user["id"])
        if not c:
            _json(self, 404, {"error": "No company"}, self._request_id); return
        _json(self, 200, {"pipeline": get_pipeline(c["id"])}, self._request_id)

    # ─────────────────────────────────────────────────────────────────────────
    # PAYMENTS
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_payment_order(self):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.payments.service import create_order
            from skillos.companies.service import get_company_for_user
            c = get_company_for_user(user["id"])
            if not c:
                _json(self, 400, {"error": "Create a company first"}, self._request_id); return
            order = create_order(c["id"], body.get("plan","growth"))
            _json(self, 201, order, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_payment_verify(self):
        body = self._read_json()
        if body is None: return
        try:
            from skillos.payments.service import verify_payment
            result = verify_payment(
                body.get("razorpay_order_id",""),
                body.get("razorpay_payment_id",""),
                body.get("razorpay_signature",""),
            )
            _json(self, 200, result, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_payment_webhook(self):
        raw = self._read_body()
        if raw is None: return
        sig = self.headers.get("X-Razorpay-Signature","")
        try:
            from skillos.payments.service import handle_webhook
            result = handle_webhook(raw, sig)
            _json(self, 200, result, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ─────────────────────────────────────────────────────────────────────────
    # PROJECTS
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_project_templates(self):
        from skillos.projects.service import get_project_templates
        _json(self, 200, {"templates": get_project_templates()}, self._request_id)

    def _handle_my_projects(self):
        user = _require_auth(self)
        if not user: return
        from skillos.projects.service import get_user_projects
        _json(self, 200, {"projects": get_user_projects(user["id"])}, self._request_id)

    def _handle_project_start(self, template_id: str):
        user = _require_auth(self)
        if not user: return
        try:
            from skillos.projects.service import start_project
            proj = start_project(user["id"], template_id)
            _json(self, 201, {"project": proj}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    def _handle_project_submit(self, project_id: str):
        user = _require_auth(self)
        if not user: return
        body = self._read_json()
        if body is None: return
        try:
            from skillos.projects.service import submit_project
            proj = submit_project(user["id"], project_id, body.get("repo_url",""))
            _json(self, 200, {"project": proj}, self._request_id)
        except SkillOSError as e:
            _json(self, e.status_code, {"error": e.message}, self._request_id)

    # ─────────────────────────────────────────────────────────────────────────
    # DAILY CHALLENGE
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_daily_challenge(self):
        from datetime import date
        today = date.today().isoformat()
        from skillos.db.database import fetchone as fone, transaction, fetchall
        import uuid
        row = fone("SELECT dc.*, t.title, t.difficulty, t.description, s.name AS skill_name FROM daily_challenges dc JOIN tasks t ON t.id=dc.task_id LEFT JOIN skills s ON s.id=t.skill_id WHERE dc.date=?", (today,))
        if not row:
            # Pick a random published task for today
            task = fone("SELECT id FROM tasks WHERE is_published=1 ORDER BY RANDOM() LIMIT 1")
            if task:
                with transaction() as db:
                    db.execute("INSERT OR IGNORE INTO daily_challenges (id,task_id,date) VALUES (?,?,?)",
                               (str(uuid.uuid4()), task['id'], today))
                row = fone("SELECT dc.*, t.title, t.difficulty, t.description, s.name AS skill_name FROM daily_challenges dc JOIN tasks t ON t.id=dc.task_id LEFT JOIN skills s ON s.id=t.skill_id WHERE dc.date=?", (today,))
        _json(self, 200, {"challenge": dict(row) if row else None}, self._request_id)

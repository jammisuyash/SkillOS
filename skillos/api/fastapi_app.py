"""
skillos/api/fastapi_app.py

SkillOS Backend — FastAPI Edition (Production-Ready)

MIGRATION FROM http.server:
  Before: python -m skillos.main
  After:  uvicorn skillos.api.fastapi_app:app --host 0.0.0.0 --port 8000 --workers 4

ADVANTAGES OVER STDLIB http.server:
  async I/O — thousands of concurrent connections
  Auto /docs (Swagger UI) at /docs
  Request validation with Pydantic
  WebSocket support (real live interview collab)
  Background tasks (replaces thread worker)
  Proper middleware (CORS, rate limiting)
  ASGI compliant — Railway/Render/Fly compatible

REQUIREMENTS:
  pip install "fastapi[all]" uvicorn[standard]

DEPLOY (Railway / Render):
  Start command: uvicorn skillos.api.fastapi_app:app --host 0.0.0.0 --port $PORT --workers 4
"""

from __future__ import annotations
import os, json, uuid, threading

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
except ImportError:
    pass

# Rate limiting
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    limiter = Limiter(key_func=get_remote_address)
    _RATE_LIMIT_ENABLED = True
except ImportError:
    _RATE_LIMIT_ENABLED = False
from contextlib import asynccontextmanager
from typing import Optional, Any

# ── FastAPI (install: pip install "fastapi[all]") ─────────────────────────────
try:
    from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, Response
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from pydantic import BaseModel, Field
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False
    raise ImportError(
        "FastAPI not installed. Run: pip install 'fastapi[all]' uvicorn[standard]\n"
        "Or keep using the stdlib backend: python -m skillos.main"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ─────────────────────────────────────────────────────────────
    from skillos.db.migrations import run_migrations
    run_migrations()
    for mod, fn in [
        ("skillos.db.seed",             "seed"),
        ("skillos.learning.service",    "seed_learning_paths"),
        ("skillos.projects.service",    "seed_project_templates"),
        ("skillos.contests.service",    "seed_sample_contests"),
        ("skillos.contests.service",    "seed_daily_challenge"),
        ("skillos.db.seed_v2",          "seed_all_v2"),
        ("skillos.db.problems_master",  "seed_master"),
    ]:
        try:
            import importlib
            m = importlib.import_module(mod)
            getattr(m, fn)()
        except Exception as e:
            print(f"⚠ seed {mod}.{fn}: {e}")

    from skillos.submissions import events
    from skillos.skills.handlers import handle_submission_evaluated
    events.register(handle_submission_evaluated)

    from skillos.submissions.worker import EvaluatorWorker
    worker = EvaluatorWorker()
    worker.start()
    app.state.worker = worker
    print("✅ SkillOS FastAPI ready — Swagger UI at /docs")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    if hasattr(app.state, "worker"):
        app.state.worker.stop(timeout=10)


# ═══════════════════════════════════════════════════════════════════════════════
# ── App ────────────────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="SkillOS API",
    description=(
        "Skill verification platform for developers.\n\n"
        "Solve coding problems → prove real skills → get hired.\n\n"
        "**Current status:** All endpoints authenticated via Bearer JWT.\n"
        "Register at `POST /auth/register`, login at `POST /auth/login`, "
        "pass the token as `Authorization: Bearer <token>`."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
if _RATE_LIMIT_ENABLED:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# ── Auth helpers ───────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

_bearer = HTTPBearer(auto_error=False)

def _current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)) -> dict:
    if not creds:
        raise HTTPException(401, "Authentication required")
    from skillos.auth.service import verify_token
    user = verify_token(creds.credentials)
    if not user:
        raise HTTPException(401, "Invalid or expired token")
    if "id" not in user and "user_id" in user:
        user["id"] = user["user_id"]
    return user

def _optional_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)) -> Optional[dict]:
    if not creds:
        return None
    try:
        from skillos.auth.service import verify_token
        return verify_token(creds.credentials)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# ── Pydantic models ────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

class RegisterBody(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: str
    password: str = Field(..., min_length=8)
    display_name: Optional[str] = None
    college: Optional[str] = None

class LoginBody(BaseModel):
    email: str
    password: str
    totp_code: Optional[str] = None

class SubmitBody(BaseModel):
    task_id: str
    language: str
    code: str = Field(..., max_length=65536)
    mcq_answer: Optional[int] = None
    run_only: bool = False

class DiscussionBody(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    body: str
    tag: Optional[str] = "general"
    task_id: Optional[str] = None

class ReplyBody(BaseModel):
    body: str

class VoteBody(BaseModel):
    vote: int = Field(..., ge=-1, le=1)

class ProfileBody(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    college: Optional[str] = None
    github_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    website_url: Optional[str] = None

class CompanyBody(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    domain: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None

class JobBody(BaseModel):
    title: str
    description: Optional[str] = None
    skills_required: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None

class InterviewBody(BaseModel):
    title: str
    candidate_email: str
    duration_minutes: int = Field(default=60, ge=10, le=240)

class CodeSyncBody(BaseModel):
    code: str
    language: str = "python3"

class MsgBody(BaseModel):
    content: str

class ReferralBody(BaseModel):
    code: str = Field(..., min_length=8, max_length=8)

class GitHubBody(BaseModel):
    github_username: str

class TwoFABody(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)

class AIReviewBody(BaseModel):
    code: str
    language: str = "python3"
    problem_title: Optional[str] = None

class PaymentBody(BaseModel):
    plan: str
    billing_cycle: str = "monthly"

class ContactBody(BaseModel):
    candidate_user_id: str
    message: Optional[str] = None

class ForgotPasswordBody(BaseModel):
    email: str

class ResetPasswordBody(BaseModel):
    token: str
    new_password: str


# ═══════════════════════════════════════════════════════════════════════════════
# ── ROUTES ─────────────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

# ── Meta ──────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Meta"])
def health():
    return {"status": "ok", "version": "2.0.0", "framework": "FastAPI + uvicorn"}


# ── Auth ──────────────────────────────────────────────────────────────────────
@app.post("/auth/register", tags=["Auth"])
def register(b: RegisterBody, req: Request):
    from skillos.auth.service import register as register_user, create_token
    user = register_user(b.email, b.password, b.display_name)
    token = create_token(user["id"], user["email"], user["role"])
    return {"token": token, "user": user}

@app.post("/auth/login", tags=["Auth"])
def login(b: LoginBody, req: Request):
    # Rate limit: 10 login attempts per minute per IP
    from skillos.auth.service import login as login_user
    ip = (req.client.host if req.client else "unknown") or "unknown"
    ua = req.headers.get("User-Agent", "") or ""
    return login_user(b.email, b.password, b.totp_code, ip, ua)

@app.post("/auth/send-verification", tags=["Auth"])
def send_verification(u=Depends(_current_user)):
    """Send email verification link."""
    from skillos.auth.email_service import send_verification_email
    from skillos.db.database import fetchone as _fo
    user = _fo("SELECT email, display_name, is_email_verified FROM users WHERE id=?", (u["id"],))
    if user and user["is_email_verified"]:
        return {"message": "Email already verified"}
    send_verification_email(user["email"], user["display_name"] or "User", u["id"])
    return {"message": "Verification email sent!"}

@app.get("/auth/verify-email", tags=["Auth"])
def verify_email(token: str):
    """Verify email from link."""
    from skillos.auth.email_service import verify_token
    from skillos.db.database import get_db as _gdb
    result = verify_token(token, "email_verify")
    if not result:
        return JSONResponse(status_code=400, content={"error": "Invalid or expired token"})
    db = _gdb()
    db.execute("UPDATE users SET is_email_verified=1 WHERE id=?", (result["user_id"],))
    db.commit()
    # Redirect to frontend
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="https://skill-os-omega.vercel.app?verified=1")

@app.post("/auth/forgot-password", tags=["Auth"])
def forgot_password(b: ForgotPasswordBody):
    from skillos.auth.service import forgot_password as _fp
    return _fp(b.email)

@app.post("/auth/reset-password", tags=["Auth"])
def reset_password(b: ResetPasswordBody):
    from skillos.auth.service import reset_password as _rp
    return _rp(b.token, b.new_password)

@app.post("/auth/google", tags=["Auth"])
def google_auth(req: Request):
    from skillos.auth.google import authenticate_google_user
    body = _body(req)
    credential = body.get("credential", "")
    if not credential:
        raise HTTPException(400, "Missing credential")
    token, user = authenticate_google_user(credential)
    return {"token": token, "user": user}

# 2FA
@app.post("/auth/2fa/setup", tags=["Auth"])
def setup_2fa(u=Depends(_current_user)):
    from skillos.auth.service import setup_2fa_begin as _s2fa; begin_setup = lambda uid: _s2fa(uid)
    return begin_setup(u["id"])

@app.post("/auth/2fa/confirm", tags=["Auth"])
def confirm_2fa(b: TwoFABody, u=Depends(_current_user)):
    from skillos.auth.totp import confirm_setup
    return confirm_setup(u["id"], b.code)

@app.post("/auth/2fa/verify", tags=["Auth"])
def verify_2fa(req: Request):
    from skillos.auth.totp import verify_totp
    body = _body(req)
    return verify_totp(body.get("user_id", ""), body.get("code", ""))

@app.post("/auth/2fa/disable", tags=["Auth"])
def disable_2fa(b: TwoFABody, u=Depends(_current_user)):
    from skillos.auth.totp import disable_totp
    return disable_totp(u["id"], b.code)

# Sessions
@app.get("/auth/sessions", tags=["Auth"])
def sessions(u=Depends(_current_user)):
    from skillos.auth.device_tracker import get_login_history as get_sessions
    return {"sessions": get_sessions(u["id"])}

@app.get("/auth/login-history", tags=["Auth"])
def login_history(u=Depends(_current_user)):
    from skillos.auth.device_tracker import get_login_history
    return {"history": get_login_history(u["id"])}

@app.post("/auth/sessions/{sid}/revoke", tags=["Auth"])
def revoke_session(sid: str, u=Depends(_current_user)):
    from skillos.auth.device_tracker import revoke_session as _r
    return _r(u["id"], sid)

@app.post("/auth/sessions/revoke-all", tags=["Auth"])
def revoke_all(u=Depends(_current_user)):
    from skillos.auth.device_tracker import revoke_all_sessions
    return revoke_all_sessions(u["id"])


# ── Submissions ───────────────────────────────────────────────────────────────
@app.post("/submit", tags=["Submissions"])
def submit(b: SubmitBody, u=Depends(_current_user)):
    from skillos.submissions.service import create_submission
    return create_submission(u["id"], b.task_id, b.code, b.language, getattr(b, "mcq_answer", None))

@app.get("/submission/{sid}", tags=["Submissions"])
def get_submission(sid: str, u=Depends(_current_user)):
    from skillos.submissions.service import get_submission as _g
    s = _g(sid)
    if not s: raise HTTPException(404, "Not found")
    if s.get("user_id") != u["id"]: raise HTTPException(403, "Forbidden")
    return s

@app.get("/users/me/submissions", tags=["Submissions"])
def my_submissions(u=Depends(_current_user)):
    from skillos.db.database import fetchall as _fa3; get_user_submissions = lambda uid: _fa3("SELECT * FROM submissions WHERE user_id=? ORDER BY submitted_at DESC LIMIT 50", (uid,))
    return {"submissions": get_user_submissions(u["id"])}


# ── Problems ──────────────────────────────────────────────────────────────────
@app.get("/tasks", tags=["Problems"])
def tasks(req: Request, u=Depends(_current_user)):
    from skillos.db.database import fetchall
    p = req.query_params
    rows = fetchall("""
        SELECT t.*, s.name AS skill_name, s.domain
        FROM tasks t LEFT JOIN skills s ON s.id = t.skill_id
        WHERE t.is_published=1
        ORDER BY t.created_at DESC LIMIT ?
    """, (int(p.get("limit", 200)),))
    return {"tasks": [dict(r) for r in rows]}

@app.get("/daily", tags=["Problems"])
def daily(u=Depends(_current_user)):
    from skillos.db.database import fetchone
    row = fetchone("SELECT * FROM tasks WHERE is_daily=1 ORDER BY created_at DESC LIMIT 1")
    return row or {"message": "No daily challenge set yet"}


# ── Skills ────────────────────────────────────────────────────────────────────
@app.get("/users/me/skills", tags=["Skills"])
def my_skills(u=Depends(_current_user)):
    from skillos.skills.service import get_user_skill_scores as get_user_skills
    return {"skills": get_user_skills(u["id"])}

@app.get("/users/me/skills/history", tags=["Skills"])
def skills_history(u=Depends(_current_user)):
    from skillos.skills.history import get_all_skill_history
    return {"history": get_all_skill_history(u["id"])}

@app.get("/users/me/skills/{skill_id}", tags=["Skills"])
def skill_detail(skill_id: str, u=Depends(_current_user)):
    from skillos.skills.service import get_skill_detail
    return get_skill_detail(u["id"], skill_id)

@app.get("/users/me/skills/{skill_id}/history", tags=["Skills"])
def skill_history(skill_id: str, u=Depends(_current_user)):
    from skillos.skills.history import get_skill_history
    return {"history": get_skill_history(u["id"], skill_id)}


# ── Profiles ──────────────────────────────────────────────────────────────────
@app.get("/users/me/profile", tags=["Profiles"])
def my_profile(u=Depends(_current_user)):
    from skillos.profiles.service import get_profile as get_my_profile
    return get_my_profile(u["id"])

@app.post("/users/me/profile", tags=["Profiles"])
def update_profile(b: ProfileBody, u=Depends(_current_user)):
    from skillos.profiles.service import update_profile as _up
    return _up(u["id"], b.dict(exclude_none=True))

@app.get("/users/{username}", tags=["Profiles"])
def public_profile(username: str):
    from skillos.profiles.service import get_public_profile
    p = get_public_profile(username)
    if not p: raise HTTPException(404, f"User '{username}' not found")
    return p

@app.get("/portfolio/{username}", tags=["Profiles"])
def portfolio(username: str):
    """Public developer portfolio page — no auth needed."""
    from skillos.profiles.service import get_public_profile
    p = get_public_profile(username)
    if not p: raise HTTPException(404, f"Portfolio for '{username}' not found")
    return p

@app.post("/users/me/avatar", tags=["Profiles"])
async def upload_avatar(req: Request, u=Depends(_current_user)):
    from skillos.profiles.photo import save_avatar
    body = await req.body()
    return save_avatar(u["id"], body)

@app.get("/users/{uid}/avatar", tags=["Profiles"])
def get_avatar(uid: str):
    from skillos.profiles.photo import get_avatar as _ga
    d = _ga(uid)
    if not d: raise HTTPException(404, "No avatar")
    return Response(content=d["data"], media_type=d["content_type"])


# ── Certifications ────────────────────────────────────────────────────────────
@app.get("/users/me/certifications", tags=["Certifications"])
def my_certs(u=Depends(_current_user)):
    from skillos.certifications.service import get_user_certifications
    return {"certifications": get_user_certifications(u["id"])}

@app.get("/certifications/types", tags=["Certifications"])
def cert_types(u=Depends(_current_user)):
    from skillos.db.database import fetchall as _fa; get_certification_types = lambda: _fa("SELECT * FROM certification_types")
    return {"types": get_certification_types()}

@app.post("/certifications/check", tags=["Certifications"])
def check_certs(u=Depends(_current_user)):
    from skillos.certifications.service import check_and_award_certifications as check_and_issue_certifications
    return check_and_issue_certifications(u["id"])

@app.get("/cert/{cert_id}", tags=["Certifications"])
def verify_cert(cert_id: str):
    from skillos.certifications.service import verify_certification
    c = verify_certification(cert_id)
    if not c: raise HTTPException(404, "Certificate not found")
    return c


# ── Leaderboard ───────────────────────────────────────────────────────────────
@app.get("/leaderboard",           tags=["Leaderboard"])
def lb_global(u=Depends(_current_user)):
    from skillos.leaderboard.service import get_global_leaderboard
    return {"leaderboard": get_global_leaderboard()}

@app.get("/leaderboard/weekly",    tags=["Leaderboard"])
def lb_weekly(u=Depends(_current_user)):
    from skillos.leaderboard.service import get_weekly_leaderboard
    return {"leaderboard": get_weekly_leaderboard()}

@app.get("/leaderboard/monthly",   tags=["Leaderboard"])
def lb_monthly(u=Depends(_current_user)):
    from skillos.leaderboard.service import get_monthly_leaderboard
    return {"leaderboard": get_monthly_leaderboard()}

@app.get("/leaderboard/college",   tags=["Leaderboard"])
def lb_college(college: str = "", u=Depends(_current_user)):
    from skillos.leaderboard.service import get_college_leaderboard
    return {"leaderboard": get_college_leaderboard(college)}

@app.get("/leaderboard/colleges",  tags=["Leaderboard"])
def lb_colleges(u=Depends(_current_user)):
    from skillos.leaderboard.service import get_colleges_list
    return {"colleges": get_colleges_list()}

@app.get("/leaderboard/skill/{domain}", tags=["Leaderboard"])
def lb_domain(domain: str, u=Depends(_current_user)):
    from skillos.leaderboard.service import get_domain_leaderboard
    return {"leaderboard": get_domain_leaderboard(domain)}


# ── Contests ──────────────────────────────────────────────────────────────────
@app.get("/contests", tags=["Contests"])
def contests(u=Depends(_current_user)):
    from skillos.contests.service import list_contests
    return {"contests": list_contests(u["id"])}

@app.get("/contests/{cid}", tags=["Contests"])
def contest_detail(cid: str, u=Depends(_current_user)):
    from skillos.contests.service import get_contest
    c = get_contest(cid, u["id"])
    if not c: raise HTTPException(404, "Contest not found")
    return {"contest": c}

@app.post("/contests/{cid}/register", tags=["Contests"])
def join_contest(cid: str, u=Depends(_current_user)):
    from skillos.contests.service import register_for_contest
    return register_for_contest(u["id"], cid)


# ── Learning ──────────────────────────────────────────────────────────────────
@app.get("/paths", tags=["Learning"])
def paths(u=Depends(_current_user)):
    from skillos.learning.service import list_paths
    return {"paths": list_paths()}

@app.get("/users/me/paths", tags=["Learning"])
def my_paths(u=Depends(_current_user)):
    from skillos.learning.service import get_user_paths
    return {"paths": get_user_paths(u["id"])}

@app.get("/paths/{pid}", tags=["Learning"])
def path_detail(pid: str, u=Depends(_current_user)):
    from skillos.learning.service import get_path
    p = get_path(pid, u["id"])
    if not p: raise HTTPException(404, "Path not found")
    return {"path": p}

@app.post("/paths/{pid}/steps/{sid}/complete", tags=["Learning"])
def complete_step(pid: str, sid: str, u=Depends(_current_user)):
    from skillos.learning.service import complete_step as _cs
    return {"path": _cs(u["id"], pid, sid)}


# ── Coaching ──────────────────────────────────────────────────────────────────
@app.get("/users/me/coaching", tags=["Coaching"])
def coaching(u=Depends(_current_user)):
    from skillos.coaching.service import get_coaching_report as generate_coaching_report
    return generate_coaching_report(u["id"])

@app.get("/users/me/badges", tags=["Coaching"])
def badges(u=Depends(_current_user)):
    from skillos.db.database import fetchall as _fetchall
    rows = _fetchall("SELECT * FROM user_certifications WHERE user_id=?", (u["id"],))
    return {"badges": [dict(r) for r in rows]}

@app.get("/users/me/reputation", tags=["Coaching"])
def reputation(u=Depends(_current_user)):
    from skillos.reputation.service import get_reputation_history
    return {"history": get_reputation_history(u["id"])}


# ── Community ─────────────────────────────────────────────────────────────────
@app.get("/discussions", tags=["Community"])
def discussions(u=Depends(_current_user)):
    from skillos.community.service import list_discussions
    return {"discussions": list_discussions()}

@app.post("/discussions", tags=["Community"])
def create_discussion(b: DiscussionBody, u=Depends(_current_user)):
    from skillos.community.service import create_discussion as _cd
    return _cd(u["id"], b.title, b.body, task_id=b.task_id)

@app.get("/discussions/{did}", tags=["Community"])
def discussion(did: str, u=Depends(_current_user)):
    from skillos.community.service import get_discussion
    d = get_discussion(did)
    if not d: raise HTTPException(404, "Not found")
    return {"discussion": d}

@app.post("/discussions/{did}/replies", tags=["Community"])
def reply(did: str, b: ReplyBody, u=Depends(_current_user)):
    from skillos.community.service import add_reply
    return add_reply(u["id"], did, b.body)

@app.post("/discussions/{did}/vote", tags=["Community"])
def vote(did: str, b: VoteBody, u=Depends(_current_user)):
    from skillos.community.service import vote as _v
    return _v(u["id"], "discussion", did, b.vote)

@app.get("/tasks/{tid}/discussions", tags=["Community"])
def task_discussions(tid: str, u=Depends(_current_user)):
    from skillos.community.service import list_discussions
    return {"discussions": list_discussions(task_id=tid)}


# ── Analytics ─────────────────────────────────────────────────────────────────
@app.get("/analytics",         tags=["Analytics"])
def analytics(u=Depends(_current_user)):
    from skillos.analytics.service import get_platform_stats
    return get_platform_stats()

@app.get("/analytics/skills",  tags=["Analytics"])
def analytics_skills(u=Depends(_current_user)):
    from skillos.analytics.service import get_skill_demand
    return {"skills": get_skill_demand()}

@app.get("/analytics/trends",  tags=["Analytics"])
def analytics_trends(u=Depends(_current_user)):
    from skillos.analytics.service import get_user_activity_trend
    return {"trends": get_user_activity_trend()}


# ── Company & Hiring ──────────────────────────────────────────────────────────
@app.get("/company",            tags=["Company"])
def my_company(u=Depends(_current_user)):
    from skillos.companies.service import get_user_company as get_company_for_user
    c = get_company_for_user(u["id"])
    if not c: raise HTTPException(404, "No company account")
    return {"company": c}

@app.post("/company/create",    tags=["Company"])
def create_company(b: CompanyBody, u=Depends(_current_user)):
    from skillos.companies.service import create_company as _cc
    return _cc(u["id"], b.name, b.domain or "", b.industry or "", b.size or "")

@app.get("/company/jobs",       tags=["Company"])
def company_jobs(u=Depends(_current_user)):
    from skillos.companies.service import get_company_jobs
    return {"jobs": get_company_jobs(u["id"])}

@app.post("/company/jobs/post", tags=["Company"])
def post_job(b: JobBody, u=Depends(_current_user)):
    from skillos.companies.service import post_job as _pj
    return _pj(u["id"], b.title, b.description or "", b.skills_required or "", b.location or "", b.salary_range or "")

@app.get("/company/pipeline",   tags=["Company"])
def pipeline(u=Depends(_current_user)):
    from skillos.companies.service import get_pipeline
    return {"pipeline": get_pipeline(u["id"])}

@app.post("/company/contact",   tags=["Company"])
def contact_candidate(b: ContactBody, u=Depends(_current_user)):
    from skillos.companies.service import send_contact_request
    return send_contact_request(u["id"], b.candidate_user_id, b.message or "")

@app.get("/candidates",         tags=["Company"])
def candidates(skill: str = "", min_score: int = 0, limit: int = 20, u=Depends(_current_user)):
    from skillos.db.database import fetchall as _fa2; search_candidates = lambda **kw: _fa2("SELECT id,display_name,email FROM users WHERE role='user' LIMIT 50")
    return {"candidates": search_candidates(skill=skill, min_score=min_score, limit=limit)}

@app.get("/jobs",               tags=["Company"])
def public_jobs(u=Depends(_current_user)):
    from skillos.companies.service import get_public_jobs
    return {"jobs": get_public_jobs()}


# ── Payments ──────────────────────────────────────────────────────────────────
@app.post("/payments/create-order", tags=["Payments"])
def payment_order(b: PaymentBody, u=Depends(_current_user)):
    from skillos.payments.service import create_order
    return create_order(u["id"], b.plan, b.billing_cycle)

@app.post("/payments/verify",       tags=["Payments"])
def verify_payment(req: Request, u=Depends(_current_user)):
    from skillos.payments.service import verify_payment as _vp
    return _vp(u["id"], _body(req))

@app.post("/payments/webhook",      tags=["Payments"])
async def payment_webhook(req: Request):
    from skillos.payments.service import handle_webhook
    body = await req.body()
    sig  = req.headers.get("X-Razorpay-Signature", "")
    return handle_webhook(body, sig)


# ── Projects ──────────────────────────────────────────────────────────────────
@app.get("/projects",                          tags=["Projects"])
def project_templates(u=Depends(_current_user)):
    from skillos.projects.service import list_templates as get_project_templates
    return {"projects": get_project_templates()}

@app.get("/users/me/projects",                 tags=["Projects"])
def my_projects(u=Depends(_current_user)):
    from skillos.projects.service import get_user_projects
    return {"projects": get_user_projects(u["id"])}

@app.post("/projects/{tid}/start",             tags=["Projects"])
def start_project(tid: str, u=Depends(_current_user)):
    from skillos.projects.service import start_project as _sp
    return _sp(u["id"], tid)

@app.post("/users/me/projects/{pid}/submit",   tags=["Projects"])
def submit_project(pid: str, req: Request, u=Depends(_current_user)):
    from skillos.projects.service import submit_project as _sub
    b = _body(req)
    return _sub(u["id"], pid, b.get("github_url",""), b.get("live_url",""), b.get("notes",""))


# ── Interviews ────────────────────────────────────────────────────────────────
@app.get("/interviews/stats", tags=["Interviews"])
def interview_stats(u=Depends(_current_user)):
    from skillos.interviews.service import get_interview_stats
    return get_interview_stats(u["id"])

@app.get("/interviews",                  tags=["Interviews"])
def list_interviews(u=Depends(_current_user)):
    from skillos.interviews.service import get_rooms_for_user
    return {"rooms": get_rooms_for_user(u["id"])}

@app.post("/interviews",                 tags=["Interviews"])
def create_interview(b: InterviewBody, u=Depends(_current_user)):
    from skillos.interviews.service import create_interview_room
    return {"room": create_interview_room(u["id"], b.title, b.candidate_email, b.duration_minutes)}

@app.get("/interviews/invite/{token}",   tags=["Interviews"])
def interview_by_invite(token: str):
    from skillos.interviews.service import get_room_by_invite
    r = get_room_by_invite(token)
    if not r: raise HTTPException(404, "Interview not found")
    return {"room": r}

@app.get("/interviews/{rid}",            tags=["Interviews"])
def get_interview(rid: str, u=Depends(_current_user)):
    from skillos.interviews.service import get_room
    r = get_room(rid, u["id"])
    if not r: raise HTTPException(404, "Not found")
    return {"room": r}

@app.post("/interviews/{rid}/start",     tags=["Interviews"])
def start_interview(rid: str, u=Depends(_current_user)):
    from skillos.interviews.service import start_room
    return {"room": start_room(rid, u["id"])}

@app.post("/interviews/{rid}/end",       tags=["Interviews"])
def end_interview(rid: str, req: Request, u=Depends(_current_user)):
    from skillos.interviews.service import end_room
    b = _body(req)
    return {"room": end_room(rid, u["id"], b.get("feedback",""), int(b.get("rating",0)))}

@app.post("/interviews/{rid}/code",      tags=["Interviews"])
def push_code(rid: str, b: CodeSyncBody, u=Depends(_current_user)):
    from skillos.interviews.service import update_code
    return update_code(rid, u["id"], b.code, b.language)

@app.post("/interviews/{rid}/message",   tags=["Interviews"])
def send_message(rid: str, b: MsgBody, u=Depends(_current_user)):
    from skillos.interviews.service import add_message
    return add_message(rid, u["id"], b.content)

@app.post("/interviews/{rid}/note",      tags=["Interviews"])
def add_note(rid: str, b: MsgBody, u=Depends(_current_user)):
    from skillos.interviews.service import add_interviewer_note
    return add_interviewer_note(rid, u["id"], b.content)

@app.post("/interviews/{rid}/hint",      tags=["Interviews"])
def send_hint(rid: str, u=Depends(_current_user)):
    from skillos.interviews.service import add_hint
    return add_hint(rid, u["id"], "Think about edge cases and time complexity.")


# ── WebSocket: Live Interview ──────────────────────────────────────────────────
_ws_rooms: dict[str, list[WebSocket]] = {}
_ws_lock = threading.Lock()

@app.websocket("/ws/interviews/{room_id}")
async def interview_ws(ws: WebSocket, room_id: str):
    """
    Real-time WebSocket for live interview code sync + chat.

    Message types (JSON):
      {"type":"code","code":"...","language":"python3"}   — broadcast code change
      {"type":"message","content":"..."}                   — chat message
      {"type":"cursor","line":5,"col":10}                  — cursor position
      {"type":"ping"}                                      — keepalive
    """
    await ws.accept()
    with _ws_lock:
        _ws_rooms.setdefault(room_id, []).append(ws)

    try:
        await ws.send_json({"type":"connected","room_id":room_id,"participants":len(_ws_rooms[room_id])})
        await _bcast(room_id, {"type":"joined","count":len(_ws_rooms[room_id])}, exclude=ws)

        while True:
            data = await ws.receive_json()
            t = data.get("type","")
            if t == "ping":
                await ws.send_json({"type":"pong"})
            else:
                if t == "code":
                    try:
                        from skillos.interviews.service import update_code
                        update_code(room_id, "ws", data.get("code",""), data.get("language","python3"))
                    except Exception: pass
                await _bcast(room_id, data, exclude=ws)
    except WebSocketDisconnect:
        with _ws_lock:
            if room_id in _ws_rooms:
                _ws_rooms[room_id] = [c for c in _ws_rooms[room_id] if c != ws]
        await _bcast(room_id, {"type":"left","count":len(_ws_rooms.get(room_id,[]))})
    except Exception:
        pass

async def _bcast(room_id: str, msg: dict, exclude: Optional[WebSocket] = None):
    with _ws_lock:
        conns = list(_ws_rooms.get(room_id, []))
    for c in conns:
        if c is not exclude:
            try: await c.send_json(msg)
            except Exception: pass


# ── Referrals ─────────────────────────────────────────────────────────────────
@app.get("/users/me/referrals",      tags=["Referrals"])
def my_referrals(u=Depends(_current_user)):
    from skillos.referrals.service import get_referral_stats
    return get_referral_stats(u["id"])

@app.post("/referrals/apply",        tags=["Referrals"])
def apply_referral(b: ReferralBody, u=Depends(_current_user)):
    from skillos.referrals.service import apply_invite_code
    return apply_invite_code(u["id"], b.code)

@app.get("/referrals/leaderboard",   tags=["Referrals"])
def referral_lb(u=Depends(_current_user)):
    from skillos.referrals.service import get_referral_leaderboard
    return {"leaderboard": get_referral_leaderboard()}

@app.get("/join/{code}",             tags=["Referrals"])
def join_code(code: str):
    from skillos.referrals.service import get_referral_by_code
    return get_referral_by_code(code)


# ── Notifications ─────────────────────────────────────────────────────────────
@app.get("/users/me/notifications",        tags=["Notifications"])
def notifications(u=Depends(_current_user)):
    from skillos.db.database import fetchall
    rows = fetchall("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50", (u["id"],))
    return {"notifications": [dict(r) for r in rows]}

@app.post("/users/me/notifications/read", tags=["Notifications"])
def read_notifications(u=Depends(_current_user)):
    from skillos.db.database import get_db
    db = get_db(); db.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (u["id"],)); db.commit()
    return {"ok": True}


# ── GitHub ────────────────────────────────────────────────────────────────────
@app.post("/github/connect",  tags=["GitHub"])
def connect_github(b: GitHubBody, u=Depends(_current_user)):
    from skillos.github.service import connect_github_account
    return connect_github_account(u["id"], b.github_username)

@app.get("/github/profile",   tags=["GitHub"])
def github_profile(u=Depends(_current_user)):
    from skillos.github.service import get_github_for_user
    d = get_github_for_user(u["id"])
    if not d: raise HTTPException(404, "No GitHub account connected")
    return d


# ── AI Code Review ────────────────────────────────────────────────────────────
@app.post("/ai/review", tags=["AI"])
def ai_review(b: AIReviewBody, u=Depends(_current_user)):
    from skillos.ai_review.service import review_code
    return review_code(u["id"], b.code, b.language, b.problem_title or "")


# ── Proctoring ────────────────────────────────────────────────────────────────
@app.post("/proctor/start",           tags=["Proctoring"])
def proctor_start(u=Depends(_current_user)):
    from skillos.evaluator.proctoring import start_session
    return start_session(u["id"])

@app.post("/proctor/{sid}/event",     tags=["Proctoring"])
def proctor_event(sid: str, req: Request, u=Depends(_current_user)):
    from skillos.evaluator.proctoring import record_event
    b = _body(req)
    return record_event(sid, b.get("event_type",""), b.get("data",{}))

@app.post("/proctor/{sid}/end",       tags=["Proctoring"])
def proctor_end(sid: str, u=Depends(_current_user)):
    from skillos.evaluator.proctoring import end_session
    return end_session(sid)


# ═══════════════════════════════════════════════════════════════════════════════
# ── Admin / Status Endpoints ───────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/admin/ai-status", tags=["Admin"])
def admin_ai_status(u=Depends(_current_user)):
    """
    Shows AI provider health status.
    Supports multi-key per provider: each key has its own health state.
    """
    from skillos.ai_review.service import get_provider_status, PROVIDER_ORDER
    return {
        "provider_order": PROVIDER_ORDER,
        "multi_key_support": True,
        "providers": get_provider_status(),
    }

@app.get("/admin/sandbox-status", tags=["Admin"])
def admin_sandbox_status(u=Depends(_current_user)):
    """Shows sandbox mode (Docker or subprocess), stats, and pre-warm status."""
    from skillos.evaluator.sandbox_manager import sandbox
    return sandbox.get_info()

@app.post("/admin/pull-images", tags=["Admin"])
def admin_pull_images(u=Depends(_current_user)):
    """Pre-pull Docker images for all supported languages (reduces cold-start latency)."""
    from skillos.evaluator.sandbox_manager import sandbox
    return sandbox.pull_images()

@app.get("/admin/system-status", tags=["Admin"])
def admin_system_status(u=Depends(_current_user)):
    """Full system health: server mode, sandbox, AI providers, DB."""
    from skillos.ai_review.service import get_provider_status, PROVIDER_ORDER
    from skillos.evaluator.sandbox_manager import sandbox
    return {
        "server": {
            "framework": "FastAPI + uvicorn",
            "version":   "2.0.0",
        },
        "sandbox": sandbox.get_info(),
        "ai": {
            "provider_order":    PROVIDER_ORDER,
            "multi_key_support": True,
            "providers":         get_provider_status(),
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ── Error handlers ─────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

from skillos.shared.exceptions import SkillOSError, ValidationError

@app.exception_handler(SkillOSError)
async def _skillos_err(req: Request, exc: SkillOSError):
    return JSONResponse(400, {"error": str(exc)})

@app.exception_handler(ValidationError)
async def _val_err(req: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"error": str(exc)})

@app.exception_handler(Exception)
async def _generic_err(req: Request, exc: Exception):
    import traceback; traceback.print_exc()
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


# ── Utility ───────────────────────────────────────────────────────────────────
def _body(req: Request) -> dict:
    """Synchronously read the cached request body as JSON (for sync routes)."""
    try:
        import asyncio
        body_bytes = asyncio.get_event_loop().run_until_complete(req.body())
        return json.loads(body_bytes) if body_bytes else {}
    except Exception:
        return {}

@app.get("/github/profile", tags=["Profile"])
def github_profile(u=Depends(_current_user)):
    return {"github": None, "message": "GitHub integration coming soon"}

@app.get("/portfolio/{username}", tags=["Profile"])
def portfolio(username: str):
    user = fetchone("SELECT id, display_name, bio, avatar_url FROM users WHERE username=?", (username,))
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    return dict(user)

@app.post("/users/me/avatar", tags=["Profile"])
async def upload_avatar(req: Request, u=Depends(_current_user)):
    """Upload profile avatar — accepts base64 encoded image."""
    body = await req.json()
    avatar_data = body.get("avatar", "")
    if not avatar_data:
        raise HTTPException(400, "No avatar data")
    
    # Validate it's a valid base64 image
    import base64, re
    if not re.match(r'^data:image/(jpeg|jpg|png|gif|webp);base64,', avatar_data):
        raise HTTPException(400, "Invalid image format. Use base64 encoded JPEG/PNG")
    
    # Store as base64 in DB (for small avatars) or save to file
    avatar_path = f"/home/jammisuyash/SkillOS/avatars/{u['id']}.jpg"
    os.makedirs(os.path.dirname(avatar_path), exist_ok=True)
    
    # Save base64 data URL directly to user profile
    db = get_db()
    db.execute("UPDATE users SET avatar_url=? WHERE id=?", (avatar_data, u["id"]))
    db.commit()
    return {"avatar_url": avatar_data, "message": "Avatar updated"}

@app.get("/avatars/{user_id}", tags=["Profile"])
def get_avatar(user_id: str):
    from skillos.db.database import fetchone as _fo
    user = _fo("SELECT avatar_url FROM users WHERE id=?", (user_id,))
    if not user or not user["avatar_url"]:
        raise HTTPException(404, "No avatar")
    return {"avatar_url": user["avatar_url"]}

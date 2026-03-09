# SkillOS — How to Run

## Quick Start (3 steps)

```bash
# 1. Copy and configure environment
cp .env.example .env
# Open .env and fill in your API keys (see below)

# 2. Validate your setup
python scripts/validate_setup.py

# 3. Start the server
./START_MAC_LINUX.sh       # Mac / Linux
START_WINDOWS.bat          # Windows
```

Server is at: **http://localhost:8000**
Swagger UI: **http://localhost:8000/docs**

---

## What changed: FastAPI is now the default

| Before | After |
|--------|-------|
| `python -m skillos.main` | `uvicorn skillos.api.fastapi_app:app` |
| stdlib `http.server` | FastAPI + uvicorn (ASGI, async) |
| Single-threaded | Thousands of concurrent connections |
| No docs | Swagger UI at `/docs`, ReDoc at `/redoc` |
| No WebSockets | Real-time interview rooms |

The old `python -m skillos.main` still works as a fallback if FastAPI is not installed.

---

## Option B: Docker Compose (Recommended for Production-like Dev)

```bash
cp .env.example .env
# Edit .env with your API keys

docker-compose up
# Backend:  http://localhost:8000
# Frontend: http://localhost:5173
# Swagger:  http://localhost:8000/docs
```

This starts: FastAPI backend + React frontend + PostgreSQL + Redis + Celery worker.
Code execution runs in isolated Docker containers automatically.

---

## AI Providers Setup (Multi-Key Support)

SkillOS uses 4 AI providers with automatic fallback:
**Groq → Gemini → Anthropic → OpenAI → rule-based**

Each provider supports **multiple keys** (comma-separated). Keys are used in round-robin
rotation. Failed or rate-limited keys are automatically skipped and retried after cooldown.

```bash
# Single key per provider:
GROQ_API_KEY=gsk_abc123
ANTHROPIC_API_KEY=sk-ant-abc123

# Multiple keys per provider (rotation + automatic failover):
GROQ_API_KEY=gsk_key1,gsk_key2,gsk_key3
ANTHROPIC_API_KEY=sk-ant-key1,sk-ant-key2
```

| Provider | Where to Get Key | Free Tier |
|----------|-----------------|-----------| 
| Groq     | https://console.groq.com | Very generous (free) |
| Gemini   | https://aistudio.google.com/app/apikey | 1500 req/day free |
| Anthropic | https://console.anthropic.com | Pay-per-use (~$0.001/review) |
| OpenAI   | https://platform.openai.com/api-keys | Pay-per-use (~$0.002/review) |

You don't need all 4. Even zero keys works (uses rule-based analysis).

Check which providers are active and healthy:
```
GET http://localhost:8000/admin/ai-status   (requires JWT token)
```

---

## Code Execution Sandbox

### Modes

| Mode | Safety | When Used |
|------|--------|-----------|
| Docker sandbox | Full isolation (production-safe) | Docker is running + SKILLOS_USE_DOCKER=true or auto |
| Subprocess sandbox | Process-level limits only | Docker not available or SKILLOS_USE_DOCKER=false |

### Enable Docker Sandbox

```bash
# Make sure Docker is running
sudo systemctl start docker   # Linux
# or start Docker Desktop      # Mac/Windows

# Set in .env:
SKILLOS_USE_DOCKER=true

# Optional: pre-pull language images at startup (reduces cold-start):
SANDBOX_PREWARM=true
```

Docker sandbox provides:
- Filesystem isolation (read-only host, /tmp only writable)
- Network disabled (--network none)
- CPU + memory hard limits
- PID limits (prevents fork bombs)
- No privilege escalation

Check sandbox mode:
```
GET http://localhost:8000/admin/sandbox-status   (requires JWT token)
```

Manually pre-pull Docker images:
```
POST http://localhost:8000/admin/pull-images     (requires JWT token)
```

---

## Database

| Mode | When | How |
|------|------|-----|
| SQLite | `DATABASE_URL` not set | Automatic, zero setup, dev only |
| PostgreSQL | `DATABASE_URL=postgresql://...` | Get free at neon.tech |

Migrations run automatically on startup.

---

## Deployment

### Railway (Backend)
```yaml
# Procfile (already configured):
web: uvicorn skillos.api.fastapi_app:app --host 0.0.0.0 --port $PORT --workers 4
```

Add environment variables from `.env` in Railway dashboard.

### Vercel (Frontend)
Set root directory to `frontend`, add `VITE_API_URL=https://your-railway-url.railway.app`.

### Required Environment Variables for Production
```
DATABASE_URL        -> from neon.tech
REDIS_URL           -> from upstash.com
SKILLOS_SECRET_KEY  -> python3 -c "import secrets; print(secrets.token_hex(32))"
SKILLOS_ENV         -> production
SKILLOS_USE_DOCKER  -> true (if Docker available on your platform)
GROQ_API_KEY        -> from console.groq.com
GEMINI_API_KEY      -> from aistudio.google.com
ANTHROPIC_API_KEY   -> from console.anthropic.com
OPENAI_API_KEY      -> from platform.openai.com
RAZORPAY_KEY_ID     -> from dashboard.razorpay.com
RAZORPAY_KEY_SECRET -> from dashboard.razorpay.com
SMTP_USER           -> your Gmail address
SMTP_PASS           -> Gmail app password
GOOGLE_CLIENT_ID    -> from console.cloud.google.com
APP_URL             -> https://your-vercel-app.vercel.app
```

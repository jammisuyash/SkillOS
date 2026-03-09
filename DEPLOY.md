# SkillOS v7 — Complete Deployment Guide
# From Zero to Production in 30 Minutes

---

## Stack Overview

| Layer      | Technology          | Free Host            | Cost         |
|------------|---------------------|----------------------|--------------|
| Frontend   | React + Vite        | Vercel               | Free forever |
| Backend    | FastAPI + Python    | Railway / Render     | Free tier    |
| Database   | PostgreSQL          | Neon / Supabase      | Free 3GB     |
| Queue      | Redis + Celery      | Railway Redis        | Free tier    |
| CDN        | Cloudflare          | Cloudflare           | Free forever |
| Domain     | Custom domain       | Any registrar        | ₹800/year    |

**Total cost: ₹800/year** (just the domain)

---

## 1. Local Development Setup

### Prerequisites
- Python 3.12+
- Node.js 20+
- Docker (optional but recommended)

### Option A: Docker Compose (Easiest)
```bash
# Clone and start everything with one command
git clone https://github.com/YOUR_USERNAME/skillos
cd skillos
cp .env.example .env
# Edit .env with your API keys (optional for local dev)
docker-compose up
```

Services will start at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Celery Monitor: http://localhost:5555

### Option B: Manual Setup
```bash
# Backend
pip install -r requirements.txt
cp .env.example .env
uvicorn skillos.api.fastapi_app:app --reload --port 8000

# Frontend (in a new terminal)
cd frontend
npm install
npm run dev

# Celery worker (in another terminal)
celery -A skillos.worker_celery worker --loglevel=info
```

---

## 2. Database Setup

### SQLite (Default — Zero Config)
Works out of the box. Database stored at `/tmp/skillos_dev.db`.

### PostgreSQL (Production — Free with Neon)
1. Go to https://neon.tech → Create account → New project → "skillos"
2. Copy the connection string (looks like `postgresql://user:pass@host/skillos`)
3. Set `DATABASE_URL=postgresql://...` in your environment

That's it. The app auto-detects and switches to PostgreSQL.

---

## 3. Deploy to Railway (Recommended)

### Backend
1. Go to https://railway.app → New Project → Deploy from GitHub
2. Select your SkillOS repository
3. Railway auto-detects Python and reads `railway.json`
4. Add environment variables:
   ```
   SKILLOS_SECRET_KEY=<generate 32 random chars>
   SKILLOS_ENV=production
   DATABASE_URL=<from Neon>
   ANTHROPIC_API_KEY=<optional, for AI review>
   GITHUB_TOKEN=<optional, for GitHub integration>
   RAZORPAY_KEY_ID=<for payments>
   RAZORPAY_KEY_SECRET=<for payments>
   ```
5. Click Deploy → Your API is live at `https://yourapp.railway.app`

### Add Redis
In Railway dashboard → New Service → Redis → Copy `REDIS_URL` → Add to backend env vars

### Worker
Add a new Railway service → Same repo → Start command:
```
celery -A skillos.worker_celery worker --loglevel=info
```

---

## 4. Deploy Frontend to Vercel

1. Go to https://vercel.com → New Project → Import your GitHub repo
2. Set Root Directory to `frontend`
3. Add environment variable: `VITE_API_URL=https://yourapp.railway.app`
4. Deploy → Your app is live at `https://yourdomain.vercel.app`

### Custom Domain
In Vercel: Settings → Domains → Add your domain
Point your domain's DNS to Vercel's nameservers.

---

## 5. Environment Variables Reference

### Backend
| Variable | Required | Description |
|---|---|---|
| `SKILLOS_SECRET_KEY` | ✅ Yes | JWT signing secret (32+ random chars) |
| `SKILLOS_ENV` | ✅ Yes | `development` or `production` |
| `DATABASE_URL` | No | PostgreSQL URL (SQLite if not set) |
| `REDIS_URL` | No | Redis URL (threading fallback if not set) |
| `ANTHROPIC_API_KEY` | No | Enables AI code review |
| `GITHUB_TOKEN` | No | Higher GitHub API rate limits |
| `RAZORPAY_KEY_ID` | No | Enables payments |
| `RAZORPAY_KEY_SECRET` | No | Enables payments |
| `SMTP_USER` | No | Gmail for email notifications |
| `SMTP_PASS` | No | Gmail app password |
| `APP_URL` | No | Your frontend URL (for email links) |
| `GOOGLE_CLIENT_ID` | No | Google OAuth login |

### Frontend
| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | ✅ Yes | Backend URL |
| `VITE_GOOGLE_CLIENT_ID` | No | Google OAuth |

---

## 6. API Documentation

Once running, interactive API docs are available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 7. Architecture

```
Internet → Cloudflare CDN
                ↓
         Vercel (Frontend)
                ↓ API calls
        Railway (FastAPI)
           /          \
    Neon (PostgreSQL)  Railway (Redis)
                            ↓
                    Celery Workers
                    (code evaluation,
                     cert checks, emails)
```

---

## 8. Celery Task Queue

Start workers for background tasks:
```bash
# All queues
celery -A skillos.worker_celery worker --loglevel=info

# Monitor (web UI at localhost:5555)
celery -A skillos.worker_celery flower

# Scheduled tasks (analytics, cleanup)
celery -A skillos.worker_celery beat
```

Queues:
- `evaluation` — Code submission evaluation (high priority)
- `awards` — Badge and certification checking
- `emails` — Notification emails  
- `analytics` — Leaderboard recalculation, analytics aggregation

---

## 9. Production Checklist

- [ ] Set `SKILLOS_SECRET_KEY` to a strong 32+ character random string
- [ ] Set `SKILLOS_ENV=production`
- [ ] Use PostgreSQL (not SQLite) in production
- [ ] Set up Redis for Celery job queue
- [ ] Configure Cloudflare in front of both frontend and backend
- [ ] Add your domain to Vercel + Railway
- [ ] Set up Razorpay for payments
- [ ] Configure Gmail SMTP for email notifications
- [ ] Set up Sentry for error monitoring (optional)
- [ ] Enable GitHub Actions for CI/CD (optional)

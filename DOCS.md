# SkillOS — Full Documentation

## Features (27 Total — All Implemented)

| # | Feature | Details |
|---|---------|---------|
| 1 | Auth | Email/Google/2FA/sessions/rate-limit/device-tracking |
| 2 | Profiles | Username, bio, streak, public page |
| 3 | Skill Graph | 6 domains, score by submission quality |
| 4 | Problem Platform | 12 problems, test cases, difficulty |
| 5 | Code Editor | Python 3, sandboxed, live result |
| 6 | Code Execution | Process sandbox, time/output limits |
| 7 | Submission System | Async queue, worker, polling |
| 8 | Skill Scoring | quality × recency factor |
| 9 | Leaderboard | Global, weekly, per-domain |
| 10 | Contests | Create, register, score, rank |
| 11 | Learning Paths | 4 paths, step progress |
| 12 | AI Coach | Rule-based analysis + recommendations |
| 13 | Recruiter Platform | Search, contact pipeline |
| 14 | Company Dashboard | Jobs, team, contact requests |
| 16 | Certifications | Auto-awarded, shareable link |
| 17 | Project Evaluation | GitHub repo submission |
| 19 | Community | Discussions, replies, votes |
| 20 | Reputation | Points, badges, event log |
| 21 | Analytics | Platform stats, skill demand |
| 23 | Security | RBAC, 2FA, rate-limiting, CAPTCHA-ready |
| 24 | Database | 13 migrations, SQLite → swap to Postgres |
| 26 | Monetization | Razorpay (₹2,999/₹7,999/₹24,999 plans) |

## Environment Variables

```bash
SKILLOS_SECRET_KEY=changeme            # Required: JWT secret
SKILLOS_DB_PATH=/var/data/skillos.db   # Default: /tmp/skillos_dev.db
SKILLOS_HOST=0.0.0.0
SKILLOS_PORT=8000
GOOGLE_CLIENT_ID=...                   # Optional: Google OAuth
SMTP_HOST=smtp.gmail.com               # Optional: Email sending
SMTP_USER=you@gmail.com
SMTP_PASS=app-password
APP_URL=https://yourdomain.com
RAZORPAY_KEY_ID=rzp_live_...          # Optional: Payments
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
```

## Deployment (free tier)

| Service | Purpose | Free |
|---------|---------|------|
| Railway/Render | Backend | ✓ |
| Neon/Turso | Postgres/SQLite | ✓ 500MB |
| Vercel | Frontend | ✓ |
| Cloudflare | CDN + HTTPS | ✓ |
| Gmail SMTP | Email | ✓ 500/day |
| Razorpay | Payments | ✓ 2%/txn |
| Google OAuth | Auth | ✓ |

## Upgrading from SQLite to PostgreSQL

1. Change `SKILLOS_DB_PATH` to your Postgres connection string (starts with `postgresql://`)
2. The database module auto-detects the dialect


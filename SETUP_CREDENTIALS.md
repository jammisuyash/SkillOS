# SkillOS — Credentials Setup Guide

Everything runs in **dev mode** with zero credentials.
Add these env vars to go live, one by one as you need them.

---

## 1. 🤖 AI Skill Coach — Claude API (Free credits to start)

```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
```

- Sign up: https://console.anthropic.com
- Free tier: $5 credits (enough for ~5,000 coaching reports)
- Cost per report: ~$0.001 (very cheap)

Without this → coach uses smart rule-based analysis (still works, just not AI)

---

## 2. 💳 Payments — Razorpay (Free, 2% per transaction)

```bash
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxx
RAZORPAY_WEBHOOK_SECRET=xxxxxxxxxxxxxxxxxxxx  # optional
```

- Sign up: https://razorpay.com (free account)
- Get keys: Dashboard → Settings → API Keys
- Test keys start with `rzp_test_` — no real money
- Live keys start with `rzp_live_` — real payments

Without this → payment buttons show "Dev mode" message

---

## 3. 🔑 Google Login — OAuth (Free forever)

```bash
GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
```

- Go to: https://console.cloud.google.com
- Create project → APIs → Credentials → OAuth 2.0 Client ID
- Authorized origins: your domain (e.g. https://skillos.com)

Without this → Google login button is hidden

---

## 4. 📧 Email — Gmail SMTP (Free up to 500/day)

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=your-app-password  # NOT your Gmail password — use App Passwords
APP_URL=https://yourskillos.com
```

- Enable 2FA on Gmail → Settings → App Passwords → Generate
- Without this → emails print to console (dev mode)

---

## 5. 🔐 Secret Key (REQUIRED for production)

```bash
SKILLOS_SECRET_KEY=change-this-to-a-long-random-string-in-production
```

Generate one: `python3 -c "import secrets; print(secrets.token_hex(32))"`

---

## Full .env file example

```bash
# Required for production
SKILLOS_SECRET_KEY=your-secret-key-here

# Optional — each unlocks a feature
ANTHROPIC_API_KEY=sk-ant-api03-...
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
GOOGLE_CLIENT_ID=....apps.googleusercontent.com
SMTP_HOST=smtp.gmail.com
SMTP_USER=you@gmail.com
SMTP_PASS=your-app-password
APP_URL=https://yourskillos.com

# Database (default: /tmp/skillos_dev.db)
SKILLOS_DB_PATH=/var/data/skillos.db
```

---

## Running locally

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m skillos.main

# Frontend (in another terminal)
cd frontend
npm install
npm run dev
```

Backend runs on: http://localhost:8000
Frontend runs on: http://localhost:5173

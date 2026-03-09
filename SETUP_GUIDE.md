# SkillOS — Setup Guide: AI Coach + Code Editor + Payments

---

## 1️⃣ AI COACH — Make it Real AI (not rule-based)

**FREE. Takes 5 minutes.**

1. Go to **https://console.anthropic.com** → Sign up
2. Click **API Keys** → **Create Key** 
3. Copy the key (starts `sk-ant-api03-...`)
4. Add to your `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
   ```

**Free credits:** $5 on signup = ~5,000 coaching reports. After that ~$0.001/report.

**What changes:** The AI now reads the developer's real data — skill scores, submission patterns, streaks, contest performance — and gives a genuinely personalised report with a 7-day plan, career path prediction, and specific weakness analysis. Not generic advice.

---

## 2️⃣ CODE EDITOR — All Languages Fixed

**The multi-language bug is now fixed.** Previously only Python worked. Now Python, JavaScript, Java, C++, C, Go, and Rust all work — the Monaco Editor (VS Code's editor) is already running in the browser with syntax highlighting + autocomplete for all of them.

**To run code in all languages, install runtimes on your server:**

```bash
# On Ubuntu/Debian (Railway, Render, etc.)
sudo apt-get install -y nodejs default-jdk build-essential golang-go

# Python is usually pre-installed
python3 --version

# Rust (optional)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

**If using Docker** (recommended for production), add this `Dockerfile` to your project:

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y nodejs npm default-jdk build-essential golang-go && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "-m", "skillos"]
```

If a runtime isn't installed, the error message is clear: `"Runtime 'node' not found on this server"` — it never crashes silently.

---

## 3️⃣ PAYMENTS — Real Money via Razorpay

**Free to sign up. No monthly fee. Only 2% per transaction.**

**Step 1: Create account**
1. Go to **https://razorpay.com** → Sign Up (free)
2. For live payments, complete KYC (takes 1-2 days)

**Step 2: Get keys**
1. Dashboard → Settings → API Keys → Generate Test Key
2. Add to `.env`:
   ```
   RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxxxxx
   RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
   ```

**Step 3: Test with these card details**
- Card: `4111 1111 1111 1111`
- Expiry: any future date | CVV: any 3 digits | OTP: `1234`

**Step 4: Go live** → Switch to `rzp_live_` keys after KYC approval

**Plans already configured:**
- Starter: ₹2,999/mo (10 recruiter contacts)
- Growth: ₹7,999/mo (50 contacts)  
- Enterprise: ₹24,999/mo (unlimited)

---

## 4️⃣ Complete .env Setup

```bash
cp .env.example .env
# Then fill in all values — see .env.example for detailed instructions
```

| Variable | Where to get it | Cost |
|----------|----------------|------|
| `SKILLOS_SECRET_KEY` | Generate: `python3 -c "import secrets; print(secrets.token_hex(32))"` | Free |
| `ANTHROPIC_API_KEY` | console.anthropic.com | $5 free credits |
| `SMTP_USER` + `SMTP_PASS` | Gmail App Passwords | Free |
| `GOOGLE_CLIENT_ID` | console.cloud.google.com | Free |
| `RAZORPAY_KEY_ID` + `RAZORPAY_KEY_SECRET` | razorpay.com | Free + 2%/txn |

---

## 5️⃣ Free Deployment

| What | Where | Cost |
|------|-------|------|
| Backend | Railway (`railway up`) | Free |
| Frontend | Vercel (`vercel`) | Free |
| Database | SQLite included / Neon for PostgreSQL | Free |
| CDN + HTTPS | Cloudflare | Free |
| Domain | Namecheap | ~₹800/year |

**Total: ₹0/month (₹800/year if you want a domain)**

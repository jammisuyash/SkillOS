#!/usr/bin/env python3
"""
scripts/validate_setup.py

SkillOS Setup Validator
========================
Checks your environment and API keys before starting the server.

Usage:
    python scripts/validate_setup.py
"""

import os
import sys
import subprocess
import urllib.request
import urllib.error
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ANSI colors
G = "\033[92m"  # green
Y = "\033[93m"  # yellow
R = "\033[91m"  # red
B = "\033[94m"  # blue
RESET = "\033[0m"
BOLD  = "\033[1m"

def ok(msg):  print(f"  {G}[OK]{RESET}  {msg}")
def warn(msg): print(f"  {Y}[!!]{RESET}  {msg}")
def err(msg):  print(f"  {R}[XX]{RESET}  {msg}")
def info(msg): print(f"  {B}[--]{RESET}  {msg}")

errors = []
warnings = []


print(f"\n{BOLD}SkillOS Setup Validator{RESET}")
print("=" * 60)


# ── 1. Python version ─────────────────────────────────────────────────────────
print(f"\n{BOLD}Python{RESET}")
v = sys.version_info
if v >= (3, 10):
    ok(f"Python {v.major}.{v.minor}.{v.micro}")
elif v >= (3, 8):
    warn(f"Python {v.major}.{v.minor} -- Python 3.10+ recommended")
    warnings.append("Upgrade to Python 3.10+")
else:
    err(f"Python {v.major}.{v.minor} -- Python 3.8+ required")
    errors.append("Python 3.8+ required")


# ── 2. Required packages ──────────────────────────────────────────────────────
print(f"\n{BOLD}Python Packages{RESET}")
required = [
    ("fastapi",          "pip install 'fastapi[all]'"),
    ("uvicorn",          "pip install 'uvicorn[standard]'"),
    ("pydantic",         "pip install pydantic"),
    ("jwt",              "pip install PyJWT"),
    ("bcrypt",           "pip install bcrypt"),
]
optional = [
    ("anthropic",        "pip install anthropic"),
    ("openai",           "pip install openai"),
    ("google.generativeai", "pip install google-generativeai"),
    ("groq",             "pip install groq"),
    ("celery",           "pip install celery[redis]"),
    ("dotenv",           "pip install python-dotenv"),
]

for pkg, install_cmd in required:
    try:
        __import__(pkg)
        ok(f"{pkg}")
    except ImportError:
        err(f"{pkg} not installed -- run: {install_cmd}")
        errors.append(f"Missing package: {pkg}")

for pkg, install_cmd in optional:
    try:
        __import__(pkg)
        ok(f"{pkg} (optional)")
    except ImportError:
        warn(f"{pkg} not installed (optional) -- run: {install_cmd}")


# ── 3. Required env vars ──────────────────────────────────────────────────────
print(f"\n{BOLD}Environment Variables{RESET}")

secret = os.environ.get("SKILLOS_SECRET_KEY", "")
if not secret:
    err("SKILLOS_SECRET_KEY not set")
    errors.append("SKILLOS_SECRET_KEY required")
elif secret == "change-this-to-a-32-character-random-string":
    warn("SKILLOS_SECRET_KEY is still the placeholder -- change it for production")
    warnings.append("Set a real SKILLOS_SECRET_KEY")
elif len(secret) < 32:
    warn(f"SKILLOS_SECRET_KEY is short ({len(secret)} chars) -- 32+ recommended")
else:
    ok(f"SKILLOS_SECRET_KEY ({len(secret)} chars)")

db_url = os.environ.get("DATABASE_URL", "")
if not db_url:
    info("DATABASE_URL not set -- will use SQLite (dev mode)")
else:
    ok(f"DATABASE_URL configured ({db_url[:30]}...)")


# ── 4. AI Provider Keys ───────────────────────────────────────────────────────
print(f"\n{BOLD}AI Providers (Multi-Key Support){RESET}")

providers = {
    "GROQ_API_KEY":      ("Groq",      "llama-3.3-70b -- fastest, free tier"),
    "GEMINI_API_KEY":    ("Gemini",    "gemini-2.0-flash, 1500 req/day free"),
    "ANTHROPIC_API_KEY": ("Anthropic", "claude-haiku-4-5, best code reasoning"),
    "OPENAI_API_KEY":    ("OpenAI",    "gpt-4o-mini, reliable fallback"),
}

ai_configured = 0
for env_var, (name, desc) in providers.items():
    raw = os.environ.get(env_var, "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if keys:
        if len(keys) > 1:
            ok(f"{name}: {len(keys)} keys configured (round-robin rotation) -- {desc}")
        else:
            ok(f"{name}: 1 key configured -- {desc}")
        ai_configured += 1
    else:
        warn(f"{name}: not configured -- {desc}")
        info(f"   Set {env_var}=your_key in .env")

if ai_configured == 0:
    warn("No AI providers configured -- will use rule-based analysis only")
    info("   Add at least one API key to .env for AI-powered code review")
    warnings.append("No AI providers configured")
else:
    info(f"Fallback chain active: Groq -> Gemini -> Anthropic -> OpenAI -> rule-based")


# ── 5. Docker sandbox ─────────────────────────────────────────────────────────
print(f"\n{BOLD}Code Execution Sandbox{RESET}")

force_docker = os.environ.get("SKILLOS_USE_DOCKER", "auto").lower()
docker_ok = False
try:
    result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
    docker_ok = (result.returncode == 0)
except (FileNotFoundError, subprocess.TimeoutExpired):
    docker_ok = False

if docker_ok:
    ok("Docker daemon is running")
    if force_docker == "false":
        warn("SKILLOS_USE_DOCKER=false -- subprocess sandbox will be used despite Docker being available")
    else:
        ok("Docker sandbox will be used (isolated, production-safe)")
    # Check Docker version
    try:
        r = subprocess.run(["docker", "--version"], capture_output=True, timeout=3)
        info(r.stdout.decode().strip())
    except Exception:
        pass
else:
    warn("Docker daemon is NOT running (or not installed)")
    if force_docker == "true":
        err("SKILLOS_USE_DOCKER=true but Docker is not available")
        errors.append("Docker required but not available")
    else:
        info("Subprocess sandbox will be used (safe for dev, not for production)")
        info("Start Docker + set SKILLOS_USE_DOCKER=true for production-safe isolation")


# ── 6. Optional API connections ───────────────────────────────────────────────
print(f"\n{BOLD}Optional Services{RESET}")

# Test a quick Groq call if key is present
groq_key = os.environ.get("GROQ_API_KEY", "").split(",")[0].strip()
if groq_key:
    try:
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {groq_key}"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            ok("Groq API key is valid (connection test passed)")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            err("Groq API key is INVALID (401 Unauthorized)")
            errors.append("Invalid GROQ_API_KEY")
        else:
            warn(f"Groq API key check returned HTTP {e.code}")
    except Exception as e:
        warn(f"Could not verify Groq key: {e}")

anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").split(",")[0].strip()
if anthropic_key:
    if anthropic_key.startswith("sk-ant-"):
        ok("Anthropic API key format looks correct")
    else:
        warn("Anthropic API key format looks unusual (expected sk-ant-...)")

openai_key = os.environ.get("OPENAI_API_KEY", "").split(",")[0].strip()
if openai_key:
    if openai_key.startswith("sk-"):
        ok("OpenAI API key format looks correct")
    else:
        warn("OpenAI API key format looks unusual (expected sk-...)")

gemini_key = os.environ.get("GEMINI_API_KEY", "").split(",")[0].strip()
if gemini_key:
    if gemini_key.startswith("AIza"):
        ok("Gemini API key format looks correct")
    else:
        warn("Gemini API key format looks unusual (expected AIza...)")


# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
if errors:
    print(f"{R}{BOLD}ERRORS ({len(errors)}){RESET}")
    for e in errors:
        print(f"  {R}x{RESET} {e}")
    print()

if warnings:
    print(f"{Y}{BOLD}WARNINGS ({len(warnings)}){RESET}")
    for w in warnings:
        print(f"  {Y}!{RESET} {w}")
    print()

if not errors:
    print(f"{G}{BOLD}Setup looks good!{RESET}")
    print()
    print("Start the server with:")
    print(f"  {B}./START_MAC_LINUX.sh{RESET}                     (Mac/Linux)")
    print(f"  {B}START_WINDOWS.bat{RESET}                        (Windows)")
    print(f"  {B}uvicorn skillos.api.fastapi_app:app --reload{RESET}  (manual)")
    print(f"  {B}docker-compose up{RESET}                        (Docker stack)")
    print()
    print(f"  Swagger UI: http://localhost:8000/docs")
    print(f"  AI status:  http://localhost:8000/admin/ai-status  (after login)")
    print(f"  Sandbox:    http://localhost:8000/admin/sandbox-status  (after login)")
else:
    print(f"{R}{BOLD}Fix the errors above before starting the server.{RESET}")
    sys.exit(1)

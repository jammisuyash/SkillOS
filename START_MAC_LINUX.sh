#!/bin/bash
# SkillOS -- Start Backend (FastAPI / uvicorn -- DEFAULT)
# Usage: ./START_MAC_LINUX.sh

# Load .env if it exists
if [ -f .env ]; then
    echo "  Loading .env..."
    set -a; source .env; set +a
fi

# Defaults for development (override in .env)
export SKILLOS_SECRET_KEY="${SKILLOS_SECRET_KEY:-skillos-secret-key-change-in-production}"
export SKILLOS_ENV="${SKILLOS_ENV:-development}"
export PHASE_AUTH="${PHASE_AUTH:-true}"
export PHASE_SKILLS="${PHASE_SKILLS:-true}"
export SKILLOS_USE_DOCKER="${SKILLOS_USE_DOCKER:-auto}"

echo ""
echo " ============================================================"
echo "  SkillOS -- FastAPI Backend (replaces old http.server)"
echo " ============================================================"
echo ""
echo "  Server:     http://localhost:8000"
echo "  Swagger UI: http://localhost:8000/docs"
echo "  ReDoc:      http://localhost:8000/redoc"
echo ""

# Check FastAPI is installed
if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "  Installing FastAPI + uvicorn..."
    pip install "fastapi[all]" "uvicorn[standard]" --quiet
fi

# AI Provider Status
echo "  AI Providers (fallback chain: Groq -> Gemini -> Anthropic -> OpenAI):"
[ -n "$GROQ_API_KEY"      ] && echo "    [OK] Groq       (llama-3.3-70b -- fastest, free tier)" || echo "    [ ] Groq       (add GROQ_API_KEY to .env)"
[ -n "$GEMINI_API_KEY"    ] && echo "    [OK] Gemini     (gemini-2.0-flash, 1500 req/day free)" || echo "    [ ] Gemini     (add GEMINI_API_KEY to .env)"
[ -n "$ANTHROPIC_API_KEY" ] && echo "    [OK] Anthropic  (claude-haiku-4-5, best code reasoning)" || echo "    [ ] Anthropic  (add ANTHROPIC_API_KEY to .env)"
[ -n "$OPENAI_API_KEY"    ] && echo "    [OK] OpenAI     (gpt-4o-mini, reliable fallback)" || echo "    [ ] OpenAI     (add OPENAI_API_KEY to .env)"
echo ""

# Code Execution Sandbox
echo "  Code Execution Sandbox:"
if docker info >/dev/null 2>&1 && [ "$SKILLOS_USE_DOCKER" != "false" ]; then
    echo "    [OK] Docker sandbox -- fully isolated (production-safe)"
    export SKILLOS_USE_DOCKER=true
else
    echo "    [!!] Subprocess sandbox (dev-safe, not production)"
    echo "         --> Start Docker + set SKILLOS_USE_DOCKER=true for full isolation"
fi
echo ""
echo "  Press Ctrl+C to stop"
echo ""

# Start FastAPI Server
exec uvicorn skillos.api.fastapi_app:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --reload \
    --reload-dir skillos \
    --log-level info

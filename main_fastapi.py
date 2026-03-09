"""
main_fastapi.py -- SkillOS Backend Entry Point (FastAPI -- DEFAULT)

This IS the primary server. The old http.server (skillos/main.py) is
kept only as a legacy fallback for environments without FastAPI installed.

USAGE:
  Development:
    uvicorn main_fastapi:app --reload --port 8000

    Or use the helper script:
    ./START_MAC_LINUX.sh     (Mac/Linux)
    START_WINDOWS.bat        (Windows)

  Production (Railway / Render):
    uvicorn main_fastapi:app --host 0.0.0.0 --port $PORT --workers 4

  Docker:
    docker-compose up

WHAT THIS REPLACES:
  Before: python -m skillos.main  (stdlib http.server, single-threaded, no async)
  After:  uvicorn FastAPI app     (async, thousands of concurrent connections,
                                   auto /docs Swagger UI, WebSocket support,
                                   Pydantic validation, proper middleware)

FEATURES:
  [*] FastAPI + uvicorn (ASGI, async)
  [*] Docker sandbox for code execution (auto-detects, falls back to subprocess)
  [*] Multi-provider AI with 4 providers: Groq, Gemini, Anthropic, OpenAI
  [*] Multi-key per provider (comma-separate keys in .env)
  [*] Circuit breaking -- per-key + per-provider
  [*] Swagger UI at /docs, ReDoc at /redoc
  [*] WebSocket support for live interviews
  [*] Background task pre-warming of Docker images
"""

# Load .env in development (no-op in production where env vars are set directly)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Re-export the FastAPI app from the module
from skillos.api.fastapi_app import app  # noqa: F401

__all__ = ["app"]

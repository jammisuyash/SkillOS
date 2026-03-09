# SkillOS — Multi-stage Dockerfile
#
# Stages:
#   base     — Python base with system deps
#   backend  — Backend only (API server + worker)
#   frontend — Frontend builder
#   prod     — Combined production image with nginx
#
# Usage:
#   Development:  docker build --target backend -t skillos-backend .
#   Production:   docker build --target prod    -t skillos-prod .

# ── Stage 1: Base ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

LABEL maintainer="SkillOS Team" \
      description="SkillOS — Developer Skill Verification Platform"

# System deps for code execution sandboxes
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    gcc \
    g++ \
    default-jdk-headless \
    golang-go \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# ── Stage 2: Backend ─────────────────────────────────────────────────────────
FROM base AS backend

# Install Python deps
COPY requirements-fastapi.txt .
RUN pip install --no-cache-dir -r requirements-fastapi.txt

# Copy source
COPY skillos/ ./skillos/
COPY requirements.txt .

# Data directory (SQLite or volume mount for PostgreSQL)
RUN mkdir -p /var/data
ENV SKILLOS_DB_PATH=/var/data/skillos.db

EXPOSE 8000

# Default: FastAPI with uvicorn (4 workers)
CMD ["uvicorn", "skillos.api.fastapi_app:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", "--loop", "uvloop", "--http", "httptools"]

# Fallback stdlib mode (no FastAPI required):
# CMD ["python", "-m", "skillos.main"]

# ── Stage 3: Frontend Builder ─────────────────────────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ .
RUN npm run build

# ── Stage 4: Production (nginx + backend) ─────────────────────────────────────
FROM backend AS prod

# Copy nginx for serving frontend
RUN apt-get update && apt-get install -y --no-install-recommends nginx && apt-get clean

# Copy built frontend
COPY --from=frontend-build /app/dist /usr/share/nginx/html

# Nginx config
COPY scripts/nginx.conf /etc/nginx/conf.d/default.conf

# Supervisor to run both nginx + uvicorn
RUN pip install --no-cache-dir supervisor
COPY scripts/supervisord.conf /etc/supervisor/conf.d/skillos.conf

EXPOSE 80 8000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/skillos.conf"]

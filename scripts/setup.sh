#!/bin/bash
# scripts/setup.sh
# First-time setup: migrate + seed.
# Safe to run multiple times (idempotent).

set -e
PYTHON=${PYTHON:-python3}
ROOT=$(dirname "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)")
cd "$ROOT"

echo "[setup] Running migrations..."
$PYTHON -m skillos.db.migrations

echo "[setup] Seeding database..."
$PYTHON -m skillos.db.seed

echo "[setup] Done. Start the server with:"
echo "        python -m skillos.main"

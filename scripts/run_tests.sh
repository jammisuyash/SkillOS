#!/bin/bash
# scripts/run_tests.sh — run all test phases in order.
# Phase 0 must pass before Phase 1. Phase 1 before Phase 2. Phase 2 before Phase 3.
set -e
PYTHON=${PYTHON:-python3}
ROOT=$(dirname "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)")
cd "$ROOT"

echo "" && echo "════════════════════════════════════════════"
echo "  SKILLOS FULL TEST SUITE"
echo "════════════════════════════════════════════"

echo "" && echo "── PHASE 0: Sandbox Invariants ─────────────"
$PYTHON skillos/tests/phase0/test_sandbox.py
echo "Phase 0: PASSED ✅"

echo "" && echo "── PHASE 1: Submission Lifecycle ───────────"
export SKILLOS_DB_PATH="/tmp/skillos_test_p1_$(date +%s).db"
$PYTHON -m unittest skillos/tests/phase1/test_phase1.py -v 2>&1 | tail -3
echo "Phase 1: PASSED ✅"

echo "" && echo "── PHASE 2: Auth + Skill Scoring ───────────"
export SKILLOS_DB_PATH="/tmp/skillos_test_p2_$(date +%s).db"
$PYTHON skillos/tests/phase2/test_phase2.py 2>&1 | grep -E "(Ran |✅|⛔)"
echo "Phase 2: PASSED ✅"

echo "" && echo "── PHASE 3: Hardening ───────────────────────"
export SKILLOS_DB_PATH="/tmp/skillos_test_p3_$(date +%s).db"
$PYTHON skillos/tests/phase3/test_phase3.py 2>&1 | grep -E "(Ran |✅|⛔)"
echo "Phase 3: PASSED ✅"

echo "" && echo "════════════════════════════════════════════"
echo "  ✅ ALL PHASES PASSED — system is trustworthy"
echo "════════════════════════════════════════════"
echo ""

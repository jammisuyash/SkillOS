# SkillOS — Phase Roadmap

Each phase has explicit exit criteria. You do not proceed until all criteria pass.
This is not a timeline — it is a sequence of proofs.

---

## Phase 0 — Evaluator ✅ COMPLETE

**Goal:** Prove untrusted Python code can be executed safely.

**Built:**
- `evaluator/limits.py` — resource constants
- `evaluator/sandbox.py` — OS-level isolated execution
- `evaluator/comparator.py` — output comparison (exact, float, multiline)
- `evaluator/runner.py` — orchestrates sandbox across all test cases

**Exit criteria (all 8 pass):**
- [x] Infinite loop killed
- [x] Memory bomb killed
- [x] Output flood capped
- [x] Fork attempt blocked (non-root) / documented (root)
- [x] Subprocess spawn blocked (non-root) / documented (root)
- [x] Correct code executes cleanly
- [x] Syntax error is `runtime_error`, not `crash`
- [x] Sandbox crash returns dict, never raises

**Known production gap:** RLIMIT_NPROC ineffective for root. Fix: run as non-root user.

---

## Phase 1 — Submission Lifecycle ✅ COMPLETE

**Goal:** Prove the submit → evaluate → persist loop is atomic and durable.

**Built:**
- `db/database.py` — DB abstraction (SQLite dev / Postgres prod)
- `db/migrations.py` — versioned schema migrations
- `db/seed.py` — 2 tasks with hidden test cases
- `submissions/service.py` — create, persist, zombie cleaner
- `submissions/worker.py` — background evaluation thread
- `submissions/events.py` — event dispatcher (seam for future consumers)
- `api/app.py` — `POST /submit`, `GET /submission/{id}`

**Exit criteria (all 17 pass):**
- [x] Kill evaluator mid-run → zombie cleaner marks crash
- [x] DB never contains partial results (rollback test)
- [x] Terminal state immutable (double-write returns False)
- [x] Hidden test cases never leak output
- [x] Two submissions with same code are independent records
- [x] System recovers cleanly after restart
- [x] All 5 terminal states (accepted/wrong_answer/timeout/runtime_error/crash) work

---

## Phase 2 — Auth + Skill Scoring (NEXT)

**Goal:** Prove users are real and skill scores are trustworthy.

**Will build:**
- `db/migration_phase2.py` → `users`, `skills`, `user_skill_scores` tables
- `auth/` module → register, login, JWT issuance, `get_current_user()` dependency
- `users/` module → profile CRUD
- `skills/scoring.py` → v1 algorithm (already written, not yet wired)
- `skills/handlers.py` → event consumer (already written, gated by `PHASE_SKILLS`)
- `skills/service.py` → read endpoints
- API additions: `POST /auth/register`, `POST /auth/login`, `GET /users/me/skills`

**Exit criteria (define before building):**
- [ ] Register + login produces valid JWT
- [ ] Protected endpoints reject missing/invalid tokens
- [ ] Skill score replay: delete scores, recompute, assert identical
- [ ] Skill score increases only for accepted submissions
- [ ] Skill score never increases for wrong_answer/timeout/crash
- [ ] Two different users have independent skill scores

**Phase flag:** `PHASE_AUTH=true PHASE_SKILLS=true`

---

## Phase 3 — Frontend

**Goal:** Make the proof visible to users and employers.

**Will build (only after Phase 2 exit criteria pass):**
- Task list + filter by difficulty/skill
- Code editor + submit + result polling
- Skill proof dashboard (`/users/me/skills`)
- Submission history per task

**Will NOT build in Phase 3:**
- Social features, leaderboards, comments
- Employer dashboards (separate product)
- AI features

---

## Phase 4 — Employer Integration

Only after user-side trust is established (SkillOS has users with real skill scores).

**Will build:**
- Company dashboard (read-only view of candidate skill proofs)
- Candidate sharing (user opts in to share their proof with a company)
- Hiring signals derived from submission patterns

**This is a second product, not a feature.**
Do not design it until Phase 3 is complete and users are real.

---

## Invariants That Must Never Change

Regardless of what phase you're in:

1. **Evaluator never receives user context.** If it ever needs to know who submitted, the design is wrong.
2. **Terminal states are immutable.** Once `accepted`, always `accepted`.
3. **Skill scores are replayable.** Delete derived scores, rerun, get same result.
4. **Retries are forbidden.** Crashes are investigated, not hidden.
5. **Hidden test cases never leak.** Trust is the product.

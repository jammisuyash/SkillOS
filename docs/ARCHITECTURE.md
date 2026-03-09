# SkillOS — Architecture Decision Record

This document explains WHY each major decision was made.
These decisions are locked. Changes require new evidence, not new opinions.

---

## ADR-001: Clean Monolith over Microservices

**Decision:** Single deployable unit. One database. One codebase.

**Reasoning:**
- Solo founder. Microservices multiply operational surface area per person linearly.
- Module boundaries (evaluator/, submissions/, skills/) provide the future extraction path.
- One DB transaction can span submission + skill score update. In distributed: saga pattern.
- If `evaluator` needs to become a service later, it already has a clean interface. Extract then.

**Not:** A performance decision. A correctness and velocity decision.

---

## ADR-002: Evaluator as Hermetic Pure Function

**Decision:** Evaluator receives only `code + test_cases + limits`. Never user context.

**Reasoning:**
- Enables third-party audits (evaluator can be verified independently)
- Makes future extraction trivial (the interface is already clean)
- Improves security reasoning (one attack surface, not entangled with auth)
- Deterministic: same inputs → same outputs → independently verifiable

**Rule:** `evaluator/` never imports from any other module. Enforced by convention, verified by grep.

---

## ADR-003: Exit Code Semantics (SIGKILL disambiguation)

**Decision:** `exit_code=-9` without wall-time expiry → reclassified as `timed_out=True`, not `crashed=True`.

**Reasoning:**
- SIGKILL from RLIMIT_CPU means the CPU limit fired. The sandbox worked.
- SIGKILL from RLIMIT_AS (MemoryError path) means the memory limit fired. Also correct.
- "Crash" means the sandbox itself failed — not that the resource limits worked.
- User sees "time limit exceeded", not "system error". Honest and accurate.

---

## ADR-004: Three Score Concepts, Not One

**Decision:** Split `correctness (result_status)`, `performance (performance_tier)`, `skill contribution` into separate fields.

**Reasoning:**
- A single `score (0-100)` is ambiguous. Solving fizzbuzz fast ≠ high skill.
- Prevents gaming: users can't optimize for one number at the expense of understanding.
- Employers need to see correctness and performance separately.
- Skill contribution (Phase 2) is derived from correctness + difficulty, not from performance.

---

## ADR-005: Atomic Persistence with Idempotency Guard

**Decision:** `UPDATE submissions SET ... WHERE id=? AND status='pending'`

**Reasoning:**
- Single transaction: all fields written atomically or none are.
- `AND status='pending'` guard: double evaluation cannot overwrite a terminal state.
- Zombie cleaner can run concurrently without race conditions.
- If evaluator crashes after evaluate() but before persist: submission stays pending → zombie cleaner handles it.

**The principle:** A crash-marked submission is honest. A partially-written submission is a lie.

---

## ADR-006: Event-Shaped Module Communication

**Decision:** `submissions emits → skills reacts` via `submissions/events.py` dispatcher.

**Reasoning:**
- submissions never imports skills. skills registers itself at startup.
- Adding a new consumer (badges, analytics) = one line in main.py. Zero changes to submissions.
- In MVP: synchronous function calls. In future: async queue. Same interface.
- The seam is explicit and findable: one file, one place.

---

## ADR-007: N=20 Sliding Window for Skill Scores

**Decision:** Skill score computed from 20 most recent accepted submissions.

**Reasoning:**
- Old easy tasks fade naturally without explicit decay math.
- Bounded computation: always exactly 20 rows, regardless of submission history length.
- Replayable: same 20 rows → same score. No hidden state.
- Explainable to users: "your score reflects your best recent work, weighted by difficulty."

**Reserved:** `recency_weight = 1.0` slot exists. Future v2 can add exponential decay without changing the formula shape.

---

## ADR-008: No Retries on Failed Evaluations

**Decision:** Zombie cleaner marks stuck submissions as `crash`. No retry logic.

**Reasoning:**
- Retries hide bugs. A burst of crashes = evaluator is broken. Investigate, don't retry.
- One occasional zombie = normal (server restart). Acceptable.
- Trust is the product. Silently re-evaluating and getting a different result is untrustworthy.

---

## ADR-009: RLIMIT_NPROC Root Bypass (Known Gap)

**Decision:** Document the gap. Do not hide it. Require production fix before launch.

**Context:** `RLIMIT_NPROC` is ignored for root (UID 0) on Linux. Tests 4 and 5 (fork/subprocess) explicitly warn when running as root.

**Production fix (required before public users):**
- Option A: `useradd -r -s /bin/false skillos-eval` + run evaluator as this user
- Option B: Docker `--security-opt seccomp` (blocks fork at syscall level)
- Option C: Both (defense in depth)

**`preexec_fn` resource limits then become defense-in-depth, not the first line.**

---

## What Is Intentionally NOT Built (and why)

| Feature | Reason |
|---|---|
| Frontend | Correctness must be proven before presentation |
| Auth | Phase 2 — hardcoded user_id in Phase 1 is explicit, not lazy |
| Multi-language | Python only until sandbox is rock-solid |
| Retries | Hide bugs |
| AI hints | Vendor dependency, cost, latency. No proven demand. |
| Leaderboards | Distraction from core proof loop. Post-PMF. |
| Certificates | Trust must be earned first. |
| Employer dashboards | Second product, different persona. After user-side is validated. |

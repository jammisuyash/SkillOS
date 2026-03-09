"""
tests/phase2/test_phase2.py

Phase 2 Exit Criteria — ALL must pass before Phase 3 begins.

EXIT CRITERIA:
  ✓ 1. Same submission replayed → identical score (REPLAY INVARIANT)
  ✓ 2. Different tasks affect different skills correctly (SKILL ISOLATION)
  ✓ 3. Wrong answer never increases score (WRONG ANSWER = ZERO CONTRIBUTION)
  ✓ 4. Timeout/crash give zero contribution (FAILURE = ZERO)
  ✓ 5. Score math is deterministic and test-covered (ALGORITHM CORRECTNESS)
  ✓ 6. Auth failure cannot submit code (AUTH GATE)
  ✓ 7. Token expiry is enforced (TOKEN SECURITY)
  ✓ 8. Task deduplication prevents score gaming (ANTI-GAMING)

Run: python -m unittest skillos/tests/phase2/test_phase2.py -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

import unittest
import uuid
import datetime
import threading

os.environ["SKILLOS_DB_PATH"] = "/tmp/skillos_test_phase2.db"
os.environ["SKILLOS_SECRET_KEY"] = "test-secret-key-phase2"
if os.path.exists("/tmp/skillos_test_phase2.db"):
    os.remove("/tmp/skillos_test_phase2.db")

from skillos.db.migrations import run_migrations
from skillos.db.database import get_db, transaction, fetchone, fetchall
from skillos.shared.utils import utcnow_iso
from skillos.skills.scoring import compute_skill_score, upsert_skill_score, WINDOW, MAX_WEIGHT
from skillos.evaluator.limits import DIFFICULTY_WEIGHTS
from skillos.auth.service import (
    register, login, verify_token, get_current_user,
    hash_password, verify_password,
)


# ─────────────────────────────────────────────────────────────────────────────
# TEST FIXTURES
# ─────────────────────────────────────────────────────────────────────────────

SKILL_A = "skill-arrays-001"
SKILL_B = "skill-graphs-001"

TASK_EASY_A   = "task-easy-a-001"
TASK_MEDIUM_A = "task-medium-a-001"
TASK_HARD_A   = "task-hard-a-001"
TASK_EASY_B   = "task-easy-b-001"    # different skill
USER_1        = "user-scoring-001"
USER_2        = "user-scoring-002"


def setUpModule():
    run_migrations()
    db = get_db()

    # Seed skills
    for sid, name in [(SKILL_A, "Python Arrays"), (SKILL_B, "Graph Algorithms")]:
        db.execute("INSERT OR IGNORE INTO skills (id, name) VALUES (?, ?)", (sid, name))

    # Seed test users — required for user_skill_scores FK constraint
    from skillos.auth.service import hash_password as _hp
    from skillos.shared.utils import utcnow_iso
    for uid, email in [(USER_1, "user1@test.com"), (USER_2, "user2@test.com")]:
        db.execute("""
            INSERT OR IGNORE INTO users (id, email, password_hash, display_name, created_at)
            VALUES (?, ?, ?, 'Test User', ?)
        """, (uid, email, _hp("testpass"), utcnow_iso()))

    # Seed tasks across two skills
    tasks = [
        (TASK_EASY_A,   "Easy Array Task",   "easy",   SKILL_A),
        (TASK_MEDIUM_A, "Medium Array Task", "medium", SKILL_A),
        (TASK_HARD_A,   "Hard Array Task",   "hard",   SKILL_A),
        (TASK_EASY_B,   "Easy Graph Task",   "easy",   SKILL_B),
    ]
    for tid, title, diff, skill in tasks:
        db.execute("""
            INSERT OR IGNORE INTO tasks
                (id, title, description, difficulty, skill_id, time_limit_ms,
                 memory_limit_kb, is_published)
            VALUES (?, ?, 'test task', ?, ?, 2000, 131072, 1)
        """, (tid, title, diff, skill))

    db.commit()


def _insert_submission(user_id: str, task_id: str, status: str,
                        submitted_at: str = None) -> str:
    """Insert a bare submission directly — bypasses evaluation for scoring tests."""
    sid = str(uuid.uuid4())
    now = submitted_at or utcnow_iso()
    db = get_db()
    db.execute("""
        INSERT INTO submissions
            (id, user_id, task_id, code, language, status,
             passed_cases, total_cases, submitted_at, evaluated_at)
        VALUES (?, ?, ?, 'test code', 'python', ?, 1, 1, ?, ?)
    """, (sid, user_id, task_id, status, now, now))
    db.commit()
    return sid


def _clear_scores(user_id: str = None):
    """Clear derived scores (and optionally submissions) for a user."""
    db = get_db()
    if user_id:
        db.execute("DELETE FROM user_skill_scores WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM submissions WHERE user_id = ?", (user_id,))
    else:
        db.execute("DELETE FROM user_skill_scores")
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1 — REPLAY INVARIANT (most critical test in the entire suite)
# ─────────────────────────────────────────────────────────────────────────────

class TestReplayInvariant(unittest.TestCase):
    """
    EXIT CRITERION 1: Replay invariant.

    Delete all user_skill_scores.
    Recompute from raw submissions.
    Assert every score matches within 0.0001.

    If this test fails: there is hidden state in the scoring function.
    That means SkillOS cannot be trusted. Fix before proceeding.
    """
    # Isolated users for this class — never shared with other classes
    USER = "user-replay-001"

    @classmethod
    def setUpClass(cls):
        # Ensure isolated user exists in users table
        from skillos.auth.service import hash_password as _hp
        from skillos.shared.utils import utcnow_iso
        db = get_db()
        db.execute("INSERT OR IGNORE INTO users (id, email, password_hash, display_name, created_at) VALUES (?, ?, ?, 'Replay', ?)",
            (cls.USER, "replay@test.com", _hp("p"), utcnow_iso()))
        db.commit()

    def setUp(self):
        _clear_scores(self.USER)

    def test_replay_produces_identical_scores(self):
        """
        This is the trust test. Everything else depends on this passing.
        """
        _clear_scores()

        # Create a realistic submission history
        _insert_submission(self.USER, TASK_EASY_A,   "accepted")
        _insert_submission(self.USER, TASK_MEDIUM_A, "accepted")
        _insert_submission(self.USER, TASK_HARD_A,   "accepted")
        _insert_submission(self.USER, TASK_EASY_B,   "accepted")
        _insert_submission(self.USER, TASK_EASY_A,   "wrong_answer")  # should not count

        # First computation
        score_a_run1 = upsert_skill_score(self.USER, SKILL_A, fetchall, transaction)
        score_b_run1 = upsert_skill_score(self.USER, SKILL_B, fetchall, transaction)

        # Wipe ONLY derived scores — simulate bug recovery / algorithm upgrade
        # Keep submissions intact — they are the source of truth
        db = get_db()
        db.execute("DELETE FROM user_skill_scores WHERE user_id = ?", (self.USER,))
        db.commit()

        # Second computation from identical raw data
        score_a_run2 = upsert_skill_score(self.USER, SKILL_A, fetchall, transaction)
        score_b_run2 = upsert_skill_score(self.USER, SKILL_B, fetchall, transaction)

        self.assertAlmostEqual(score_a_run1, score_a_run2, places=4,
            msg=f"SKILL_A score changed after replay: {score_a_run1} → {score_a_run2}")
        self.assertAlmostEqual(score_b_run1, score_b_run2, places=4,
            msg=f"SKILL_B score changed after replay: {score_b_run1} → {score_b_run2}")

        print(f"  ✓ Replay invariant holds: "
              f"SKILL_A={score_a_run1:.4f}={score_a_run2:.4f}, "
              f"SKILL_B={score_b_run1:.4f}={score_b_run2:.4f}")

    def test_replay_with_zero_submissions(self):
        """User with no accepted submissions: score = 0.0, always."""
        _clear_scores()
        score1 = compute_skill_score(self.USER + "-empty", SKILL_A, fetchall)
        score2 = compute_skill_score(self.USER + "-empty", SKILL_A, fetchall)
        self.assertEqual(score1, 0.0)
        self.assertEqual(score2, 0.0)
        print("  ✓ Zero submissions → 0.0, replay stable")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2 — ALGORITHM CORRECTNESS (math must be right)
# ─────────────────────────────────────────────────────────────────────────────

class TestScoringAlgorithm(unittest.TestCase):
    """
    EXIT CRITERION 5: Score math is deterministic and test-covered.

    We verify the formula with known inputs and expected outputs.
    If these fail, the algorithm is wrong regardless of other tests passing.
    """

    def _mock_fetchall(self, difficulties: list) -> callable:
        """Return a mock fetchall that yields rows with given difficulties."""
        rows = [{"difficulty": d, "latest": "2026-01-01"} for d in difficulties]
        def mock(sql, params):
            limit = params[2] if len(params) > 2 else WINDOW
            return rows[:limit]
        return mock

    def test_single_easy_task(self):
        """
        1 easy task:
        contribution = 1.0
        max_possible = 1 × 2.5 = 2.5
        score = (1.0 / 2.5) × 100 = 40.0
        """
        mock = self._mock_fetchall(["easy"])
        score = compute_skill_score("u", "s", mock)
        self.assertAlmostEqual(score, 40.0, places=2)
        print(f"  ✓ 1 easy task → {score:.4f} (expected 40.0)")

    def test_single_medium_task(self):
        """
        1 medium task:
        contribution = 1.5
        max_possible = 1 × 2.5 = 2.5
        score = (1.5 / 2.5) × 100 = 60.0
        """
        mock = self._mock_fetchall(["medium"])
        score = compute_skill_score("u", "s", mock)
        self.assertAlmostEqual(score, 60.0, places=2)
        print(f"  ✓ 1 medium task → {score:.4f} (expected 60.0)")

    def test_single_hard_task(self):
        """
        1 hard task:
        contribution = 2.5
        max_possible = 1 × 2.5 = 2.5
        score = (2.5 / 2.5) × 100 = 100.0
        """
        mock = self._mock_fetchall(["hard"])
        score = compute_skill_score("u", "s", mock)
        self.assertAlmostEqual(score, 100.0, places=2)
        print(f"  ✓ 1 hard task → {score:.4f} (expected 100.0)")

    def test_mixed_difficulty(self):
        """
        1 easy + 1 medium + 1 hard:
        contributions = 1.0 + 1.5 + 2.5 = 5.0
        max_possible  = 3 × 2.5 = 7.5
        score = (5.0 / 7.5) × 100 = 66.6667
        """
        mock = self._mock_fetchall(["easy", "medium", "hard"])
        score = compute_skill_score("u", "s", mock)
        expected = (5.0 / 7.5) * 100
        self.assertAlmostEqual(score, expected, places=2)
        print(f"  ✓ easy+medium+hard → {score:.4f} (expected {expected:.4f})")

    def test_all_hard_tasks_approaches_100(self):
        """20 hard tasks should score 100.0 exactly."""
        mock = self._mock_fetchall(["hard"] * 20)
        score = compute_skill_score("u", "s", mock)
        self.assertAlmostEqual(score, 100.0, places=4)
        print(f"  ✓ 20 hard tasks → {score:.4f} (expected 100.0)")

    def test_score_never_exceeds_100(self):
        """Score is always capped at 100.0."""
        mock = self._mock_fetchall(["hard"] * 50)
        score = compute_skill_score("u", "s", mock)
        self.assertLessEqual(score, 100.0)
        print(f"  ✓ 50 hard tasks → {score:.4f} (capped at 100)")

    def test_score_never_below_zero(self):
        """Score is always non-negative."""
        mock = self._mock_fetchall([])
        score = compute_skill_score("u", "s", mock)
        self.assertGreaterEqual(score, 0.0)
        print(f"  ✓ No submissions → {score:.4f} (non-negative)")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3 — WRONG ANSWER / FAILURE = ZERO CONTRIBUTION
# ─────────────────────────────────────────────────────────────────────────────

class TestFailureContributions(unittest.TestCase):
    """
    EXIT CRITERIA 3 & 4:
      - Wrong answer never increases score
      - Timeout/crash give zero contribution
    """

    @classmethod
    def setUpClass(cls):
        from skillos.auth.service import hash_password as _hp
        from skillos.shared.utils import utcnow_iso
        cls.USER = "user-failures-001"
        db = get_db()
        db.execute("INSERT OR IGNORE INTO users (id, email, password_hash, display_name, created_at) VALUES (?, ?, ?, 'Failures', ?)",
            (cls.USER, "failures@test.com", _hp("p"), utcnow_iso()))
        db.commit()

    def setUp(self):
        # Full reset: clear both scores AND submissions for this user
        _clear_scores(self.USER)

    def test_wrong_answer_does_not_increase_score(self):
        """Submitting wrong answers must not change a skill score."""
        # Baseline: no submissions
        score_before = compute_skill_score(self.USER, SKILL_A, fetchall)
        self.assertEqual(score_before, 0.0)

        _insert_submission(self.USER, TASK_EASY_A, "wrong_answer")
        _insert_submission(self.USER, TASK_EASY_A, "wrong_answer")
        _insert_submission(self.USER, TASK_EASY_A, "wrong_answer")

        score_after = compute_skill_score(self.USER, SKILL_A, fetchall)
        self.assertEqual(score_after, 0.0,
            f"Wrong answers must not increase score: {score_after}")
        print(f"  ✓ 3 wrong answers → score unchanged ({score_after:.4f})")

    def test_timeout_does_not_increase_score(self):
        """Timeouts must not contribute to skill score."""
        _insert_submission(self.USER, TASK_MEDIUM_A, "timeout")
        score = compute_skill_score(self.USER, SKILL_A, fetchall)
        self.assertEqual(score, 0.0,
            f"Timeout must not increase score: {score}")
        print(f"  ✓ Timeout → score unchanged ({score:.4f})")

    def test_crash_does_not_increase_score(self):
        """Crashes must not contribute to skill score."""
        _insert_submission(self.USER, TASK_HARD_A, "crash")
        score = compute_skill_score(self.USER, SKILL_A, fetchall)
        self.assertEqual(score, 0.0,
            f"Crash must not increase score: {score}")
        print(f"  ✓ Crash → score unchanged ({score:.4f})")

    def test_runtime_error_does_not_increase_score(self):
        """Runtime errors must not contribute to skill score."""
        _insert_submission(self.USER, TASK_EASY_A, "runtime_error")
        score = compute_skill_score(self.USER, SKILL_A, fetchall)
        self.assertEqual(score, 0.0,
            f"Runtime error must not increase score: {score}")
        print(f"  ✓ Runtime error → score unchanged ({score:.4f})")

    def test_accepted_after_failures_scores_correctly(self):
        """
        Failure submissions followed by an accepted submission:
        only the accepted submission contributes.
        """
        _insert_submission(self.USER, TASK_EASY_A, "wrong_answer")
        _insert_submission(self.USER, TASK_EASY_A, "wrong_answer")
        _insert_submission(self.USER, TASK_EASY_A, "accepted")  # finally solved it

        score = compute_skill_score(self.USER, SKILL_A, fetchall)
        # 1 easy task accepted → (1.0 / (1 × 2.5)) × 100 = 40.0
        self.assertAlmostEqual(score, 40.0, places=2,
            msg=f"Expected 40.0 for 1 accepted easy task, got {score}")
        print(f"  ✓ Failures then accepted → {score:.4f} (expected 40.0)")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4 — SKILL ISOLATION
# ─────────────────────────────────────────────────────────────────────────────

class TestSkillIsolation(unittest.TestCase):
    """
    EXIT CRITERION 2: Different tasks affect different skills correctly.
    """

    @classmethod
    def setUpClass(cls):
        from skillos.auth.service import hash_password as _hp
        from skillos.shared.utils import utcnow_iso
        cls.USER_A = "user-isolation-a"
        cls.USER_B = "user-isolation-b"
        db = get_db()
        for uid, email in [(cls.USER_A, "isoa@test.com"), (cls.USER_B, "isob@test.com")]:
            db.execute("INSERT OR IGNORE INTO users (id, email, password_hash, display_name, created_at) VALUES (?, ?, ?, 'Iso', ?)",
                (uid, email, _hp("p"), utcnow_iso()))
        db.commit()

    def setUp(self):
        _clear_scores(self.USER_A)
        _clear_scores(self.USER_B)

    def test_tasks_affect_only_their_skill(self):
        """
        Solving a SKILL_A task must not change SKILL_B score and vice versa.
        """
        _insert_submission(self.USER_A, TASK_EASY_A, "accepted")   # SKILL_A
        _insert_submission(self.USER_A, TASK_EASY_B, "accepted")   # SKILL_B

        score_a = compute_skill_score(self.USER_A, SKILL_A, fetchall)
        score_b = compute_skill_score(self.USER_A, SKILL_B, fetchall)

        self.assertGreater(score_a, 0.0, "SKILL_A should have a score")
        self.assertGreater(score_b, 0.0, "SKILL_B should have a score")

        # They should be equal (both 1 easy task solved)
        self.assertAlmostEqual(score_a, score_b, places=4,
            msg="Both skills should score equally for 1 easy task each")
        print(f"  ✓ Skills isolated: A={score_a:.4f}, B={score_b:.4f}")

    def test_unplayed_skill_stays_zero(self):
        """
        If a user has only solved SKILL_A tasks, SKILL_B must be 0.0.
        """
        _insert_submission(self.USER_A, TASK_HARD_A, "accepted")  # SKILL_A only

        score_b = compute_skill_score(self.USER_A, SKILL_B, fetchall)
        self.assertEqual(score_b, 0.0,
            f"Untouched skill must be 0.0, got {score_b}")
        print(f"  ✓ Untouched skill stays 0.0")

    def test_two_users_independent(self):
        """Two users' skill scores are completely independent."""
        _insert_submission(self.USER_A, TASK_HARD_A,   "accepted")  # hard
        _insert_submission(self.USER_B, TASK_EASY_A,   "accepted")  # easy

        score_1 = compute_skill_score(self.USER_A, SKILL_A, fetchall)
        score_2 = compute_skill_score(self.USER_B, SKILL_A, fetchall)

        self.assertGreater(score_1, score_2,
            f"Hard solver ({score_1:.2f}) should outscore easy solver ({score_2:.2f})")
        print(f"  ✓ USER_1 (hard)={score_1:.4f} > USER_2 (easy)={score_2:.4f}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 5 — ANTI-GAMING: TASK DEDUPLICATION
# ─────────────────────────────────────────────────────────────────────────────

class TestAntiGaming(unittest.TestCase):
    """
    EXIT CRITERION 8: Submitting the same task N times does not inflate the score.
    GROUP BY task_id ensures each task counts at most once.
    """

    @classmethod
    def setUpClass(cls):
        from skillos.auth.service import hash_password as _hp
        from skillos.shared.utils import utcnow_iso
        cls.USER_SPAM    = "user-spammer-001"
        cls.USER_DIVERSE = "user-diverse-001"
        db = get_db()
        for uid, email in [(cls.USER_SPAM, "spam@test.com"), (cls.USER_DIVERSE, "diverse@test.com")]:
            db.execute("INSERT OR IGNORE INTO users (id, email, password_hash, display_name, created_at) VALUES (?, ?, ?, 'G', ?)",
                (uid, email, _hp("p"), utcnow_iso()))
        db.commit()

    def setUp(self):
        _clear_scores(self.USER_SPAM)
        _clear_scores(self.USER_DIVERSE)

    def test_spam_same_task_does_not_inflate_score(self):
        """
        Solving the same easy task 20 times must produce same score as solving it once.
        """
        for _ in range(20):
            _insert_submission(self.USER_DIVERSE, TASK_EASY_A, "accepted")

        score_spammed = compute_skill_score(self.USER_DIVERSE, SKILL_A, fetchall)

        # Expected: 1 easy task (deduplication) → (1.0 / 2.5) × 100 = 40.0
        expected = (DIFFICULTY_WEIGHTS["easy"] / (1 * MAX_WEIGHT)) * 100
        self.assertAlmostEqual(score_spammed, expected, places=2,
            msg=f"Spamming task should not inflate score: got {score_spammed:.4f}, "
                f"expected {expected:.4f}")
        print(f"  ✓ 20 same-task submissions → {score_spammed:.4f} "
              f"(same as 1 submission, dedup works)")

    def test_diverse_tasks_score_higher_than_spam(self):
        """
        Solving 3 different tasks should score higher than spamming 1 task.
        """
        # User 1: diverse (easy + medium + hard on SKILL_A)
        _insert_submission(self.USER_DIVERSE, TASK_EASY_A,   "accepted")
        _insert_submission(self.USER_DIVERSE, TASK_MEDIUM_A, "accepted")
        _insert_submission(self.USER_DIVERSE, TASK_HARD_A,   "accepted")
        score_diverse = compute_skill_score(self.USER_DIVERSE, SKILL_A, fetchall)

        # User 2: spam (20× easy)
        for _ in range(20):
            _insert_submission(self.USER_SPAM, TASK_EASY_A, "accepted")
        score_spam = compute_skill_score(self.USER_SPAM, SKILL_A, fetchall)

        self.assertGreater(score_diverse, score_spam,
            f"Diverse solving ({score_diverse:.4f}) must beat spam ({score_spam:.4f})")
        print(f"  ✓ Diverse={score_diverse:.4f} > Spam={score_spam:.4f}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 6 — AUTH: REGISTER / LOGIN / TOKEN
# ─────────────────────────────────────────────────────────────────────────────

class TestAuth(unittest.TestCase):
    """
    EXIT CRITERIA 6 & 7: Auth gate + token security.
    """

    def test_register_and_login(self):
        """Full register → login → verify flow."""
        email    = f"test-{uuid.uuid4().hex[:8]}@example.com"
        password = "secure-password-123"
        name     = "Test User"

        user = register(email=email, password=password, display_name=name)
        self.assertEqual(user["email"], email)
        self.assertIn("id", user)
        self.assertNotIn("password_hash", user, "Password hash must not be returned")

        token = login(email=email, password=password)
        self.assertIsInstance(token, str)
        self.assertEqual(token.count("."), 2, "Token must have 3 parts (JWT format)")

        current = get_current_user(token)
        self.assertIsNotNone(current)
        self.assertEqual(current["email"], email)
        print(f"  ✓ Register → login → verify works")

    def test_wrong_password_rejected(self):
        """Wrong password must return ValidationError, never a token."""
        from skillos.shared.exceptions import ValidationError as VE
        email = f"test-{uuid.uuid4().hex[:8]}@example.com"
        register(email=email, password="correct-password", display_name="U")
        with self.assertRaises(VE):
            login(email=email, password="wrong-password")
        print(f"  ✓ Wrong password raises ValidationError")

    def test_wrong_email_rejected(self):
        """Non-existent email must return same error (no user enumeration)."""
        from skillos.shared.exceptions import ValidationError as VE
        with self.assertRaises(VE) as ctx:
            login(email="nobody@nowhere.com", password="whatever")
        # Error message must not reveal whether email exists
        self.assertNotIn("email", ctx.exception.message.lower().replace("invalid email or password", ""))
        print(f"  ✓ Unknown email rejected with safe error message")

    def test_duplicate_email_rejected(self):
        """Registering same email twice must fail."""
        from skillos.shared.exceptions import ValidationError as VE
        email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
        register(email=email, password="pass1234", display_name="A")
        with self.assertRaises(VE):
            register(email=email, password="pass1234", display_name="B")
        print(f"  ✓ Duplicate email registration rejected")

    def test_invalid_token_rejected(self):
        """Tampered token must not authenticate."""
        email = f"test-{uuid.uuid4().hex[:8]}@example.com"
        register(email=email, password="pass1234", display_name="T")
        token = login(email=email, password="pass1234")

        # Tamper with the payload
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + "TAMPERED" + "." + parts[2]
        result = get_current_user(tampered)
        self.assertIsNone(result, "Tampered token must return None")
        print(f"  ✓ Tampered token rejected")

    def test_expired_token_rejected(self):
        """Manually-created expired token must be rejected."""
        import json, base64, hmac as hmac_mod, hashlib
        from skillos.auth.service import SECRET_KEY, _b64url_encode, _sign

        # Create a token that expired 1 hour ago
        header  = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        exp     = int((datetime.datetime.now(datetime.timezone.utc)
                       - datetime.timedelta(hours=1)).timestamp())
        payload = _b64url_encode(json.dumps(
            {"user_id": "u1", "email": "x@x.com", "exp": exp}
        ).encode())
        sig   = _sign(f"{header}.{payload}")
        token = f"{header}.{payload}.{sig}"

        result = verify_token(token)
        self.assertIsNone(result, "Expired token must return None")
        print(f"  ✓ Expired token rejected")

    def test_password_hash_is_never_stored_plaintext(self):
        """Stored password hash must not contain the plaintext password."""
        email    = f"pw-{uuid.uuid4().hex[:8]}@example.com"
        password = "my-secret-password"
        register(email=email, password=password, display_name="P")

        row = fetchone("SELECT password_hash FROM users WHERE email = ?", (email,))
        self.assertIsNotNone(row)
        self.assertNotIn(password, row["password_hash"],
            "Plaintext password must not appear in stored hash")
        self.assertGreater(len(row["password_hash"]), 32,
            "Hash must be substantial (not trivially short)")
        print(f"  ✓ Password stored as hash, not plaintext")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 7 — END-TO-END HTTP: AUTH GATE + SUBMISSION OWNERSHIP
# ─────────────────────────────────────────────────────────────────────────────

class TestHTTPAuthGate(unittest.TestCase):
    """
    EXIT CRITERION 6 (HTTP layer): Auth failure cannot submit code via the API.

    These tests start a real HTTP server on a random port.
    They prove the route handler itself enforces auth — not just the service layer.

    WHY THIS MATTERS:
      Phase 1's test_phase1.py proved service-layer correctness.
      This class proves the HTTP layer enforces auth as a gate.
      A bug in _handle_submit() that skips _require_auth() would be
      caught here and nowhere else.

    REAL BUGS FOUND HERE:
      1. threading not imported (caught first run)
      2. config.PHASE_AUTH_ENABLED reload doesn't affect already-imported modules
         Fix: set env var AND patch config object directly
      3. task-double-001 not seeded in Phase 2 test DB
         Fix: seed it in setUpClass before starting server
    """

    @classmethod
    def setUpClass(cls):
        import http.server
        from skillos.config import config as _config

        # Patch config DIRECTLY — importlib.reload doesn't affect already-imported refs
        _config.PHASE_AUTH_ENABLED = True

        # Seed a published task for the HTTP tests to submit to
        from skillos.db.database import get_db
        from skillos.db.seed import seed as _seed
        _seed()  # idempotent — seeds task-double-001 if not already present
        # Also ensure it's published
        db = get_db()
        db.execute("UPDATE tasks SET is_published = 1 WHERE id = 'task-double-001'")
        db.commit()

        # Register and login a real user for bearer token tests
        from skillos.auth.service import register as _reg, login as _log
        cls.email    = f"http-test-{uuid.uuid4().hex[:6]}@example.com"
        cls.password = "http-test-password"
        _reg(email=cls.email, password=cls.password, display_name="HTTP Tester")
        cls.token = _log(email=cls.email, password=cls.password)

        # Start a real HTTP server on a random free port
        cls.server = http.server.HTTPServer(("127.0.0.1", 0), SkillOSHandler)
        cls.port   = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        from skillos.config import config as _config
        _config.PHASE_AUTH_ENABLED = False

    def _post(self, path: str, body: dict, token: str = None) -> tuple[int, dict]:
        import http.client, json as _json
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        payload = _json.dumps(body).encode()
        conn.request("POST", path, body=payload, headers=headers)
        resp = conn.getresponse()
        return resp.status, _json.loads(resp.read())

    def _get(self, path: str, token: str = None) -> tuple[int, dict]:
        import http.client, json as _json
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        return resp.status, _json.loads(resp.read())

    def test_submit_without_token_returns_401(self):
        """POST /submit without Authorization header must return 401."""
        status, body = self._post("/submit", {
            "task_id": "task-double-001", "code": "print(1)"
        }, token=None)
        self.assertEqual(status, 401,
            f"Expected 401, got {status}: {body}")
        self.assertIn("error", body)
        print(f"  ✓ Submit without token → 401 ({body['error']})")

    def test_submit_with_invalid_token_returns_401(self):
        """POST /submit with a garbage token must return 401."""
        status, body = self._post("/submit", {
            "task_id": "task-double-001", "code": "print(1)"
        }, token="not.a.real.token")
        self.assertEqual(status, 401,
            f"Expected 401, got {status}: {body}")
        print(f"  ✓ Submit with invalid token → 401")

    def test_submit_with_valid_token_accepted(self):
        """POST /submit with valid token must return 202 (submission created)."""
        status, body = self._post("/submit", {
            "task_id": "task-double-001",
            "code": "n = int(input()); print(n * 2)",
        }, token=self.token)
        self.assertEqual(status, 202,
            f"Expected 202, got {status}: {body}")
        self.assertIn("submission_id", body)
        print(f"  ✓ Submit with valid token → 202 (id={body['submission_id'][:8]}...)")

    def test_submission_ownership_enforced(self):
        """
        User A's submission must not be visible to User B.
        GET /submission/{id} must return 404 for a different user's submission.
        """
        from skillos.auth.service import register as _reg, login as _log

        # Create User B
        email_b = f"user-b-{uuid.uuid4().hex[:6]}@example.com"
        _reg(email=email_b, password="password-b-123", display_name="User B")
        token_b = _log(email=email_b, password="password-b-123")

        # User A submits
        status, body = self._post("/submit", {
            "task_id": "task-double-001",
            "code": "n = int(input()); print(n * 2)",
        }, token=self.token)
        self.assertEqual(status, 202)
        sub_id = body["submission_id"]

        # User B tries to read User A's submission → must be 404
        status_b, body_b = self._get(f"/submission/{sub_id}", token=token_b)
        self.assertEqual(status_b, 404,
            f"User B should not see User A's submission. Got {status_b}: {body_b}")

        # User A can read their own submission → must be 200
        status_a, body_a = self._get(f"/submission/{sub_id}", token=self.token)
        self.assertEqual(status_a, 200,
            f"User A should see their own submission. Got {status_a}: {body_a}")

        print(f"  ✓ Submission ownership enforced: UserB→404, UserA→200")


# ─────────────────────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────────────────────

from skillos.api.app import SkillOSHandler


# ─────────────────────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    test_classes = [
        TestReplayInvariant,
        TestScoringAlgorithm,
        TestFailureContributions,
        TestSkillIsolation,
        TestAntiGaming,
        TestAuth,
        TestHTTPAuthGate,
    ]
    criteria = {
        TestReplayInvariant:      "CRITERION 1 — Replay invariant (THE trust test)",
        TestScoringAlgorithm:     "CRITERION 5 — Algorithm math is correct",
        TestFailureContributions: "CRITERIA 3&4 — Wrong/timeout/crash = zero",
        TestSkillIsolation:       "CRITERION 2 — Skills are isolated correctly",
        TestAntiGaming:           "CRITERION 8 — Task dedup prevents gaming",
        TestAuth:                 "CRITERIA 6&7 — Auth gate + token security",
        TestHTTPAuthGate:         "CRITERION 6 (HTTP) — Auth gate enforced at route level",
    }

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    print("\n" + "═" * 65)
    print("  SKILLOS PHASE 2 — EXIT CRITERIA TEST SUITE")
    print("  All must pass before Phase 3 (frontend)")
    print("═" * 65)
    for cls, label in criteria.items():
        print(f"  {label}")
    print("═" * 65 + "\n")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "═" * 65)
    if result.wasSuccessful():
        print("  ✅ ALL PHASE 2 EXIT CRITERIA PASSED")
        print("  You may proceed to Phase 3: frontend.")
    else:
        n = len(result.failures) + len(result.errors)
        print(f"  ⛔ {n} FAILURE(S) — fix all before proceeding")
    print("═" * 65)

    sys.exit(0 if result.wasSuccessful() else 1)

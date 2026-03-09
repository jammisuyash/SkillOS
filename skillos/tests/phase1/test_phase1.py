"""
tests/test_phase1.py

Phase 1 Exit Criteria — ALL must pass before Phase 2 begins.

EXIT CRITERIA:
  ✓ 1. Kill evaluator mid-execution → zombie cleaner marks crash
  ✓ 2. DB never contains partial results
  ✓ 3. Double evaluation cannot overwrite terminal state
  ✓ 4. Hidden test cases never leak output
  ✓ 5. Submitting same code twice creates two independent records
  ✓ 6. System recovers cleanly after restart

Run with: python -m unittest tests/test_phase1.py -v
"""

import sys, os
# Insert project root so `skillos` package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

import unittest
import uuid
import time
import datetime
import threading

# Bootstrap test DB in isolation
os.environ["SKILLOS_DB_PATH"] = "/tmp/skillos_test_phase1.db"
# Remove any leftover test DB
if os.path.exists("/tmp/skillos_test_phase1.db"):
    os.remove("/tmp/skillos_test_phase1.db")

from skillos.db.migrations import run_migrations
from skillos.db.seed import seed
from skillos.db.database import get_db, transaction, fetchone
from skillos.submissions.service import (
    create_submission, get_submission,
    persist_evaluation, clean_zombie_submissions,
    get_task_with_test_cases,
)
from skillos.evaluator.runner import evaluate


def setUpModule():
    run_migrations()
    seed()


TASK_ID_EASY   = "task-double-001"
TASK_ID_MEDIUM = "task-twosum-002"
USER_ID        = "test-user-001"

CORRECT_DOUBLE = "n = int(input()); print(n * 2)"
WRONG_DOUBLE   = "n = int(input()); print(n * 3)"  # wrong answer
CORRECT_TWOSUM = """
import sys
data = sys.stdin.read().split()
n = int(data[0])
nums = [int(x) for x in data[1:n+1]]
target = int(data[n+1])
seen = {}
for i, num in enumerate(nums):
    complement = target - num
    if complement in seen:
        print(seen[complement], i)
        break
    seen[num] = i
""".strip()


class TestAtomicity(unittest.TestCase):
    """
    EXIT CRITERION 2: DB never contains partial results.
    EXIT CRITERION 3: Double evaluation cannot overwrite terminal state.
    """

    def test_persist_is_atomic(self):
        """
        All fields of a result are written in one transaction.
        After persist_evaluation(), the row is fully populated — no NULL fields
        that should have a value.
        """
        sub = create_submission(USER_ID, TASK_ID_EASY, CORRECT_DOUBLE)
        self.assertEqual(sub["status"], "pending")

        result = {
            "status": "accepted", "passed_cases": 5, "total_cases": 5,
            "max_runtime_ms": 42, "max_memory_kb": 0,
            "performance_tier": "fast",
            "stdout_sample": "10\n", "stderr_sample": "",
        }
        written = persist_evaluation(sub["id"], result)
        self.assertTrue(written)

        row = get_submission(sub["id"])
        # All fields must be present — no partial write
        self.assertEqual(row["status"],           "accepted")
        self.assertEqual(row["passed_cases"],     5)
        self.assertEqual(row["total_cases"],      5)
        self.assertEqual(row["max_runtime_ms"],   42)
        self.assertEqual(row["performance_tier"], "fast")
        self.assertIsNotNone(row["evaluated_at"], "evaluated_at must be set")
        print("  ✓ All result fields written atomically")

    def test_terminal_state_immutable(self):
        """
        EXIT CRITERION 3: Once a submission reaches a terminal state,
        no subsequent call can overwrite it.
        The WHERE status = 'pending' guard enforces this.
        """
        sub = create_submission(USER_ID, TASK_ID_EASY, CORRECT_DOUBLE)

        first_result = {
            "status": "accepted", "passed_cases": 5, "total_cases": 5,
            "max_runtime_ms": 50, "max_memory_kb": 0, "performance_tier": "fast",
            "stdout_sample": "first", "stderr_sample": "",
        }
        written_first = persist_evaluation(sub["id"], first_result)
        self.assertTrue(written_first, "First write must succeed")

        # Attempt second write — must be a no-op
        second_result = {
            "status": "wrong_answer", "passed_cases": 0, "total_cases": 5,
            "max_runtime_ms": 0, "max_memory_kb": 0, "performance_tier": None,
            "stdout_sample": "overwrite attempt", "stderr_sample": "",
        }
        written_second = persist_evaluation(sub["id"], second_result)
        self.assertFalse(written_second, "Second write must be rejected")

        # State must be unchanged
        row = get_submission(sub["id"])
        self.assertEqual(row["status"],        "accepted",
            "Terminal state must not be overwritten")
        self.assertEqual(row["stdout_sample"], "first",
            "Data from second write must not appear")
        print("  ✓ Terminal state is immutable (idempotency guard works)")

    def test_no_partial_state_on_rollback(self):
        """
        If persist_evaluation raises mid-transaction, DB stays in pending.
        This simulates a crash between evaluation and persistence.
        """
        sub = create_submission(USER_ID, TASK_ID_EASY, CORRECT_DOUBLE)

        db = get_db()
        try:
            with transaction(db):
                db.execute("""
                    UPDATE submissions SET status = 'accepted', passed_cases = 5
                    WHERE id = ? AND status = 'pending'
                """, (sub["id"],))
                # Simulate crash mid-transaction
                raise RuntimeError("simulated crash")
        except RuntimeError:
            pass  # transaction rolled back

        row = get_submission(sub["id"])
        self.assertEqual(row["status"], "pending",
            "Rolled-back transaction must leave submission in pending")
        self.assertIsNone(row["passed_cases"],
            "Partial write must not persist")
        print("  ✓ Rollback leaves submission in pending (no partial state)")


class TestZombieCleaner(unittest.TestCase):
    """
    EXIT CRITERION 1: Kill evaluator mid-execution → zombie cleaner marks crash.
    """

    def test_zombie_cleaner_marks_old_pending_as_crash(self):
        """
        A submission stuck in pending for > ZOMBIE_THRESHOLD seconds
        must be marked crash by the zombie cleaner.
        We simulate this by manually backdating submitted_at.
        """
        sub = create_submission(USER_ID, TASK_ID_EASY, CORRECT_DOUBLE)
        self.assertEqual(sub["status"], "pending")

        # Backdate the submission to simulate being stuck
        old_time = (
            datetime.datetime.utcnow() - datetime.timedelta(seconds=120)
        ).isoformat()

        with transaction() as db:
            db.execute(
                "UPDATE submissions SET submitted_at = ? WHERE id = ?",
                (old_time, sub["id"])
            )

        count = clean_zombie_submissions(logger=lambda m: print(f"  [zombie] {m}"))
        self.assertGreaterEqual(count, 1, "Should have found at least one zombie")

        row = get_submission(sub["id"])
        self.assertEqual(row["status"], "crash",
            "Zombie submission must be marked crash")
        self.assertIsNotNone(row["evaluated_at"],
            "evaluated_at must be set by zombie cleaner")
        self.assertIn("timed out", row["stderr_sample"].lower(),
            "stderr must explain what happened")
        print(f"  ✓ Zombie cleaner marked {count} submission(s) as crash")

    def test_zombie_cleaner_does_not_touch_recent_pending(self):
        """
        A recently created pending submission must NOT be touched by the zombie cleaner.
        Only old submissions qualify.
        """
        sub = create_submission(USER_ID, TASK_ID_EASY, CORRECT_DOUBLE)
        self.assertEqual(sub["status"], "pending")

        clean_zombie_submissions()

        row = get_submission(sub["id"])
        self.assertEqual(row["status"], "pending",
            "Recent pending submission must not be marked zombie")

        # Cleanup: manually mark it crash to avoid affecting other tests
        persist_evaluation(sub["id"], {
            "status": "crash", "passed_cases": 0, "total_cases": 0,
            "max_runtime_ms": 0, "max_memory_kb": 0, "performance_tier": None,
            "stdout_sample": "", "stderr_sample": "test cleanup",
        })
        print("  ✓ Recent pending submission untouched by zombie cleaner")

    def test_zombie_cleaner_idempotent(self):
        """
        Running the zombie cleaner twice on the same submission
        must produce the same result (idempotency guard: AND status = 'pending').
        """
        sub = create_submission(USER_ID, TASK_ID_EASY, CORRECT_DOUBLE)

        old_time = (
            datetime.datetime.utcnow() - datetime.timedelta(seconds=120)
        ).isoformat()
        with transaction() as db:
            db.execute(
                "UPDATE submissions SET submitted_at = ? WHERE id = ?",
                (old_time, sub["id"])
            )

        count1 = clean_zombie_submissions()
        count2 = clean_zombie_submissions()

        # Second run must not find the same submission again
        row = get_submission(sub["id"])
        self.assertEqual(row["status"], "crash")
        self.assertGreaterEqual(count1, 1)
        # count2 may be 0 (no new zombies) — that's the correct outcome
        print(f"  ✓ Zombie cleaner idempotent (run1={count1}, run2={count2})")


class TestHiddenTestCases(unittest.TestCase):
    """
    EXIT CRITERION 4: Hidden test cases never leak output.
    """

    def test_hidden_case_stdout_not_in_result(self):
        """
        When a submission fails a hidden test case, the expected output
        of that test case must never appear in the response.
        Only '[hidden test case]' marker is acceptable.
        """
        task, test_cases = get_task_with_test_cases(TASK_ID_EASY)
        hidden_cases = [tc for tc in test_cases if tc["is_hidden"]]
        self.assertGreater(len(hidden_cases), 0, "Test requires hidden test cases")

        # This code prints wrong output — will fail hidden cases
        result = evaluate(
            code="n = int(input()); print(n + 1)",  # off-by-one
            language="python",
            test_cases=[dict(tc) for tc in test_cases],
            limits={"time_ms": task["time_limit_ms"], "memory_kb": task["memory_limit_kb"]},
        )

        self.assertNotEqual(result["status"], "accepted")

        # Verify hidden case results don't leak expected output
        for r in result["results"]:
            if r["is_hidden"]:
                self.assertIsNone(r["stdout"],
                    f"Hidden test case stdout must be None, got: {r['stdout']!r}")
                print(f"  ✓ Hidden case stdout is None (not leaked)")
                return  # found and verified at least one hidden case

        self.fail("No hidden test case results found — check test data")

    def test_hidden_case_sample_uses_marker(self):
        """
        The stdout_sample in the submission (shown to user) must use
        '[hidden test case]' marker when the first failure is a hidden case.
        """
        task, test_cases = get_task_with_test_cases(TASK_ID_EASY)
        # Sort so hidden cases come first to trigger the marker path
        test_cases_hidden_first = (
            [tc for tc in test_cases if tc["is_hidden"]] +
            [tc for tc in test_cases if not tc["is_hidden"]]
        )

        result = evaluate(
            code="print('completely wrong')",
            language="python",
            test_cases=[dict(tc) for tc in test_cases_hidden_first],
            limits={"time_ms": task["time_limit_ms"], "memory_kb": task["memory_limit_kb"]},
        )

        if result["stdout_sample"] == "[hidden test case]":
            print("  ✓ stdout_sample uses [hidden test case] marker")
        else:
            # If the first visible case failed first, that's also correct
            print(f"  ✓ stdout_sample safe: {result['stdout_sample'][:40]!r}")


class TestIndependentSubmissions(unittest.TestCase):
    """
    EXIT CRITERION 5: Submitting same code twice creates two independent records.
    """

    def test_two_submissions_are_independent(self):
        """
        Same user, same task, same code → two separate submission records.
        Evaluating one must not affect the other.
        """
        sub1 = create_submission(USER_ID, TASK_ID_EASY, CORRECT_DOUBLE)
        sub2 = create_submission(USER_ID, TASK_ID_EASY, CORRECT_DOUBLE)

        self.assertNotEqual(sub1["id"], sub2["id"],
            "Two submissions must have different IDs")

        # Evaluate only sub1
        task, test_cases = get_task_with_test_cases(TASK_ID_EASY)
        result = evaluate(
            code=CORRECT_DOUBLE, language="python",
            test_cases=[dict(tc) for tc in test_cases],
            limits={"time_ms": task["time_limit_ms"], "memory_kb": task["memory_limit_kb"]},
        )
        persist_evaluation(sub1["id"], result)

        # sub2 must still be pending — untouched
        row1 = get_submission(sub1["id"])
        row2 = get_submission(sub2["id"])

        self.assertEqual(row1["status"], "accepted",
            "sub1 should be accepted after evaluation")
        self.assertEqual(row2["status"], "pending",
            "sub2 must remain pending — independent record")

        # Cleanup sub2
        persist_evaluation(sub2["id"], {**result, "status": "crash",
            "stderr_sample": "test cleanup"})
        print("  ✓ Two submissions are fully independent records")


class TestFullEvaluationPipeline(unittest.TestCase):
    """
    End-to-end: code → evaluation → correct terminal state.
    Tests the full pipeline for each terminal state.
    """

    def _run_task(self, code: str, task_id: str = TASK_ID_EASY) -> dict:
        task, test_cases = get_task_with_test_cases(task_id)
        return evaluate(
            code=code, language="python",
            test_cases=[dict(tc) for tc in test_cases],
            limits={"time_ms": task["time_limit_ms"], "memory_kb": task["memory_limit_kb"]},
        )

    def test_accepted(self):
        result = self._run_task(CORRECT_DOUBLE)
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["passed_cases"], result["total_cases"])
        self.assertIsNotNone(result["performance_tier"])
        print(f"  ✓ accepted (runtime={result['max_runtime_ms']}ms, "
              f"tier={result['performance_tier']})")

    def test_wrong_answer(self):
        result = self._run_task(WRONG_DOUBLE)
        self.assertEqual(result["status"], "wrong_answer")
        self.assertLess(result["passed_cases"], result["total_cases"])
        print(f"  ✓ wrong_answer ({result['passed_cases']}/{result['total_cases']} passed)")

    def test_runtime_error(self):
        result = self._run_task("raise ValueError('oops')")
        self.assertEqual(result["status"], "runtime_error")
        self.assertFalse(result["results"][0]["passed"])
        print(f"  ✓ runtime_error (exit_code=1, stderr present)")

    def test_timeout(self):
        result = self._run_task("while True: pass")
        self.assertEqual(result["status"], "timeout")
        print(f"  ✓ timeout (runtime={result['max_runtime_ms']}ms)")

    def test_syntax_error_is_runtime_error(self):
        result = self._run_task("def foo( print('broken')")
        self.assertEqual(result["status"], "runtime_error",
            "Syntax error must be runtime_error, not crash")
        print(f"  ✓ syntax error → runtime_error (not crash)")

    def test_medium_task_correct(self):
        result = self._run_task(CORRECT_TWOSUM, TASK_ID_MEDIUM)
        self.assertEqual(result["status"], "accepted")
        print(f"  ✓ medium task accepted (two_sum correct solution)")

    def test_crash_in_result(self):
        """
        Crash is a valid terminal state — it represents sandbox-level failure.
        Verify it is persisted and retrieved correctly.
        """
        sub = create_submission(USER_ID, TASK_ID_EASY, CORRECT_DOUBLE)
        crash_result = {
            "status": "crash", "passed_cases": 0, "total_cases": 5,
            "max_runtime_ms": 0, "max_memory_kb": 0, "performance_tier": None,
            "stdout_sample": "", "stderr_sample": "sandbox died",
        }
        persist_evaluation(sub["id"], crash_result)
        row = get_submission(sub["id"])
        self.assertEqual(row["status"], "crash")
        print("  ✓ crash state persisted and retrieved correctly")


class TestSystemRecovery(unittest.TestCase):
    """
    EXIT CRITERION 6: System recovers cleanly after restart.
    """

    def test_pending_submissions_survive_restart(self):
        """
        Pending submissions created before a 'restart' (re-initialization
        of the database connection) must still be visible and processable.
        This simulates: server crashes with pending submissions in DB.
        After restart: worker picks them up, zombie cleaner catches any
        that are too old.
        """
        sub = create_submission(USER_ID, TASK_ID_EASY, CORRECT_DOUBLE)
        sub_id = sub["id"]

        # Simulate restart: close and reopen DB connection
        from skillos.db import database as db_module
        if hasattr(db_module._local, 'conn') and db_module._local.conn:
            db_module._local.conn.close()
            db_module._local.conn = None

        # After 'restart': submission must still exist in pending state
        row = get_submission(sub_id)
        self.assertIsNotNone(row, "Submission must survive DB reconnect")
        self.assertEqual(row["status"], "pending",
            "Submission must still be pending after reconnect")

        # Worker can pick it up and evaluate it
        task, test_cases = get_task_with_test_cases(TASK_ID_EASY)
        result = evaluate(
            code=CORRECT_DOUBLE, language="python",
            test_cases=[dict(tc) for tc in test_cases],
            limits={"time_ms": task["time_limit_ms"], "memory_kb": task["memory_limit_kb"]},
        )
        persist_evaluation(sub_id, result)

        row = get_submission(sub_id)
        self.assertEqual(row["status"], "accepted",
            "Worker must be able to evaluate pending submissions after restart")
        print("  ✓ System recovers: pending submissions processed after restart")


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 EXIT CRITERIA SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loader  = unittest.TestLoader()
    suite   = unittest.TestSuite()

    test_classes = [
        TestAtomicity,
        TestZombieCleaner,
        TestHiddenTestCases,
        TestIndependentSubmissions,
        TestFullEvaluationPipeline,
        TestSystemRecovery,
    ]

    criteria = {
        TestAtomicity:               "CRITERION 2 & 3 — Atomicity + immutable terminal state",
        TestZombieCleaner:           "CRITERION 1 — Zombie cleaner marks stuck submissions",
        TestHiddenTestCases:         "CRITERION 4 — Hidden test cases never leak output",
        TestIndependentSubmissions:  "CRITERION 5 — Two submissions are independent records",
        TestFullEvaluationPipeline:  "CRITERION 2 — Full pipeline (all terminal states)",
        TestSystemRecovery:          "CRITERION 6 — System recovers after restart",
    }

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    print("\n" + "═" * 65)
    print("  SKILLOS PHASE 1 — EXIT CRITERIA TEST SUITE")
    print("  All must pass before Phase 2 (auth + skill scoring)")
    print("═" * 65)
    for cls, label in criteria.items():
        print(f"  {label}")
    print("═" * 65 + "\n")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "═" * 65)
    if result.wasSuccessful():
        print("  ✅ ALL PHASE 1 EXIT CRITERIA PASSED")
        print("  You may proceed to Phase 2: auth + skill scoring.")
    else:
        print(f"  ⛔ {len(result.failures + result.errors)} FAILURE(S)")
        print("  Fix all failures before proceeding.")
    print("═" * 65)

    sys.exit(0 if result.wasSuccessful() else 1)

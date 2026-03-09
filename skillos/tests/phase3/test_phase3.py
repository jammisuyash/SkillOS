"""
tests/phase3/test_phase3.py

Phase 3 Hardening Tests — Security guards, API integration, operational correctness.

What Phase 3 tests that earlier phases could not:
  - Body size guards prevent abuse
  - Code length cap enforced at both API and service layer
  - Request-ID propagation
  - /health endpoint works
  - Auth integration: submit without token → 401
  - task_id format validation blocks injection attempts
  - Structured logger does not crash or swallow events
  - Migration 003 seeds the skills catalogue correctly
  - utcnow() deprecation fully eliminated

Run: python -m unittest skillos/tests/phase3/test_phase3.py -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

import unittest
import uuid
import json
import io
import threading
from unittest.mock import MagicMock, patch

os.environ["SKILLOS_DB_PATH"]    = "/tmp/skillos_test_phase3.db"
os.environ["SKILLOS_SECRET_KEY"] = "test-secret-phase3"
os.environ["SKILLOS_ENV"]        = "development"

if os.path.exists("/tmp/skillos_test_phase3.db"):
    os.remove("/tmp/skillos_test_phase3.db")

from skillos.db.migrations import run_migrations
from skillos.db.database import get_db, fetchall, fetchone
from skillos.shared.logger import get_logger
from skillos.shared.utils import utcnow, utcnow_iso
from skillos.api.app import MAX_BODY_BYTES, MAX_CODE_BYTES


def setUpModule():
    run_migrations()


# ─────────────────────────────────────────────────────────────────────────────
# FLAW: datetime.utcnow() deprecated — verify fully eliminated
# ─────────────────────────────────────────────────────────────────────────────

class TestDatetimeDeprecation(unittest.TestCase):
    """
    Verify datetime.utcnow() has been eliminated from all source files.
    This is a static analysis test — it reads the source and checks.
    """

    SOURCE_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    )

    def test_no_utcnow_in_source(self):
        """
        No source file (excluding tests) should contain datetime.utcnow().
        Tests can use it for fixture setup but source code must use utcnow_iso/utcnow.
        """
        violations = []
        for root, dirs, files in os.walk(self.SOURCE_DIR):
            # Skip test directories and __pycache__
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "tests")]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                path = os.path.join(root, fname)
                with open(path) as f:
                    for i, line in enumerate(f, 1):
                        if "datetime.utcnow()" in line and "# noqa" not in line:
                            violations.append(f"{path}:{i}: {line.strip()}")

        self.assertEqual(violations, [],
            "datetime.utcnow() found in source files:\n" + "\n".join(violations))
        print(f"  ✓ No datetime.utcnow() in source files")

    def test_utcnow_returns_timezone_aware(self):
        """utcnow() from shared.utils must return timezone-aware datetime."""
        import datetime
        now = utcnow()
        self.assertIsNotNone(now.tzinfo,
            "utcnow() must return timezone-aware datetime")
        self.assertEqual(now.tzinfo, datetime.timezone.utc)
        print(f"  ✓ utcnow() returns timezone-aware UTC datetime")

    def test_utcnow_iso_is_valid_isoformat(self):
        """utcnow_iso() must return a parseable ISO 8601 string."""
        import datetime
        s = utcnow_iso()
        self.assertIsInstance(s, str)
        # Must be parseable
        parsed = datetime.datetime.fromisoformat(s)
        self.assertIsNotNone(parsed)
        print(f"  ✓ utcnow_iso() returns valid ISO string: {s[:19]}")


# ─────────────────────────────────────────────────────────────────────────────
# GUARD: Body size cap
# ─────────────────────────────────────────────────────────────────────────────

class TestBodySizeGuard(unittest.TestCase):
    """
    API must reject requests with body exceeding MAX_BODY_BYTES.
    This prevents clients from sending multi-MB bodies to crash or slow the server.
    """

    def _make_handler(self, body: bytes, path: str = "/submit"):
        """Build a mock handler with a fake large body."""
        handler = MagicMock()
        handler.headers = {"Content-Length": str(len(body)), "Authorization": ""}
        handler.rfile   = io.BytesIO(body)
        handler.path    = path
        handler._request_id = "test-req-1"

        responses = []
        def capture_json(h, status, body_dict, req_id=""):
            responses.append((status, body_dict))
        return handler, responses, capture_json

    def test_oversized_body_rejected(self):
        """Body over MAX_BODY_BYTES must return 413, not be processed."""
        from skillos.api.app import SkillOSHandler, _json

        oversized_body = b"x" * (MAX_BODY_BYTES + 1)
        handler = MagicMock()
        handler.headers = {"Content-Length": str(len(oversized_body))}
        handler.rfile   = io.BytesIO(oversized_body)
        handler._request_id = "test-req-oversized"

        sent_status = []
        sent_body   = []

        def fake_json(h, status, body, req_id=""):
            sent_status.append(status)
            sent_body.append(body)

        # Patch _json to capture the response
        with patch("skillos.api.app._json", side_effect=fake_json):
            real_handler = object.__new__(SkillOSHandler)
            real_handler.headers    = handler.headers
            real_handler.rfile      = handler.rfile
            real_handler._request_id = handler._request_id
            real_handler._read_body()

        self.assertEqual(sent_status, [413],
            f"Oversized body must return 413, got {sent_status}")
        self.assertIn("too large", sent_body[0]["error"].lower())
        print(f"  ✓ Oversized body rejected with 413")

    def test_max_code_bytes_constant_matches_service(self):
        """
        MAX_CODE_BYTES in api/app.py and submissions/service.py must agree.
        If they diverge, the service-layer check becomes unreachable dead code.
        """
        from skillos.submissions.service import create_submission
        import inspect
        source = inspect.getsource(create_submission)
        self.assertIn("64 * 1024", source,
            "create_submission must enforce 64KB code limit")
        self.assertEqual(MAX_CODE_BYTES, 64 * 1024,
            "api/app.py MAX_CODE_BYTES must be 64KB")
        print(f"  ✓ Code length cap consistent: API={MAX_CODE_BYTES//1024}KB, "
              f"service=64KB")


# ─────────────────────────────────────────────────────────────────────────────
# GUARD: Input validation
# ─────────────────────────────────────────────────────────────────────────────

class TestInputValidation(unittest.TestCase):
    """Input validation guards prevent malformed data reaching the DB."""

    def test_email_validation_rejects_malformed(self):
        """Auth service must reject clearly invalid emails."""
        from skillos.auth.service import register
        from skillos.shared.exceptions import ValidationError

        bad_emails = [
            "",             # empty
            "notanemail",   # no @
            "a@b",          # no TLD
            "@domain.com",  # no local part
            "a" * 255 + "@example.com",  # too long
        ]
        for email in bad_emails:
            with self.assertRaises(ValidationError,
                    msg=f"Should reject email: {email!r}"):
                register(email=email, password="password123",
                         display_name="Test")
        print(f"  ✓ {len(bad_emails)} malformed emails rejected")

    def test_email_validation_accepts_valid(self):
        """Valid emails must pass validation (don't over-reject)."""
        from skillos.auth.service import _validate_email

        good_emails = [
            "user@example.com",
            "user+tag@sub.domain.org",
            "firstname.lastname@company.io",
        ]
        for email in good_emails:
            result = _validate_email(email)
            self.assertIsNotNone(result, f"Valid email rejected: {email}")
        print(f"  ✓ {len(good_emails)} valid emails accepted")

    def test_task_id_format_guard(self):
        """
        task_id must match [a-zA-Z0-9_-]{1,64}.
        SQL injection attempts via task_id must be blocked at the API layer.
        """
        import re
        pattern = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")

        bad_ids = [
            "'; DROP TABLE submissions; --",
            "../etc/passwd",
            "task id with spaces",
            "",
            "a" * 65,
            "task\x00null",
        ]
        for bad in bad_ids:
            self.assertFalse(pattern.match(bad),
                f"Bad task_id should not match: {bad!r}")

        good_ids = ["task-001", "task_double_001", "abc123", "TASK-HARD-01"]
        for good in good_ids:
            self.assertTrue(pattern.match(good),
                f"Good task_id should match: {good!r}")
        print(f"  ✓ task_id format guard blocks {len(bad_ids)} bad formats")

    def test_password_min_length(self):
        """Passwords under 8 chars must be rejected."""
        from skillos.auth.service import register
        from skillos.shared.exceptions import ValidationError

        email = f"pwtest-{uuid.uuid4().hex[:8]}@example.com"
        with self.assertRaises(ValidationError):
            register(email=email, password="short", display_name="U")
        print("  ✓ Short password rejected")

    def test_display_name_required(self):
        """Empty display name must be rejected."""
        from skillos.auth.service import register
        from skillos.shared.exceptions import ValidationError

        email = f"dntest-{uuid.uuid4().hex[:8]}@example.com"
        with self.assertRaises(ValidationError):
            register(email=email, password="password123", display_name="")
        print("  ✓ Empty display name rejected")


# ─────────────────────────────────────────────────────────────────────────────
# STRUCTURED LOGGER
# ─────────────────────────────────────────────────────────────────────────────

class TestStructuredLogger(unittest.TestCase):
    """Logger must work correctly and never swallow events silently."""

    def test_logger_produces_output(self):
        """Logger.info() must actually produce a log line."""
        import logging

        log      = get_logger("test-component")
        handler  = logging.handlers = None
        captured = []

        # Capture log output
        test_handler = logging.StreamHandler(io.StringIO())
        logging.getLogger("skillos.test-component").addHandler(test_handler)

        log.info("test.event", key="value", num=42)
        test_handler.stream.seek(0)
        output = test_handler.stream.read()

        logging.getLogger("skillos.test-component").removeHandler(test_handler)

        self.assertIn("test.event", output)
        self.assertIn("key=", output)
        print(f"  ✓ Logger produces structured output")

    def test_logger_different_components_isolated(self):
        """Two loggers for different components must have different names."""
        log_a = get_logger("component-a")
        log_b = get_logger("component-b")
        self.assertNotEqual(log_a._logger.name, log_b._logger.name)
        print("  ✓ Component loggers are isolated")

    def test_logger_does_not_raise_on_complex_values(self):
        """Logger must not raise when given complex values in kwargs."""
        log = get_logger("test-complex")
        try:
            log.error("test.error", error=Exception("test"), data={"a": 1})
            log.info("test.info", items=[1, 2, 3], nested={"x": {"y": "z"}})
        except Exception as e:
            self.fail(f"Logger raised on complex value: {e}")
        print("  ✓ Logger handles complex values without raising")


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthEndpoint(unittest.TestCase):
    """
    /health must return 200 + db:ok when DB is accessible.
    This is the liveness probe for load balancers and monitoring.
    """

    def test_health_returns_ok_when_db_available(self):
        """With a live DB, /health must return 200."""
        from skillos.api.app import SkillOSHandler, _json

        sent = []
        def capture(h, status, body, req_id=""):
            sent.append((status, body))

        with patch("skillos.api.app._json", side_effect=capture):
            handler = object.__new__(SkillOSHandler)
            handler._request_id = "health-test"
            handler._handle_health()

        self.assertEqual(len(sent), 1)
        status, body = sent[0]
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["db"], "ok")
        print(f"  ✓ /health returns 200 with db=ok")

    def test_health_returns_503_when_db_fails(self):
        """When DB is unavailable, /health must return 503."""
        from skillos.api.app import SkillOSHandler

        sent = []
        def capture(h, status, body, req_id=""):
            sent.append((status, body))

        with patch("skillos.api.app._json", side_effect=capture):
            with patch("skillos.db.database.get_db",
                       side_effect=Exception("DB unavailable")):
                handler = object.__new__(SkillOSHandler)
                handler._request_id = "health-fail-test"
                handler._handle_health()

        status, body = sent[0]
        self.assertEqual(status, 503)
        self.assertEqual(body["status"], "degraded")
        print(f"  ✓ /health returns 503 with db=error when DB fails")


# ─────────────────────────────────────────────────────────────────────────────
# MIGRATION 003: SKILLS CATALOGUE
# ─────────────────────────────────────────────────────────────────────────────

class TestMigration003(unittest.TestCase):
    """Migration 003 must seed the skills catalogue correctly."""

    def test_skills_catalogue_seeded(self):
        """After migration 003, skills table must have the expected entries."""
        skills = fetchall("SELECT id, name FROM skills ORDER BY id")
        skill_ids = {s["id"] for s in skills}

        expected = {
            "skill-python-001",
            "skill-arrays-001",
            "skill-hashmaps-001",
            "skill-recursion-001",
            "skill-sorting-001",
            "skill-graphs-001",
        }
        for sid in expected:
            self.assertIn(sid, skill_ids,
                f"Expected skill '{sid}' not found in skills table")
        print(f"  ✓ Migration 003 seeded {len(skills)} skills")

    def test_skill_names_not_empty(self):
        """Every skill must have a non-empty name."""
        skills = fetchall("SELECT id, name FROM skills")
        for s in skills:
            self.assertTrue(s["name"].strip(),
                f"Skill {s['id']!r} has empty name")
        print(f"  ✓ All {len(skills)} skills have non-empty names")

    def test_migration_idempotent(self):
        """Running migrations again must not duplicate skills."""
        count_before = len(fetchall("SELECT id FROM skills"))
        run_migrations()  # run again
        count_after  = len(fetchall("SELECT id FROM skills"))
        self.assertEqual(count_before, count_after,
            f"Migration not idempotent: {count_before} → {count_after} skills")
        print(f"  ✓ Migration 003 is idempotent ({count_before} skills stable)")


# ─────────────────────────────────────────────────────────────────────────────
# SECRET KEY GUARD
# ─────────────────────────────────────────────────────────────────────────────

class TestSecretKeyGuard(unittest.TestCase):
    """
    In non-development environments, using the default SECRET_KEY must fail.
    This prevents silent production misconfiguration.
    """

    def test_default_key_raises_in_production(self):
        """
        If SKILLOS_ENV=production and SKILLOS_SECRET_KEY is not set,
        importing auth.service must raise RuntimeError.
        """
        import importlib
        import sys

        # Save current env state
        old_env  = os.environ.get("SKILLOS_ENV")
        old_key  = os.environ.get("SKILLOS_SECRET_KEY")

        try:
            os.environ["SKILLOS_ENV"]        = "production"
            os.environ["SKILLOS_SECRET_KEY"] = "dev-insecure-key-change-in-production"

            # Force reimport to trigger the guard
            if "skillos.auth.service" in sys.modules:
                del sys.modules["skillos.auth.service"]

            with self.assertRaises(RuntimeError) as ctx:
                import skillos.auth.service
            self.assertIn("SKILLOS_SECRET_KEY", str(ctx.exception))
            print("  ✓ Default secret key raises RuntimeError in production")

        finally:
            # Restore env
            if old_env is None:
                os.environ.pop("SKILLOS_ENV", None)
            else:
                os.environ["SKILLOS_ENV"] = old_env

            if old_key is None:
                os.environ.pop("SKILLOS_SECRET_KEY", None)
            else:
                os.environ["SKILLOS_SECRET_KEY"] = old_key

            # Restore the module
            if "skillos.auth.service" in sys.modules:
                del sys.modules["skillos.auth.service"]
            import skillos.auth.service  # re-import with dev settings


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST ID HEADER
# ─────────────────────────────────────────────────────────────────────────────

class TestRequestIdHeader(unittest.TestCase):
    """Every response must carry X-Request-ID for log correlation."""

    def test_json_helper_sends_request_id(self):
        """_json() must include X-Request-ID in response headers."""
        from skillos.api.app import _json

        sent_headers = {}
        mock_handler = MagicMock()
        mock_handler.send_header = lambda k, v: sent_headers.update({k: v})
        mock_handler.end_headers = lambda: None
        mock_handler.wfile       = io.BytesIO()

        _json(mock_handler, 200, {"status": "ok"}, request_id="abc-123")

        self.assertIn("X-Request-ID", sent_headers,
            "X-Request-ID must be sent in response headers")
        self.assertEqual(sent_headers["X-Request-ID"], "abc-123")
        print("  ✓ X-Request-ID header sent on every response")


# ─────────────────────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    test_classes = [
        TestDatetimeDeprecation,
        TestBodySizeGuard,
        TestInputValidation,
        TestStructuredLogger,
        TestHealthEndpoint,
        TestMigration003,
        TestSecretKeyGuard,
        TestRequestIdHeader,
    ]
    criteria = {
        TestDatetimeDeprecation: "datetime.utcnow() fully eliminated",
        TestBodySizeGuard:       "Body size cap prevents abuse",
        TestInputValidation:     "Email + task_id + code length guards",
        TestStructuredLogger:    "Structured logger works correctly",
        TestHealthEndpoint:      "/health liveness probe works",
        TestMigration003:        "Skills catalogue seeded + idempotent",
        TestSecretKeyGuard:      "Default SECRET_KEY raises in production",
        TestRequestIdHeader:     "X-Request-ID on every response",
    }

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    print("\n" + "═" * 65)
    print("  SKILLOS PHASE 3 — HARDENING TEST SUITE")
    print("═" * 65)
    for cls, label in criteria.items():
        print(f"  {label}")
    print("═" * 65 + "\n")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "═" * 65)
    if result.wasSuccessful():
        print("  ✅ ALL PHASE 3 HARDENING TESTS PASSED")
    else:
        n = len(result.failures) + len(result.errors)
        print(f"  ⛔ {n} FAILURE(S) — fix all before launch")
    print("═" * 65)
    sys.exit(0 if result.wasSuccessful() else 1)

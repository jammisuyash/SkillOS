"""
evaluator/sandbox_manager.py

Unified Sandbox Manager — Auto-detects and manages Docker vs subprocess sandbox.
================================================================================

This is the single entry point for all code execution in SkillOS.
It wraps both sandbox backends and provides:

  - Automatic Docker/subprocess selection (respects SKILLOS_USE_DOCKER env var)
  - Health checks + status reporting
  - Pre-warming (pull Docker images in background at startup)
  - Language support detection
  - Execution stats (counts, avg runtime, timeouts)

USAGE:
  from skillos.evaluator.sandbox_manager import sandbox

  result = sandbox.run(
      code="print('hello')",
      stdin_input="",
      time_limit_ms=2000,
      memory_limit_kb=262144,  # 256MB
      language="python3",
  )
  # result: {stdout, stderr, exit_code, runtime_ms, timed_out, crashed, oom_killed, sandbox_mode}

  # Status (for /admin/sandbox-status):
  info = sandbox.get_info()

CONFIGURATION (.env):
  SKILLOS_USE_DOCKER=auto     # auto-detect (default)
  SKILLOS_USE_DOCKER=true     # force Docker
  SKILLOS_USE_DOCKER=false    # force subprocess
  DOCKER_MEMORY_LIMIT=256m
  DOCKER_CPU_LIMIT=0.5
  SANDBOX_PREWARM=true        # pull Docker images at startup (default: true)
"""

from __future__ import annotations
import os
import threading
import time
from typing import Optional
from skillos.shared.logger import get_logger

log = get_logger("sandbox_manager")

# ── Config ────────────────────────────────────────────────────────────────────
_FORCE      = os.environ.get("SKILLOS_USE_DOCKER", "auto").lower()
_PREWARM    = os.environ.get("SANDBOX_PREWARM", "true").lower() == "true"

# ── Language support ──────────────────────────────────────────────────────────
SUPPORTED_LANGUAGES = [
    "python3", "python",
    "javascript",
    "java",
    "cpp", "c",
    "go",
    "rust",
]

# ── Stats ─────────────────────────────────────────────────────────────────────
_stats = {
    "total":     0,
    "timeouts":  0,
    "crashes":   0,
    "total_ms":  0,
}
_stats_lock = threading.Lock()


def _record(result: dict) -> None:
    with _stats_lock:
        _stats["total"]    += 1
        _stats["total_ms"] += result.get("runtime_ms", 0)
        if result.get("timed_out"): _stats["timeouts"] += 1
        if result.get("crashed"):   _stats["crashes"]  += 1


class SandboxManager:
    """
    Unified sandbox manager — single interface for both Docker and subprocess sandboxes.
    Created once at module level; import `sandbox` directly.
    """

    def __init__(self):
        self._mode: Optional[str] = None   # "docker" or "subprocess"
        self._docker_available: bool = False
        self._prewarm_thread: Optional[threading.Thread] = None
        self._prewarm_done: bool = False
        self._prewarm_results: dict = {}
        self._init()

    def _init(self) -> None:
        """Determine sandbox mode and optionally pre-warm Docker images."""
        from skillos.evaluator.docker_sandbox import _docker_available, USE_DOCKER

        self._docker_available = _docker_available()

        if _FORCE == "true":
            self._mode = "docker"
        elif _FORCE == "false":
            self._mode = "subprocess"
        else:
            self._mode = "docker" if self._docker_available else "subprocess"

        log.info("sandbox_manager.init",
                 mode=self._mode,
                 docker_available=self._docker_available,
                 forced=_FORCE)

        # Pre-warm Docker images in background (non-blocking)
        if self._mode == "docker" and _PREWARM:
            self._prewarm_thread = threading.Thread(
                target=self._prewarm_images, daemon=True, name="sandbox-prewarm"
            )
            self._prewarm_thread.start()

    def _prewarm_images(self) -> None:
        """Pull all Docker language images in background (reduces cold-start)."""
        log.info("sandbox_manager.prewarm_start")
        try:
            from skillos.evaluator.docker_sandbox import pull_images
            self._prewarm_results = pull_images()
            ok = sum(1 for v in self._prewarm_results.values() if v)
            total = len(self._prewarm_results)
            log.info("sandbox_manager.prewarm_done",
                     ok=ok, total=total, results=self._prewarm_results)
        except Exception as e:
            log.warning("sandbox_manager.prewarm_failed", error=str(e))
        finally:
            self._prewarm_done = True

    def run(
        self,
        code:            str,
        stdin_input:     str,
        time_limit_ms:   int,
        memory_limit_kb: int,
        language:        str = "python3",
    ) -> dict:
        """
        Execute code safely. Returns standardized result dict.

        Result keys:
          stdout       (str)   — program output
          stderr       (str)   — error output / error message
          exit_code    (int|None)
          runtime_ms   (int)   — wall-clock time in milliseconds
          timed_out    (bool)
          crashed      (bool)
          oom_killed   (bool)
          sandbox_mode (str)   — "docker" or "subprocess"
        """
        start = time.perf_counter()

        try:
            from skillos.evaluator.docker_sandbox import run_in_sandbox
            result = run_in_sandbox(
                code=code,
                stdin_input=stdin_input,
                time_limit_ms=time_limit_ms,
                memory_limit_kb=memory_limit_kb,
                language=language,
            )
        except Exception as e:
            log.error("sandbox_manager.run_error", error=str(e), language=language)
            result = {
                "stdout": "", "stderr": f"Sandbox error: {e}",
                "exit_code": None, "runtime_ms": int((time.perf_counter() - start) * 1000),
                "timed_out": False, "crashed": True, "oom_killed": False,
            }

        result["sandbox_mode"] = self._mode
        _record(result)
        return result

    def get_info(self) -> dict:
        """Returns sandbox status for /admin/sandbox-status endpoint."""
        avg_ms = (
            _stats["total_ms"] / _stats["total"]
            if _stats["total"] > 0 else 0
        )
        return {
            "mode":                self._mode,
            "docker_available":    self._docker_available,
            "forced":              _FORCE,
            "prewarm_done":        self._prewarm_done,
            "prewarm_results":     self._prewarm_results,
            "supported_languages": SUPPORTED_LANGUAGES,
            "stats": {
                "total_executions": _stats["total"],
                "timeouts":         _stats["timeouts"],
                "crashes":          _stats["crashes"],
                "avg_runtime_ms":   round(avg_ms, 1),
            },
        }

    def pull_images(self) -> dict:
        """Manually trigger Docker image pre-pull (for /admin/pull-images)."""
        if self._mode != "docker":
            return {"message": "Docker not in use -- running subprocess sandbox", "pulled": {}}
        from skillos.evaluator.docker_sandbox import pull_images
        results = pull_images()
        self._prewarm_results = results
        self._prewarm_done = True
        return {"pulled": results, "all_ok": all(results.values())}


# ── Module-level singleton ─────────────────────────────────────────────────────
sandbox = SandboxManager()

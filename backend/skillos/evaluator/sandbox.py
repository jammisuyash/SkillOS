"""
skillos/evaluator/sandbox.py

Cross-platform sandbox — works on Windows AND Linux.

WINDOWS: Wall-time timeout only. No kernel resource limits.
LINUX:   Full kernel limits (CPU, memory, process count) via RLIMIT.

Production note: For real isolation, run on Linux with Docker.
Windows is for development only.
"""

import os
import sys
import subprocess
import shutil
import time
import uuid
from skillos.evaluator.limits import (
    MAX_CPU_TIME_S, MAX_WALL_TIME_S, MAX_MEMORY_BYTES,
    MAX_OUTPUT_BYTES, MAX_FILE_HANDLES, SANDBOX_TEMP_ROOT
)

_IS_WINDOWS = sys.platform == "win32"

if not _IS_WINDOWS:
    import resource
    import functools

    def _apply_resource_limits(cpu_time_s: int, memory_bytes: int):
        resource.setrlimit(resource.RLIMIT_CPU,    (cpu_time_s, cpu_time_s))
        resource.setrlimit(resource.RLIMIT_AS,     (memory_bytes, memory_bytes))
        resource.setrlimit(resource.RLIMIT_NPROC,  (1, 1))
        resource.setrlimit(resource.RLIMIT_NOFILE, (MAX_FILE_HANDLES, MAX_FILE_HANDLES))


def _python_exe() -> str:
    return "python" if _IS_WINDOWS else "python3"


def run_in_sandbox(
    code: str,
    stdin_input: str,
    time_limit_ms: int,
    memory_limit_kb: int,
) -> dict:
    """
    Execute untrusted Python code against one test case input.

    INVARIANTS:
      1. Temp dir always deleted
      2. Subprocess always terminated
      3. Always returns a dict, never raises
      4. Always bounded by wall_time_s
    """
    cpu_time_s   = min(time_limit_ms // 1000 + 1, MAX_CPU_TIME_S)
    wall_time_s  = min(cpu_time_s * 3, MAX_WALL_TIME_S)
    memory_bytes = min(memory_limit_kb * 1024, MAX_MEMORY_BYTES)

    sandbox_id    = str(uuid.uuid4())
    sandbox_dir   = os.path.join(SANDBOX_TEMP_ROOT, sandbox_id)
    solution_path = os.path.join(sandbox_dir, "solution.py")
    process       = None

    try:
        os.makedirs(sandbox_dir, exist_ok=False)
        with open(solution_path, "w") as f:
            f.write(code)

        popen_kwargs = dict(
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=sandbox_dir,
        )

        if _IS_WINDOWS:
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        else:
            preexec = functools.partial(_apply_resource_limits, cpu_time_s, memory_bytes)
            popen_kwargs["preexec_fn"] = preexec

        start_time = time.perf_counter()

        process = subprocess.Popen(
            [_python_exe(), "-u", solution_path],
            **popen_kwargs,
        )

        try:
            raw_stdout, raw_stderr = process.communicate(
                input=stdin_input.encode(),
                timeout=wall_time_s,
            )
            runtime_ms = int((time.perf_counter() - start_time) * 1000)
            timed_out  = False

        except subprocess.TimeoutExpired:
            process.kill()
            raw_stdout, raw_stderr = process.communicate()
            runtime_ms = int(wall_time_s * 1000)
            timed_out  = True

        exit_code = process.returncode

        # Windows returns 1 for Python exceptions, Linux returns -9 for SIGKILL
        sigkill = (exit_code == -9)
        if sigkill and not timed_out:
            timed_out = True

        crashed = (exit_code not in (0, 1)) and not timed_out and not sigkill

        return {
            "stdout":     raw_stdout[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"),
            "stderr":     raw_stderr[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"),
            "exit_code":  exit_code,
            "runtime_ms": runtime_ms,
            "timed_out":  timed_out,
            "crashed":    crashed,
            "oom_killed": sigkill and not timed_out,
        }

    except Exception as e:
        return {
            "stdout":     "",
            "stderr":     f"Sandbox infrastructure error: {str(e)}",
            "exit_code":  None,
            "runtime_ms": 0,
            "timed_out":  False,
            "crashed":    True,
            "oom_killed": False,
        }

    finally:
        if process and process.poll() is None:
            process.kill()
        shutil.rmtree(sandbox_dir, ignore_errors=True)

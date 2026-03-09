"""
skillos/evaluator/sandbox.py

Multi-language sandbox — Python, JavaScript (Node), Java, C++, C, Go, Rust.

LANGUAGE SUPPORT:
  - python3    → python3 solution.py
  - javascript → node solution.js
  - java       → javac Solution.java && java Solution
  - cpp        → g++ -O2 solution.cpp -o sol && ./sol
  - c          → gcc solution.c -o sol && ./sol
  - go         → go run solution.go
  - rust       → rustc solution.rs -o sol && ./sol

ISOLATION:
  - Linux: kernel resource limits (CPU, memory, process count)
  - Windows: wall-time only (for local dev)

PRODUCTION: Put Docker in front for real isolation.
"""

import os
import sys
import subprocess
import shutil
import time
import uuid
import tempfile
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
        resource.setrlimit(resource.RLIMIT_NPROC,  (50, 50))   # allow Java threads
        resource.setrlimit(resource.RLIMIT_NOFILE, (MAX_FILE_HANDLES, MAX_FILE_HANDLES))


# ── Language configs ─────────────────────────────────────────────────────────

LANGUAGE_CONFIG = {
    "python3": {
        "filename":  "solution.py",
        "compile":   None,
        "run":       ["python3", "-u", "solution.py"],
        "run_win":   ["python", "-u", "solution.py"],
    },
    "python": {
        "filename":  "solution.py",
        "compile":   None,
        "run":       ["python3", "-u", "solution.py"],
        "run_win":   ["python", "-u", "solution.py"],
    },
    "javascript": {
        "filename": "solution.js",
        "compile":  None,
        "run":      ["node", "solution.js"],
        "run_win":  ["node", "solution.js"],
    },
    "java": {
        "filename": "Solution.java",
        "compile":  ["javac", "Solution.java"],
        "run":      ["java", "-Xmx256m", "-Xms32m", "Solution"],
        "run_win":  ["java", "-Xmx256m", "-Xms32m", "Solution"],
    },
    "cpp": {
        "filename": "solution.cpp",
        "compile":  ["g++", "-O2", "-o", "sol", "solution.cpp", "-lm"],
        "run":      ["./sol"],
        "run_win":  ["sol.exe"],
    },
    "c": {
        "filename": "solution.c",
        "compile":  ["gcc", "-O2", "-o", "sol", "solution.c", "-lm"],
        "run":      ["./sol"],
        "run_win":  ["sol.exe"],
    },
    "go": {
        "filename": "solution.go",
        "compile":  None,
        "run":      ["go", "run", "solution.go"],
        "run_win":  ["go", "run", "solution.go"],
    },
    "rust": {
        "filename": "solution.rs",
        "compile":  ["rustc", "-o", "sol", "solution.rs"],
        "run":      ["./sol"],
        "run_win":  ["sol.exe"],
    },
}


def _check_lang_available(lang: str) -> tuple[bool, str]:
    """Check if the runtime for a language is installed."""
    cfg = LANGUAGE_CONFIG.get(lang)
    if not cfg:
        return False, f"Language '{lang}' is not supported."

    # Determine the binary to check
    run_cmd = cfg["run_win"] if _IS_WINDOWS else cfg["run"]
    compile_cmd = cfg.get("compile")

    binaries = []
    if compile_cmd:
        binaries.append(compile_cmd[0])
    binaries.append(run_cmd[0])

    for binary in binaries:
        if shutil.which(binary) is None:
            return False, f"Runtime '{binary}' not found on this server. Ask admin to install it."

    return True, ""


def run_in_sandbox(
    code: str,
    stdin_input: str,
    time_limit_ms: int,
    memory_limit_kb: int,
    language: str = "python3",
) -> dict:
    """
    Execute untrusted code against one test case input.

    Returns dict with: stdout, stderr, exit_code, runtime_ms,
                       timed_out, crashed, oom_killed
    """
    # Validate language
    cfg = LANGUAGE_CONFIG.get(language)
    if not cfg:
        return _error(f"Language '{language}' not supported. Supported: {', '.join(LANGUAGE_CONFIG.keys())}")

    # Check runtime available
    ok, reason = _check_lang_available(language)
    if not ok:
        return _error(reason)

    cpu_time_s   = min(time_limit_ms // 1000 + 2, MAX_CPU_TIME_S)
    wall_time_s  = min(cpu_time_s * 4, MAX_WALL_TIME_S)
    memory_bytes = min(memory_limit_kb * 1024, MAX_MEMORY_BYTES)

    sandbox_id  = str(uuid.uuid4())
    sandbox_dir = os.path.join(SANDBOX_TEMP_ROOT, sandbox_id)
    process     = None

    try:
        os.makedirs(sandbox_dir, exist_ok=False)

        # Write source file
        filename = cfg["filename"]
        src_path = os.path.join(sandbox_dir, filename)
        with open(src_path, "w", encoding="utf-8") as f:
            f.write(code)

        # ── Compile step (if needed) ─────────────────────────────────────────
        compile_cmd = cfg.get("compile")
        if compile_cmd:
            compile_result = subprocess.run(
                compile_cmd,
                cwd=sandbox_dir,
                capture_output=True,
                timeout=30,  # compile timeout
            )
            if compile_result.returncode != 0:
                err = compile_result.stderr.decode("utf-8", errors="replace")[:2048]
                return {
                    "stdout":     "",
                    "stderr":     err,
                    "exit_code":  compile_result.returncode,
                    "runtime_ms": 0,
                    "timed_out":  False,
                    "crashed":    True,
                    "oom_killed": False,
                    "compile_error": True,
                }

        # ── Run step ─────────────────────────────────────────────────────────
        run_cmd = cfg["run_win"] if _IS_WINDOWS else cfg["run"]

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

        process = subprocess.Popen(run_cmd, **popen_kwargs)

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
        sigkill   = (exit_code == -9)
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
        return _error(f"Sandbox error: {str(e)}")

    finally:
        if process and process.poll() is None:
            process.kill()
        shutil.rmtree(sandbox_dir, ignore_errors=True)


def _error(msg: str) -> dict:
    return {
        "stdout":     "",
        "stderr":     msg,
        "exit_code":  None,
        "runtime_ms": 0,
        "timed_out":  False,
        "crashed":    True,
        "oom_killed": False,
    }

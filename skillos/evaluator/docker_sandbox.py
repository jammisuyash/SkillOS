"""
evaluator/docker_sandbox.py

Docker-based code execution sandbox — production-grade isolation.
=================================================================

WHY DOCKER:
  Running user code directly (subprocess) is dangerous:
    - Fork bombs can crash the server
    - rm -rf / can destroy data
    - Infinite loops block threads
    - Network calls can exfiltrate data
    - Users can read other users' code from /tmp

  Docker containers give:
    - Full filesystem isolation (read-only host)
    - Network disabled (--network none)
    - CPU + memory hard limits (--memory, --cpus)
    - PID limits (--pids-limit)
    - No privilege escalation (--security-opt no-new-privileges)
    - Automatic cleanup (--rm)

DOCKER IMAGES USED (auto-pulled on first use):
  python3/python  → python:3.12-alpine
  javascript      → node:20-alpine
  java            → openjdk:21-alpine
  cpp/c           → gcc:13-alpine
  go              → golang:1.22-alpine
  rust            → rust:1.77-alpine

REQUIREMENTS:
  - Docker daemon running: sudo systemctl start docker
  - User in docker group:  sudo usermod -aG docker $USER

FALLBACK:
  If Docker is not available (e.g. dev laptop), automatically
  falls back to subprocess sandbox with resource limits.

CONFIGURATION:
  SKILLOS_USE_DOCKER=true      # Force Docker (default: auto-detect)
  SKILLOS_USE_DOCKER=false     # Force subprocess fallback
  DOCKER_MEMORY_LIMIT=256m     # Memory limit per container
  DOCKER_CPU_LIMIT=0.5         # CPU cores per container
  DOCKER_TIMEOUT_BUFFER=5      # Extra seconds beyond problem's time limit
"""

from __future__ import annotations
import os, sys, json, uuid, shutil, subprocess, tempfile, time
from skillos.shared.logger import get_logger

log = get_logger("docker_sandbox")

# ── Configuration ─────────────────────────────────────────────────────────────
_FORCE = os.environ.get("SKILLOS_USE_DOCKER", "auto").lower()
_MEM   = os.environ.get("DOCKER_MEMORY_LIMIT", "256m")
_CPU   = os.environ.get("DOCKER_CPU_LIMIT",    "0.5")
_BUF   = int(os.environ.get("DOCKER_TIMEOUT_BUFFER", "5"))
_MAX_OUTPUT = 64 * 1024  # 64KB

# ── Docker images per language ────────────────────────────────────────────────
_IMAGES = {
    "python3":    "python:3.12-alpine",
    "python":     "python:3.12-alpine",
    "javascript": "node:20-alpine",
    "java":       "openjdk:21-slim",
    "cpp":        "gcc:13",
    "c":          "gcc:13",
    "go":         "golang:1.22-alpine",
    "rust":       "rust:1.77-alpine",
}

# ── Run commands inside container ─────────────────────────────────────────────
_RUN_CMDS = {
    "python3":    "python3 -u /code/solution.py",
    "python":     "python3 -u /code/solution.py",
    "javascript": "node /code/solution.js",
    "java":       "sh -c 'cd /code && javac Solution.java && java -Xmx200m Solution'",
    "cpp":        "sh -c 'g++ -O2 -o /code/sol /code/solution.cpp -lm && /code/sol'",
    "c":          "sh -c 'gcc -O2 -o /code/sol /code/solution.c -lm && /code/sol'",
    "go":         "go run /code/solution.go",
    "rust":       "sh -c 'rustc -o /code/sol /code/solution.rs && /code/sol'",
}

_FILENAMES = {
    "python3": "solution.py", "python": "solution.py",
    "javascript": "solution.js", "java": "Solution.java",
    "cpp": "solution.cpp", "c": "solution.c",
    "go": "solution.go", "rust": "solution.rs",
}


def _docker_available() -> bool:
    """Check if Docker daemon is running and accessible."""
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# Detect Docker availability once at startup
if _FORCE == "true":
    USE_DOCKER = True
elif _FORCE == "false":
    USE_DOCKER = False
else:
    USE_DOCKER = _docker_available()

log.info("docker_sandbox.init", use_docker=USE_DOCKER, memory=_MEM, cpu=_CPU)


def run_in_sandbox(
    code:           str,
    stdin_input:    str,
    time_limit_ms:  int,
    memory_limit_kb: int,
    language:       str = "python3",
) -> dict:
    """
    Execute code safely. Uses Docker if available, subprocess fallback otherwise.
    Returns: {stdout, stderr, exit_code, runtime_ms, timed_out, crashed, oom_killed}
    """
    if USE_DOCKER:
        return _docker_run(code, stdin_input, time_limit_ms, memory_limit_kb, language)
    else:
        # Import subprocess sandbox as fallback
        from skillos.evaluator.sandbox import run_in_sandbox as subprocess_sandbox
        log.debug("docker_sandbox.using_subprocess_fallback")
        return subprocess_sandbox(code, stdin_input, time_limit_ms, memory_limit_kb, language)


def _docker_run(code: str, stdin_input: str, time_limit_ms: int,
                memory_limit_kb: int, language: str) -> dict:
    """Execute code inside an isolated Docker container."""
    lang = language.lower().strip()
    image    = _IMAGES.get(lang)
    run_cmd  = _RUN_CMDS.get(lang)
    filename = _FILENAMES.get(lang)

    if not image:
        return _err(f"Language '{lang}' not supported in Docker sandbox. "
                    f"Supported: {', '.join(_IMAGES.keys())}")

    sandbox_id  = str(uuid.uuid4())
    sandbox_dir = os.path.join(tempfile.gettempdir(), f"skillos_{sandbox_id}")
    wall_time_s = (time_limit_ms // 1000) + _BUF
    mem_limit   = f"{min(memory_limit_kb // 1024, 512)}m"

    try:
        os.makedirs(sandbox_dir, mode=0o700, exist_ok=False)

        # Write source file
        src_path = os.path.join(sandbox_dir, filename)
        with open(src_path, "w", encoding="utf-8") as f:
            f.write(code)

        # Build Docker run command
        docker_cmd = [
            "docker", "run",
            "--rm",                             # auto-remove container after exit
            "--network", "none",                # no internet access
            "--memory", mem_limit,              # memory limit (e.g. 256m)
            "--memory-swap", mem_limit,         # disable swap
            "--cpus", _CPU,                     # CPU limit (e.g. 0.5 cores)
            "--pids-limit", "50",               # max processes (prevents fork bombs)
            "--read-only",                      # read-only root filesystem
            "--tmpfs", "/tmp:size=16m",         # allow writes only to /tmp
            "--security-opt", "no-new-privileges:true",  # no privilege escalation
            "--cap-drop", "ALL",                # drop all Linux capabilities
            "-v", f"{sandbox_dir}:/code:ro",    # mount code as read-only
            "-i",                               # stdin
            image,
            "sh", "-c", run_cmd,
        ]

        start_time = time.perf_counter()
        timed_out  = False

        try:
            proc = subprocess.run(
                docker_cmd,
                input=stdin_input.encode("utf-8"),
                capture_output=True,
                timeout=wall_time_s,
            )
            runtime_ms = int((time.perf_counter() - start_time) * 1000)
        except subprocess.TimeoutExpired:
            runtime_ms = wall_time_s * 1000
            timed_out  = True
            # Container is auto-removed (--rm), but kill dangling by name
            proc = None

        if timed_out:
            return {
                "stdout": "", "stderr": "Time Limit Exceeded",
                "exit_code": None, "runtime_ms": runtime_ms,
                "timed_out": True, "crashed": False, "oom_killed": False,
            }

        stdout = proc.stdout[:_MAX_OUTPUT].decode("utf-8", errors="replace")
        stderr = proc.stderr[:_MAX_OUTPUT].decode("utf-8", errors="replace")
        exit_code = proc.returncode

        # Docker OOM killer sets exit code 137
        oom_killed = (exit_code == 137)

        return {
            "stdout":     stdout,
            "stderr":     stderr,
            "exit_code":  exit_code,
            "runtime_ms": runtime_ms,
            "timed_out":  False,
            "crashed":    exit_code not in (0, 1) and not oom_killed,
            "oom_killed": oom_killed,
        }

    except Exception as e:
        log.error("docker_sandbox.error", error=str(e), language=lang)
        return _err(f"Docker sandbox error: {e}")

    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


def _err(msg: str) -> dict:
    return {
        "stdout": "", "stderr": msg, "exit_code": None, "runtime_ms": 0,
        "timed_out": False, "crashed": True, "oom_killed": False,
    }


def pull_images() -> dict[str, bool]:
    """
    Pre-pull all Docker images to avoid cold-start delays.
    Call this during server startup.
    Returns {image: success} dict.
    """
    if not USE_DOCKER:
        return {}

    results = {}
    unique_images = list(set(_IMAGES.values()))
    log.info("docker_sandbox.pulling_images", count=len(unique_images))

    for image in unique_images:
        try:
            r = subprocess.run(
                ["docker", "pull", image],
                capture_output=True, timeout=120
            )
            results[image] = (r.returncode == 0)
            log.info("docker_sandbox.pulled", image=image, ok=results[image])
        except Exception as e:
            results[image] = False
            log.warning("docker_sandbox.pull_failed", image=image, error=str(e))

    return results


def get_sandbox_info() -> dict:
    """Status info for /admin/sandbox-status endpoint."""
    return {
        "mode":         "docker" if USE_DOCKER else "subprocess",
        "docker_available": _docker_available(),
        "forced":       _FORCE,
        "memory_limit": _MEM,
        "cpu_limit":    _CPU,
        "supported_languages": list(_IMAGES.keys()),
        "images":       _IMAGES,
    }

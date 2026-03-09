"""
skillos/evaluator/runner.py

Runs code against all test cases for a given language.
Supports: python3, javascript, java, cpp, c, go, rust
"""

# Use Docker sandbox if available, fall back to subprocess sandbox automatically
from skillos.evaluator.docker_sandbox import run_in_sandbox, get_sandbox_info
from skillos.evaluator.sandbox import LANGUAGE_CONFIG   # language metadata still from subprocess module
from skillos.evaluator.comparator import compare
from skillos.evaluator.limits import PERF_TIER_FAST, PERF_TIER_SLOW

SUPPORTED_LANGUAGES = list(LANGUAGE_CONFIG.keys())


def evaluate(code: str, language: str, test_cases: list, limits: dict) -> dict:
    """
    Run code against all test cases.

    Args:
        code:       Source code string
        language:   One of SUPPORTED_LANGUAGES
        test_cases: List of {input, expected_output, is_hidden, comparison_mode}
        limits:     {time_ms, memory_kb}

    Returns:
        {status, results, total_cases, passed_cases, max_runtime_ms, ...}
    """
    # Normalise language key
    lang = language.lower().strip()
    if lang not in LANGUAGE_CONFIG:
        return _terminal(
            "crash", [], 0, 0, 0, 0, None,
            "", f"Unsupported language: '{language}'. Supported: {', '.join(SUPPORTED_LANGUAGES)}"
        )

    results       = []
    passed_cases  = 0
    max_runtime   = 0
    max_memory    = 0
    stdout_sample = ""
    stderr_sample = ""
    final_status  = "accepted"
    compile_error = False

    for i, tc in enumerate(test_cases):
        raw = run_in_sandbox(
            code=code,
            stdin_input=tc.get("input", ""),
            time_limit_ms=limits.get("time_ms", 2000),
            memory_limit_kb=limits.get("memory_kb", 262144),
            language=lang,
        )

        max_runtime = max(max_runtime, raw["runtime_ms"])
        max_memory  = max(max_memory, raw.get("memory_kb", 0))

        # Detect compile error on first test case
        if raw.get("compile_error"):
            compile_error = True
            return _terminal(
                "compile_error", [], len(test_cases), 0, 0, 0, None,
                "", raw["stderr"]
            )

        if raw["crashed"]:
            tc_status    = "crash"
            final_status = "crash"
        elif raw["timed_out"]:
            tc_status = "timeout"
            if final_status not in ("crash",):
                final_status = "timeout"
        elif raw["exit_code"] != 0:
            tc_status = "runtime_error"
            if final_status not in ("crash", "timeout"):
                final_status = "runtime_error"
        else:
            passed = compare(
                raw["stdout"],
                tc.get("expected_output", ""),
                tc.get("comparison_mode", "exact"),
            )
            if passed:
                tc_status = "passed"
                passed_cases += 1
            else:
                tc_status = "wrong_answer"
                if final_status not in ("crash", "timeout", "runtime_error"):
                    final_status = "wrong_answer"

        if tc_status != "passed" and not stdout_sample:
            stdout_sample = "[hidden]" if tc.get("is_hidden") else raw["stdout"][:2048]
            stderr_sample = raw["stderr"][:2048]

        results.append({
            "passed":     tc_status == "passed",
            "status":     tc_status,
            "runtime_ms": raw["runtime_ms"],
            "is_hidden":  tc.get("is_hidden", False),
            "stdout":     None if tc.get("is_hidden") else raw["stdout"][:2048],
        })

        if raw["crashed"]:
            break  # sandbox failing — stop early

    if final_status == "accepted" and passed_cases < len(test_cases):
        final_status = "wrong_answer"

    performance_tier = None
    if final_status == "accepted" and limits.get("time_ms", 0) > 0:
        ratio = max_runtime / limits["time_ms"]
        performance_tier = (
            "fast"       if ratio < PERF_TIER_FAST else
            "acceptable" if ratio < PERF_TIER_SLOW else
            "slow"
        )

    return _terminal(
        final_status, results, len(test_cases), passed_cases,
        max_runtime, max_memory, performance_tier,
        stdout_sample, stderr_sample,
    )


def _terminal(status, results, total, passed, runtime, memory, perf, stdout, stderr):
    return {
        "status":           status,
        "results":          results,
        "total_cases":      total,
        "passed_cases":     passed,
        "max_runtime_ms":   runtime,
        "max_memory_kb":    memory,
        "performance_tier": perf,
        "stdout_sample":    stdout,
        "stderr_sample":    stderr,
    }

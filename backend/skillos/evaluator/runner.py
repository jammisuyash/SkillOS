from skillos.evaluator.sandbox import run_in_sandbox
from skillos.evaluator.comparator import compare
from skillos.evaluator.limits import PERF_TIER_FAST, PERF_TIER_SLOW


def evaluate(code: str, language: str, test_cases: list, limits: dict) -> dict:
    if language != "python":
        return _terminal("crash", [], 0, 0, 0, 0, None, "", "Unsupported language")

    results       = []
    passed_cases  = 0
    max_runtime   = 0
    max_memory    = 0
    stdout_sample = ""
    stderr_sample = ""
    final_status  = "accepted"

    for tc in test_cases:
        raw = run_in_sandbox(
            code=code,
            stdin_input=tc["input"],
            time_limit_ms=limits["time_ms"],
            memory_limit_kb=limits["memory_kb"],
        )

        max_runtime = max(max_runtime, raw["runtime_ms"])
        max_memory  = max(max_memory,  raw.get("memory_kb", 0))

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
                tc["expected_output"],
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
            break  # no value continuing — sandbox is failing

    # FIX 2: crash dominance — only downgrade to wrong_answer if still accepted.
    # Compare against len(results), not len(test_cases), to handle early break.
    # This prevents crash/timeout/runtime_error being overwritten by wrong_answer.
    if final_status == "accepted" and passed_cases < len(test_cases):
        final_status = "wrong_answer"

    performance_tier = None
    if final_status == "accepted" and limits["time_ms"] > 0:
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

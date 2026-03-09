"""
evaluator/multi_type.py — Evaluation for non-coding problem types.

Problem types handled here:
  - mcq:           Multiple choice. Compare answer index. Instant.
  - debugging:     User fixes broken code. Run fixed code against tests.
  - system_design: AI evaluates against a rubric. Needs ANTHROPIC_API_KEY.
  - fill_in_blank: User fills gaps in code. Run completed code.

coding problems go through sandbox.py as before — this file doesn't touch them.
"""
import os, json, urllib.request
from skillos.shared.exceptions import ValidationError

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


# ── MCQ ───────────────────────────────────────────────────────────────────────

def evaluate_mcq(task: dict, answer_index: int) -> dict:
    """
    Evaluate a multiple choice answer.
    Returns evaluation result matching the standard submission schema.
    """
    correct = task.get("mcq_correct_index")
    if correct is None:
        return _result("wrong_answer", 0, 1, "MCQ answer key not configured.", "")

    options = []
    if task.get("mcq_options"):
        try:
            options = json.loads(task["mcq_options"])
        except Exception:
            options = []

    if answer_index == correct:
        chosen = options[answer_index] if options and answer_index < len(options) else str(answer_index)
        return _result("accepted", 1, 1,
                       f"✓ Correct! Answer: {chosen}", "",
                       ai_feedback=f"Correct! Option {answer_index + 1} is right.",
                       ai_score=100)
    else:
        correct_text = options[correct] if options and correct < len(options) else str(correct)
        chosen_text  = options[answer_index] if options and answer_index < len(options) else str(answer_index)
        return _result("wrong_answer", 0, 1,
                       f"✗ Wrong. You chose: {chosen_text}",
                       f"Correct answer: {correct_text}",
                       ai_feedback=f"Incorrect. The right answer was option {correct + 1}: {correct_text}",
                       ai_score=0)


# ── System Design (AI Evaluation) ────────────────────────────────────────────

def evaluate_system_design(task: dict, user_answer: str) -> dict:
    """
    Use Claude to evaluate a system design answer against a rubric.
    Falls back to a simple length/keyword check if no API key.
    """
    if not user_answer or len(user_answer.strip()) < 50:
        return _result("wrong_answer", 0, 1,
                       "Answer too short. Please write at least a paragraph.", "",
                       ai_feedback="Your answer needs more detail. Aim for 200+ words.",
                       ai_score=0)

    if ANTHROPIC_API_KEY:
        return _ai_evaluate_system_design(task, user_answer)
    else:
        return _heuristic_system_design(task, user_answer)


def _ai_evaluate_system_design(task: dict, user_answer: str) -> dict:
    rubric = task.get("system_design_rubric") or task.get("ai_evaluation_prompt") or \
             "Evaluate the system design answer for correctness, completeness, scalability thinking, and trade-off awareness."

    prompt = f"""You are a senior software engineer evaluating a system design answer.

PROBLEM:
{task.get('title', 'System Design Problem')}

{task.get('description', '')}

EVALUATION RUBRIC:
{rubric}

CANDIDATE'S ANSWER:
{user_answer[:3000]}

Evaluate this answer and return JSON with exactly these fields:
{{
  "score": <integer 0-100>,
  "verdict": "accepted|partial|wrong_answer",
  "strengths": ["<what they got right>"],
  "gaps": ["<what is missing or wrong>"],
  "feedback": "<2-3 sentence overall feedback, constructive and specific>",
  "suggested_additions": "<one specific thing they should add to improve the answer>"
}}

Scoring guide:
- 0-40: Missing key concepts, wrong approach
- 41-70: Correct direction but missing important details
- 71-89: Good answer with minor gaps  
- 90-100: Comprehensive, demonstrates real understanding

Return ONLY JSON. No markdown."""

    try:
        body = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 800,
            "messages": [{"role": "user", "content": prompt}]
        }).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body, method="POST",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())

        raw = resp["content"][0]["text"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        result = json.loads(raw.strip())

        score    = result.get("score", 50)
        verdict  = result.get("verdict", "partial")
        feedback = result.get("feedback", "")
        gaps     = result.get("gaps", [])
        strengths= result.get("strengths", [])
        suggested= result.get("suggested_additions", "")

        if verdict == "accepted":
            status, passed, total = "accepted", 1, 1
        elif verdict == "partial":
            status, passed, total = "wrong_answer", 0, 1
        else:
            status, passed, total = "wrong_answer", 0, 1

        full_feedback = feedback
        if strengths:
            full_feedback += "\n\n✓ Strengths:\n" + "\n".join(f"• {s}" for s in strengths)
        if gaps:
            full_feedback += "\n\n✗ Missing:\n" + "\n".join(f"• {g}" for g in gaps)
        if suggested:
            full_feedback += f"\n\n💡 Tip: {suggested}"

        return _result(status, passed, total,
                       f"Score: {score}/100\n\n{full_feedback}", "",
                       ai_feedback=full_feedback, ai_score=score)

    except Exception as e:
        return _heuristic_system_design(task, user_answer)


def _heuristic_system_design(task: dict, user_answer: str) -> dict:
    """Fallback when no API key. Basic keyword scoring."""
    keywords = [
        "database", "cache", "load balancer", "api", "microservice",
        "scale", "cdn", "queue", "async", "replica", "sharding",
        "consistency", "availability", "partition", "latency", "throughput"
    ]
    answer_lower = user_answer.lower()
    found = [k for k in keywords if k in answer_lower]
    word_count = len(user_answer.split())

    score = min(100, len(found) * 6 + min(word_count // 10, 40))
    status = "accepted" if score >= 50 else "wrong_answer"

    feedback = (
        f"Your answer covers {len(found)} key system design concepts. "
        f"({'Great coverage!' if len(found) >= 8 else 'Consider adding more about: ' + ', '.join([k for k in keywords if k not in answer_lower][:4])})"
        f"\n\n💡 Add ANTHROPIC_API_KEY to get AI-powered detailed feedback."
    )
    return _result(status, 1 if status == "accepted" else 0, 1,
                   feedback, "", ai_feedback=feedback, ai_score=score)


# ── Debugging ─────────────────────────────────────────────────────────────────

def prepare_debugging_task(task: dict, user_code: str) -> str:
    """
    For debugging tasks, the user's code IS their fix.
    Just return it — it goes through the normal sandbox.
    The broken starter code is shown in the editor, user fixes it.
    """
    return user_code  # Goes to sandbox.py normally


# ── Helpers ───────────────────────────────────────────────────────────────────

def _result(status: str, passed: int, total: int,
            stdout: str, stderr: str,
            ai_feedback: str = None, ai_score: int = None) -> dict:
    return {
        "status":        status,
        "passed_cases":  passed,
        "total_cases":   total,
        "max_runtime_ms": 0,
        "max_memory_kb":  0,
        "performance_tier": "instant",
        "stdout_sample": stdout[:2000],
        "stderr_sample": stderr[:2000],
        "ai_feedback":   ai_feedback,
        "ai_score":      ai_score,
    }

"""
ai_review/service.py

Multi-Provider AI Code Review — Production Grade
================================================

Provider chain (fastest/cheapest first):
  1. Groq          -- ultra-fast (Llama 3.3 70B), generous free tier, ~50ms
  2. Google Gemini -- fast + large context, 1500 free req/day, ~200ms
  3. Anthropic      -- Claude Haiku, best code reasoning, ~400ms
  4. OpenAI         -- GPT-4o-mini, reliable fallback, ~500ms
  5. Rule-based     -- always works, zero cost, zero latency

Multi-key support: Set comma-separated keys in .env:
  ANTHROPIC_API_KEY=sk-ant-key1,sk-ant-key2,sk-ant-key3
  GROQ_API_KEY=gsk_key1,gsk_key2

CONFIGURATION (.env):
  ANTHROPIC_API_KEY=sk-ant-...
  GEMINI_API_KEY=AIza...
  GROQ_API_KEY=gsk_...
  OPENAI_API_KEY=sk-...

  # Optional overrides
  AI_PROVIDER_ORDER=groq,gemini,anthropic,openai
  AI_DISABLE_PROVIDERS=openai
"""

from __future__ import annotations
import os, json, re, time, urllib.request, urllib.error
from skillos.shared.logger import get_logger
from skillos.ai_review.multi_key_manager import key_manager

log = get_logger("ai_review")

# ── Provider order ─────────────────────────────────────────────────────────────
_DEFAULT_ORDER = ["groq", "gemini", "anthropic", "openai"]
_ORDER_ENV     = os.environ.get("AI_PROVIDER_ORDER", "")
_DISABLED      = set(x for x in os.environ.get("AI_DISABLE_PROVIDERS", "").lower().split(",") if x)

PROVIDER_ORDER: list[str] = (
    [p.strip() for p in _ORDER_ENV.split(",") if p.strip()]
    if _ORDER_ENV else _DEFAULT_ORDER
)
PROVIDER_ORDER = [p for p in PROVIDER_ORDER if p not in _DISABLED]

# ── Circuit Breaker (per-provider, not per-key -- key CB is in multi_key_manager) ─
_prov_failures:  dict[str, int]   = {}
_prov_last_fail: dict[str, float] = {}
_PROV_COOLDOWN_S, _PROV_MAX_FAILS = 120, 5

def _provider_healthy(p: str) -> bool:
    if _prov_failures.get(p, 0) < _PROV_MAX_FAILS:
        return True
    if time.time() - _prov_last_fail.get(p, 0) > _PROV_COOLDOWN_S:
        _prov_failures[p] = 0
        return True
    return False

def _prov_ok(p: str):   _prov_failures[p] = 0
def _prov_fail(p: str): _prov_failures[p] = _prov_failures.get(p, 0) + 1; _prov_last_fail[p] = time.time()


# ── Shared prompt ─────────────────────────────────────────────────────────────
def _prompt(code: str, language: str, problem_title: str) -> str:
    lang_name = {"python3":"Python 3","python":"Python 3","javascript":"JavaScript",
                 "java":"Java","cpp":"C++","c":"C","go":"Go","rust":"Rust"}.get(language, language)
    return f"""You are an expert competitive programming coach reviewing a student's solution.

Problem: {problem_title or "Unknown"}
Language: {lang_name}

Code:
```{language}
{code[:3000]}
```

Respond ONLY with valid JSON (no markdown fences, no text outside JSON):
{{
  "time_complexity": "O(??) with brief explanation",
  "space_complexity": "O(??) with brief explanation",
  "overall_score": <integer 1-10>,
  "summary": "2-3 sentence overall assessment",
  "strengths": ["strength1", "strength2"],
  "issues": [
    {{"severity": "high|medium|low", "description": "issue description", "line_hint": "relevant snippet"}}
  ],
  "improved_snippet": "optional 5-10 lines showing key improvement or null",
  "alternative_approach": "brief description of better algorithm if applicable or null",
  "tags": ["clean-code", "optimal", "edge-cases"]
}}"""


# ── Provider calls (now using multi_key_manager for key rotation) ─────────────
def _parse(text: str) -> dict:
    text = re.sub(r"^```[a-z]*\n?|```$", "", text, flags=re.MULTILINE).strip()
    return json.loads(text)

def _post(url: str, payload: dict, headers: dict, timeout=20) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def _is_rate_limit_error(e: Exception) -> bool:
    """Detect HTTP 429 rate limit responses."""
    return hasattr(e, "code") and e.code == 429


def _call_groq(code, language, title):
    key = key_manager.get_key("groq")
    if not key:
        raise ValueError("no key")
    try:
        d = _post("https://api.groq.com/openai/v1/chat/completions",
                  {"model": "llama-3.3-70b-versatile", "max_tokens": 800, "temperature": 0.1,
                   "messages": [{"role": "user", "content": _prompt(code, language, title)}]},
                  {"Authorization": f"Bearer {key}"}, timeout=15)
        key_manager.mark_success("groq", key)
        return {"review": _parse(d["choices"][0]["message"]["content"]), "source": "groq", "model": "llama-3.3-70b-versatile"}
    except Exception as e:
        key_manager.mark_failure("groq", key, rate_limited=_is_rate_limit_error(e))
        raise

def _call_gemini(code, language, title):
    key = key_manager.get_key("gemini")
    if not key:
        raise ValueError("no key")
    try:
        model = "gemini-2.0-flash"
        d = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                  {"contents": [{"parts": [{"text": _prompt(code, language, title)}]}],
                   "generationConfig": {"maxOutputTokens": 800, "temperature": 0.1}}, {}, timeout=20)
        key_manager.mark_success("gemini", key)
        return {"review": _parse(d["candidates"][0]["content"]["parts"][0]["text"]), "source": "gemini", "model": model}
    except Exception as e:
        key_manager.mark_failure("gemini", key, rate_limited=_is_rate_limit_error(e))
        raise

def _call_anthropic(code, language, title):
    key = key_manager.get_key("anthropic")
    if not key:
        raise ValueError("no key")
    try:
        d = _post("https://api.anthropic.com/v1/messages",
                  {"model": "claude-haiku-4-5-20251001", "max_tokens": 800,
                   "messages": [{"role": "user", "content": _prompt(code, language, title)}]},
                  {"x-api-key": key, "anthropic-version": "2023-06-01"})
        key_manager.mark_success("anthropic", key)
        return {"review": _parse(d["content"][0]["text"]), "source": "anthropic", "model": "claude-haiku-4-5"}
    except Exception as e:
        key_manager.mark_failure("anthropic", key, rate_limited=_is_rate_limit_error(e))
        raise

def _call_openai(code, language, title):
    key = key_manager.get_key("openai")
    if not key:
        raise ValueError("no key")
    try:
        d = _post("https://api.openai.com/v1/chat/completions",
                  {"model": "gpt-4o-mini", "max_tokens": 800, "temperature": 0.1,
                   "messages": [{"role": "user", "content": _prompt(code, language, title)}]},
                  {"Authorization": f"Bearer {key}"})
        key_manager.mark_success("openai", key)
        return {"review": _parse(d["choices"][0]["message"]["content"]), "source": "openai", "model": "gpt-4o-mini"}
    except Exception as e:
        key_manager.mark_failure("openai", key, rate_limited=_is_rate_limit_error(e))
        raise

_FNS = {"groq": _call_groq, "gemini": _call_gemini, "anthropic": _call_anthropic, "openai": _call_openai}


# ── Public API ────────────────────────────────────────────────────────────────
def review_code(user_id: str, code: str, language: str = "python3",
                problem_title: str = "", submission_id: str = None) -> dict:
    """
    AI code review with automatic multi-provider + multi-key fallback.
    Tries: Groq -> Gemini -> Anthropic -> OpenAI -> rule-based
    Each provider has N keys that rotate round-robin; failed/rate-limited
    keys are skipped automatically until their cooldown expires.
    """
    if not code.strip():
        return {"error": "No code to review"}

    tried: list[str] = []
    for provider in PROVIDER_ORDER:
        if not _provider_healthy(provider):
            continue
        if not key_manager.is_configured(provider):
            continue
        if not key_manager.has_healthy_key(provider):
            log.warning("ai_review.all_keys_suspended", provider=provider)
            continue
        fn = _FNS.get(provider)
        if not fn:
            continue
        tried.append(provider)
        try:
            result = fn(code, language, problem_title)
            _prov_ok(provider)
            if len(tried) > 1:
                result["providers_tried"] = tried
                result["fallback_used"]   = True
            log.info("ai_review.success", provider=provider, user=user_id)
            return result
        except ValueError:
            tried.pop()   # unconfigured key -- don't count as failure
            continue
        except Exception as e:
            _prov_fail(provider)
            log.warning("ai_review.failed", provider=provider, error=str(e))

    # All failed -> rule-based (always works)
    log.info("ai_review.heuristic_fallback", tried=tried)
    result = _rule_based_review(code, language)
    result["providers_tried"] = tried
    return result


def get_provider_status() -> dict:
    """Health status for /admin/ai-status endpoint."""
    summary = key_manager.get_provider_summary()
    detail  = key_manager.get_status()
    return {
        p: {
            "configured":        summary[p]["configured"],
            "healthy":           summary[p]["healthy"],
            "key_count":         summary[p]["key_count"],
            "healthy_key_count": summary[p]["healthy_key_count"],
            "in_order":          p in PROVIDER_ORDER,
            "provider_healthy":  _provider_healthy(p),
            "keys":              detail[p]["keys"],
        }
        for p in ["groq", "gemini", "anthropic", "openai"]
    }


# ── Rule-based fallback (zero cost, always available) ─────────────────────────
def _rule_based_review(code: str, language: str) -> dict:
    lines = code.strip().splitlines()
    n = len(lines)
    issues, strengths, score = [], [], 7

    nested = sum(1 for i, l in enumerate(lines)
                 if any(k in l for k in ["for ", "while "]) and
                    any(k in lines[j] for j in range(max(0, i-5), i) for k in ["for ", "while "]))
    tc = "O(n^2)" if nested > 0 else "O(n)"
    if nested > 1:
        tc = "O(n^3)+"; score -= 2
        issues.append({"severity": "high",
                        "description": f"{nested} nested loops detected -- consider hash map to reduce complexity",
                        "line_hint": ""})
    if len(re.findall(r'\b[a-df-hj-z]\b', code)) > 5:
        score -= 1
        issues.append({"severity": "low", "description": "Many single-char variable names", "line_hint": ""})
    if n > 50:
        score -= 1
        issues.append({"severity": "medium", "description": f"Function is {n} lines -- split into helpers", "line_hint": ""})
    has_comments = any(l.strip().startswith(("#", "//", "/*", "*")) for l in lines)
    if not has_comments and n > 10:
        issues.append({"severity": "low", "description": "No comments -- explain your approach", "line_hint": ""})
    else:
        strengths.append("Code is well-commented")
    if any(k in code for k in ["dict(", "{}", "HashMap", "unordered_map", "new Map"]):
        strengths.append("Good use of hash map for O(1) lookups"); score = min(10, score + 1)
    if not issues:
        strengths.append("No major issues detected"); score = min(10, score + 1)
    sc = "O(n)" if any(k in code for k in ["dict(", "[]", "set(", "HashMap"]) else "O(1)"
    return {
        "review": {
            "time_complexity": tc, "space_complexity": sc,
            "overall_score": max(1, min(10, score)),
            "summary": ("Clean, efficient solution." if score >= 8 else "Solid solution with room for improvement.") + f" {n} lines.",
            "strengths": strengths, "issues": issues,
            "improved_snippet": None,
            "alternative_approach": "Consider hash map approach to reduce O(n^2) to O(n).",
            "tags": (["optimal"] if nested == 0 else []) + (["readable"] if has_comments else []),
        },
        "source": "heuristic", "model": "rule-based",
    }

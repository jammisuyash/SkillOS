"""
coaching/service.py — AI Skill Coach powered by Claude API.

HOW IT WORKS:
  1. Gathers user's real performance data from DB (scores, submissions, streaks)
  2. Sends it to Claude API as structured context
  3. Claude returns personalised analysis, weaknesses, action plan
  4. Falls back to rule-based analysis if no API key set

SETUP (free tier available):
  Set env var: ANTHROPIC_API_KEY=sk-ant-...
  Get key at: https://console.anthropic.com (free $5 credits to start)

COST: ~$0.001 per coaching report (very cheap)
"""

import os, json, urllib.request, urllib.error
from skillos.db.database import fetchone, fetchall
from skillos.shared.utils import utcnow_iso

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
_USE_AI = bool(ANTHROPIC_API_KEY)


# ── Main entry point ─────────────────────────────────────────────────────────

def get_coaching_report(user_id: str) -> dict:
    """Full AI-powered coaching report. Falls back to rule-based if no key."""
    data = _gather_user_data(user_id)

    if _USE_AI:
        try:
            return _ai_coaching_report(data)
        except Exception as e:
            # Never crash — fall back to rule-based
            pass

    return _rule_based_report(data)


# ── Data gathering ────────────────────────────────────────────────────────────

def _gather_user_data(user_id: str) -> dict:
    """Pull all performance data needed for coaching analysis."""

    # Skill scores
    skills = fetchall("""
        SELECT s.id, s.name, s.domain,
               uss.current_score, uss.tasks_attempted, uss.tasks_passed,
               uss.last_updated_at
        FROM user_skill_scores uss JOIN skills s ON s.id = uss.skill_id
        WHERE uss.user_id = ?
        ORDER BY uss.current_score DESC
    """, (user_id,))

    # All skills (to find untouched ones)
    all_skills = fetchall("SELECT id, name, domain FROM skills WHERE is_active=1", ())
    attempted_ids = {s["id"] for s in skills}
    untouched = [s for s in all_skills if s["id"] not in attempted_ids]

    # Recent submissions (last 30)
    recent_subs = fetchall("""
        SELECT t.title, t.difficulty, s.name AS skill_name,
               sub.status, sub.max_runtime_ms, sub.submitted_at
        FROM submissions sub
        JOIN tasks t ON t.id = sub.task_id
        JOIN skills s ON s.id = t.skill_id
        WHERE sub.user_id = ?
        ORDER BY sub.submitted_at DESC LIMIT 30
    """, (user_id,))

    # Contest performance
    contests = []

    # Streak / profile
    profile = fetchone("""
        SELECT streak_current, streak_best, 0 AS total_problems_solved
        FROM users WHERE id = ?
    """, (user_id,))

    # Compute per-skill stats
    skill_stats = []
    for s in skills:
        attempted = s["tasks_attempted"] or 0
        passed    = s["tasks_passed"]    or 0
        skill_stats.append({
            "name":          s["name"],
            "domain":        s["domain"],
            "score":         round(s["current_score"] or 0, 1),
            "attempted":     attempted,
            "passed":        passed,
            "success_rate":  round(passed / attempted * 100) if attempted else 0,
        })

    return {
        "skill_stats":    skill_stats,
        "untouched":      [s["name"] for s in untouched[:5]],
        "recent_subs":    [dict(r) for r in recent_subs],
        "contests":       [dict(c) for c in contests],
        "streak":         dict(profile) if profile else {},
        "total_skills_attempted": len(skills),
    }


def _table_exists(table: str) -> bool:
    from skillos.db.database import get_db
    r = get_db().execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return bool(r)


# ── AI-powered report ─────────────────────────────────────────────────────────

def _ai_coaching_report(data: dict) -> dict:
    """Call Claude API to generate personalised coaching report."""

    # Build a rich context summary for the AI
    skill_summary = ""
    if data["skill_stats"]:
        skill_summary = "\n".join(
            f"  - {s['name']} ({s['domain']}): {s['score']}/100, "
            f"{s['attempted']} attempted, {s['success_rate']}% success rate"
            for s in data["skill_stats"]
        )
    else:
        skill_summary = "  - No skills attempted yet"

    recent_summary = ""
    if data["recent_subs"]:
        from collections import Counter
        statuses = Counter(s["status"] for s in data["recent_subs"])
        skills_hit = Counter(s["skill_name"] for s in data["recent_subs"])
        recent_summary = (
            f"Last {len(data['recent_subs'])} submissions: "
            f"{statuses.get('accepted',0)} accepted, "
            f"{statuses.get('wrong_answer',0)} wrong answers, "
            f"{statuses.get('runtime_error',0)} runtime errors. "
            f"Most practiced: {skills_hit.most_common(1)[0][0] if skills_hit else 'none'}."
        )

    streak_info = ""
    if data.get("streak"):
        s = data["streak"]
        streak_info = (
            f"Current streak: {s.get('streak_current', 0)} days. "
            f"Longest streak: {s.get('streak_best', 0)} days. "
            f"Total problems solved: {s.get('total_problems_solved', 0)}."
        )

    contest_info = ""
    if data.get("contests"):
        c = data["contests"][0]
        contest_info = f"Latest contest: rank #{c.get('rank','?')}, solved {c.get('problems_solved',0)} problems."

    prompt = f"""You are a world-class software engineering skills coach on SkillOS — a platform where developers prove their skills through real coding challenges.

Your job: give this developer a deeply personalised, actionable, honest coaching report based on their real performance data.

═══════════ DEVELOPER PERFORMANCE DATA ═══════════

SKILL SCORES:
{skill_summary}

RECENT ACTIVITY:
{recent_summary or "No recent submissions."}

CONSISTENCY:
{streak_info or "No streak data yet."}

CONTEST PERFORMANCE:
{contest_info or "No contest participation yet."}

UNEXPLORED SKILLS: {', '.join(data['untouched'][:5]) if data['untouched'] else 'None — great coverage!'}

═══════════ YOUR TASK ═══════════

Analyse this data deeply. Look for:
- Skill gaps (low scores, high attempt rates but low success)
- Consistency patterns (are they practicing regularly?)
- Breadth vs depth (are they avoiding certain domains?)
- Contest readiness (are they ready for competitive programming?)
- Career trajectory (what role are they heading towards?)

Return a JSON object with EXACTLY these fields (no extra fields, no missing fields):
{{
  "overall_level": "beginner|intermediate|advanced|expert",
  "overall_score": <integer 0-100, weighted average of skill scores>,
  "summary": "<3-4 sentences. Be specific: mention actual skills, scores, patterns. NOT generic praise.>",
  "strengths": [
    {{
      "skill_name": "<exact skill name from data>",
      "score": <their actual score>,
      "insight": "<1-2 sentences: WHY they're strong here, what this tells you about them as a developer>"
    }}
  ],
  "weaknesses": [
    {{
      "skill_name": "<exact skill name>",
      "score": <their actual score or 0 if untouched>,
      "reason": "<specific: is it low score? Low attempt rate? High failure rate? Be precise.>",
      "priority": "high|medium"
    }}
  ],
  "insights": [
    "<Each insight should be a sharp observation about their learning patterns, habits, or tendencies. Be specific, not generic. E.g.: 'You attempt hard problems before mastering medium ones — this is causing your 34% success rate on Algorithms.'>"
  ],
  "recommendations": [
    {{
      "title": "<specific, actionable title>",
      "description": "<concrete steps: exactly what to do, what problems to solve, what concept to study>",
      "skill": "<exact skill name>",
      "priority": "high|medium|low",
      "estimated_time": "<realistic estimate, e.g. '30 min/day for 2 weeks'>"
    }}
  ],
  "weekly_plan": {{
    "monday": "<specific task with skill name and difficulty level>",
    "tuesday": "<specific task>",
    "wednesday": "<specific task>",
    "thursday": "<specific task>",
    "friday": "<specific task>",
    "saturday": "<specific task — slightly harder or contest practice>",
    "sunday": "<review + reflection task>"
  }},
  "career_path": "<Based on their skill profile, what role are they best suited for right now? E.g. Backend Engineer, Data Engineer, Full-Stack Dev, etc. Be honest.>",
  "motivational_message": "<1-2 sentences. Personalised to their specific situation — reference their actual data. Not generic. Make it real.>"
}}

RULES:
- Reference actual skill names and scores from the data
- If they have no data yet, give beginner-friendly advice
- Be honest about weaknesses — sugar-coating helps no one
- Weekly plan must have all 7 days
- Return ONLY the JSON — no markdown fences, no explanation, no preamble"""

    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 2500,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        method="POST",
        headers={
            "x-api-key":         ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        }
    )

    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read())

    raw = resp["content"][0]["text"].strip()
    # Strip markdown fences if model added them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    report = json.loads(raw.strip())
    report["ai_powered"] = True
    return report


# ── Rule-based fallback ───────────────────────────────────────────────────────

def _rule_based_report(data: dict) -> dict:
    """Deterministic coaching report — no AI needed."""
    stats = data["skill_stats"]

    strong   = [s for s in stats if s["score"] >= 75]
    moderate = [s for s in stats if 40 <= s["score"] < 75]
    weak     = [s for s in stats if s["score"] < 40]

    # Overall level
    if not stats:
        level, overall = "beginner", 0
    else:
        avg = sum(s["score"] for s in stats) / len(stats)
        overall = round(avg)
        if avg >= 80:   level = "expert"
        elif avg >= 60: level = "advanced"
        elif avg >= 35: level = "intermediate"
        else:           level = "beginner"

    insights = []
    if not stats:
        insights.append("Solve your first problem to unlock performance insights.")
    else:
        if data["recent_subs"]:
            last = data["recent_subs"][0]["skill_name"]
            insights.append(f"You've been focused on {last} recently — great consistency.")
        if strong:
            insights.append(f"Strong in {strong[0]['name']} ({strong[0]['score']}/100) — highlight this on your profile.")
        if weak:
            insights.append(f"{weak[0]['name']} needs attention ({weak[0]['score']}/100) — targeted practice will help fast.")
        streak = data.get("streak", {})
        if streak.get("streak_current", 0) >= 3:
            insights.append(f"You're on a {streak['streak_current']}-day streak — keep it up!")

    weaknesses = [{"skill_name": s["name"], "score": s["score"],
                   "reason": "low_score", "priority": "high"} for s in weak[:3]]
    strengths  = [{"skill_name": s["name"], "score": s["score"],
                   "insight": "Consistently solving hard problems"} for s in strong[:3]]

    recommendations = []
    for s in weak[:2]:
        recommendations.append({
            "title":          f"Focus on {s['name']}",
            "description":    f"Your score is {s['score']}/100. Attempt 3 easy {s['name']} problems this week.",
            "skill":          s["name"],
            "priority":       "high",
            "estimated_time": "3 hours/week",
        })
    for name in data["untouched"][:2]:
        recommendations.append({
            "title":          f"Explore {name}",
            "description":    f"You haven't tried {name} yet. Start with 1 easy problem to get a baseline score.",
            "skill":          name,
            "priority":       "low",
            "estimated_time": "1 hour",
        })

    summary = (
        f"You have {data['total_skills_attempted']} active skill(s). "
        f"Your strongest area is {strong[0]['name']} ({strong[0]['score']}/100). " if strong else
        "Start solving problems to build your skill profile. "
    )
    if weak:
        summary += f"Focus on {weak[0]['name']} for the biggest improvement."

    return {
        "overall_level":    level,
        "overall_score":    overall,
        "summary":          summary,
        "strengths":        strengths,
        "weaknesses":       weaknesses,
        "insights":         insights,
        "recommendations":  recommendations,
        "weekly_plan":      {
            "monday":    f"Attempt 1 {weak[0]['name'] if weak else 'algorithm'} problem (easy)",
            "tuesday":   "Read solutions to yesterday's problem — understand the pattern",
            "wednesday": "Attempt 1 medium difficulty problem",
            "thursday":  "Review weak areas — re-read theory if needed",
            "friday":    "Try a medium or hard problem",
            "saturday":  "Participate in a mini contest or timed challenge",
            "sunday":    "Review the week: what clicked, what didn't? Write it down.",
        },
        "career_path": _infer_career_path(stats),
        "motivational_message": "Every expert was once a beginner. Keep coding!",
        "ai_powered": False,
    }


def _infer_career_path(stats: list) -> str:
    """Infer likely career path from skill scores."""
    if not stats:
        return "Software Engineer (general)"
    domain_scores = {}
    for s in stats:
        d = s.get("domain", "general")
        domain_scores[d] = max(domain_scores.get(d, 0), s["score"])
    top = sorted(domain_scores.items(), key=lambda x: -x[1])
    if not top:
        return "Software Engineer (general)"
    top_domain = top[0][0].lower()
    if "data" in top_domain:
        return "Data Engineer / ML Engineer"
    elif "security" in top_domain or "cyber" in top_domain:
        return "Security Engineer"
    elif "web" in top_domain:
        return "Full-Stack Web Developer"
    elif "algorithm" in top_domain or "software" in top_domain:
        return "Backend / Systems Engineer"
    return "Software Engineer (general)"


# ── Daily challenge ───────────────────────────────────────────────────────────

def get_daily_challenge() -> dict | None:
    from datetime import date
    today = date.today().isoformat()
    row = fetchone("""
        SELECT dc.task_id, t.title, t.difficulty, t.description, s.name AS skill_name
        FROM daily_challenges dc JOIN tasks t ON t.id=dc.task_id
        JOIN skills s ON s.id=t.skill_id
        WHERE dc.date=?
    """, (today,))
    return dict(row) if row else None


def seed_daily_challenge():
    from datetime import date
    import uuid
    today = date.today().isoformat()
    exists = fetchone("SELECT id FROM daily_challenges WHERE date=?", (today,))
    if exists: return
    task = fetchone("""
        SELECT id FROM tasks WHERE is_published=1
        AND id NOT IN (SELECT task_id FROM daily_challenges)
        ORDER BY RANDOM() LIMIT 1
    """, ())
    if not task:
        task = fetchone("SELECT id FROM tasks WHERE is_published=1 ORDER BY RANDOM() LIMIT 1", ())
    if not task: return
    from skillos.db.database import transaction
    with transaction() as db:
        db.execute("INSERT OR IGNORE INTO daily_challenges (id,task_id,date) VALUES (?,?,?)",
                   (str(uuid.uuid4()), task["id"], today))


def analyse_performance(user_id: str) -> dict:
    """Legacy alias — used by some older endpoints."""
    return get_coaching_report(user_id)

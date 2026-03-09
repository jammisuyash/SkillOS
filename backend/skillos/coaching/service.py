"""coaching/service.py — AI Skill Coach: weakness detection, recommendations, performance analysis."""
from skillos.db.database import fetchone, fetchall
from skillos.shared.utils import utcnow_iso

def analyse_performance(user_id: str) -> dict:
    """Full performance analysis + personalised recommendations."""
    skills = fetchall("""
        SELECT s.id, s.name, uss.current_score, uss.tasks_attempted, uss.tasks_passed,
               uss.last_updated_at
        FROM user_skill_scores uss JOIN skills s ON s.id=uss.skill_id
        WHERE uss.user_id=? ORDER BY uss.current_score ASC
    """, (user_id,))

    all_skills = fetchall("SELECT id, name FROM skills", ())
    attempted_ids = {s["id"] for s in skills}
    untouched = [s for s in all_skills if s["id"] not in attempted_ids]

    # Categorise skills
    strong   = [s for s in skills if s["current_score"] >= 75]
    moderate = [s for s in skills if 40 <= s["current_score"] < 75]
    weak     = [s for s in skills if s["current_score"] < 40]

    # Success rate per skill
    for s in skills:
        s = dict(s)
        s["success_rate"] = round(s["tasks_passed"] / s["tasks_attempted"] * 100) if s["tasks_attempted"] else 0

    # Recent activity
    recent = fetchall("""
        SELECT t.skill_id, s.name AS skill_name, sub.status, sub.submitted_at
        FROM submissions sub JOIN tasks t ON t.id=sub.task_id
        JOIN skills s ON s.id=t.skill_id
        WHERE sub.user_id=? ORDER BY sub.submitted_at DESC LIMIT 20
    """, (user_id,))

    recommendations = _build_recommendations(weak, moderate, untouched)
    insights        = _build_insights(skills, recent)
    next_steps      = _build_next_steps(user_id, weak, untouched)

    return {
        "summary": {
            "total_skills_active": len(skills),
            "strong_skills":  [{"name":s["name"],"score":s["current_score"]} for s in strong],
            "weak_skills":    [{"name":s["name"],"score":s["current_score"]} for s in weak],
            "untouched_skills": [{"name":s["name"]} for s in untouched],
        },
        "insights":        insights,
        "recommendations": recommendations,
        "next_steps":      next_steps,
    }

def _build_recommendations(weak, moderate, untouched) -> list:
    recs = []
    for s in weak[:2]:
        recs.append({
            "type":    "improve_weakness",
            "skill":   s["name"],
            "message": f"Your {s['name']} score is {s['current_score']:.0f}/100. Focus here for the biggest gains.",
            "priority": "high",
        })
    for s in moderate[:1]:
        recs.append({
            "type":    "consolidate",
            "skill":   s["name"],
            "message": f"You're making good progress in {s['name']} ({s['current_score']:.0f}/100). A few more problems will push you to strong.",
            "priority": "medium",
        })
    for s in untouched[:2]:
        recs.append({
            "type":    "explore_new",
            "skill":   s["name"],
            "message": f"You haven't tried {s['name']} yet. Expanding your skill set boosts your overall score and recruiter visibility.",
            "priority": "low",
        })
    return recs

def _build_insights(skills, recent) -> list:
    insights = []
    if not skills:
        insights.append({"type":"no_data","message":"Solve your first problem to unlock performance insights."})
        return insights

    # Streak in recent submissions
    if recent:
        last_skill = recent[0]["skill_name"]
        insights.append({"type":"recent_focus","message":f"You've been focused on {last_skill} recently."})

    # Best skill callout
    best = max(skills, key=lambda s: s["current_score"])
    if best["current_score"] >= 80:
        insights.append({"type":"strength","message":f"You're in the top tier for {best['name']} — highlight this on your profile."})

    return insights

def _build_next_steps(user_id: str, weak, untouched) -> list:
    """Return specific tasks to attempt next."""
    target_skill = weak[0]["id"] if weak else (untouched[0]["id"] if untouched else None)
    if not target_skill: return []

    # Find unsolved tasks for this skill
    solved = fetchall("""
        SELECT DISTINCT task_id FROM submissions WHERE user_id=? AND status='accepted'
    """, (user_id,))
    solved_ids = {r["task_id"] for r in solved}

    tasks = fetchall("""
        SELECT t.id, t.title, t.difficulty, s.name AS skill_name
        FROM tasks t JOIN skills s ON s.id=t.skill_id
        WHERE t.skill_id=? AND t.is_published=1
        ORDER BY CASE t.difficulty WHEN 'easy' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END
        LIMIT 5
    """, (target_skill,))

    return [{"task_id": t["id"], "title": t["title"], "difficulty": t["difficulty"],
             "skill": t["skill_name"], "completed": t["id"] in solved_ids}
            for t in tasks]

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
    """Auto-pick a daily challenge. Idempotent."""
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
    if not task: task = fetchone("SELECT id FROM tasks WHERE is_published=1 ORDER BY RANDOM() LIMIT 1", ())
    if not task: return
    from skillos.db.database import transaction
    with transaction() as db:
        db.execute("INSERT OR IGNORE INTO daily_challenges (id,task_id,date) VALUES (?,?,?)",
                   (str(uuid.uuid4()), task["id"], today))

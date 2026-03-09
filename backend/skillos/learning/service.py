"""learning/service.py — Learning paths, roadmaps, progress tracking."""
import uuid
from skillos.db.database import fetchone, fetchall, transaction
from skillos.shared.exceptions import ValidationError
from skillos.shared.utils import utcnow_iso

def list_paths(domain=None) -> list:
    if domain:
        paths = fetchall("SELECT * FROM learning_paths WHERE is_active=1 AND domain=? ORDER BY ordinal", (domain,))
    else:
        paths = fetchall("SELECT * FROM learning_paths WHERE is_active=1 ORDER BY domain, ordinal")
    result = []
    for p in paths:
        d = dict(p)
        d["step_count"] = fetchone("SELECT COUNT(*) AS c FROM path_steps WHERE path_id=?", (p["id"],))["c"]
        result.append(d)
    return result

def get_path(path_id: str) -> dict | None:
    p = fetchone("SELECT * FROM learning_paths WHERE id=?", (path_id,))
    if not p: return None
    steps = fetchall("""
        SELECT ps.*, t.title AS task_title, t.difficulty, s.name AS skill_name
        FROM path_steps ps
        LEFT JOIN tasks t ON t.id=ps.task_id
        LEFT JOIN skills s ON s.id=ps.skill_id
        WHERE ps.path_id=? ORDER BY ps.ordinal
    """, (path_id,))
    return {**dict(p), "steps": [dict(s) for s in steps]}

def get_user_progress(user_id: str, path_id: str) -> dict:
    path  = get_path(path_id)
    if not path: raise ValidationError("Path not found")
    done  = fetchall("""
        SELECT step_id FROM user_path_progress WHERE user_id=? AND path_id=?
    """, (user_id, path_id))
    completed_ids = {r["step_id"] for r in done}
    total    = len(path["steps"])
    complete = sum(1 for s in path["steps"] if s["id"] in completed_ids)
    steps    = [{**s, "completed": s["id"] in completed_ids} for s in path["steps"]]
    return {
        "path_id": path_id,
        "title":   path["title"],
        "steps":   steps,
        "progress_pct": round(complete/total*100) if total else 0,
        "completed": complete,
        "total":   total,
    }

def complete_step(user_id: str, path_id: str, step_id: str):
    step = fetchone("SELECT * FROM path_steps WHERE id=? AND path_id=?", (step_id, path_id))
    if not step: raise ValidationError("Step not found in this path")
    existing = fetchone("SELECT id FROM user_path_progress WHERE user_id=? AND path_id=? AND step_id=?",
                        (user_id, path_id, step_id))
    if existing: return  # Already done — idempotent
    with transaction() as db:
        db.execute("INSERT INTO user_path_progress (id,user_id,path_id,step_id) VALUES (?,?,?,?)",
                   (str(uuid.uuid4()), user_id, path_id, step_id))
    # Award reputation
    try:
        from skillos.reputation.service import award_reputation
        award_reputation(user_id, "path_step_complete", 5, step_id, "path_step")
    except Exception:
        pass

def seed_learning_paths():
    """Seed default learning paths. Idempotent."""
    existing = fetchone("SELECT id FROM learning_paths LIMIT 1")
    if existing: return

    paths = [
        {
            "id":   "path-backend-001",
            "title": "Backend Developer Path",
            "description": "Go from Python basics to building production APIs",
            "domain": "software", "difficulty": "beginner", "ordinal": 1,
            "steps": [
                {"title":"Python Fundamentals","task_id":"task-double-001","skill_id":"skill-python-001","step_type":"problem","ordinal":1},
                {"title":"FizzBuzz","task_id":"task-fizzbuzz-003","skill_id":"skill-python-001","step_type":"problem","ordinal":2},
                {"title":"Two Sum","task_id":"task-twosum-002","skill_id":"skill-python-001","step_type":"problem","ordinal":3},
                {"title":"Arrays — Maximum Subarray","task_id":"task-maxsub-004","skill_id":"skill-arrays-001","step_type":"problem","ordinal":4},
                {"title":"Binary Search","task_id":"task-bsearch-006","skill_id":"skill-sorting-001","step_type":"problem","ordinal":5},
                {"title":"Hash Maps — Contains Duplicate","task_id":"task-dupcheck-008","skill_id":"skill-hashmaps-001","step_type":"problem","ordinal":6},
            ],
        },
        {
            "id":   "path-algorithms-001",
            "title": "Algorithms & Data Structures",
            "description": "Core CS fundamentals for technical interviews",
            "domain": "software", "difficulty": "intermediate", "ordinal": 2,
            "steps": [
                {"title":"Binary Search","task_id":"task-bsearch-006","skill_id":"skill-sorting-001","step_type":"problem","ordinal":1},
                {"title":"Kth Largest Element","task_id":"task-kthlargest-007","skill_id":"skill-sorting-001","step_type":"problem","ordinal":2},
                {"title":"Climbing Stairs (DP intro)","task_id":"task-climb-009","skill_id":"skill-recursion-001","step_type":"problem","ordinal":3},
                {"title":"Tree Height","task_id":"task-treeh-011","skill_id":"skill-graphs-001","step_type":"problem","ordinal":4},
                {"title":"BFS Shortest Path","task_id":"task-bfs-010","skill_id":"skill-graphs-001","step_type":"problem","ordinal":5},
                {"title":"Number of Islands (Hard)","task_id":"task-numislands-012","skill_id":"skill-graphs-001","step_type":"problem","ordinal":6},
            ],
        },
    ]

    with transaction() as db:
        for p in paths:
            steps = p.pop("steps")
            db.execute("""INSERT OR IGNORE INTO learning_paths
                (id,title,description,domain,difficulty,ordinal,is_active) VALUES (?,?,?,?,?,?,1)
            """, (p["id"],p["title"],p["description"],p["domain"],p["difficulty"],p["ordinal"]))
            for s in steps:
                db.execute("""INSERT OR IGNORE INTO path_steps
                    (id,path_id,title,task_id,skill_id,step_type,ordinal,is_required)
                    VALUES (?,?,?,?,?,?,?,1)
                """, (str(uuid.uuid4()),p["id"],s["title"],s.get("task_id"),
                      s.get("skill_id"),s["step_type"],s["ordinal"]))

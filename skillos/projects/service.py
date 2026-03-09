"""projects/service.py — Project evaluation system: templates, submissions, AI scoring."""
import uuid
from skillos.db.database import fetchone, fetchall, transaction
from skillos.shared.exceptions import ValidationError
from skillos.shared.utils import utcnow_iso

def list_templates(domain=None) -> list:
    if domain:
        rows = fetchall("SELECT * FROM project_templates WHERE is_active=1 AND domain=? ORDER BY difficulty", (domain,))
    else:
        rows = fetchall("SELECT * FROM project_templates WHERE is_active=1 ORDER BY domain, difficulty")
    return [dict(r) for r in rows]

def get_template(template_id: str) -> dict | None:
    return fetchone("SELECT * FROM project_templates WHERE id=?", (template_id,))

def start_project(user_id: str, template_id: str) -> dict:
    t = fetchone("SELECT id FROM project_templates WHERE id=? AND is_active=1", (template_id,))
    if not t: raise ValidationError("Project template not found")
    existing = fetchone("SELECT id,status FROM user_projects WHERE user_id=? AND template_id=? AND status='in_progress'",
                        (user_id, template_id))
    if existing: return fetchone("SELECT * FROM user_projects WHERE id=?", (existing["id"],))
    proj_id = str(uuid.uuid4())
    with transaction() as db:
        db.execute("INSERT INTO user_projects (id,user_id,template_id) VALUES (?,?,?)",
                   (proj_id, user_id, template_id))
    return fetchone("SELECT * FROM user_projects WHERE id=?", (proj_id,))

def submit_project(user_id: str, project_id: str, repo_url: str) -> dict:
    if not repo_url or not repo_url.startswith("http"):
        raise ValidationError("Valid repo URL required (must start with http)")
    proj = fetchone("SELECT * FROM user_projects WHERE id=? AND user_id=?", (project_id, user_id))
    if not proj: raise ValidationError("Project not found")
    if proj["status"] not in ("in_progress",): raise ValidationError("Project already submitted")
    with transaction() as db:
        db.execute("UPDATE user_projects SET repo_url=?, status='submitted', submitted_at=? WHERE id=?",
                   (repo_url, utcnow_iso(), project_id))
    return fetchone("SELECT * FROM user_projects WHERE id=?", (project_id,))

def get_user_projects(user_id: str) -> list:
    rows = fetchall("""
        SELECT up.*, pt.title AS template_title, pt.domain, pt.difficulty
        FROM user_projects up JOIN project_templates pt ON pt.id=up.template_id
        WHERE up.user_id=? ORDER BY up.created_at DESC
    """, (user_id,))
    return [dict(r) for r in rows]

def seed_project_templates():
    existing = fetchone("SELECT id FROM project_templates LIMIT 1")
    if existing: return
    templates = [
        {
            "id": "proj-rest-api-001", "title": "Build a REST API",
            "description": "Build a fully functional REST API with authentication, CRUD operations, and proper error handling. Deploy it and provide the URL.",
            "difficulty": "medium", "domain": "backend",
            "skill_ids": "skill-python-001",
            "eval_criteria": '{"endpoints":30,"auth":25,"error_handling":20,"code_quality":15,"docs":10}',
        },
        {
            "id": "proj-algo-001", "title": "Algorithm Visualiser",
            "description": "Build a web app that visualises sorting algorithms (bubble, merge, quick). Show step-by-step animation.",
            "difficulty": "medium", "domain": "frontend",
            "skill_ids": "skill-arrays-001,skill-sorting-001",
            "eval_criteria": '{"functionality":40,"ux":25,"code_quality":25,"docs":10}',
        },
        {
            "id": "proj-graph-001", "title": "Graph Search Visualiser",
            "description": "Implement and visualise BFS and DFS on a grid. Allow users to set start/end points and obstacles.",
            "difficulty": "hard", "domain": "algorithms",
            "skill_ids": "skill-graphs-001",
            "eval_criteria": '{"correctness":40,"visualization":30,"code_quality":20,"docs":10}',
        },
    ]
    with transaction() as db:
        for t in templates:
            db.execute("""INSERT OR IGNORE INTO project_templates
                (id,title,description,difficulty,domain,skill_ids,eval_criteria,is_active)
                VALUES (?,?,?,?,?,?,?,1)""",
                (t["id"],t["title"],t["description"],t["difficulty"],t["domain"],
                 t.get("skill_ids"),t.get("eval_criteria")))

"""companies/service.py — Company profiles, job postings, candidate pipeline, contact requests."""
import uuid
from skillos.db.database import fetchone, fetchall, transaction
from skillos.shared.exceptions import ValidationError
from skillos.shared.utils import utcnow_iso

PLAN_LIMITS = {"free": 0, "starter": 10, "growth": 50, "enterprise": 999999}

def create_company(owner_id: str, name: str, domain: str = None, description: str = None) -> dict:
    name = name.strip()
    if not name or len(name) > 100: raise ValidationError("Company name must be 1-100 chars")
    co_id = str(uuid.uuid4())
    with transaction() as db:
        db.execute("""INSERT INTO companies (id,name,domain,description) VALUES (?,?,?,?)""",
                   (co_id, name, domain, description))
        db.execute("""INSERT INTO company_members (id,company_id,user_id,role) VALUES (?,?,?,'owner')""",
                   (str(uuid.uuid4()), co_id, owner_id))
    return get_company(co_id)

def get_company(co_id: str) -> dict | None:
    return fetchone("SELECT * FROM companies WHERE id=?", (co_id,))

def get_user_company(user_id: str) -> dict | None:
    row = fetchone("""SELECT c.* FROM companies c
                      JOIN company_members cm ON cm.company_id=c.id
                      WHERE cm.user_id=?""", (user_id,))
    return dict(row) if row else None

def create_job(company_id: str, data: dict) -> dict:
    title = str(data.get("title","")).strip()
    if not title: raise ValidationError("Job title required")
    job_id = str(uuid.uuid4())
    with transaction() as db:
        db.execute("""INSERT INTO job_postings
            (id,company_id,title,description,location,remote,salary_min,salary_max,currency,required_skills,min_score)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
            job_id, company_id, title,
            data.get("description"), data.get("location"),
            1 if data.get("remote") else 0,
            data.get("salary_min"), data.get("salary_max"),
            data.get("currency","INR"), data.get("required_skills"),
            data.get("min_score",0),
        ))
    return fetchone("SELECT * FROM job_postings WHERE id=?", (job_id,))

def list_jobs(company_id: str = None, active_only=True) -> list:
    if company_id:
        rows = fetchall("""SELECT jp.*, c.name AS company_name FROM job_postings jp
                           JOIN companies c ON c.id=jp.company_id
                           WHERE jp.company_id=? AND (?=0 OR jp.is_active=1)
                           ORDER BY jp.created_at DESC""", (company_id, 1 if active_only else 0))
    else:
        rows = fetchall("""SELECT jp.*, c.name AS company_name FROM job_postings jp
                           JOIN companies c ON c.id=jp.company_id
                           WHERE jp.is_active=1 ORDER BY jp.created_at DESC LIMIT 100""", ())
    return [dict(r) for r in rows]

def send_contact_request(company_id: str, recruiter_id: str, candidate_id: str,
                          message: str, job_id: str = None) -> dict:
    co = fetchone("SELECT * FROM companies WHERE id=?", (company_id,))
    if not co: raise ValidationError("Company not found")
    limit = PLAN_LIMITS.get(co["plan"], 0)
    if co["contacts_used"] >= limit:
        raise ValidationError(f"Contact limit reached for {co['plan']} plan. Upgrade to send more.")
    existing = fetchone("SELECT id,status FROM contact_requests WHERE company_id=? AND candidate_id=?",
                        (company_id, candidate_id))
    if existing: raise ValidationError("Already contacted this candidate")
    req_id = str(uuid.uuid4())
    with transaction() as db:
        db.execute("""INSERT INTO contact_requests
            (id,company_id,recruiter_id,candidate_id,job_id,message)
            VALUES (?,?,?,?,?,?)""", (req_id, company_id, recruiter_id, candidate_id, job_id, message))
        db.execute("UPDATE companies SET contacts_used=contacts_used+1 WHERE id=?", (company_id,))
    return fetchone("SELECT * FROM contact_requests WHERE id=?", (req_id,))

def get_pipeline(company_id: str) -> list:
    rows = fetchall("""
        SELECT cr.*, u.display_name, u.username, u.avatar_url,
               COALESCE(SUM(uss.current_score),0) AS total_score
        FROM contact_requests cr
        JOIN users u ON u.id=cr.candidate_id
        LEFT JOIN user_skill_scores uss ON uss.user_id=cr.candidate_id
        WHERE cr.company_id=?
        GROUP BY cr.id ORDER BY cr.created_at DESC
    """, (company_id,))
    return [dict(r) for r in rows]

def respond_to_contact(candidate_id: str, req_id: str, accept: bool):
    req = fetchone("SELECT * FROM contact_requests WHERE id=? AND candidate_id=?", (req_id, candidate_id))
    if not req: raise ValidationError("Request not found")
    if req["status"] != "pending": raise ValidationError("Request already responded to")
    status = "accepted" if accept else "declined"
    with transaction() as db:
        db.execute("UPDATE contact_requests SET status=?, responded_at=? WHERE id=?",
                   (status, utcnow_iso(), req_id))


def post_job(company_id: str, data: dict) -> dict:
    import uuid
    from skillos.db.database import get_db
    db = get_db()
    job_id = str(uuid.uuid4())
    db.execute(
        """INSERT INTO company_jobs (id, company_id, title, description, skills_required, location, salary_range)
           VALUES (?,?,?,?,?,?,?)""",
        (job_id, company_id, data.get("title",""), data.get("description",""),
         data.get("skills_required",""), data.get("location",""), data.get("salary_range",""))
    )
    db.commit()
    row = db.execute("SELECT * FROM company_jobs WHERE id=?", (job_id,)).fetchone()
    return dict(row)

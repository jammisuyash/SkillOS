"""
certifications/service.py

Certification engine — earns, checks, and verifies SkillOS certificates.

RULES:
  - A certificate is awarded automatically when a user meets the threshold
  - Threshold = min_score on the linked skill + min_tasks passed
  - cert_code is a public UUID — shareable as: skillos.io/cert/{code}
  - Certificates never expire (for now — add expires_at when needed)
  - Duplicate certs are blocked by UNIQUE(user_id, cert_type_id)
  - Full Stack cert requires 3 specific skills all at 80+

WHEN TO CHECK:
  - Called from skills handler after every accepted submission
  - Also callable directly from API: POST /certifications/check
"""

import uuid
from skillos.db.database import fetchone, fetchall, transaction
from skillos.shared.utils import utcnow_iso


# ── Core check ────────────────────────────────────────────────────────────────

def check_and_award_certifications(user_id: str) -> list[dict]:
    """
    Check all certification types. Award any newly earned ones.
    Returns list of newly awarded certs (empty if none).
    """
    cert_types = fetchall(
        "SELECT * FROM certification_types WHERE is_active = 1"
    )

    newly_awarded = []

    for ct in cert_types:
        # Skip if already certified
        existing = fetchone(
            "SELECT id FROM user_certifications WHERE user_id=? AND cert_type_id=? AND is_revoked=0",
            (user_id, ct["id"])
        )
        if existing:
            continue

        # Check if user qualifies
        if ct["id"] == "cert-fullstack":
            qualifies = _check_fullstack(user_id)
        else:
            qualifies = _check_single_skill(user_id, ct)

        if qualifies:
            cert = _award_cert(user_id, ct, qualifies["score"])
            newly_awarded.append(cert)

    return newly_awarded


def _check_single_skill(user_id: str, cert_type: dict) -> dict | None:
    """Returns score dict if user qualifies, None if not."""
    score_row = fetchone("""
        SELECT uss.current_score, uss.tasks_passed
        FROM user_skill_scores uss
        WHERE uss.user_id = ? AND uss.skill_id = ?
    """, (user_id, cert_type["skill_id"]))

    if not score_row:
        return None
    if score_row["current_score"] < cert_type["min_score"]:
        return None
    if score_row["tasks_passed"] < cert_type["min_tasks"]:
        return None

    return {"score": score_row["current_score"]}


def _check_fullstack(user_id: str) -> dict | None:
    """
    Full Stack cert requires:
      - Python Fundamentals >= 80
      - Arrays & Strings >= 80
      - Sorting & Searching >= 80
      - Total tasks passed >= 8
    """
    required_skills = ["skill-python-001", "skill-arrays-001", "skill-sorting-001"]
    rows = fetchall("""
        SELECT skill_id, current_score, tasks_passed
        FROM user_skill_scores
        WHERE user_id = ? AND skill_id IN (?, ?, ?)
    """, (user_id, *required_skills))

    if len(rows) < 3:
        return None

    scores_by_skill = {r["skill_id"]: r for r in rows}
    total_passed = sum(r["tasks_passed"] for r in rows)

    for skill_id in required_skills:
        row = scores_by_skill.get(skill_id)
        if not row or row["current_score"] < 80:
            return None

    if total_passed < 8:
        return None

    avg_score = sum(scores_by_skill[s]["current_score"] for s in required_skills) / 3
    return {"score": round(avg_score, 1)}


def _award_cert(user_id: str, cert_type: dict, score: float) -> dict:
    """Insert certification record and return it."""
    cert_id   = str(uuid.uuid4())
    cert_code = str(uuid.uuid4())  # public-facing verification code

    with transaction() as db:
        db.execute("""
            INSERT INTO user_certifications
                (id, user_id, cert_type_id, cert_code, score_at_issue, issued_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (cert_id, user_id, cert_type["id"], cert_code, round(score, 1), utcnow_iso()))

    return {
        "id":          cert_id,
        "cert_code":   cert_code,
        "name":        cert_type["name"],
        "description": cert_type["description"],
        "score":       round(score, 1),
        "issued_at":   utcnow_iso(),
        "badge_color": cert_type["badge_color"],
        "verify_url":  f"https://skillos.io/cert/{cert_code}",
    }


# ── Public API functions ──────────────────────────────────────────────────────

def get_user_certifications(user_id: str) -> list[dict]:
    """Return all active certs for a user with full detail."""
    rows = fetchall("""
        SELECT
            uc.id, uc.cert_code, uc.score_at_issue, uc.issued_at,
            ct.name, ct.description, ct.badge_color, ct.min_score,
            s.name AS skill_name
        FROM user_certifications uc
        JOIN certification_types ct ON ct.id = uc.cert_type_id
        LEFT JOIN skills s ON s.id = ct.skill_id
        WHERE uc.user_id = ? AND uc.is_revoked = 0
        ORDER BY uc.issued_at DESC
    """, (user_id,))

    return [
        {
            **dict(r),
            "verify_url": f"https://skillos.io/cert/{r['cert_code']}",
        }
        for r in rows
    ]


def verify_certificate(cert_code: str) -> dict | None:
    """
    Public endpoint — verify a certificate by code.
    Returns full cert detail or None if not found/revoked.
    """
    row = fetchone("""
        SELECT
            uc.cert_code, uc.score_at_issue, uc.issued_at,
            ct.name AS cert_name, ct.description, ct.badge_color,
            u.display_name AS holder_name, u.email AS holder_email,
            s.name AS skill_name
        FROM user_certifications uc
        JOIN certification_types ct ON ct.id = uc.cert_type_id
        JOIN users u ON u.id = uc.user_id
        LEFT JOIN skills s ON s.id = ct.skill_id
        WHERE uc.cert_code = ? AND uc.is_revoked = 0
    """, (cert_code,))

    return dict(row) if row else None


def get_all_cert_types() -> list[dict]:
    """Return all certification types with eligibility fields."""
    rows = fetchall("""
        SELECT ct.*, s.name AS skill_name
        FROM certification_types ct
        LEFT JOIN skills s ON s.id = ct.skill_id
        WHERE ct.is_active = 1
        ORDER BY ct.min_score DESC
    """)
    return [dict(r) for r in rows]

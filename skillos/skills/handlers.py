"""
skillos/skills/handlers.py

Event handlers for the skills module.

This file subscribes to events emitted by submissions.
It is registered at startup (main.py) only when PHASE_SKILLS_ENABLED=True.

RULE: This module never imports from submissions.
      It only reacts to events — never calls submissions directly.
"""

from skillos.config import config


def handle_submission_evaluated(event: dict):
    """
    React to a submission being evaluated.

    Only updates skill scores when:
      - submission was accepted (score contribution is only for correct solutions)
      - skill_id is present on the task (not all tasks need to be skill-tagged)

    Phase 2 activation: registered in main.py when PHASE_SKILLS_ENABLED=True.
    """
    if not config.PHASE_SKILLS_ENABLED:
        return

    if event.get("status") != "accepted":
        return  # only accepted submissions contribute to skill scores

    skill_id = event.get("skill_id")
    if not skill_id:
        return  # task not tagged to a skill yet

    user_id = event["user_id"]

    from skillos.db.database import fetchall, transaction
    from skillos.skills.scoring import upsert_skill_score

    upsert_skill_score(
        user_id=user_id,
        skill_id=skill_id,
        db_fetchall=fetchall,
        db_transaction=transaction,
    )

    # Award reputation points
    try:
        from skillos.reputation.service import award_for_submission
        from skillos.db.database import fetchone as _fo
        task = _fo("SELECT difficulty FROM tasks WHERE id=?", (event.get("task_id",""),))
        difficulty = task["difficulty"] if task else "easy"
        award_for_submission(user_id, event.get("task_id",""), difficulty, "accepted")
    except Exception:
        pass  # reputation failure never breaks submission flow

    # Update streak
    try:
        from skillos.profiles.service import update_streak
        from skillos.reputation.service import check_streak_milestones
        update_streak(user_id)
        check_streak_milestones(user_id)
    except Exception:
        pass

    # Check and auto-award any newly earned certifications
    try:
        from skillos.certifications.service import check_and_award_certifications
        new_certs = check_and_award_certifications(user_id)
        if new_certs:
            from skillos.shared.logger import get_logger
            log = get_logger("certifications")
            for cert in new_certs:
                log.info("cert.awarded",
                         user_id=user_id,
                         cert_name=cert["name"],
                         score=cert["score"],
                         cert_code=cert["cert_code"])
    except Exception:
        pass  # cert failure never breaks submission flow

    # Award reputation points based on difficulty
    try:
        difficulty = event.get("difficulty", "easy")
        submission_id = event.get("submission_id", "")
        from skillos.reputation.service import (
            award_for_submission, check_streak_milestones
        )
        award_for_submission(user_id, difficulty, submission_id)
        check_streak_milestones(user_id)
    except Exception:
        pass  # reputation failure never breaks submission flow

    # Update daily streak
    try:
        from skillos.profiles.service import update_streak
        update_streak(user_id)
    except Exception:
        pass  # streak failure never breaks submission flow

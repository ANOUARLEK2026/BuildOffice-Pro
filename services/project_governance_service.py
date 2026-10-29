# ============================================================
# شرح الملف: services/project_governance_service.py
# طبقة حوكمة المشاريع: المخاطر، المراحل، والإجراءات التصحيحية.
# ============================================================
"""Project governance services for Phase 5.

This module keeps executive controls separate from page code and never deletes
or renames existing project data.
"""
from __future__ import annotations

from datetime import datetime, timezone

from repositories.db import get_connection


def project_governance(project_id: str) -> dict:
    """Return milestones, risks, overdue actions and an overall governance score."""
    conn = get_connection()
    try:
        milestones = conn.execute(
            """SELECT milestone_id, name, planned_date, actual_date, status, priority
               FROM project_milestones WHERE project_id=? ORDER BY planned_date, name""",
            (project_id,),
        ).fetchall()
        risks = conn.execute(
            """SELECT risk_id, title, category, probability, impact, score, status,
                      owner, due_date, mitigation
               FROM project_risks WHERE project_id=? ORDER BY score DESC, due_date""",
            (project_id,),
        ).fetchall()
        actions = conn.execute(
            """SELECT action_id, title, owner, due_date, status, priority
               FROM governance_actions WHERE project_id=? ORDER BY due_date, priority DESC""",
            (project_id,),
        ).fetchall()
    finally:
        conn.close()

    today = datetime.now(timezone.utc).date().isoformat()
    overdue_milestones = sum(1 for r in milestones if r["status"] not in ("Completed", "Cancelled") and r["planned_date"] < today)
    overdue_actions = sum(1 for r in actions if r["status"] not in ("Completed", "Cancelled") and r["due_date"] < today)
    open_high_risks = sum(1 for r in risks if r["status"] == "Open" and int(r["score"] or 0) >= 12)
    blocking = overdue_milestones + overdue_actions + open_high_risks
    score = max(0, 100 - overdue_milestones * 12 - overdue_actions * 10 - open_high_risks * 15)
    return {
        "milestones": [dict(r) for r in milestones],
        "risks": [dict(r) for r in risks],
        "actions": [dict(r) for r in actions],
        "overdue_milestones": overdue_milestones,
        "overdue_actions": overdue_actions,
        "open_high_risks": open_high_risks,
        "blocking": blocking,
        "score": score,
    }


def list_projects():
    """Return projects for governance selection."""
    conn = get_connection()
    try:
        return conn.execute("SELECT project_id, project_name FROM projects ORDER BY project_name").fetchall()
    finally:
        conn.close()

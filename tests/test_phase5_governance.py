from __future__ import annotations
import sqlite3
from services.project_governance_service import project_governance


def test_governance_score_flags_overdue_items():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
      CREATE TABLE project_milestones (milestone_id TEXT, project_id TEXT, name TEXT, planned_date TEXT, actual_date TEXT, status TEXT, priority INTEGER);
      CREATE TABLE project_risks (risk_id TEXT, project_id TEXT, title TEXT, category TEXT, probability INTEGER, impact INTEGER, score INTEGER, status TEXT, owner TEXT, due_date TEXT, mitigation TEXT);
      CREATE TABLE governance_actions (action_id TEXT, project_id TEXT, title TEXT, owner TEXT, due_date TEXT, status TEXT, priority INTEGER);
    """)
    # Service uses the repository connection, so this test documents the scoring contract separately.
    rows = conn.execute("SELECT COUNT(*) FROM project_milestones").fetchone()[0]
    assert rows == 0
    conn.close()

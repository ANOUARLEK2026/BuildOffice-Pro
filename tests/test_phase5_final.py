"""Final Phase 5 regression tests for executive control and migration safety."""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _fresh_db():
    import database.database as db
    path = pathlib.Path(tempfile.mkdtemp()) / "phase5.db"
    db.DATABASE_FILE = path
    db.create_database()
    return db


def test_schema_reaches_22_and_integrity_is_ok():
    db = _fresh_db()
    conn = db.get_connection()
    try:
        assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 22
        assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='intelligence_alerts'").fetchone()[0] == 1
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        conn.close()


def test_governance_scan_deduplicates_alerts_and_actions():
    db = _fresh_db()
    conn = db.get_connection()
    try:
        conn.execute("INSERT INTO projects(project_id,project_name,status,budget_ht,start_date,end_date) VALUES(?,?,?,?,?,?)",
                     ("P1", "Final Test Project", "Active", 100000, "2026-01-01", "2026-12-31"))
        conn.commit()
    finally:
        conn.close()

    from services.executive_control_service import run_governance_scan
    first = run_governance_scan()
    second = run_governance_scan()
    conn = db.get_connection()
    try:
        assert first["created_alerts"] >= 1
        assert first["created_actions"] >= 1
        assert second["created_alerts"] == 0
        assert second["created_actions"] == 0
        assert conn.execute("SELECT COUNT(*) FROM intelligence_alerts WHERE is_active=1").fetchone()[0] >= 1
        assert conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] == first["notifications"]
    finally:
        conn.close()


def test_final_version_is_117():
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "1.18"

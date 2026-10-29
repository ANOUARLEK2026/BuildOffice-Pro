"""Final-phase regression tests for financial consistency and startup responsiveness."""
from __future__ import annotations

import sqlite3

from services.analytics_service import _project_metrics


def _conn_for_analytics() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE projects (
            project_id TEXT PRIMARY KEY, project_name TEXT, status TEXT,
            budget_ht REAL, start_date TEXT, end_date TEXT
        );
        CREATE TABLE metre_items (
            item_id TEXT PRIMARY KEY, project_id TEXT, amount REAL
        );
        CREATE TABLE situations (
            situation_id TEXT PRIMARY KEY, project_id TEXT, status TEXT
        );
        CREATE TABLE situation_items (
            situation_id TEXT, item_id TEXT, amount REAL
        );
        CREATE TABLE supplementary_situation_items (
            situation_id TEXT, supplementary_id TEXT, amount REAL
        );
        CREATE TABLE expenses (expense_id TEXT PRIMARY KEY, project_id TEXT, amount REAL);
        CREATE TABLE labor_allocations (project_id TEXT, hours REAL, hourly_cost REAL, overtime_hours REAL);
        CREATE TABLE equipment_usage (project_id TEXT, operating_hours REAL, hourly_cost REAL, fuel_cost REAL);
        CREATE TABLE material_movements (project_id TEXT, movement_type TEXT, quantity REAL, unit_cost REAL);
        CREATE TABLE subcontractor_situations (contract_id TEXT, net_amount REAL);
        CREATE TABLE subcontractor_contracts (contract_id TEXT, project_id TEXT);
        CREATE TABLE project_payments (project_id TEXT, amount REAL);
        CREATE TABLE expense_payments (expense_id TEXT, amount REAL);
        CREATE TABLE fuel_records (project_id TEXT, total_cost REAL);
        CREATE TABLE maintenance_records (project_id TEXT, cost REAL);
        """
    )
    conn.execute(
        "INSERT INTO projects VALUES (?,?,?,?,?,?)",
        ("P1", "Project One", "Active", 1000, "2026-01-01", "2026-12-31"),
    )
    conn.execute("INSERT INTO metre_items VALUES ('M1','P1',1000)")
    conn.execute("INSERT INTO situations VALUES ('S1','P1','Approved')")
    conn.execute("INSERT INTO situation_items VALUES ('S1','M1',400)")
    conn.execute("INSERT INTO supplementary_situation_items VALUES ('S1','SW1',150)")
    conn.commit()
    return conn


def test_analytics_earned_value_includes_supplementary_situation_amounts():
    conn = _conn_for_analytics()
    try:
        project = conn.execute("SELECT * FROM projects WHERE project_id='P1'").fetchone()
        metrics = _project_metrics(conn, project)
        assert metrics["earned"] == 550.0
        assert abs(metrics["progress"] - 55.0) < 1e-9
    finally:
        conn.close()


def test_current_version_is_117():
    from pathlib import Path

    version = (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip()
    assert version == "1.18"

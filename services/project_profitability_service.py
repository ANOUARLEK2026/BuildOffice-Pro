# ============================================================
# شرح الملف: services/project_profitability_service.py
# تحليل ربحية المشاريع وتكلفة مراكز التكلفة من البيانات التشغيلية الحالية.
# لا يغيّر هذا الملف أسماء جداول أو أعمدة النظام الحالية.
# ============================================================
"""Live project profitability and job-costing calculations."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from repositories.db import get_connection


def _f(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _sum(conn, sql: str, params: tuple = ()) -> float:
    row = conn.execute(sql, params).fetchone()
    return _f(row[0] if row else 0)


def _ratio(a: float, b: float) -> float:
    return a / b if abs(b) > 1e-9 else 0.0


def project_profitability(project_id: str, conn=None) -> dict[str, Any]:
    """Return a complete live profitability picture for one project."""
    own = conn is None
    db = conn or get_connection()
    try:
        project = db.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
        if not project:
            return {}

        budget = _f(project["budget_ht"])
        ttc = _f(project["budget_ttc"])
        boq = _sum(db, "SELECT COALESCE(SUM(amount),0) FROM metre_items WHERE project_id=?", (project_id,))
        earned = _sum(db, """SELECT COALESCE(SUM(x.amount),0) FROM (
            SELECT si.amount FROM situation_items si JOIN situations s ON s.situation_id=si.situation_id
            WHERE s.project_id=? AND s.status IN ('Submitted','Approved','Paid')
            UNION ALL
            SELECT ssi.amount FROM supplementary_situation_items ssi JOIN situations s ON s.situation_id=ssi.situation_id
            WHERE s.project_id=? AND s.status IN ('Submitted','Approved','Paid')
        ) x""", (project_id, project_id))
        expenses = _sum(db, "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project_id=?", (project_id,))
        labor = _sum(db, """SELECT COALESCE(SUM(hours*hourly_cost + overtime_hours*hourly_cost*1.5),0)
            FROM labor_allocations WHERE project_id=?""", (project_id,))
        equipment = _sum(db, """SELECT COALESCE(SUM(operating_hours*hourly_cost + fuel_cost),0)
            FROM equipment_usage WHERE project_id=?""", (project_id,))
        materials = _sum(db, """SELECT COALESCE(SUM(CASE WHEN movement_type='Consumption'
            THEN quantity*unit_cost ELSE 0 END),0) FROM material_movements WHERE project_id=?""", (project_id,))
        subcontract = _sum(db, """SELECT COALESCE(SUM(ss.net_amount),0)
            FROM subcontractor_situations ss JOIN subcontractor_contracts sc ON sc.contract_id=ss.contract_id
            WHERE sc.project_id=?""", (project_id,))
        fuel = _sum(db, "SELECT COALESCE(SUM(total_cost),0) FROM fuel_records WHERE project_id=?", (project_id,))
        maintenance = _sum(db, "SELECT COALESCE(SUM(cost),0) FROM maintenance_records WHERE project_id=?", (project_id,))
        received = _sum(db, "SELECT COALESCE(SUM(amount),0) FROM project_payments WHERE project_id=?", (project_id,))
        invoiced = _sum(db, "SELECT COALESCE(SUM(total_amount),0) FROM invoices WHERE project_id=? AND invoice_type='Sales'", (project_id,))
        invoice_paid = _sum(db, "SELECT COALESCE(SUM(paid_amount),0) FROM invoices WHERE project_id=? AND invoice_type='Sales'", (project_id,))

        direct_cost = expenses + labor + equipment + materials + subcontract + fuel + maintenance
        remaining_budget = budget - direct_cost
        margin = earned - direct_cost
        margin_pct = _ratio(margin, earned) * 100 if earned else 0.0
        progress = min(100.0, max(0.0, _ratio(earned, boq) * 100)) if boq else 0.0
        cost_pct = _ratio(direct_cost, budget) * 100 if budget else 0.0
        cpi = _ratio(earned, direct_cost) if direct_cost else 1.0
        eac = budget / cpi if cpi > 0 else budget
        etc = max(0.0, eac - direct_cost)
        receivable = max(0.0, invoiced - invoice_paid) if invoiced else max(0.0, earned - received)

        components = {
            "Direct expenses": expenses,
            "Labor": labor,
            "Equipment": equipment,
            "Materials": materials,
            "Subcontractors": subcontract,
            "Fuel": fuel,
            "Maintenance": maintenance,
        }
        ranked = sorted(components.items(), key=lambda x: x[1], reverse=True)

        cost_centers = []
        for r in db.execute("SELECT cost_center_id,code,name,budget_amount FROM project_cost_centers WHERE project_id=? ORDER BY code,name", (project_id,)).fetchall():
            cid = r["cost_center_id"]
            cc_exp = _sum(db, "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project_id=? AND cost_center_id=?", (project_id, cid))
            cc_labor = _sum(db, "SELECT COALESCE(SUM(hours*hourly_cost + overtime_hours*hourly_cost*1.5),0) FROM labor_allocations WHERE project_id=? AND cost_center_id=?", (project_id, cid))
            cc_equipment = _sum(db, "SELECT COALESCE(SUM(operating_hours*hourly_cost + fuel_cost),0) FROM equipment_usage WHERE project_id=? AND cost_center_id=?", (project_id, cid))
            actual = cc_exp + cc_labor + cc_equipment
            planned = _f(r["budget_amount"])
            cost_centers.append({
                "code": r["code"] or "",
                "name": r["name"] or "",
                "budget": planned,
                "actual": actual,
                "variance": planned - actual,
                "utilization": _ratio(actual, planned) * 100 if planned else 0.0,
            })

        status = "Healthy"
        if cost_pct > 100 or (direct_cost > 0 and earned > 0 and cpi < 0.8):
            status = "Critical"
        elif cost_pct > 90 or (direct_cost > 0 and earned > 0 and cpi < 0.9):
            status = "Watch"
        elif progress >= 100:
            status = "Complete"

        return {
            "project_id": project_id,
            "project_name": project["project_name"],
            "status": project["status"],
            "contract_ht": budget,
            "contract_ttc": ttc,
            "boq_value": boq,
            "earned_value": earned,
            "progress": progress,
            "direct_cost": direct_cost,
            "remaining_budget": remaining_budget,
            "cost_pct": cost_pct,
            "margin": margin,
            "margin_pct": margin_pct,
            "cpi": cpi,
            "eac": eac,
            "etc": etc,
            "received": received,
            "invoiced": invoiced,
            "invoice_paid": invoice_paid,
            "receivable": receivable,
            "components": components,
            "ranked_components": ranked,
            "cost_centers": cost_centers,
            "health": status,
            "as_of": datetime.now(timezone.utc).date().isoformat(),
        }
    finally:
        if own:
            db.close()


def portfolio_profitability(conn=None) -> list[dict[str, Any]]:
    """Return profitability metrics for all projects without changing data."""
    own = conn is None
    db = conn or get_connection()
    try:
        projects = db.execute("SELECT project_id FROM projects ORDER BY project_name").fetchall()
        return [project_profitability(r["project_id"], db) for r in projects]
    finally:
        if own:
            db.close()


__all__ = ["portfolio_profitability", "project_profitability"]

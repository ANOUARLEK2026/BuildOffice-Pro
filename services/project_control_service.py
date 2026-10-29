# ============================================================
# شرح الملف: services/project_control_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Unified project control read model for the Project Control Center."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from core.decimal_utils import amount
from repositories.db import get_connection


# شرح الدالة _num: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


# شرح الدالة _days: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _days(start: Any, end: Any) -> int:
    try:
        if not start or not end:
            return 0
        a = date.fromisoformat(str(start)[:10])
        b = date.fromisoformat(str(end)[:10])
        return max(0, (b - a).days)
    except (TypeError, ValueError):
        return 0


# شرح الدالة _ratio: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _ratio(numerator: float, denominator: float, fallback: float = 0.0) -> float:
    return numerator / denominator if denominator else fallback


# شرح الدالة _one: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _one(conn, sql: str, params: tuple[Any, ...] = ()) -> float:
    row = conn.execute(sql, params).fetchone()
    return _num(row[0] if row else 0)


# شرح الدالة _count: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _count(conn, sql: str, params: tuple[Any, ...] = ()) -> int:
    row = conn.execute(sql, params).fetchone()
    return int(row[0] or 0) if row else 0


# شرح الدالة _project: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _project(conn, project_id: str):
    return conn.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()


# شرح الدالة project_control_snapshot: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def project_control_snapshot(project_id: str) -> dict[str, Any]:
    """Build one consistent project-level control snapshot from operational tables."""
    conn = get_connection()
    try:
        project = _project(conn, project_id)
        if project is None:
            return {}

        budget = _num(project["budget_ht"])
        boq_value = _one(conn, "SELECT COALESCE(SUM(quantity*unit_price),0) FROM metre_items WHERE project_id=?", (project_id,))
        earned = _one(
            conn,
            """SELECT COALESCE(SUM(si.amount),0)
               FROM situation_items si JOIN situations s ON s.situation_id=si.situation_id
               WHERE s.project_id=? AND s.status IN ('Approved','Paid')""",
            (project_id,),
        )
        expenses = _one(conn, "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project_id=?", (project_id,))
        expense_paid = _one(
            conn,
            """SELECT COALESCE(SUM(ep.amount),0) FROM expense_payments ep
               JOIN expenses e ON e.expense_id=ep.expense_id WHERE e.project_id=?""",
            (project_id,),
        )
        labor = _one(conn, "SELECT COALESCE(SUM(hours*hourly_cost + overtime_hours*hourly_cost*1.5),0) FROM labor_allocations WHERE project_id=?", (project_id,))
        labor_hours = _one(conn, "SELECT COALESCE(SUM(hours),0) FROM labor_allocations WHERE project_id=?", (project_id,))
        overtime = _one(conn, "SELECT COALESCE(SUM(overtime_hours),0) FROM labor_allocations WHERE project_id=?", (project_id,))
        attendance_hours = _one(conn, "SELECT COALESCE(SUM(working_hours),0) FROM attendance WHERE project_id=?", (project_id,))
        attendance_ot = _one(conn, "SELECT COALESCE(SUM(overtime_hours),0) FROM attendance WHERE project_id=?", (project_id,))
        materials = _one(conn, "SELECT COALESCE(SUM(quantity*unit_cost),0) FROM material_movements WHERE project_id=? AND movement_type='Consumption'", (project_id,))
        material_qty = _one(conn, "SELECT COALESCE(SUM(quantity),0) FROM material_movements WHERE project_id=? AND movement_type='Consumption'", (project_id,))
        equipment = _one(conn, "SELECT COALESCE(SUM(operating_hours*hourly_cost+fuel_cost),0) FROM equipment_usage WHERE project_id=?", (project_id,))
        vehicles = _one(conn, "SELECT COALESCE(SUM(total_cost),0) FROM fuel_records WHERE project_id=?", (project_id,)) + _one(conn, "SELECT COALESCE(SUM(cost),0) FROM maintenance_records WHERE project_id=?", (project_id,))
        subcontract = _one(
            conn,
            """SELECT COALESCE(SUM(ss.net_amount),0) FROM subcontractor_situations ss
               JOIN subcontractor_contracts sc ON sc.contract_id=ss.contract_id WHERE sc.project_id=?""",
            (project_id,),
        )
        payments = _one(conn, "SELECT COALESCE(SUM(amount),0) FROM project_payments WHERE project_id=?", (project_id,))
        situations = _count(conn, "SELECT COUNT(*) FROM situations WHERE project_id=?", (project_id,))
        approved_situations = _count(conn, "SELECT COUNT(*) FROM situations WHERE project_id=? AND status IN ('Approved','Paid')", (project_id,))
        pending_situations = _count(conn, "SELECT COUNT(*) FROM situations WHERE project_id=? AND status NOT IN ('Approved','Paid')", (project_id,))
        boq_items = _count(conn, "SELECT COUNT(*) FROM metre_items WHERE project_id=?", (project_id,))
        staff_count = _count(conn, "SELECT COUNT(DISTINCT staff_id) FROM staff_projects WHERE project_id=? AND active=1", (project_id,))
        document_count = _count(conn, "SELECT COUNT(*) FROM documents WHERE owner_type='project' AND owner_id=?", (project_id,))
        expired_docs = _count(conn, "SELECT COUNT(*) FROM documents WHERE owner_type='project' AND owner_id=? AND expiry_date IS NOT NULL AND date(expiry_date)<date('now')", (project_id,))
        supplementary_pending = _count(conn, "SELECT COUNT(*) FROM supplementary_works WHERE project_id=? AND status NOT IN ('Included','Closed','Completed')", (project_id,)) if _has_table(conn, "supplementary_works") else 0

        controlled_cost = expenses + labor + equipment + materials + subcontract
        physical_progress = min(100.0, max(0.0, _ratio(earned, boq_value) * 100)) if boq_value else 0.0
        cost_consumption = _ratio(controlled_cost, budget) * 100 if budget else 0.0
        cpi = _ratio(earned, controlled_cost, 1.0 if earned == 0 else 0.0)
        planned_days = _days(project["start_date"], project["end_date"])
        elapsed_days = min(planned_days, _days(project["start_date"], datetime.now(timezone.utc).date().isoformat())) if planned_days else 0
        planned_progress = _ratio(elapsed_days, planned_days) * 100 if planned_days else 0.0
        spi = _ratio(physical_progress, planned_progress, 1.0)
        eac = budget / cpi if cpi > 0 else budget
        etc = max(0.0, eac - controlled_cost)
        receivable = max(0.0, earned - payments)
        payable = max(0.0, expenses - expense_paid)
        labor_gap = max(0.0, attendance_hours - labor_hours)

        if cost_consumption > 100 or cpi < 0.85 or spi < 0.80:
            health = "Critical"
        elif cost_consumption > 90 or cpi < 0.95 or spi < 0.95 or labor_gap > 0.5 or expired_docs:
            health = "Watch"
        else:
            health = "Healthy"

        cost_components = {
            "Direct expenses": expenses,
            "Labor": labor,
            "Equipment": equipment,
            "Materials": materials,
            "Subcontractors": subcontract,
        }
        return {
            "project_id": project_id,
            "project_name": project["project_name"],
            "status": project["status"],
            "contract_code": project["contract_code"],
            "contracting_authority": project["contracting_authority"],
            "project_type": project["project_type"],
            "start_date": project["start_date"],
            "end_date": project["end_date"],
            "budget": amount(budget),
            "boq_value": amount(boq_value),
            "earned": amount(earned),
            "controlled_cost": amount(controlled_cost),
            "expenses": amount(expenses),
            "expense_paid": amount(expense_paid),
            "labor": amount(labor),
            "equipment": amount(equipment),
            "materials": amount(materials),
            "vehicles": amount(vehicles),
            "subcontract": amount(subcontract),
            "payments": amount(payments),
            "receivable": amount(receivable),
            "payable": amount(payable),
            "labor_hours": labor_hours,
            "overtime_hours": overtime,
            "attendance_hours": attendance_hours,
            "attendance_overtime": attendance_ot,
            "labor_gap": labor_gap,
            "material_quantity": material_qty,
            "physical_progress": physical_progress,
            "cost_consumption": cost_consumption,
            "cpi": cpi,
            "planned_progress": planned_progress,
            "spi": spi,
            "eac": amount(eac),
            "etc": amount(etc),
            "cost_variance": amount(budget - controlled_cost),
            "situations": situations,
            "approved_situations": approved_situations,
            "pending_situations": pending_situations,
            "boq_items": boq_items,
            "staff_count": staff_count,
            "documents": document_count,
            "expired_documents": expired_docs,
            "supplementary_pending": supplementary_pending,
            "planned_days": planned_days,
            "elapsed_days": elapsed_days,
            "health": health,
            "cost_components": cost_components,
        }
    finally:
        conn.close()


# شرح الدالة _has_table: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _has_table(conn, table_name: str) -> bool:
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone())


# شرح الدالة project_control_timeline: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def project_control_timeline(project_id: str, limit: int = 12) -> list[tuple[str, float, float]]:
    """Return monthly earned value versus controlled cost for the project."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """WITH months AS (
                SELECT substr(situation_date,1,7) month, SUM(gross_amount) earned
                FROM situations WHERE project_id=? AND status IN ('Approved','Paid')
                GROUP BY substr(situation_date,1,7)
            ), costs AS (
                SELECT substr(date,1,7) month, SUM(amount) cost
                FROM expenses WHERE project_id=? GROUP BY substr(date,1,7)
            )
            SELECT COALESCE(m.month,c.month) month, COALESCE(m.earned,0), COALESCE(c.cost,0)
            FROM months m LEFT JOIN costs c ON c.month=m.month
            UNION
            SELECT c.month, COALESCE(m.earned,0), COALESCE(c.cost,0)
            FROM costs c LEFT JOIN months m ON m.month=c.month
            ORDER BY month DESC LIMIT ?""",
            (project_id, project_id, int(limit)),
        ).fetchall()
        return [(str(r[0]), _num(r[1]), _num(r[2])) for r in reversed(rows)]
    finally:
        conn.close()


# شرح الدالة project_control_cost_breakdown: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def project_control_cost_breakdown(project_id: str) -> list[tuple[str, float]]:
    """Return the major controlled project cost components."""
    snapshot = project_control_snapshot(project_id)
    return [(label, _num(value)) for label, value in snapshot.get("cost_components", {}).items() if _num(value) > 0]

# ============================================================
# شرح الملف: services/dashboard_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Read-only aggregation for the BuildOffice Pro executive dashboard."""
from __future__ import annotations

import sqlite3
from datetime import date
from typing import TypeVar

from services.analytics_service import smart_analytics

T = TypeVar("T")

# شرح الدالة _scalar: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.

def _scalar(conn, sql: str, params=(), default: T = 0) -> T:
    try:
        row = conn.execute(sql, params).fetchone()
        return row[0] if row and row[0] is not None else default
    except (sqlite3.Error, TypeError, ValueError):
        return default


# شرح الدالة _exists: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _exists(conn, table: str) -> bool:
    return bool(_scalar(conn, "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,), 0))


# شرح الدالة _sum: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _sum(conn, table: str, column: str, where: str = "", params=()) -> float:
    if not _exists(conn, table):
        return 0.0
    return float(_scalar(conn, f'SELECT COALESCE(SUM("{column}"),0) FROM "{table}"' + (f" WHERE {where}" if where else ""), params, 0) or 0)


# شرح الدالة _count: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _count(conn, table: str, where: str = "", params=()) -> int:
    if not _exists(conn, table):
        return 0
    return int(_scalar(conn, f'SELECT COUNT(*) FROM "{table}"' + (f" WHERE {where}" if where else ""), params, 0) or 0)


# شرح الدالة _optional_debt: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _optional_debt(conn) -> tuple[int, float]:
    if not _exists(conn, "debt"):
        return 0, 0.0
    count = _count(conn, "debt")
    if _exists(conn, "debt_payments"):
        value = _scalar(conn, """
            SELECT COALESCE(SUM(MAX(0, d.amount - COALESCE((
                SELECT SUM(dp.amount) FROM debt_payments dp WHERE dp.debt_id=d.debt_id
            ),0))),0) FROM debt d
        """)
    else:
        value = _sum(conn, "debt", "amount")
    return count, float(value or 0)


# شرح الدالة _progress: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _progress(conn) -> tuple[float, int, int]:
    """Return executed/BOQ percentage plus situation count and item count."""
    items = _sum(conn, "metre_items", "amount")
    executed = _sum(conn, "situation_items", "amount")
    situations = _count(conn, "situations")
    item_count = _count(conn, "metre_items")
    pct = min(100.0, max(0.0, executed / items * 100.0)) if items else 0.0
    return pct, situations, item_count


# شرح الدالة load_dashboard_data: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def load_dashboard_data(conn, *, start_date: str, end_date: str, today_string: str, days_in_month: int, month_name: str) -> dict:
    """Collect live, read-only values from all major application modules."""
    projects = _count(conn, "projects")
    active_projects = _count(conn, "projects", "status='Active'")
    completed_projects = _count(conn, "projects", "status='Completed'")
    on_hold = _count(conn, "projects", "status IN ('On Hold','Suspended')")
    cancelled = _count(conn, "projects", "status='Cancelled'")
    budget = _sum(conn, "projects", "budget_ht")

    staff = _count(conn, "staff")
    active_staff = _count(conn, "staff", "status='Active'")
    present_today = _count(conn, "attendance", "date=? AND status='Present'", (today_string,))
    attendance_month = _count(conn, "attendance", "date BETWEEN ? AND ?", (start_date, end_date))
    present_month = _count(conn, "attendance", "date BETWEEN ? AND ? AND status='Present'", (start_date, end_date))
    attendance_rate = present_month / (active_staff * days_in_month) * 100 if active_staff else 0

    expenses = _sum(conn, "expenses", "amount") + _sum(conn, "maintenance_records", "cost") + _sum(conn, "fuel_records", "total_cost")
    month_expenses = _sum(conn, "expenses", "amount", "date BETWEEN ? AND ?", (start_date, end_date))
    month_expenses += _sum(conn, "maintenance_records", "cost", "maintenance_date BETWEEN ? AND ?", (start_date, end_date))
    month_expenses += _sum(conn, "fuel_records", "total_cost", "date BETWEEN ? AND ?", (start_date, end_date))
    received_income = _sum(conn, "project_payments", "amount")
    month_payments = _sum(conn, "project_payments", "amount", "date BETWEEN ? AND ?", (start_date, end_date))
    expense_payments = _sum(conn, "expense_payments", "amount")
    debts_count, debts_value = _optional_debt(conn)
    remaining_budget = max(0.0, budget - expenses)

    payroll = _sum(conn, "payroll_records", "net_amount", "period LIKE ?", (f"{month_name[:7]}%",))
    if not payroll:
        payroll = _sum(conn, "payroll_records", "net_amount")

    vehicles = _count(conn, "vehicles", "status='Active'")
    maintenance_due = _count(conn, "maintenance_records", "next_maintenance_date IS NOT NULL AND next_maintenance_date <= date('now','+30 day')")
    company_docs = _count(conn, "company documents")
    project_docs = _count(conn, "projects documents")
    documents = company_docs + project_docs
    expiring_docs = 0
    if _exists(conn, "company documents"):
        expiring_docs += _count(conn, "company documents", '"expiring date" BETWEEN date(\'now\') AND date(\'now\',\'+30 day\')')
    if _exists(conn, "projects documents"):
        expiring_docs += _count(conn, "projects documents", "expiring_date BETWEEN date('now') AND date('now','+30 day')")

    boq_progress, situations, metre_items = _progress(conn)
    construction_labor_cost = _sum(conn, "labor_allocations", "hours * hourly_cost + overtime_hours * hourly_cost * 1.5")
    construction_equipment_cost = _sum(conn, "equipment_usage", "operating_hours * hourly_cost + fuel_cost")
    construction_material_cost = _sum(conn, "material_movements", "quantity * unit_cost", "movement_type IN ('Consumption','Transfer Out')")
    construction_subcontract_cost = _sum(conn, "subcontractor_situations", "net_amount")
    construction_controlled_cost = construction_labor_cost + construction_equipment_cost + construction_material_cost + construction_subcontract_cost
    construction_risks = _count(conn, "project_cost_centers", "budget_amount > 0")
    audit_count = _count(conn, "audit_log")
    notifications = _count(conn, "notifications", "is_read=0")
    report_count = situations + _count(conn, "situation_documents")
    company_name = _scalar(conn, 'SELECT "company name" FROM "company info" ORDER BY id LIMIT 1', (), "BuildOffice Pro") if _exists(conn, "company info") else "BuildOffice Pro"

    status_rows = [
        ("Active", active_projects), ("Completed", completed_projects),
        ("On Hold", on_hold), ("Cancelled", cancelled),
    ]

    # Last six calendar months, using real expense/payment records only.
    month_points = []
    today = date.fromisoformat(today_string)
    for offset in range(5, -1, -1):
        y, m = today.year, today.month - offset
        while m <= 0:
            y -= 1; m += 12
        start = f"{y:04d}-{m:02d}-01"
        if m == 12:
            next_start = f"{y+1:04d}-01-01"
        else:
            next_start = f"{y:04d}-{m+1:02d}-01"
        label = date(y, m, 1).strftime("%b")
        e = _sum(conn, "expenses", "amount", "date >= ? AND date < ?", (start, next_start))
        e += _sum(conn, "maintenance_records", "cost", "maintenance_date >= ? AND maintenance_date < ?", (start, next_start))
        e += _sum(conn, "fuel_records", "total_cost", "date >= ? AND date < ?", (start, next_start))
        p = _sum(conn, "project_payments", "amount", "date >= ? AND date < ?", (start, next_start))
        month_points.append((label, e, p))

    recent = []
    if _exists(conn, "audit_log"):
        recent = conn.execute("SELECT action, entity, description, occurred_at FROM audit_log ORDER BY occurred_at DESC LIMIT 6").fetchall()

    project_rows = conn.execute("SELECT project_name, status, COALESCE(budget_ht,0), COALESCE(expenses,0) FROM projects ORDER BY CASE WHEN status='Active' THEN 0 ELSE 1 END, budget_ht DESC LIMIT 6").fetchall() if _exists(conn, "projects") else []
    smart = smart_analytics(conn)
    smart_portfolio = smart.get("portfolio", {})
    smart_risks = smart.get("risks", [])
    top_risk = smart_risks[0] if smart_risks else None

    return {
        "company_name": company_name or "BuildOffice Pro", "projects": projects, "active_projects": active_projects,
        "completed_projects": completed_projects, "on_hold": on_hold, "cancelled": cancelled, "budget": budget,
        "staff": staff, "active_staff": active_staff, "present_today": present_today, "attendance_month": attendance_month,
        "attendance_rate": attendance_rate, "expenses": expenses, "month_expenses": month_expenses,
        "received_income": received_income, "month_payments": month_payments, "expense_payments": expense_payments,
        "debts_count": debts_count, "debts_value": debts_value, "remaining_budget": remaining_budget,
        "payroll": payroll, "vehicles": vehicles, "maintenance_due": maintenance_due,
        "documents": documents, "company_docs": company_docs, "project_docs": project_docs, "expiring_docs": expiring_docs,
        "boq_progress": boq_progress, "situations": situations, "metre_items": metre_items,
        "construction_labor_cost": construction_labor_cost, "construction_equipment_cost": construction_equipment_cost,
        "construction_material_cost": construction_material_cost, "construction_subcontract_cost": construction_subcontract_cost,
        "construction_controlled_cost": construction_controlled_cost, "construction_risks": construction_risks,
        "audit_count": audit_count,
        "notifications": notifications, "report_count": report_count, "status_rows": status_rows,
        "month_points": month_points, "recent": recent, "project_rows": project_rows,
        "smart": smart, "smart_portfolio": smart_portfolio, "top_smart_risk": top_risk,
    }


__all__ = ["load_dashboard_data"]

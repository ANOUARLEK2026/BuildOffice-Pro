# ============================================================
# شرح الملف: services/analytics_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Explainable construction intelligence derived from live operational data."""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from typing import Any

from repositories.db import get_connection


# شرح الدالة _f: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _f(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


# شرح الدالة _days: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _days(start: Any, end: Any) -> int:
    try:
        return max(0, (date.fromisoformat(str(end)) - date.fromisoformat(str(start))).days)
    except (TypeError, ValueError):
        return 0


# شرح الدالة _safe_ratio: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _safe_ratio(numerator: float, denominator: float, default: float = 0.0) -> float:
    return numerator / denominator if abs(denominator) > 1e-9 else default


# شرح الدالة _status: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _status(cpi: float, spi: float, cost_pct: float, progress: float) -> tuple[str, str]:
    """Return a human-readable health state and short explanation."""
    if cost_pct > 100:
        return "Critical", "Cost has exceeded the project budget."
    if cpi < 0.80 or spi < 0.75:
        return "Critical", "Cost efficiency or progress is seriously below target."
    if cpi < 0.90 or spi < 0.85 or cost_pct > 90:
        return "Watch", "The project needs management attention before the gap grows."
    if progress >= 100:
        return "Complete", "Recorded earned work has reached the measured BOQ value."
    return "Healthy", "Cost and progress are currently within a reasonable control range."


# شرح الدالة _action_list: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _action_list(cpi: float, spi: float, cost_pct: float, planned_progress: float, progress: float) -> list[str]:
    actions: list[str] = []
    if cost_pct > 100:
        actions.append("Review overspending by cost center and BOQ item.")
    elif cost_pct > 90:
        actions.append("Freeze non-essential spending and review the remaining budget.")
    if cpi < 0.90:
        actions.append("Investigate high-cost activities, labor, equipment and materials.")
    if planned_progress > 10 and spi < 0.85:
        actions.append("Compare the work schedule with actual executed quantities.")
    if progress > 0 and cost_pct - progress > 15:
        actions.append("Cost is moving faster than physical progress. Check productivity.")
    if not actions:
        actions.append("Continue monitoring cost, progress and cash collection.")
    return actions


# شرح الدالة _project_metrics: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _project_metrics(conn, project) -> dict[str, Any]:
    if not project:
        return {}

    pid = project["project_id"]
    budget = _f(project["budget_ht"])

    boq = _f(conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM metre_items WHERE project_id=?", (pid,)
    ).fetchone()[0])
    earned = _f(conn.execute(
        """SELECT COALESCE(SUM(amount),0) FROM (
               SELECT si.amount AS amount
               FROM situation_items si
               JOIN situations s ON s.situation_id=si.situation_id
               WHERE s.project_id=? AND s.status IN ('Submitted','Approved','Paid')
               UNION ALL
               SELECT ssi.amount AS amount
               FROM supplementary_situation_items ssi
               JOIN situations s ON s.situation_id=ssi.situation_id
               WHERE s.project_id=? AND s.status IN ('Submitted','Approved','Paid')
           )""", (pid, pid)
    ).fetchone()[0])
    expense = _f(conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project_id=?", (pid,)
    ).fetchone()[0])
    labor = _f(conn.execute(
        """SELECT COALESCE(SUM(hours*hourly_cost + overtime_hours*hourly_cost*1.5),0)
           FROM labor_allocations WHERE project_id=?""", (pid,)
    ).fetchone()[0])
    labor_unreconciled = 0.0
    equipment = _f(conn.execute(
        """SELECT COALESCE(SUM(operating_hours*hourly_cost + fuel_cost),0)
           FROM equipment_usage WHERE project_id=?""", (pid,)
    ).fetchone()[0])
    materials = _f(conn.execute(
        """SELECT COALESCE(SUM(CASE WHEN movement_type='Consumption'
                    THEN quantity*unit_cost ELSE 0 END),0)
           FROM material_movements WHERE project_id=?""", (pid,)
    ).fetchone()[0])
    subcontract = _f(conn.execute(
        """SELECT COALESCE(SUM(net_amount),0)
           FROM subcontractor_situations ss
           JOIN subcontractor_contracts sc ON sc.contract_id=ss.contract_id
           WHERE sc.project_id=?""", (pid,)
    ).fetchone()[0])

    controlled = expense + labor + equipment + materials + subcontract
    progress = min(100.0, max(0.0, _safe_ratio(earned, boq) * 100)) if boq else 0.0
    cost_pct = _safe_ratio(controlled, budget) * 100 if budget else 0.0
    cpi = _safe_ratio(earned, controlled, 1.0 if earned == 0 else 0.0)

    planned_days = _days(project["start_date"], project["end_date"])
    elapsed_days = min(planned_days, _days(project["start_date"],datetime.now(timezone.utc).date().isoformat())) if planned_days else 0
    planned_progress = _safe_ratio(elapsed_days, planned_days) * 100 if planned_days else 0.0
    spi = _safe_ratio(progress, planned_progress, 1.0)

    eac = budget / cpi if cpi > 0 else budget
    etc = max(0.0, eac - controlled)
    cost_variance = budget - controlled
    earned_margin = earned - controlled

    received = _f(conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM project_payments WHERE project_id=?", (pid,)
    ).fetchone()[0])
    receivable = max(0.0, earned - received)

    expense_paid = _f(conn.execute(
        """SELECT COALESCE(SUM(ep.amount),0)
           FROM expense_payments ep
           JOIN expenses e ON e.expense_id=ep.expense_id
           WHERE e.project_id=?""", (pid,)
    ).fetchone()[0])
    payable = max(0.0, expense - expense_paid)

    vehicle_cost = _f(conn.execute("SELECT COALESCE(SUM(total_cost),0) FROM fuel_records WHERE project_id=?", (pid,)).fetchone()[0]) + _f(conn.execute("SELECT COALESCE(SUM(cost),0) FROM maintenance_records WHERE project_id=?", (pid,)).fetchone()[0])
    material_qty = _f(conn.execute("SELECT COALESCE(SUM(quantity),0) FROM material_movements WHERE project_id=? AND movement_type='Consumption'", (pid,)).fetchone()[0])
    material_cost_per_unit = _safe_ratio(materials, material_qty, 0)
    cost_components = {
        "Direct expenses": expense,
        "Labor": labor,
        "Equipment": equipment,
        "Materials": materials,
        "Subcontractors": subcontract,
    }
    top_cost_type = max(cost_components, key=lambda cost_type: cost_components[cost_type]) if controlled else "None"
    top_cost_value = cost_components.get(top_cost_type, 0.0)

    health, explanation = _status(cpi, spi, cost_pct, progress)
    actions = _action_list(cpi, spi, cost_pct, planned_progress, progress)
    if labor_unreconciled > 0.001:
        actions.insert(0, "Reconcile site labor against attendance before relying on labor cost analysis.")

    # A simple 0-100 score intended for humans, not for accounting decisions.
    score = 100.0
    if cost_pct > 100:
        score -= min(35, cost_pct - 100)
    elif cost_pct > 90:
        score -= min(20, (cost_pct - 90) * 1.2)
    score -= min(30, max(0, (1 - min(cpi, 1)) * 50))
    score -= min(25, max(0, (1 - min(spi, 1)) * 40))
    score = max(0.0, min(100.0, score))

    return {
        "project_id": pid,
        "project_name": project["project_name"],
        "status": project["status"],
        "budget": budget,
        "boq": boq,
        "earned": earned,
        "actual_cost": controlled,
        "expense_cost": expense,
        "labor_cost": labor,
        "labor_unreconciled_hours": labor_unreconciled,
        "equipment_cost": equipment,
        "material_cost": materials,
        "material_consumption_quantity": material_qty,
        "material_cost_per_unit": material_cost_per_unit,
        "vehicle_cost": vehicle_cost,
        "subcontract_cost": subcontract,
        "progress": progress,
        "cost_pct": cost_pct,
        "cpi": cpi,
        "planned_progress": planned_progress,
        "spi": spi,
        "eac": eac,
        "etc": etc,
        "cost_variance": cost_variance,
        "margin": earned_margin,
        "days_elapsed": elapsed_days,
        "planned_days": planned_days,
        "received": received,
        "receivable": receivable,
        "expense_paid": expense_paid,
        "payable": payable,
        "cost_components": cost_components,
        "top_cost_type": top_cost_type,
        "top_cost_value": top_cost_value,
        "health": health,
        "health_score": score,
        "explanation": explanation,
        "actions": actions,
    }


# شرح الدالة _portfolio_insights: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _portfolio_insights(metrics: list[dict[str, Any]], conn) -> dict[str, Any]:
    active = [m for m in metrics if m["status"] == "Active"]
    budget = sum(m["budget"] for m in active)
    cost = sum(m["actual_cost"] for m in active)
    earned = sum(m["earned"] for m in active)
    received = sum(m["received"] for m in active)
    receivable = sum(m["receivable"] for m in active)
    payable = sum(m["payable"] for m in active)
    cpi = _safe_ratio(earned, cost, 1.0 if earned == 0 else 0.0)
    eac = budget / cpi if cpi > 0 else budget
    forecast_margin = earned - cost

    overdue = _f(conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE payment_status='Overdue'"
    ).fetchone()[0])
    open_debt = _f(conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM debt WHERE status='Open'"
    ).fetchone()[0])

    healthy = sum(1 for m in active if m["health"] in {"Healthy", "Complete"})
    watch = sum(1 for m in active if m["health"] == "Watch")
    critical = sum(1 for m in active if m["health"] == "Critical")

    if critical:
        headline = f"{critical} active project(s) need immediate attention."
    elif watch:
        headline = f"{watch} active project(s) should be reviewed this period."
    elif active:
        headline = "The active portfolio is currently within the main control thresholds."
    else:
        headline = "There are no active projects to forecast."

    return {
        "active_projects": len(active),
        "portfolio_budget": budget,
        "portfolio_cost": cost,
        "portfolio_earned": earned,
        "portfolio_received": received,
        "receivable": receivable,
        "payable": payable,
        "portfolio_cpi": cpi,
        "portfolio_eac": eac,
        "portfolio_margin": forecast_margin,
        "overdue_expenses": overdue,
        "open_debt": open_debt,
        "healthy_count": healthy,
        "watch_count": watch,
        "critical_count": critical,
        "headline": headline,
    }


# شرح الدالة smart_analytics: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def smart_analytics(conn=None) -> dict[str, Any]:
    own_connection = conn is None
    conn = conn or get_connection()
    try:
        projects = conn.execute("SELECT * FROM projects ORDER BY project_name").fetchall()
        metrics = [_project_metrics(conn, p) for p in projects]
        active = [m for m in metrics if m["status"] == "Active"]

        risks: list[dict[str, Any]] = []
        for m in active:
            for action in m["actions"]:
                severity = "HIGH" if m["health"] == "Critical" else "MEDIUM" if m["health"] == "Watch" else "LOW"
                risks.append({
                    "severity": severity,
                    "project_name": m["project_name"],
                    "message": action,
                    "cpi": m["cpi"],
                    "spi": m["spi"],
                    "health": m["health"],
                })

        # Highest-priority project actions first, then weakest control score.
        severity_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        risks.sort(key=lambda r: (severity_rank[r["severity"]], r["cpi"], r["spi"]))

        portfolio = _portfolio_insights(metrics, conn)

        data_quality = {
            "projects_without_dates": _scalar_count(conn, "SELECT COUNT(*) FROM projects WHERE start_date IS NULL OR end_date IS NULL"),
            "projects_without_budget": _scalar_count(conn, "SELECT COUNT(*) FROM projects WHERE COALESCE(budget_ht,0)<=0"),
            "expenses_without_project": _scalar_count(conn, "SELECT COUNT(*) FROM expenses WHERE project_id IS NULL OR TRIM(project_id)=''"),
            "unpriced_labor": _scalar_count(conn, "SELECT COUNT(*) FROM labor_allocations WHERE COALESCE(hourly_cost,0)<=0"),
            "unpriced_equipment": _scalar_count(conn, "SELECT COUNT(*) FROM equipment_usage WHERE COALESCE(hourly_cost,0)<=0"),
            "unpriced_materials": _scalar_count(conn, "SELECT COUNT(*) FROM material_movements WHERE COALESCE(unit_cost,0)<=0"),
        }
        quality_issues = sum(data_quality.values())
        confidence = max(0.0, min(100.0, 100.0 - quality_issues * 4.0))

        return {
            "projects": metrics,
            "risks": risks,
            "portfolio": portfolio,
            "portfolio_budget": portfolio["portfolio_budget"],
            "portfolio_cost": portfolio["portfolio_cost"],
            "portfolio_earned": portfolio["portfolio_earned"],
            "portfolio_received": portfolio["portfolio_received"],
            "receivable": portfolio["receivable"],
            "overdue_expenses": portfolio["overdue_expenses"],
            "portfolio_cpi": portfolio["portfolio_cpi"],
            "portfolio_margin": portfolio["portfolio_margin"],
            "data_quality": data_quality,
            "data_confidence": confidence,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    finally:
        if own_connection:
            conn.close()


# شرح الدالة _scalar_count: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _scalar_count(conn, sql: str, params: tuple = ()) -> int:
    try:
        row = conn.execute(sql, params).fetchone()
        return int(row[0] or 0) if row else 0
    except (sqlite3.Error, TypeError, ValueError):
        return 0


# شرح الدالة project_smart_analytics: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def project_smart_analytics(project_id: str) -> dict[str, Any]:
    conn = get_connection()
    try:
        project = conn.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
        return _project_metrics(conn, project) if project else {}
    finally:
        conn.close()


__all__ = ["project_smart_analytics", "smart_analytics"]

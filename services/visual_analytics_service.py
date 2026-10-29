# ============================================================
# شرح الملف: services/visual_analytics_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Read-only chart datasets for BuildOffice Pro visual analytics."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from core.decimal_utils import amount


# شرح الدالة _decimal: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _decimal(value) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return amount(0)


# شرح الدالة expense_overview: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def expense_overview(conn, limit: int = 8) -> dict:
    """Return category, project and monthly expense datasets using Decimal values."""
    categories = conn.execute(
        """SELECT COALESCE(category, 'Uncategorized'), COALESCE(SUM(amount), 0)
           FROM expenses GROUP BY category ORDER BY SUM(amount) DESC LIMIT ?""",
        (max(1, int(limit)),),
    ).fetchall()

    projects = conn.execute(
        """SELECT COALESCE(p.project_name, 'General'), COALESCE(SUM(e.amount), 0)
           FROM expenses e LEFT JOIN projects p ON p.project_id=e.project_id
           GROUP BY e.project_id ORDER BY SUM(e.amount) DESC LIMIT ?""",
        (max(1, int(limit)),),
    ).fetchall()

    monthly_rows = conn.execute(
        """SELECT substr(date, 1, 7), COALESCE(SUM(amount), 0)
           FROM expenses WHERE date IS NOT NULL AND date <> ''
           GROUP BY substr(date, 1, 7) ORDER BY substr(date, 1, 7) DESC LIMIT 12"""
    ).fetchall()

    return {
        "categories": [(str(row[0]), _decimal(row[1])) for row in categories],
        "projects": [(str(row[0]), amount(row[1])) for row in projects],
        "monthly": [(str(row[0]), _decimal(row[1])) for row in reversed(monthly_rows)],
    }


# شرح الدالة workforce_overview: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def workforce_overview(conn, limit: int = 10) -> dict:
    """Return attendance and payroll trend datasets for visual analysis."""
    attendance = conn.execute(
        """SELECT substr(date, 1, 7), COALESCE(SUM(working_hours + overtime_hours), 0)
           FROM attendance WHERE date IS NOT NULL AND date <> ''
           GROUP BY substr(date, 1, 7) ORDER BY substr(date, 1, 7) DESC LIMIT ?""",
        (max(1, int(limit)),),
    ).fetchall()

    payroll = conn.execute(
        """SELECT substr(period, 1, 7), COALESCE(SUM(net_amount), 0)
           FROM payroll_records WHERE period IS NOT NULL AND period <> ''
           GROUP BY substr(period, 1, 7) ORDER BY substr(period, 1, 7) DESC LIMIT ?""",
        (max(1, int(limit)),),
    ).fetchall()

    return {
        "attendance": [(str(row[0]), amount(row[1])) for row in reversed(attendance)],
        "payroll": [(str(row[0]), amount(row[1])) for row in reversed(payroll)],
    }


# شرح الدالة project_cost_exposure: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def project_cost_exposure(conn, limit: int = 8) -> list[tuple[str, Decimal, Decimal]]:
    """Return project budget and recorded expense values for comparison."""
    rows = conn.execute(
        """SELECT p.project_name, COALESCE(p.budget_ht, 0), COALESCE(p.expenses, 0)
           FROM projects p ORDER BY COALESCE(p.budget_ht, 0) DESC LIMIT ?""",
        (max(1, int(limit)),),
    ).fetchall()
    return [(str(row[0]), amount(row[1]), amount(row[2])) for row in rows]


__all__ = ["expense_overview", "project_cost_exposure", "workforce_overview"]

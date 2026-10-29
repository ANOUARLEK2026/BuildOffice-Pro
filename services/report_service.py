# ============================================================
# شرح الملف: services/report_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
"""Read-only reporting services used by the application pages and document generators."""
from __future__ import annotations

from repositories.db import get_connection

from .situation_service import get_project_progress, get_situation


# شرح الدالة project_summary: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def project_summary(project_id: str) -> dict:
    conn = get_connection()
    try:
        project = conn.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
        if not project:
            return {}
        expenses = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project_id=?", (project_id,)
        ).fetchone()[0]
        income = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM project_payments WHERE project_id=?", (project_id,)
        ).fetchone()[0]
        maintenance = conn.execute(
            "SELECT COALESCE(SUM(cost),0) FROM maintenance_records WHERE project_id=?", (project_id,)
        ).fetchone()[0]
        fuel = conn.execute(
            "SELECT COALESCE(SUM(total_cost),0) FROM fuel_records WHERE project_id=?", (project_id,)
        ).fetchone()[0]
        metre = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM metre_items WHERE project_id=?", (project_id,)
        ).fetchone()[0]
        total_cost = float(expenses or 0) + float(maintenance or 0) + float(fuel or 0)
        return dict(project) | {
            "expenses_calculated": expenses,
            "maintenance_cost": maintenance,
            "fuel_cost": fuel,
            "total_project_cost": total_cost,
            "income_received": income,
            "boq_value": metre,
        }
    finally:
        conn.close()


# شرح الدالة project_progress_report: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def project_progress_report(project_id: str) -> dict:
    """Return the canonical progress report used by the Progress page."""
    return get_project_progress(project_id)


# شرح الدالة situation_report: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def situation_report(situation_id: str) -> dict:
    """Return the canonical report for one situation."""
    return get_situation(situation_id)

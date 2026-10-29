# ============================================================
# شرح الملف: services/project_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""خدمات دورة حياة المشاريع وعملياتها المالية."""
from __future__ import annotations

import sqlite3

from repositories.db import get_connection

from .audit_service import audit
from .financial_service import project_financials
from .situation_service import finalize_project as finalize_project_progress


# شرح الدالة project_financial_summary: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def project_financial_summary(project_id: str) -> dict:
    """إرجاع الملخص المالي للمشروع مع ضمان إغلاق الاتصال."""
    conn = get_connection()
    try:
        return project_financials(conn, project_id)
    finally:
        conn.close()


# شرح الدالة project_dependencies: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def project_dependencies(conn, project_id: str) -> dict[str, int]:
    """حساب السجلات المرتبطة بالمشروع قبل السماح بالحذف."""
    tables = {
        "expenses": "SELECT COUNT(*) FROM expenses WHERE project_id=?",
        "metre_items": "SELECT COUNT(*) FROM metre_items WHERE project_id=?",
        "situations": "SELECT COUNT(*) FROM situations WHERE project_id=?",
        "attendance": "SELECT COUNT(*) FROM attendance WHERE project_id=?",
        "payments": "SELECT COUNT(*) FROM project_payments WHERE project_id=?",
        "documents": 'SELECT COUNT(*) FROM "projects documents" WHERE project_id=?',
        "staff_assignments": "SELECT COUNT(*) FROM staff_projects WHERE project_id=?",
    }
    return {
        name: int(conn.execute(sql, (project_id,)).fetchone()[0] or 0)
        for name, sql in tables.items()
    }


# شرح الدالة delete_project: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def delete_project(project_id: str) -> None:
    """حذف مشروع لا يملك أي سجل تاريخي مرتبط به."""
    conn = get_connection()
    try:
        dependencies = project_dependencies(conn, project_id)
        blocking = {name: count for name, count in dependencies.items() if count}
        if blocking:
            details = ", ".join(f"{name}={count}" for name, count in blocking.items())
            raise ValueError(
                "Project has historical records and must be archived instead of deleted: "
                + details
            )

        cursor = conn.execute("DELETE FROM projects WHERE project_id=?", (project_id,))
        # total_changes قيمة تراكمية للاتصال، لذلك لا تصلح للتحقق من هذه العملية.
        if cursor.rowcount != 1:
            raise ValueError("Project not found.")

        audit(
            "Deleted",
            "Project",
            project_id,
            "Clean project deleted without dependent records.",
            conn=conn,
        )
        conn.commit()
    except (sqlite3.Error, ValueError, TypeError, OSError):
        conn.rollback()
        raise
    finally:
        conn.close()


# شرح الدالة archive_project: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def archive_project(project_id: str) -> None:
    """أرشفة المشروع مع الاحتفاظ بسجلاته التاريخية."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT status FROM projects WHERE project_id=?", (project_id,)
        ).fetchone()
        if not row:
            raise ValueError("Project not found.")

        conn.execute(
            "UPDATE projects SET status='Archived',updated_at=CURRENT_TIMESTAMP WHERE project_id=?",
            (project_id,),
        )
        audit(
            "Archived",
            "Project",
            project_id,
            "Project archived; historical records preserved.",
            conn=conn,
        )
        conn.commit()
    except (sqlite3.Error, ValueError, TypeError, OSError):
        conn.rollback()
        raise
    finally:
        conn.close()


# شرح الدالة finalize_project: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def finalize_project(project_id: str, completion_date: str | None = None) -> dict:
    """Finalize a project through the controlled Progress/Situations workflow."""
    return finalize_project_progress(project_id, completion_date)

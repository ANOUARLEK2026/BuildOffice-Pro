# ============================================================
# شرح الملف: services/data_quality_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""تشخيصات قراءة فقط لسلامة قاعدة البيانات."""
from __future__ import annotations

from repositories.db import get_connection


# شرح الدالة database_health: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def database_health() -> dict:
    """فحص سلامة SQLite وإرجاع معلومات تشغيل قاعدة البيانات."""
    conn = get_connection()
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
        table_count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        return {
            "integrity": integrity,
            "foreign_key_errors": len(foreign_keys),
            "tables": int(table_count or 0),
            "journal_mode": conn.execute("PRAGMA journal_mode").fetchone()[0],
            "foreign_keys": int(conn.execute("PRAGMA foreign_keys").fetchone()[0]),
        }
    finally:
        conn.close()


# شرح الدالة diagnostics: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def diagnostics() -> list[dict]:
    """تنفيذ مجموعة فحوصات مستقلة وإرجاع المشكلات التي تحتوي على بيانات."""
    conn = get_connection()
    try:
        checks = [
            (
                "orphan_attendance",
                ("SELECT COUNT(*) FROM attendance a LEFT JOIN staff s "
                "ON s.staff_id=a.staff_id WHERE s.staff_id IS NULL"),
            ),
            (
                "orphan_expense_project",
                ("SELECT COUNT(*) FROM expenses e LEFT JOIN projects p "
                "ON p.project_id=e.project_id WHERE e.project_id IS NOT NULL "
                "AND p.project_id IS NULL"),
            ),
            (
                "orphan_metre_project",
                ("SELECT COUNT(*) FROM metre_items m LEFT JOIN projects p "
                "ON p.project_id=m.project_id WHERE p.project_id IS NULL"),
            ),
            (
                "expense_overpayment",
                ("SELECT COUNT(*) FROM expenses e WHERE "
                "(SELECT COALESCE(SUM(amount),0) FROM expense_payments ep "
                "WHERE ep.expense_id=e.expense_id)>e.amount"),
            ),
            (
                "debt_overpayment",
                ("SELECT COUNT(*) FROM debt d WHERE "
                "(SELECT COALESCE(SUM(amount),0) FROM debt_payments dp "
                "WHERE dp.debt_id=d.debt_id)>d.amount"),
            ),
            (
                "attendance_duplicates",
                ("SELECT COUNT(*) FROM (SELECT staff_id,project_id,date,COUNT(*) n "
                "FROM attendance GROUP BY staff_id,project_id,date HAVING n>1)"),
            ),
            (
                "metre_duplicate_numbers",
                ("SELECT COUNT(*) FROM (SELECT project_id,item_number,COUNT(*) n "
                "FROM metre_items WHERE item_number IS NOT NULL "
                "GROUP BY project_id,item_number HAVING n>1)"),
            ),
            (
                "negative_project_progress",
                "SELECT COUNT(*) FROM situation_items WHERE executed_quantity<0",
            ),
        ]
        issues = []
        for name, sql in checks:
            count = int(conn.execute(sql).fetchone()[0] or 0)
            if count:
                issues.append({"check": name, "count": count})
        return issues
    finally:
        conn.close()


# شرح الدالة table_counts: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def table_counts() -> dict[str, int]:
    """إرجاع عدد السجلات في الجداول المعروفة باستعلام واحد لاكتشاف الجداول."""
    names = [
        "projects",
        "staff",
        "staff_projects",
        "attendance",
        "metre_items",
        "situations",
        "situation_items",
        "expenses",
        "expense_payments",
        "project_payments",
        "debt",
        "debt_payments",
        "vehicles",
        "maintenance_records",
        "fuel_records",
        "payroll_records",
        "documents",
        "audit_log",
        "notifications",
    ]
    conn = get_connection()
    try:
        existing = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        return {
            name: int(
                conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] or 0
            )
            for name in names
            if name in existing
        }
    finally:
        conn.close()

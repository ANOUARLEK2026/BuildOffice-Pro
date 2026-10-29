# ============================================================
# شرح الملف: tests/test_core.py
# هذا الملف جزء من اختبارات السلامة والتكامل وصحة الوظائف.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


# شرح الدالة test_database_migration_is_idempotent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_database_migration_is_idempotent():
    import database.database as db
    with tempfile.TemporaryDirectory() as td:
        old=db.DATABASE_FILE
        db.DATABASE_FILE=Path(td)/"test.db"
        try:
            db.create_database()
            db.create_database()
            conn=db.get_connection()
            assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 22
            conn.execute("INSERT INTO projects(project_id,project_name,budget_ht,budget_ttc) VALUES('P','Test',100,119)")
            conn.execute("INSERT INTO expenses(expense_id,project_id,date,description,amount) VALUES('E','P','2026-09-06','Overrun',150)")
            conn.commit()
            assert conn.execute("SELECT revenue FROM projects WHERE project_id='P'").fetchone()[0] == -50
            conn.close()
        finally:
            db.DATABASE_FILE=old


if __name__ == "__main__":
    test_database_migration_is_idempotent()
    print("core database test: PASS")


# شرح الدالة test_delete_missing_project_is_rejected: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_delete_missing_project_is_rejected():
    """التأكد من أن حذف معرف غير موجود لا يعتبر نجاحًا زائفًا."""
    import database.database as db
    from services.project_service import delete_project

    with tempfile.TemporaryDirectory() as td:
        old = db.DATABASE_FILE
        db.DATABASE_FILE = Path(td) / "test.db"
        try:
            db.create_database()
            try:
                delete_project("MISSING")
            except ValueError as exc:
                assert str(exc) == "Project not found."
            else:
                raise AssertionError("يجب رفض حذف مشروع غير موجود")
        finally:
            db.DATABASE_FILE = old

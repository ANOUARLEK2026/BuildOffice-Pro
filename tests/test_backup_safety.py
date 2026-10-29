# ============================================================
# شرح الملف: tests/test_backup_safety.py
# هذا الملف جزء من اختبارات السلامة والتكامل وصحة الوظائف.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
import pathlib
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


# شرح الدالة test_invalid_restore_never_changes_live_database: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_invalid_restore_never_changes_live_database():
    import database.database as db
    from services.backup_service import restore_backup, validate_backup

    with tempfile.TemporaryDirectory() as td:
        old = db.DATABASE_FILE
        live = pathlib.Path(td) / "live.db"
        bad = pathlib.Path(td) / "bad.db"
        db.DATABASE_FILE = live
        try:
            db.create_database()
            conn = db.get_connection()
            conn.execute("INSERT INTO projects(project_id,project_name) VALUES('p1','Original')")
            conn.commit()
            conn.close()

            bad_conn = sqlite3.connect(bad)
            bad_conn.execute("CREATE TABLE projects(project_id TEXT PRIMARY KEY, project_name TEXT NOT NULL)")
            bad_conn.execute("INSERT INTO projects VALUES('p2','Bad')")
            bad_conn.execute("CREATE TABLE child(project_id TEXT, FOREIGN KEY(project_id) REFERENCES projects(project_id))")
            bad_conn.execute("INSERT INTO child VALUES('missing')")
            bad_conn.commit()
            bad_conn.close()

            assert not validate_backup(bad)
            try:
                restore_backup(bad)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Invalid restore was accepted")

            conn = db.get_connection()
            assert conn.execute("SELECT project_name FROM projects WHERE project_id='p1'").fetchone()[0] == "Original"
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            conn.close()
        finally:
            db.DATABASE_FILE = old

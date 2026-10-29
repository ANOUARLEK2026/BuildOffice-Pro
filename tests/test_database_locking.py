# ============================================================
# شرح الملف: tests/test_database_locking.py
# هذا الملف جزء من اختبارات السلامة والتكامل وصحة الوظائف.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))

# شرح الدالة test_id_generation_inside_active_write_transaction_does_not_self_lock: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_id_generation_inside_active_write_transaction_does_not_self_lock():
    import database.database as db
    from core.id_service import next_child_id, next_sequence_id
    with tempfile.TemporaryDirectory() as td:
        old=db.DATABASE_FILE; db.DATABASE_FILE=Path(td)/'lock.db'
        try:
            db.create_database(); c=db.get_connection(); c.execute('BEGIN IMMEDIATE')
            pid=next_sequence_id(c,'prj',digits=3); c.execute('INSERT INTO projects(project_id,project_name) VALUES(?,?)',(pid,'P'))
            eid=next_child_id(c,'exp',pid,digits=3); c.execute('INSERT INTO expenses(expense_id,project_id,date,description,amount) VALUES(?,?,?,?,?)',(eid,pid,'2026-09-07','x',1))
            c.commit(); c.close()
        finally: db.DATABASE_FILE=old

# شرح الدالة test_failed_transaction_does_not_consume_uncommitted_id: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_failed_transaction_does_not_consume_uncommitted_id():
    import database.database as db
    from core.id_service import next_sequence_id
    with tempfile.TemporaryDirectory() as td:
        old=db.DATABASE_FILE; db.DATABASE_FILE=Path(td)/'rollback.db'
        try:
            db.create_database(); c=db.get_connection(); c.execute('BEGIN IMMEDIATE'); issued=next_sequence_id(c,'prj',digits=3); c.rollback()
            c.execute('BEGIN IMMEDIATE'); issued2=next_sequence_id(c,'prj',digits=3); c.execute('INSERT INTO projects(project_id,project_name) VALUES(?,?)',(issued2,'Committed')); c.commit(); c.close()
            assert issued == issued2
        finally: db.DATABASE_FILE=old

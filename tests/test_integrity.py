# ============================================================
# شرح الملف: tests/test_integrity.py
# هذا الملف جزء من اختبارات السلامة والتكامل وصحة الوظائف.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))


# شرح الدالة setup_db: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def setup_db():
    import database.database as db
    td=tempfile.TemporaryDirectory(); old=db.DATABASE_FILE; db.DATABASE_FILE=Path(td.name)/"test.db"; db.create_database()
    return td, old, db


# شرح الدالة test_expense_payment_reconciliation_and_overpayment: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_expense_payment_reconciliation_and_overpayment():
    td, old, db = setup_db()
    try:
        from core.id_service import next_child_id, next_sequence_id
        from services.financial_service import expense_balance, record_expense_payment
        c=db.get_connection(); pid=next_sequence_id(c,'prj',digits=3); eid=next_child_id(c,'exp',pid,digits=3)
        c.execute("INSERT INTO projects(project_id,project_name,budget_ht,budget_ttc) VALUES(?,?,?,?)",(pid,'P',1000,1190))
        c.execute("INSERT INTO expenses(expense_id,project_id,date,description,amount,payment_status) VALUES(?,?,?,?,?,?)",(eid,pid,'2026-09-01','Test',100,'Unpaid')); c.commit()
        c.close()
        record_expense_payment(next_child_id(None,'pay',eid,digits=6),eid,'2026-09-02',40,'Cash')
        c=db.get_connection(); b=expense_balance(c,eid); assert b['paid']==40 and b['outstanding']==60 and b['status']=='Partial'; c.close()
        try:
            record_expense_payment(next_child_id(None,'pay',eid,digits=6),eid,'2026-09-03',61,'Cash')
            raise AssertionError('overpayment was accepted')
        except ValueError: pass
    finally:
        db.DATABASE_FILE=old; td.cleanup()


# شرح الدالة test_attendance_duplicate_is_rejected: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_attendance_duplicate_is_rejected():
    td, old, db = setup_db()
    try:
        from core.id_service import next_child_id, next_sequence_id
        from services.attendance_service import save_attendance
        c=db.get_connection(); pid=next_sequence_id(c,'prj',digits=3); sid=next_sequence_id(c,'stf',digits=3); a1=next_child_id(c,'att',sid,pid,digits=6); a2=next_child_id(c,'att',sid,pid,digits=6)
        c.execute("INSERT INTO projects(project_id,project_name) VALUES(?,?)",(pid,'P')); c.execute("INSERT INTO staff(staff_id,full_name) VALUES(?,?)",(sid,'Worker')); c.commit();
        save_attendance(a1,sid,pid,'2026-09-07','Present',8,1,conn=c)
        try:
            save_attendance(a2,sid,pid,'2026-09-07','Present',8,0,conn=c)
            raise AssertionError('duplicate was accepted')
        except ValueError: pass
        c.rollback(); c.close()
    finally:
        db.DATABASE_FILE=old; td.cleanup()

# شرح الدالة test_sqlite_backup_round_trip: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_sqlite_backup_round_trip():
    td, old, db = setup_db()
    try:
        from services.backup_service import (
            create_backup,
            restore_backup,
            validate_backup,
        )
        c=db.get_connection(); c.execute("INSERT INTO projects(project_id,project_name) VALUES('prj-001','Backup Test')"); c.commit(); c.close()
        backup=create_backup(td.name); assert backup.exists() and validate_backup(backup)
        target=Path(td.name)/'restored.db'; restore_backup(backup,target)
        import sqlite3
        r=sqlite3.connect(target); assert r.execute("SELECT project_name FROM projects WHERE project_id='prj-001'").fetchone()[0]=='Backup Test'; r.close()
    finally: db.DATABASE_FILE=old; td.cleanup()

# ============================================================
# شرح الملف: tests/test_labor_payroll_reconciliation.py
# هذا الملف جزء من اختبارات السلامة والتكامل وصحة الوظائف.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
import tempfile
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


# شرح الدالة setup_db: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def setup_db():
    import database.database as db
    old=db.DATABASE_FILE
    td=tempfile.TemporaryDirectory()
    db.DATABASE_FILE=Path(td.name)/"test.db"
    db.create_database()
    c=db.get_connection()
    c.execute("INSERT INTO projects(project_id,project_name,budget_ht,budget_ttc) VALUES('P','Project',100000,119000)")
    c.execute("INSERT INTO staff(staff_id,full_name,salary_type,rate,status) VALUES('S','Worker','Hourly',100,'Active')")
    c.commit()
    return db, old, td, c


# شرح الدالة test_site_labor_cannot_exceed_attendance: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_site_labor_cannot_exceed_attendance():
    db, old, td, c = setup_db()
    try:
        from services.attendance_service import save_attendance
        from services.construction_control_service import save_labor_allocation
        save_attendance('A','S',None,'2026-09-10','Present',8,2,conn=c)
        save_labor_allocation('S','P','2026-09-10',5,100,attendance_id='A')
        save_labor_allocation('S','P','2026-09-10',3,100,attendance_id='A')
        try:
            save_labor_allocation('S','P','2026-09-10',1,100,attendance_id='A')
        except ValueError as exc:
            assert 'remaining attendance hours' in str(exc)
        else:
            raise AssertionError('Over-allocation must be rejected')
    finally:
        c.close(); db.DATABASE_FILE=old; td.cleanup()


# شرح الدالة test_payroll_reconciliation_sees_site_labor: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_payroll_reconciliation_sees_site_labor():
    db, old, td, c = setup_db()
    try:
        from services.attendance_service import save_attendance
        from services.construction_control_service import save_labor_allocation
        from services.payroll_service import labor_reconciliation, save_payroll
        save_attendance('A','S',None,'2026-09-10','Present',8,2,conn=c)
        save_labor_allocation('S','P','2026-09-10',8,100,attendance_id='A')
        save_labor_allocation('S','P','2026-09-10',0,100,attendance_id='A', overtime_hours=2)
        rec=labor_reconciliation(c,'S','2026-09')
        assert rec['status']=='Reconciled'
        assert rec['allocated_hours']==8
        assert rec['allocated_overtime']==2
        pid=save_payroll('S','2026-09',800,300,conn=c)
        row=c.execute("SELECT attendance_hours,allocated_hours,reconciliation_status FROM payroll_records WHERE payroll_id=?",(pid,)).fetchone()
        assert tuple(row)==(8,8,'Reconciled')
    finally:
        c.close(); db.DATABASE_FILE=old; td.cleanup()

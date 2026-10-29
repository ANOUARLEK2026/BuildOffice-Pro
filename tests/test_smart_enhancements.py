# ============================================================
# شرح الملف: tests/test_smart_enhancements.py
# هذا الملف جزء من اختبارات السلامة والتكامل وصحة الوظائف.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
import tempfile
from pathlib import Path


# شرح الدالة test_supplementary_modes_and_transition: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_supplementary_modes_and_transition():
    import database.database as db
    from services.supplementary_service import (
        amount_for,
        save_supplementary,
        transition_supplementary,
    )
    old=db.DATABASE_FILE
    with tempfile.TemporaryDirectory() as td:
        db.DATABASE_FILE=Path(td)/'x.db'; db.create_database(); c=db.get_connection(); c.execute("INSERT INTO projects(project_id,project_name,budget_ht) VALUES('P1','P1',100000)"); c.commit(); c.close()
        sid=save_supplementary('P1','Extra concrete','m3',10,2000,None,'Measured')
        assert amount_for({'work_mode':'Measured','quantity':10,'unit_price':2000})==20000
        transition_supplementary(sid,'Submitted'); transition_supplementary(sid,'Approved')
        lid=save_supplementary('P1','Forfait repair',None,None,None,5000,'Lump Sum'); assert amount_for({'work_mode':'Lump Sum','lump_sum_amount':5000})==5000  # noqa: F841
    db.DATABASE_FILE=old

# شرح الدالة test_management_what_if_and_query: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_management_what_if_and_query():
    import database.database as db
    from services.management_intelligence import what_if
    from services.natural_query_service import answer
    old=db.DATABASE_FILE
    with tempfile.TemporaryDirectory() as td:
        db.DATABASE_FILE=Path(td)/'x.db'; db.create_database(); c=db.get_connection(); c.execute("INSERT INTO projects(project_id,project_name,budget_ht,start_date,end_date,status) VALUES('P1','P1',100000,'2026-01-01','2026-12-31','Active')"); c.commit(); c.close()
        r=what_if('P1',10,30,5); assert r['forecast_cost']>=0
        assert 'answer' in answer('what needs attention')
    db.DATABASE_FILE=old

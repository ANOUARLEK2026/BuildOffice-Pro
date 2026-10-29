# ============================================================
# شرح الملف: tests/test_financial_concurrency.py
# هذا الملف جزء من اختبارات السلامة والتكامل وصحة الوظائف.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
import pathlib
import sqlite3
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _setup(kind):
    import database.database as db
    from core.id_service import next_child_id, next_sequence_id

    td = tempfile.TemporaryDirectory()
    old = db.DATABASE_FILE
    db.DATABASE_FILE = pathlib.Path(td.name) / "test.db"
    db.create_database()
    conn = db.get_connection()
    project_id = next_sequence_id(conn, "prj")
    conn.execute(
        "INSERT INTO projects(project_id,project_name,budget_ht,budget_ttc) VALUES(?,?,?,?)",
        (project_id, "Stress", 1000, 1190),
    )
    if kind == "expense":
        item_id = next_child_id(conn, "exp", project_id)
        conn.execute(
            "INSERT INTO expenses(expense_id,project_id,date,description,amount) VALUES(?,?,?,?,?)",
            (item_id, project_id, "2026-09-07", "Stress", 100),
        )
    else:
        item_id = next_child_id(conn, "debt", project_id)
        conn.execute(
            "INSERT INTO debt(debt_id,project_id,lender,date,amount,status) VALUES(?,?,?,?,?,?)",
            (item_id, project_id, "Stress lender", "2026-09-07", 100, "Open"),
        )
    conn.commit()
    conn.close()
    return td, old, db, item_id


def test_concurrent_expense_payments_cannot_overpay():
    from core.id_service import next_child_id
    from services.financial_service import record_expense_payment

    td, old, db, expense_id = _setup("expense")
    try:
        n = 100
        barrier = threading.Barrier(n)
        results = []
        lock = threading.Lock()

        def worker():
            try:
                barrier.wait()
                payment_id = next_child_id(None, "pay", expense_id, digits=6)
                record_expense_payment(payment_id, expense_id, "2026-09-07", 2, "Cash")
                ok = True
            except (ValueError, sqlite3.IntegrityError, sqlite3.OperationalError):
                # الفشل المتوقّع عند محاولة تجاوز المبلغ المتبقّي على المصروف،
                # أو عند تضارب الكتابة المتزامنة في SQLite.
                ok = False
            with lock:
                results.append(ok)

        threads = [threading.Thread(target=worker) for _ in range(n)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        conn = db.get_connection()
        row = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM expense_payments WHERE expense_id=?",
            (expense_id,),
        ).fetchone()
        conn.close()
        assert sum(results) == 50
        assert tuple(row) == (50, 100.0)
    finally:
        db.DATABASE_FILE = old  # type: ignore[attr-defined]
        td.cleanup()


def test_concurrent_debt_payments_cannot_overpay():
    from core.id_service import next_child_id
    from services.financial_service import record_debt_payment

    td, old, db, debt_id = _setup("debt")
    try:
        n = 100
        barrier = threading.Barrier(n)
        results = []
        lock = threading.Lock()

        def worker():
            try:
                barrier.wait()
                payment_id = next_child_id(None, "pay", debt_id, digits=6)
                record_debt_payment(payment_id, debt_id, "2026-09-07", 2, "Cash")
                ok = True
            except (ValueError, sqlite3.IntegrityError, sqlite3.OperationalError):
                # الفشل المتوقّع عند محاولة تجاوز المبلغ المتبقّي على الدين،
                # أو عند تضارب الكتابة المتزامنة في SQLite.
                ok = False
            with lock:
                results.append(ok)

        threads = [threading.Thread(target=worker) for _ in range(n)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        conn = db.get_connection()
        row = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM debt_payments WHERE debt_id=?",
            (debt_id,),
        ).fetchone()
        conn.close()
        assert sum(results) == 50
        assert tuple(row) == (50, 100.0)
    finally:
        db.DATABASE_FILE = old # type: ignore[attr-defined]
        td.cleanup()
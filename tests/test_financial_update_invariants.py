# ============================================================
# شرح الملف: اختبارات ثوابت التحديثات المالية.
# هذه الاختبارات تمنع خفض قيمة المصروف أو الدين عن المبالغ المسددة بالفعل.
# ============================================================
import pathlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _setup():
    import database.database as db

    td = tempfile.TemporaryDirectory()
    old = db.DATABASE_FILE
    setattr(db, "DATABASE_FILE", pathlib.Path(td.name) / "test.db")
    db.create_database()
    conn = db.get_connection()
    conn.execute(
        "INSERT INTO projects(project_id,project_name,budget_ht,budget_ttc) VALUES(?,?,?,?)",
        ("PRJ-001", "Financial test", 1000, 1190),
    )
    conn.execute(
        "INSERT INTO expenses(expense_id,project_id,date,description,amount) VALUES(?,?,?,?,?)",
        ("EXP-001", "PRJ-001", "2026-09-07", "Expense", 100),
    )
    conn.execute(
        "INSERT INTO debt(debt_id,project_id,lender,date,amount,status) VALUES(?,?,?,?,?,?)",
        ("DBT-001", "PRJ-001", "Lender", "2026-09-07", 100, "Open"),
    )
    conn.execute(
        "INSERT INTO expense_payments(payment_id,expense_id,payment_date,amount) VALUES(?,?,?,?)",
        ("PAY-001", "EXP-001", "2026-09-08", 60),
    )
    conn.execute(
        "INSERT INTO debt_payments(payment_id,debt_id,payment_date,amount) VALUES(?,?,?,?)",
        ("PAY-002", "DBT-001", "2026-09-08", 60),
    )
    conn.commit()
    return td, old, db, conn


def test_expense_amount_cannot_be_reduced_below_paid():
    from services.financial_service import validate_expense_amount_update

    td, old, db, conn = _setup()
    try:
        try:
            validate_expense_amount_update(conn, "EXP-001", 50)
        except ValueError as exc:
            assert "already paid" in str(exc)
        else:
            raise AssertionError("Expense update incorrectly allowed an amount below paid total")
        validate_expense_amount_update(conn, "EXP-001", 60)
        validate_expense_amount_update(conn, "EXP-001", 100)
    finally:
        conn.close()
        setattr(db, "DATABASE_FILE", old)
        td.cleanup()


def test_debt_amount_cannot_be_reduced_below_paid():
    from services.financial_service import validate_debt_amount_update

    td, old, db, conn = _setup()
    try:
        try:
            validate_debt_amount_update(conn, "DBT-001", 50)
        except ValueError as exc:
            assert "already paid" in str(exc)
        else:
            raise AssertionError("Debt update incorrectly allowed an amount below paid total")
        validate_debt_amount_update(conn, "DBT-001", 60)
        validate_debt_amount_update(conn, "DBT-001", 100)
    finally:
        conn.close()
        setattr(db, "DATABASE_FILE", old)
        td.cleanup()

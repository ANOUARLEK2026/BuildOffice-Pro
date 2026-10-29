# ============================================================
# شرح الملف: services/financial_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
"""الحسابات المالية القابلة للتدقيق وعمليات الدفع الذرية."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from core.decimal_utils import amount, q2
from repositories.db import get_connection


# شرح الدالة expense_totals: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def expense_totals(conn, project_id=None):
    """إرجاع إجماليات المصروفات والدفعات باستعلام تجميعي واحد."""
    if project_id is None:
        where = ""
        args = ()
    else:
        where = " WHERE e.project_id=?"
        args = (project_id,)

    row = conn.execute(
        f"""
        SELECT
            COALESCE(SUM(e.amount), 0) AS total,
            COALESCE(SUM(COALESCE(p.paid, 0)), 0) AS paid
        FROM expenses e
        LEFT JOIN (
            SELECT expense_id, SUM(amount) AS paid
            FROM expense_payments
            GROUP BY expense_id
        ) p ON p.expense_id = e.expense_id
        {where}
        """,
        args,
    ).fetchone()
    total, paid = amount(row["total"]), amount(row["paid"])
    return {
        "total": q2(total),
        "paid": q2(paid),
        "outstanding": q2(max(total - paid, amount(0))),
    }


# شرح الدالة expense_balance: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def expense_balance(conn, expense_id: str) -> dict:
    row = conn.execute("SELECT amount,due_date FROM expenses WHERE expense_id=?", (expense_id,)).fetchone()
    if not row:
        raise ValueError("Expense not found.")
    total = amount(row["amount"])
    paid = amount(conn.execute("SELECT COALESCE(SUM(amount),0) FROM expense_payments WHERE expense_id=?", (expense_id,)).fetchone()[0])
    outstanding = max(total-paid, amount(0))
    if paid >= total:
        status = "Paid"
    elif paid > 0:
        status = "Partial"
    elif row["due_date"] and str(row["due_date"]) < datetime.now(timezone.utc).date().isoformat():
        status = "Overdue"
    else:
        status = "Unpaid"
    return {"total": q2(total), "paid": q2(paid), "outstanding": q2(outstanding), "status": status}


# شرح الدالة project_financials: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def project_financials(conn, project_id: str) -> dict:
    p = conn.execute("SELECT budget_ht,budget_ttc,tva_percent FROM projects WHERE project_id=?", (project_id,)).fetchone()
    if not p:
        raise ValueError("Project not found.")
    expenses = amount(expense_totals(conn, project_id)["total"])
    income = amount(conn.execute("SELECT COALESCE(SUM(amount),0) FROM project_payments WHERE project_id=?", (project_id,)).fetchone()[0])
    budget = amount(p["budget_ht"])
    return {
        "contract_ht": q2(budget), "contract_ttc": q2(p["budget_ttc"]), "expenses": q2(expenses),
        "income": q2(income), "remaining_budget": q2(budget-expenses), "profit": q2(income-expenses),
        "expense_ratio": float(expenses/budget*100) if budget else 0.0,
        "collection": float(income/budget*100) if budget else 0.0,
        "receivable": q2(max(budget-income, amount(0))),
    }


def validate_expense_amount_update(conn, expense_id: str, new_amount) -> None:
    """Prevent editing an expense below the amount already paid."""
    row = conn.execute(
        "SELECT amount FROM expenses WHERE expense_id=?",
        (expense_id,),
    ).fetchone()
    if not row:
        raise ValueError("Expense not found.")
    total = amount(new_amount)
    if total <= 0:
        raise ValueError("Expense amount must be greater than zero.")
    paid = amount(
        conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM expense_payments WHERE expense_id=?",
            (expense_id,),
        ).fetchone()[0]
    )
    if paid > total:
        raise ValueError("Expense amount cannot be less than the amount already paid.")


def validate_debt_amount_update(conn, debt_id: str, new_amount) -> None:
    """Prevent editing a debt below the amount already paid."""
    row = conn.execute(
        "SELECT amount FROM debt WHERE debt_id=?",
        (debt_id,),
    ).fetchone()
    if not row:
        raise ValueError("Debt not found.")
    total = amount(new_amount)
    if total <= 0:
        raise ValueError("Debt amount must be greater than zero.")
    paid = amount(
        conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM debt_payments WHERE debt_id=?",
            (debt_id,),
        ).fetchone()[0]
    )
    if paid > total:
        raise ValueError("Debt amount cannot be less than the amount already paid.")


# شرح الدالة get_expense_paid_amount: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def get_expense_paid_amount(expense_id, conn=None) -> float:
    """إرجاع مجموع الدفعات المسجلة لمصروف واحد."""
    owns = conn is None
    target = conn or get_connection()
    try:
        row = target.execute(
            "SELECT COALESCE(SUM(amount),0) FROM expense_payments WHERE expense_id=?",
            (expense_id,),
        ).fetchone()
        return float(row[0] or 0)
    finally:
        if owns:
            target.close()


# شرح الدالة get_expense_payment_history: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def get_expense_payment_history(expense_id, conn=None):
    """إرجاع سجل دفعات المصروف مرتبًا زمنيًا."""
    owns = conn is None
    target = conn or get_connection()
    try:
        return target.execute(
            """SELECT payment_id,expense_id,payment_date,amount,payment_method,reference,notes,created_at
               FROM expense_payments
               WHERE expense_id=?
               ORDER BY payment_date ASC, created_at ASC""",
            (expense_id,),
        ).fetchall()
    finally:
        if owns:
            target.close()


# شرح الدالة record_expense_payment: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def record_expense_payment(payment_id, expense_id, payment_date, amount_value, payment_method=None, reference=None, notes=None, conn=None):
    """تسجيل دفعة ضمن عملية ذرية مع رفض القيم السالبة أو المتجاوزة."""
    target = conn or get_connection()
    started = False
    try:
        # التحقق من الدفعة يجمع بين القراءة والكتابة، لذلك يجب حجز قفل الكاتب
        # قبل قراءة المدفوعات الحالية لمنع نجاح دفعتين متزامنتين في تجاوز الرصيد.
        if not target.in_transaction:
            target.execute("BEGIN IMMEDIATE")
            started = True
        row = target.execute("SELECT amount FROM expenses WHERE expense_id=?", (expense_id,)).fetchone()
        if not row:
            raise ValueError("Expense not found.")
        pay = amount(amount_value)
        if pay <= 0:
            raise ValueError("Payment must be greater than zero.")
        paid = amount(target.execute("SELECT COALESCE(SUM(amount),0) FROM expense_payments WHERE expense_id=?", (expense_id,)).fetchone()[0])
        total = amount(row["amount"])
        if paid + pay > total:
            raise ValueError("Payment cannot exceed the outstanding amount.")
        target.execute("""INSERT INTO expense_payments(payment_id,expense_id,payment_date,amount,payment_method,reference,notes)
                         VALUES(?,?,?,?,?,?,?)""", (payment_id, expense_id, payment_date, q2(pay), payment_method, reference, notes))
        target.execute("""UPDATE expenses SET payment_status=CASE
            WHEN (SELECT COALESCE(SUM(amount),0) FROM expense_payments WHERE expense_id=expenses.expense_id)>=amount THEN 'Paid'
            WHEN (SELECT COALESCE(SUM(amount),0) FROM expense_payments WHERE expense_id=expenses.expense_id)>0 THEN 'Partial'
            WHEN due_date IS NOT NULL AND due_date<date('now') THEN 'Overdue' ELSE 'Unpaid' END,
            updated_at=CURRENT_TIMESTAMP WHERE expense_id=?""", (expense_id,))
        if started:
            target.commit()
    except (sqlite3.Error, ValueError, TypeError, OSError):
        if started: target.rollback()
        raise
    finally:
        if conn is None: target.close()


# شرح الدالة record_debt_payment: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def record_debt_payment(payment_id, debt_id, payment_date, amount_value, payment_method=None, reference=None, notes=None, conn=None):
    target = conn or get_connection()
    started = False
    try:
        # تطبيق قاعدة التزامن نفسها المستخدمة في دفعات المصروفات.
        if not target.in_transaction:
            target.execute("BEGIN IMMEDIATE")
            started = True
        row = target.execute("SELECT amount FROM debt WHERE debt_id=?", (debt_id,)).fetchone()
        if not row: raise ValueError("Debt not found.")
        pay = amount(amount_value)
        if pay <= 0: raise ValueError("Payment must be greater than zero.")
        paid = amount(target.execute("SELECT COALESCE(SUM(amount),0) FROM debt_payments WHERE debt_id=?", (debt_id,)).fetchone()[0])
        total = amount(row["amount"])
        if paid + pay > total: raise ValueError("Payment cannot exceed the outstanding debt.")
        target.execute("INSERT INTO debt_payments(payment_id,debt_id,payment_date,amount,payment_method,reference,notes) VALUES(?,?,?,?,?,?,?)",
                       (payment_id,debt_id,payment_date,q2(pay),payment_method,reference,notes))
        if started: target.commit()
    except (sqlite3.Error, ValueError, TypeError, OSError):
        if started: target.rollback()
        raise
    finally:
        if conn is None: target.close()

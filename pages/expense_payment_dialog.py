# ============================================================
# شرح الملف: pages/expense_payment_dialog.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""وحدة حوار متخصصة في المصروفات."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.financial_service import (
    get_expense_paid_amount,
)
from services.settings_service import money_display, qt_date_format
from theme import set_theme_style

from .id_service import next_child_id


# شرح الدالة _record_payment_dialog: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _record_payment_dialog(page, expense_id):

    conn = get_connection()

    try:

        expense = conn.execute(
            """
            SELECT amount
            FROM expenses
            WHERE expense_id = ?
            """,
            (
                expense_id,
            ),
        ).fetchone()

    finally:
        conn.close()

    if not expense:

        page.error(
            "Expense not found."
        )

        return

    total_amount = float(
        expense["amount"]
        or 0
    )

    paid_amount = float(
        get_expense_paid_amount(
            expense_id
        )
        or 0
    )

    outstanding = max(
        0,
        total_amount
        - paid_amount,
    )

    if outstanding <= 0:

        page.error(
            "This expense is already fully paid."
        )

        return

    # -----------------------------------------------------
    # نافذة الحوار
    # -----------------------------------------------------

    d = QDialog(page)

    d.setWindowTitle(
        translate_text("Record Payment")
    )

    d.resize(
        480,
        430,
    )

    form = QFormLayout(d)
    form.setSpacing(13)

    remaining = QLabel(
        money_display(outstanding)
    )

    set_theme_style(remaining, 
        """
        font-size: 18px;
        font-weight: 700;
        color: @danger@;
        """
    )

    payment_date = QDateEdit(
        QDate.currentDate()
    )

    payment_date.setCalendarPopup(
        True
    )

    payment_date.setDisplayFormat(qt_date_format())

    payment_amount = QDoubleSpinBox()

    payment_amount.setRange(
        0.01,
        outstanding,
    )

    payment_amount.setDecimals(
        2
    )

    payment_amount.setValue(
        outstanding
    )

    payment_method = LocalizedComboBox()

    payment_method.addItem(translate_text("Select payment method..."))
    payment_method.addItems(page.PAYMENT_METHODS)

    reference = QLineEdit()

    reference.setPlaceholderText(
        translate_text("Cheque number, transfer reference...")
    )

    notes = QLineEdit()

    notes.setPlaceholderText(
        translate_text("Optional notes...")
    )

    form.addRow(
        translate_text("Remaining"),
        remaining,
    )

    form.addRow(
        translate_text("Payment Date"),
        payment_date,
    )

    form.addRow(
        translate_text("Amount"),
        payment_amount,
    )

    form.addRow(
        translate_text("Payment Method"),
        payment_method,
    )

    form.addRow(
        translate_text("Reference"),
        reference,
    )

    form.addRow(
        translate_text("Notes"),
        notes,
    )

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save
        | QDialogButtonBox.StandardButton.Cancel
    )

# شرح الدالة validate_payment_and_accept: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def validate_payment_and_accept():
        amount_value = payment_amount.value()
        method = payment_method.currentText().strip()
        reference_value = reference.text().strip()

        if not payment_date.date().isValid():
            page.error("Please enter a valid payment date.")
            payment_date.setFocus()
            return

        if amount_value <= 0:
            page.error("Payment amount must be greater than zero.")
            payment_amount.setFocus()
            return

        if amount_value > outstanding:
            page.error("Payment cannot exceed the outstanding amount.")
            payment_amount.setFocus()
            return

        if not method or method == "Select payment method...":
            page.error("Please select a payment method.")
            payment_method.setFocus()
            return

        if method in ("Cheque", "Bank Transfer") and not reference_value:
            page.error(translate_text(f"Please enter the reference for this {method.lower()} payment."))
            reference.setFocus()
            return

        d.accept()

    buttons.accepted.connect(validate_payment_and_accept)

    buttons.rejected.connect(
        d.reject
    )

    form.addRow(
        buttons
    )

    if (
        d.exec()
        != QDialog.DialogCode.Accepted
    ):
        return

    amount_value = (
        payment_amount.value()
    )

    if amount_value <= 0:

        page.error(
            "Payment amount must be greater than zero."
        )

        return

    if amount_value > outstanding:

        page.error(
            "Payment cannot exceed the outstanding amount."
        )

        return

    # -----------------------------------------------------
    # معرّف الدفعة الفريد
    # -----------------------------------------------------

    # -----------------------------------------------------
    # الحفظ
    # -----------------------------------------------------

    conn = get_connection()

    try:
        payment_id = next_child_id(conn, "pay", str(expense_id), digits=6)

        conn.execute(
            """
            INSERT INTO expense_payments (
                payment_id,
                expense_id,
                payment_date,
                amount,
                payment_method,
                reference,
                notes
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                payment_id,
                expense_id,
                payment_date.date().toString(
                    "yyyy-MM-dd"
                ),
                amount_value,
                payment_method.currentText(),
                reference.text().strip()
                or None,
                notes.text().strip()
                or None,
            ),
        )

        conn.execute("""
            UPDATE expenses
            SET payment_status = CASE
                WHEN (SELECT COALESCE(SUM(amount),0) FROM expense_payments
                      WHERE expense_id=expenses.expense_id) >= amount THEN 'Paid'
                WHEN (SELECT COALESCE(SUM(amount),0) FROM expense_payments
                      WHERE expense_id=expenses.expense_id) > 0 THEN 'Partial'
                WHEN due_date IS NOT NULL AND due_date < date('now') THEN 'Overdue'
                ELSE 'Unpaid'
            END,
            updated_at=CURRENT_TIMESTAMP
            WHERE expense_id=?
        """, (expense_id,))
        conn.commit()

    except sqlite3.IntegrityError:

        conn.rollback()

        page.error(
            "Could not record payment. The payment was not saved."
        )

        return

    finally:
        conn.close()

    try:
        from services.accounting_integration import post_expense_payment
        post_expense_payment(payment_id)
    except (sqlite3.Error, TypeError, ValueError) as exc:  
        page.error(translate_text(f"Accounting posting failed: {exc}"))
        return

    # -----------------------------------------------------
    # التحديث
    # -----------------------------------------------------

    page.load()

    page._expense_details(
        expense_id
    ) 

__all__=["_record_payment_dialog"]

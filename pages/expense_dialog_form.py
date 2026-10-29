# ============================================================
# شرح الملف: pages/expense_dialog_form.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""وحدة حوار متخصصة في المصروفات."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.financial_service import (
    get_expense_paid_amount,
    validate_expense_amount_update,
)
from services.settings_service import qt_date_format

from .id_service import next_child_id


# شرح الدالة _expense_dialog: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _expense_dialog(page, expense_id=None):
    existing = None

    # =====================================================
    # تحميل المصروف الحالي
    # =====================================================

    if expense_id:
        conn = get_connection()

        try:
            existing = conn.execute(
                """
                SELECT *
                FROM expenses
                WHERE expense_id = ?
                """,
                (expense_id,),
            ).fetchone()

        finally:
            conn.close()

    title = (
        "Edit Expense"
        if expense_id
        else "Add Expense"
    )

    # =====================================================
    # نافذة الحوار
    # =====================================================

    d = QDialog(page)
    d.setWindowTitle(title)
    d.resize(540, 620)

    form = QFormLayout(d)
    form.setSpacing(12)

    # =====================================================
    # المشروع
    # =====================================================

    project = LocalizedComboBox()

    project.addItem(
        translate_text("General company expense"),
        None,
    )

    conn = get_connection()

    try:
        projects = conn.execute(
            """
            SELECT
                project_id,
                project_name
            FROM projects
            ORDER BY project_name
            """
        ).fetchall()

    finally:
        conn.close()

    for row in projects:
        project.addItem(
            row["project_name"],
            row["project_id"],
        )

    # =====================================================
    # التاريخ
    # =====================================================

    date = QDateEdit(
        QDate.currentDate()
    )

    date.setCalendarPopup(True)
    date.setDisplayFormat(qt_date_format())

    # =====================================================
    # الوصف
    # =====================================================

    desc = QLineEdit()

    desc.setPlaceholderText(
        translate_text("Enter expense description...")
    )

    # =====================================================
    # التصنيف
    # =====================================================

    category = LocalizedComboBox()

    category.setEditable(True)

    category.addItem(
        translate_text("Select category...")
    )

    category.addItems(
        page.CATEGORIES
    )

    # =====================================================
    # نوع المصروف وطريقة احتساب المبلغ
    # =====================================================

    expense_mode = LocalizedComboBox()
    expense_mode.addItems([
        translate_text("Lump Sum"),
        translate_text("Unit-based"),
    ])

    # =====================================================
    # الكمية والوحدة وسعر الوحدة والمبلغ الإجمالي
    # =====================================================

    quantity = QDoubleSpinBox()
    quantity.setRange(0.0001, 1e12)
    quantity.setDecimals(3)
    quantity.setSingleStep(1)

    unit = LocalizedComboBox()
    unit.setEditable(True)
    unit.addItems([
        translate_text("Unit"),
        translate_text("Piece"),
        translate_text("kg"),
        translate_text("ton"),
        translate_text("m"),
        translate_text("m²"),
        translate_text("m³"),
        translate_text("liter"),
        translate_text("hour"),
        translate_text("day"),
        translate_text("trip"),
        translate_text("Lump Sum"),
    ])

    unit_price = QDoubleSpinBox()
    unit_price.setRange(0, 1e15)
    unit_price.setDecimals(2)
    unit_price.setSingleStep(100)

    amount = QDoubleSpinBox()
    amount.setRange(0, 1e15)
    amount.setDecimals(2)
    amount.setSingleStep(100)
    amount.setReadOnly(True)
    amount.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
    amount.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    # In lump-sum mode the user enters the total directly.
    # In unit-based mode the total is always calculated as quantity × unit price.
    def update_expense_mode(*_args):
        is_unit_based = expense_mode.currentText() == translate_text("Unit-based")
        quantity.setEnabled(is_unit_based)
        unit.setEnabled(is_unit_based)
        unit_price.setEnabled(is_unit_based)
        amount.setReadOnly(is_unit_based)
        amount.setButtonSymbols(
            QDoubleSpinBox.ButtonSymbols.NoButtons
            if is_unit_based
            else QDoubleSpinBox.ButtonSymbols.UpDownArrows
        )
        amount.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
            if is_unit_based
            else Qt.FocusPolicy.StrongFocus
        )
        if is_unit_based:
            update_total_amount()

    def update_total_amount(*_args):
        total = round(quantity.value() * unit_price.value(), 2)
        amount.setValue(total)

    expense_mode.currentTextChanged.connect(update_expense_mode)

    # =====================================================
    # طريقة الدفع
    # =====================================================

    payment = LocalizedComboBox()

    payment.setEditable(True)

    payment.addItem(
        translate_text("Select payment method...")
    )

    payment.addItems(
        page.PAYMENT_METHODS
    )

    # مرجع الدفعة الأولية
    payment_reference = QLineEdit()
    payment_reference.setPlaceholderText(
        translate_text("Cheque number, transfer reference...")
    )

    # =====================================================
    # حالة الدفع
    # =====================================================

    payment_status = LocalizedComboBox()

    payment_status.addItems([
        translate_text("Credit"),
        translate_text("Paid"),
        translate_text("Partial Payment"),
    ])

    # مبلغ الدفعة الأولية
    initial_payment = QDoubleSpinBox()

    initial_payment.setRange(
        0,
        1e15,
    )

    initial_payment.setDecimals(2)
    initial_payment.setSingleStep(100)

    initial_payment.setEnabled(False)

    # =====================================================
    # الملاحظات
    # =====================================================

    notes = QLineEdit()

    notes.setPlaceholderText(
        translate_text("Optional notes...")
    )

    # =====================================================
    # البيانات الحالية
    # =====================================================

    if existing:

        project_id = (
            existing["project_id"]
        )

        if project_id:

            index = project.findData(
                project_id
            )

            if index >= 0:
                project.setCurrentIndex(
                    index
                )

        else:
            project.setCurrentIndex(0)

        desc.setText(
            existing["description"]
            or ""
        )

        if existing["date"]:

            date.setDate(
                QDate.fromString(
                    existing["date"],
                    "yyyy-MM-dd",
                )
            )

        existing_category = (
            existing["category"]
            or ""
        )

        if existing_category:

            index = category.findText(
                existing_category
            )

            if index >= 0:

                category.setCurrentIndex(
                    index
                )

            else:

                category.setCurrentText(
                    existing_category
                )

        existing_unit = (existing["unit"] or "").strip()
        is_lump_sum = not existing_unit or existing_unit.lower() == "lump sum"
        expense_mode.setCurrentText(
            translate_text("Lump Sum") if is_lump_sum else translate_text("Unit-based")
        )
        quantity.setValue(float(existing["quantity"] or 1))
        unit.setCurrentText(existing_unit or translate_text("Lump Sum"))
        unit_price.setValue(float(existing["unit_price"] or existing["amount"] or 0))
        amount.setValue(float(existing["amount"] or 0))

        existing_payment = (
            existing["payment_method"]
            or ""
        )

        if existing_payment:

            index = payment.findText(
                existing_payment
            )

            if index >= 0:

                payment.setCurrentIndex(
                    index
                )

            else:

                payment.setCurrentText(
                    existing_payment
                )

        notes.setText(
            existing["notes"]
            or ""
        )

        # -------------------------------------------------
        # حالة دفعات المصروف الحالي
        # -------------------------------------------------

        paid_amount = get_expense_paid_amount(
            expense_id
        )

        total_amount = float(
            existing["amount"]
            or 0
        )

        if paid_amount <= 0:

            payment_status.setCurrentText(
                "Credit"
            )

        elif paid_amount >= total_amount:

            payment_status.setCurrentText(
                "Paid"
            )

        else:

            payment_status.setCurrentText(
                "Partial Payment"
            )

        # حالة الدفع للعرض فقط أثناء التعديل.
        payment_status.setEnabled(False)
        initial_payment.setEnabled(False)

    # =====================================================
    # حساب إجمالي المصروف
    # =====================================================

    quantity.valueChanged.connect(update_total_amount)
    unit_price.valueChanged.connect(update_total_amount)

    # =====================================================
    # سلوك حالة الدفع
    # =====================================================

    # تنفيذ وظيفة update_payment_fields ضمن هذا الجزء من البرنامج.
    def update_payment_fields():

        status = (
            payment_status.currentText()
        )

        if expense_id:
            return

        if status == "Credit":

            payment.setEnabled(False)
            payment_reference.setEnabled(False)
            initial_payment.setEnabled(False)

            payment.setCurrentIndex(0)
            payment_reference.clear()

            initial_payment.setValue(0)

        elif status == "Paid":

            payment.setEnabled(True)
            payment_reference.setEnabled(True)
            initial_payment.setEnabled(False)

            initial_payment.setValue(
                amount.value()
            )

        elif status == "Partial Payment":

            payment.setEnabled(True)
            payment_reference.setEnabled(True)
            initial_payment.setEnabled(True)

            initial_payment.setMaximum(
                amount.value()
            )

            if (
                initial_payment.value()
                > amount.value()
            ):
                initial_payment.setValue(
                    amount.value()
                )

    payment_status.currentTextChanged.connect(
        update_payment_fields
    )

    amount.valueChanged.connect(
        lambda value: (
            initial_payment.setMaximum(value),
            initial_payment.setValue(value)
            if payment_status.currentText() == "Paid"
            else None,
        )
    )

    # =====================================================
    # الحقول
    # =====================================================

    fields = [
        ("Project", project),
        ("Date", date),
        ("Description", desc),
        ("Category", category),
        ("Expense Type", expense_mode),
        ("Quantity", quantity),
        ("Unit", unit),
        ("Unit Price", unit_price),
        ("Total Amount", amount),
        ("Payment Status", payment_status),
        ("Payment Method", payment),
        ("Payment Reference", payment_reference),
        ("Initial Payment", initial_payment),
        ("Notes", notes),
    ]

    for label, widget in fields:

        form.addRow(
            label,
            widget,
        )

    # =====================================================
    # الأزرار
    # =====================================================

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save
        | QDialogButtonBox.StandardButton.Cancel
    )

# شرح الدالة validate_and_accept: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def validate_and_accept():
        # التحقق قبل الإغلاق حتى لا تضيع البيانات المدخلة.
        if not desc.text().strip():
            page.error("Description is required.")
            desc.setFocus()
            return

        if amount.value() <= 0:
            page.error("Amount must be greater than zero.")
            amount.setFocus()
            return

        # التصنيف والملاحظات اختياريان.
        # يتم هنا التحقق فقط من المعلومات الأساسية المطلوبة للحفظ.
        status = payment_status.currentText()
        payment_value = payment.currentText().strip()
        if payment_value == "Select payment method...":
            payment_value = ""

        if not expense_id and status in ("Paid", "Partial Payment"):
            if not payment_value:
                page.error("Please select a payment method.")
                payment.setFocus()
                return

            # يكون المرجع مطلوبًا فقط عند استخدام طريقة دفع قابلة للتتبع.
            if payment_value in ("Cheque", "Bank Transfer") and not payment_reference.text().strip():
                page.error(translate_text(f"Please enter the reference for this {payment_value.lower()} payment."))
                payment_reference.setFocus()
                return

        if not expense_id and status == "Partial Payment":
            if initial_payment.value() <= 0:
                page.error("Initial payment must be greater than zero.")
                initial_payment.setFocus()
                return
            if initial_payment.value() >= amount.value():
                page.error("For Partial Payment, the initial payment must be less than the total amount.")
                initial_payment.setFocus()
                return

        d.accept()

    buttons.accepted.connect(validate_and_accept)

    buttons.rejected.connect(
        d.reject
    )

    form.addRow(buttons)

    # =====================================================
    # الحالة الأولية للواجهة
    # =====================================================

    if not expense_id:
        expense_mode.setCurrentText(translate_text("Lump Sum"))
        quantity.setValue(1)
        unit.setCurrentText(translate_text("Lump Sum"))
        unit_price.setValue(0)
        amount.setValue(0)
    else:
        if existing is None:
            page.error("Expense not found.")
            return
        amount.setValue(float(existing["amount"] or 0))

    update_expense_mode()
    update_payment_fields()

    # =====================================================
    # عرض نافذة الحوار
    # =====================================================

    if (
        d.exec()
        != QDialog.DialogCode.Accepted
    ):
        return

    # =====================================================
    # التحقق
    # =====================================================

    if not desc.text().strip():

        page.error(
            "Description is required."
        )

        return

    if amount.value() <= 0:

        page.error(
            "Amount must be greater than zero."
        )

        return

    category_value = (
        category.currentText().strip()
    )

    if (
        not category_value
        or category_value
        == "Select category..."
    ):
        category_value = None

    payment_value = (
        payment.currentText().strip()
    )

    if (
        not payment_value
        or payment_value
        == "Select payment method..."
    ):
        payment_value = None

    status = (
        payment_status.currentText()
    )

    # =====================================================
    # التحقق من بيانات الدفعة
    # =====================================================

    if not expense_id:

        if status in (
            "Paid",
            "Partial Payment",
        ) and not payment_value:

            page.error(
                "Please select a payment method."
            )

            return

        if status == "Partial Payment":

            if initial_payment.value() <= 0:

                page.error(
                    "Initial payment must be greater than zero."
                )

                return

            if (
                initial_payment.value()
                >= amount.value()
            ):

                page.error(
                    "For Partial Payment, the initial payment "
                    "must be less than the total amount."
                )

                return

    # =====================================================
    # قيم المصروف
    # =====================================================

    is_unit_based = expense_mode.currentText() == translate_text("Unit-based")
    stored_quantity = quantity.value() if is_unit_based else 1.0
    stored_unit = unit.currentText().strip() if is_unit_based else "Lump Sum"
    stored_unit_price = unit_price.value() if is_unit_based else amount.value()

    values = (
        project.currentData(),
        date.date().toString(
            "yyyy-MM-dd"
        ),
        desc.text().strip(),
        category_value,
        amount.value(),
        stored_quantity,
        stored_unit or "Lump Sum",
        stored_unit_price,
        payment_value,
        notes.text().strip()
        or None,
    )

    # =====================================================
    # حفظ المعاملة
    # =====================================================

    conn = get_connection()

    try:

        # =================================================
        # تعديل المصروف
        # =================================================

        if expense_id:
            validate_expense_amount_update(
                conn,
                expense_id,
                amount.value(),
            )

            old_row = conn.execute(
                """
                SELECT project_id
                FROM expenses
                WHERE expense_id = ?
                """,
                (expense_id,),
            ).fetchone()

            new_expense_id = str(
                expense_id
            )

            if (
                old_row
                and old_row["project_id"]
                != values[0]
            ):

                new_expense_id = (
                    page._next_expense_id(
                        conn,
                        values[0],
                    )
                )

            conn.execute(
                """
                UPDATE expenses
                SET
                    expense_id = ?,
                    project_id = ?,
                    date = ?,
                    description = ?,
                    category = ?,
                    amount = ?,
                    quantity = ?,
                    unit = ?,
                    unit_price = ?,
                    payment_method = ?,
                    notes = ?,
                    updated_at =
                        CURRENT_TIMESTAMP
                WHERE expense_id = ?
                """,
                (
                    new_expense_id,
                )
                + values
                + (
                    expense_id,
                ),
            )

        # =================================================
        # إضافة المصروف
        # =================================================

        else:

            new_expense_id = (
                page._next_expense_id(
                    conn,
                    values[0],
                )
            )

            conn.execute(
                """
                INSERT INTO expenses (
                    expense_id,
                    project_id,
                    date,
                    description,
                    category,
                    amount,
                    quantity,
                    unit,
                    unit_price,
                    payment_method,
                    notes
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    new_expense_id,
                )
                + values,
            )

            # =============================================
            # إنشاء الدفعة الأولية
            # =============================================

            if status in (
                "Paid",
                "Partial Payment",
            ):

                if status == "Paid":

                    payment_amount = (
                        amount.value()
                    )

                else:

                    payment_amount = (
                        initial_payment.value()
                    )

                payment_id = next_child_id(conn, "pay", str(new_expense_id), digits=6)

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
                        new_expense_id,
                        date.date().toString(
                            "yyyy-MM-dd"
                        ),
                        payment_amount,
                        payment_value,
                        payment_reference.text().strip() or None,
                        None,
                    ),
                )

        # إعادة حساب حالة الدفع المحفوظة اعتمادًا على سجل الدفعات.
        # لا يتم اعتبار قيمة الواجهة مصدر الحقيقة.
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
        """, (new_expense_id,))

        # =================================================
        # تثبيت المعاملة
        # =================================================

        conn.commit()

    except sqlite3.IntegrityError as exc:

        conn.rollback()

        page.error(
            f"Could not save expense:\n\n{exc}"
        )

        return

    except (sqlite3.Error, TypeError, ValueError) as exc:

        conn.rollback()

        page.error(
            f"Unexpected error:\n\n{exc}"
        )

        return

    finally:

        conn.close()

    # =====================================================
    # تحديث الصفحة
    # =====================================================

    page.load()

__all__=["_expense_dialog"]

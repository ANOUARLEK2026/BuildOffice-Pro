# ============================================================
# شرح الملف: pages/expense_details_dialog.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""وحدة حوار متخصصة في المصروفات."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.i18n import translate_text
from repositories.db import get_connection
from services.financial_service import (
    get_expense_paid_amount,
    get_expense_payment_history,
)
from services.settings_service import money_display
from theme import set_theme_style


# شرح الدالة _expense_details: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _expense_details(page, expense_id):

    conn = get_connection()

    try:

        expense = conn.execute(
            """
            SELECT *
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

    if paid_amount <= 0:
        status = "UNPAID"

    elif outstanding <= 0:
        status = "PAID"

    else:
        status = "PARTIAL"

    # -----------------------------------------------------
    # نافذة الحوار
    # -----------------------------------------------------

    d = QDialog(page)

    d.setWindowTitle(
        translate_text(f"Expense Details - {expense_id}")
    )

    d.resize(
        720,
        680,
    )

    layout = QVBoxLayout(d)
    layout.setSpacing(14)

    # -----------------------------------------------------
    # الترويسة
    # -----------------------------------------------------

    title = QLabel(
        translate_text(f"Expense {expense_id}")
    )

    set_theme_style(title, 
        """
        font-size: 20px;
        font-weight: 700;
        color: @text_primary@;
        """
    )

    layout.addWidget(title)

    # -----------------------------------------------------
    # الملخص المالي
    # -----------------------------------------------------

    summary = QGridLayout()
    summary.setSpacing(10)

    total_card = page._detail_card(
        "TOTAL",
        money_display(total_amount),
    )

    paid_card = page._detail_card(
        "PAID",
        money_display(paid_amount),
    )

    remaining_card = page._detail_card(
        "OUTSTANDING",
        money_display(outstanding),
    )

    status_card = page._detail_card(
        "STATUS",
        status,
    )

    summary.addWidget(
        total_card,
        0,
        0,
    )

    summary.addWidget(
        paid_card,
        0,
        1,
    )

    summary.addWidget(
        remaining_card,
        0,
        2,
    )

    summary.addWidget(
        status_card,
        0,
        3,
    )

    layout.addLayout(summary)

    # -----------------------------------------------------
    # التقدم
    # -----------------------------------------------------

    progress = QProgressBar()
    progress.setRange(
        0,
        100,
    )

    if total_amount > 0:

        percentage = int(
            min(
                100,
                (
                    paid_amount
                    / total_amount
                )
                * 100,
            )
        )

    else:
        percentage = 0

    progress.setValue(
        percentage
    )

    progress.setFormat(
        translate_text(f"{percentage}% paid")
    )

    set_theme_style(progress, 
        """
        QProgressBar {
            border: none;
            background: @surface_alt@;
            border-radius: 6px;
            height: 14px;
            text-align: center;
        }

        QProgressBar::chunk {
            background: @kpi.positive@;
            border-radius: 6px;
        }
        """
    )

    layout.addWidget(progress)

    # -----------------------------------------------------
    # بيانات المصروف
    # -----------------------------------------------------

    info = QFormLayout()
    info.setSpacing(8)

    info.addRow(
        translate_text("Project"),
        QLabel(
            str(
                expense["project_id"]
                or "General company expense"
            )
        ),
    )

    info.addRow(
        translate_text("Date"),
        QLabel(
            str(
                expense["date"]
            )
        ),
    )

    info.addRow(
        translate_text("Description"),
        QLabel(
            str(
                expense["description"]
            )
        ),
    )

    info.addRow(
        translate_text("Category"),
        QLabel(
            str(
                expense["category"]
                or "-"
            )
        ),
    )

    info.addRow(
        translate_text("Payment Method"),
        QLabel(
            str(
                expense["payment_method"]
                or "-"
            )
        ),
    )

    layout.addLayout(info)

    # -----------------------------------------------------
    # سجل الدفعات
    # -----------------------------------------------------

    history_title = QLabel(
        translate_text("Payment History")
    )

    set_theme_style(history_title, 
        """
        font-size: 15px;
        font-weight: 700;
        color: @text_primary@;
        """
    )

    layout.addWidget(
        history_title
    )

    history = (
        get_expense_payment_history(
            expense_id
        )
    )

    payment_table = QTableWidget(
        len(history),
        5,
    )

    payment_table.setHorizontalHeaderLabels(
        [
            translate_text("Date"),
            translate_text("Amount"),
            translate_text("Payment Method"),
            translate_text("Reference"),
            translate_text("Notes"),
        ]
    )

    payment_table.setEditTriggers(
        QAbstractItemView.EditTrigger.NoEditTriggers
    )

    payment_table.setSelectionBehavior(
        QAbstractItemView.SelectionBehavior.SelectRows
    )

    payment_table.setAlternatingRowColors(
        True
    )

    payment_table.setShowGrid(
        False
    )

    payment_table.verticalHeader().setVisible(
        False
    )

    payment_table.horizontalHeader().setStretchLastSection(
        True
    )

    for i, row in enumerate(history):

        values = [
            row["payment_date"],
            money_display(row["amount"]),
            row["payment_method"] or "-",
            row["reference"] or "-",
            row["notes"] or "-",
        ]

        for j, value in enumerate(values):

            item = QTableWidgetItem(
                str(value)
            )

            if j in (0, 1):
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )

            payment_table.setItem(
                i,
                j,
                item,
            )

    layout.addWidget(
        payment_table,
        1,
    )

    # -----------------------------------------------------
    # الأزرار
    # -----------------------------------------------------

    buttons = QHBoxLayout()

    payment_button = QPushButton(
        translate_text("Record Payment")
    )

    payment_button.setObjectName(
        "primaryButton"
    )

    edit_button = QPushButton(
        translate_text("Edit Expense")
    )

    close_button = QPushButton(
        translate_text("Close")
    )

    buttons.addWidget(
        payment_button
    )

    buttons.addWidget(
        edit_button
    )

    buttons.addStretch()

    buttons.addWidget(
        close_button
    )

    layout.addLayout(
        buttons
    )

    # -----------------------------------------------------
    # الإجراءات
    # -----------------------------------------------------

    # تنفيذ وظيفة record_payment ضمن هذا الجزء من البرنامج.
    def record_payment():

        d.close()

        page._record_payment_dialog(
            expense_id
        )

    # تعديل السجل المحدد وفتح بياناته للتحرير.
    def edit_expense():

        d.close()

        page._expense_dialog(
            expense_id
        )

    payment_button.clicked.connect(
        record_payment
    )

    edit_button.clicked.connect(
        edit_expense
    )

    close_button.clicked.connect(
        d.reject
    )

    d.exec()

__all__=["_expense_details"]

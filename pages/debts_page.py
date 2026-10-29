# ============================================================
# شرح الملف: pages/debts_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
from __future__ import annotations

import sqlite3
from typing import cast

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.financial_service import record_debt_payment, validate_debt_amount_update
from services.settings_service import qt_date_format

from .base_page import BasePage, money
from .id_service import next_child_id, next_sequence_id


# شرح الصنف DebtsPage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class DebtsPage(BasePage):
    """Debt register with real payment tracking and outstanding balances."""

    METHODS = ("Cash", "Bank Transfer", "Cheque", "Bank Card", "Other")

    def __init__(self):
        super().__init__("Debts", "Track company liabilities, payments and outstanding amounts")
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(translate_text("Search creditor, project or notes…"))
        self.status = LocalizedComboBox()
        self.status.addItems([translate_text("All statuses"), translate_text("Open"), translate_text("Partial"), translate_text("Paid"), translate_text("Overdue")])
        self.search.textChanged.connect(self.load)
        self.status.currentIndexChanged.connect(self.load)
        bar.addWidget(self.search, 1)
        bar.addWidget(self.status)
        for text, slot, obj in [
            ("Refresh", self.load, None),
            ("+ Add debt", self.add, "primaryButton"),
            ("Edit", self.edit, None),
            ("Add payment", self.add_payment, "primaryButton"),
            ("Delete", self.delete, "dangerButton"),
        ]:
            b = QPushButton(translate_text(text)); b.clicked.connect(slot); b.setObjectName(obj or ""); bar.addWidget(b)
        self.body.addLayout(bar)

        cards = QHBoxLayout(); self.cards = {}
        for title in ["Total debt", "Outstanding", "Paid"]:
            c = QFrame(); c.setObjectName("card"); l = QVBoxLayout(c)
            a = QLabel(translate_text(title)); a.setObjectName("cardTitle")
            v = QLabel("0.00"); v.setObjectName("cardValue")
            l.addWidget(a); l.addWidget(v); self.cards[title] = v; cards.addWidget(c)
        self.body.addLayout(cards)

        frame, lay = self.panel()
        layout = cast(QVBoxLayout, lay)
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            translate_text("ID"), translate_text("Project"), translate_text("Creditor"), translate_text("Date"), translate_text("Due date"), translate_text("Amount"),
            translate_text("Paid"), translate_text("Outstanding"), translate_text("Status"), translate_text("Notes")
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)
        self.body.addWidget(frame)
        self.load()

# شرح الدالة selected_id: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def selected_id(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return str(item.text()).strip() if item is not None else None

# شرح الدالة load: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def load(self):
        conn = get_connection()
        try:
            q = """SELECT d.debt_id, COALESCE(p.project_name,'No project') project_name,
                           d.lender, d.date, d.due_date, d.amount,
                           COALESCE((SELECT SUM(dp.amount) FROM debt_payments dp WHERE dp.debt_id=d.debt_id),0) paid,
                           d.status, d.notes
                    FROM debt d LEFT JOIN projects p ON p.project_id=d.project_id WHERE 1=1"""
            args = []
            term = self.search.text().strip()
            if term:
                q += " AND (d.lender LIKE ? OR COALESCE(d.notes,'') LIKE ? OR COALESCE(p.project_name,'') LIKE ?)"
                args += [f"%{term}%"] * 3
            st = self.status.currentText()
            if st != "All statuses": q += " AND d.status=?"; args.append(st)
            rows = conn.execute(q + " ORDER BY d.date DESC,d.debt_id DESC", args).fetchall()
            self.table.setRowCount(len(rows))
            total = outstanding = paid_total = 0.0
            for i, r in enumerate(rows):
                amount = float(r['amount'] or 0); paid = float(r['paid'] or 0); out = max(0.0, amount-paid)
                total += amount; paid_total += min(amount, paid); outstanding += out
                vals = [r['debt_id'], r['project_name'], r['lender'], r['date'], r['due_date'] or '-',
                        money(amount), money(paid), money(out), r['status'], r['notes'] or '-']
                for j, v in enumerate(vals): self.table.setItem(i, j, QTableWidgetItem(str(v)))
            self.cards['Total debt'].setText(money(total))
            self.cards['Outstanding'].setText(money(outstanding))
            self.cards['Paid'].setText(money(paid_total))
        finally:
            conn.close()

# شرح الدالة add: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add(self): self.dialog()

# شرح الدالة edit: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def edit(self):
        did = self.selected_id()
        if did is None: self.error("Select a debt first."); return
        self.dialog(did)

# شرح الدالة dialog: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def dialog(self, did=None):
        conn = get_connection()
        try:
            existing = conn.execute("SELECT * FROM debt WHERE debt_id=?", (did,)).fetchone() if did else None
            projects = conn.execute("SELECT project_id,project_name FROM projects ORDER BY project_name").fetchall()
        finally: conn.close()
        d = QDialog(self); d.setWindowTitle(translate_text("Edit debt" if existing else "Add debt")); d.resize(520, 420); f = QFormLayout(d)
        project = LocalizedComboBox(); project.addItem(translate_text("No project"), None)
        for p in projects: project.addItem(p['project_name'], p['project_id'])
        lender = QLineEdit(); date = QDateEdit(QDate.currentDate()); date.setCalendarPopup(True); date.setDisplayFormat(qt_date_format())
        due = QDateEdit(QDate.currentDate()); due.setCalendarPopup(True); due.setDisplayFormat(qt_date_format()); due.setSpecialValueText("No due date"); due.setMinimumDate(QDate(2000,1,1))
        amount = QDoubleSpinBox(); amount.setRange(0, 1e15); amount.setDecimals(2)
        status = LocalizedComboBox(); status.addItems([translate_text("Open"), translate_text("Partial"), translate_text("Paid"), translate_text("Overdue")]); notes = QPlainTextEdit()
        for label, widget in [("Project",project),("Creditor",lender),("Date",date),("Due date",due),("Amount",amount),("Status",status),("Notes",notes)]: f.addRow(translate_text(label), widget)
        if existing:
            project.setCurrentIndex(max(0, project.findData(existing['project_id'])))
            lender.setText(existing['lender'] or '')
            if existing['date']: date.setDate(QDate.fromString(existing['date'], 'yyyy-MM-dd'))
            if existing['due_date']: due.setDate(QDate.fromString(existing['due_date'], 'yyyy-MM-dd'))
            else: due.setSpecialValueText("No due date")
            amount.setValue(float(existing['amount'] or 0)); status.setCurrentText(existing['status'] or 'Open'); notes.setPlainText(existing['notes'] or '')
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); f.addRow(bb)
        if d.exec() != QDialog.DialogCode.Accepted: return
        if not lender.text().strip(): self.error("Creditor is required."); return
        due_text = None if due.text() in ("", "No due date") else due.date().toString("yyyy-MM-dd")
        vals = (project.currentData(), lender.text().strip(), date.date().toString("yyyy-MM-dd"), due_text, amount.value(), notes.toPlainText().strip() or None)
        conn = get_connection()
        try:
            if existing:
                debt_id = cast(str, did)
                validate_debt_amount_update(conn, debt_id, amount.value())
                paid = float(conn.execute("SELECT COALESCE(SUM(amount),0) FROM debt_payments WHERE debt_id=?", (debt_id,)).fetchone()[0] or 0)
                new_status = "Paid" if paid >= amount.value() else ("Overdue" if due_text and due_text < date.date().toString("yyyy-MM-dd") else ("Partial" if paid > 0 else "Open"))
                conn.execute("UPDATE debt SET project_id=?,lender=?,date=?,due_date=?,amount=?,status=?,notes=? WHERE debt_id=?", vals[:-1] + (new_status, vals[-1], debt_id))
            else:
                did = next_sequence_id(conn, "dbt", digits=3)
                new_status = "Overdue" if due_text and due_text < date.date().toString("yyyy-MM-dd") else "Open"
                conn.execute("INSERT INTO debt(debt_id,project_id,lender,date,due_date,amount,status,notes) VALUES(?,?,?,?,?,?,?,?)", (did,) + vals[:-1] + (new_status, vals[-1]))
            conn.commit()

        except (sqlite3.IntegrityError, ValueError) as exc:
            conn.rollback(); self.error(str(exc) if isinstance(exc, ValueError) else "Could not save the debt record.")
        finally: conn.close()
        self.load()

# شرح الدالة add_payment: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_payment(self):
        did = self.selected_id()
        if did is None: self.error("Select a debt first."); return
        conn = get_connection()
        try:
            debt = conn.execute("SELECT debt_id,amount FROM debt WHERE debt_id=?", (did,)).fetchone()
            paid = conn.execute("SELECT COALESCE(SUM(amount),0) FROM debt_payments WHERE debt_id=?", (did,)).fetchone()[0]
        finally: conn.close()
        outstanding = max(0.0, float(debt['amount']) - float(paid or 0))
        if outstanding <= 0: self.error("This debt is already fully paid."); return
        d = QDialog(self); d.setWindowTitle(translate_text(f"Payment for debt #{did}")); f = QFormLayout(d)
        date = QDateEdit(QDate.currentDate()); date.setCalendarPopup(True); date.setDisplayFormat(qt_date_format())
        amount = QDoubleSpinBox(); amount.setRange(0.01, outstanding); amount.setDecimals(2); amount.setValue(outstanding)
        method = LocalizedComboBox(); method.addItems(self.METHODS); ref = QLineEdit(); notes = QPlainTextEdit()
        f.addRow(translate_text("Payment date"), date); f.addRow(translate_text("Outstanding"), QLabel(money(outstanding))); f.addRow(translate_text("Amount"), amount); f.addRow(translate_text("Payment method"), method); f.addRow(translate_text("Reference"), ref); f.addRow(translate_text("Notes"), notes)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); f.addRow(bb)
        if d.exec() != QDialog.DialogCode.Accepted: return
        conn = get_connection()
        try:
            payment_id = next_child_id(conn, "pay", str(did), digits=6)
            record_debt_payment(
                payment_id,
                did,
                date.date().toString("yyyy-MM-dd"),
                amount.value(),
                method.currentText(),
                ref.text().strip() or None,
                notes.toPlainText().strip() or None,
                conn=conn,
            )
            from services.accounting_integration import post_debt_payment

            post_debt_payment(payment_id)
            conn.commit()

        except (sqlite3.IntegrityError, ValueError) as exc:
            conn.rollback()
            self.error(
                translate_text(
                    f"The payment could not be recorded.\n\n{exc}"
                )
            )
        finally:
            conn.close()
# شرح الدالة delete: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def delete(self):
        did = self.selected_id()
        if did is None: self.error("Select a debt first."); return
        if not self.confirm(translate_text(f"Delete debt #{did} and its recorded payments? This changes financial history."), translate_text("Delete debt")): return
        conn = get_connection()
        try:
            conn.execute("DELETE FROM debt WHERE debt_id=?", (did,)); conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback(); self.error("The debt could not be deleted because another record depends on it.")
        finally: conn.close()
        self.load()

# ============================================================
# شرح الملف: pages/income_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
from __future__ import annotations

import sqlite3

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.audit_service import audit

from .base_page import BasePage, money
from .id_service import next_sequence_id


# شرح الصنف IncomePage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class IncomePage(BasePage):
    """Project/client receipts. One project may have many receipts."""
    METHODS = ("Cash", "Bank Transfer", "Cheque", "Bank Card", "Other")

    def __init__(self):
        super().__init__("Income / Payments", "Client receipts and project collection control")
        bar = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText(translate_text("Search project, reference or payment ID…"))
        self.project = LocalizedComboBox(); self.project.addItem(translate_text("All Projects"), "__ALL__")
        self.status = LocalizedComboBox(); self.status.addItems([translate_text("All"), translate_text("Received"), translate_text("Receivable")])
        self.search.textChanged.connect(self.load); self.project.currentIndexChanged.connect(self.load)
        for text, slot, obj in [("+ Add receipt", self.add, "primaryButton"), ("Delete", self.delete, "dangerButton"), ("Refresh", self.load, None)]:
            b=QPushButton(translate_text(text)); b.clicked.connect(slot); b.setObjectName(obj or ""); bar.addWidget(b)
        bar.insertWidget(0,self.search,1); bar.insertWidget(1,self.project); bar.insertWidget(2,self.status)
        self.body.addLayout(bar)
        frame, lay = self.panel()
        self.summary=QLabel(); self.summary.setObjectName("pageSubtitle"); lay.addWidget(self.summary)
        self.table=QTableWidget(0,8)
        self.table.setHorizontalHeaderLabels([translate_text("ID"),translate_text("Project"),translate_text("Date"),translate_text("Amount"),translate_text("Method"),translate_text("Reference"),translate_text("Notes"),translate_text("Created")])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(lambda *_: self.add())
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table,1); self.body.addWidget(frame)
        self._load_projects(); self.load()

# شرح الدالة _load_projects: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _load_projects(self):
        conn=get_connection()
        try:
            for r in conn.execute("SELECT project_id,project_name FROM projects ORDER BY project_name"):
                self.project.addItem(r["project_name"],r["project_id"])
        finally: conn.close()

# شرح الدالة load: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def load(self):
        if not hasattr(self,"table"): return
        conn=get_connection()
        try:
            sql="""SELECT pp.payment_id,p.project_name,pp.date,pp.amount,pp.payment_method,
                          pp.reference,pp.notes,pp.created_at
                   FROM project_payments pp JOIN projects p ON p.project_id=pp.project_id WHERE 1=1"""
            args=[]
            if self.project.currentData() and self.project.currentData()!="__ALL__":
                sql+=" AND pp.project_id=?"; args.append(self.project.currentData())
            q=self.search.text().strip()
            if q:
                sql+=" AND (pp.payment_id LIKE ? OR p.project_name LIKE ? OR COALESCE(pp.reference,'') LIKE ?)"
                args += [f"%{q}%"]*3
            rows=conn.execute(sql+" ORDER BY pp.date DESC, pp.created_at DESC",args).fetchall()
            self.table.setRowCount(len(rows))
            total=sum(float(r["amount"] or 0) for r in rows)
            for i,r in enumerate(rows):
                vals=[r["payment_id"],r["project_name"],r["date"],money(r["amount"]),r["payment_method"] or "-",r["reference"] or "-",r["notes"] or "-",r["created_at"]]
                for j,v in enumerate(vals): self.table.setItem(i,j,QTableWidgetItem(str(v)))
            all_received=conn.execute("SELECT COALESCE(SUM(amount),0) FROM project_payments").fetchone()[0]
            contract=conn.execute("SELECT COALESCE(SUM(budget_ht),0) FROM projects").fetchone()[0]
            self.summary.setText(translate_text(f"Showing {len(rows)} receipts • Current view: {money(total)} • Total received: {money(all_received)} • Contract HT: {money(contract)}"))
        finally: conn.close()

# شرح الدالة add: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add(self):
        conn=get_connection()
        try: projects=conn.execute("SELECT project_id,project_name,budget_ht FROM projects ORDER BY project_name").fetchall()
        finally: conn.close()
        if not projects: self.error("Create a project before recording income."); return
        d=QDialog(self); d.setWindowTitle(translate_text("Add project receipt")); f=QFormLayout(d)
        p=LocalizedComboBox(); [p.addItem(x["project_name"],x["project_id"]) for x in projects]
        date=QDateEdit(QDate.currentDate()); date.setCalendarPopup(True); amount=QDoubleSpinBox(); amount.setRange(.01,1e15); amount.setDecimals(2)
        method=LocalizedComboBox(); method.addItems(self.METHODS); ref=QLineEdit(); notes=QPlainTextEdit()
        for l,w in [("Project",p),("Date",date),("Amount",amount),("Payment method",method),("Reference",ref),("Notes",notes)]: f.addRow(translate_text(l),w)
        bb=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); f.addRow(bb)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        pid=p.currentData()
        conn=get_connection()
        try:
            pidcode = next_sequence_id(conn, "incm", digits=3)
            conn.execute("""INSERT INTO project_payments(payment_id,project_id,date,amount,payment_method,reference,notes)
                            VALUES(?,?,?,?,?,?,?)""",(pidcode,pid,date.date().toString("yyyy-MM-dd"),amount.value(),method.currentText(),ref.text().strip() or None,notes.toPlainText().strip() or None))
            conn.commit()
            audit("Created","Project Payment",pidcode,f"Receipt recorded for project {pid}.")
            from services.accounting_integration import post_project_payment
            post_project_payment(pidcode)
        except sqlite3.IntegrityError: conn.rollback(); self.error("Could not save the receipt. Check the project and amount."); return
        finally: conn.close()
        self.load()

# شرح الدالة delete: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def delete(self):
        row=self.table.currentRow()
        if row<0: self.error("Select a receipt first."); return
        item=self.table.item(row,0)
        if item is None: self.error("Select a receipt first."); return
        pid=item.text()
        if not self.confirm(translate_text(f"Delete receipt {pid}? This changes the project's received amount."),translate_text("Delete receipt")): return
        conn=get_connection()
        try:
            conn.execute("DELETE FROM project_payments WHERE payment_id=?",(pid,)); conn.commit(); audit("Deleted","Project Payment",pid,"Receipt deleted.")
        except sqlite3.IntegrityError: conn.rollback(); self.error("The receipt could not be deleted."); return
        finally: conn.close()
        self.load()

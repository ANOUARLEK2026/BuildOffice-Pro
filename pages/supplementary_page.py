# ============================================================
# شرح الملف: pages/supplementary_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Supplementary works management page."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.supplementary_service import (
    amount_for,
    list_supplementary,
    save_supplementary,
    transition_supplementary,
)

from .base_page import BasePage, money


# شرح الصنف SupplementaryPage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class SupplementaryPage(BasePage):
    def __init__(self):
        super().__init__("Supplementary Works","Additional work outside the original BOQ contract")
        self._build(); self.refresh_projects()
# شرح الدالة _build: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build(self):
        bar=QHBoxLayout(); bar.addWidget(QLabel(translate_text("Project"))); self.project=LocalizedComboBox(); self.project.currentIndexChanged.connect(self.refresh); bar.addWidget(self.project,1)
        add=QPushButton(translate_text("+ Add supplementary work")); add.setObjectName("primaryButton"); add.clicked.connect(self.add_work); bar.addWidget(add); self.body.addLayout(bar)
        self.table=QTableWidget(0,9); self.table.setHorizontalHeaderLabels([translate_text(x) for x in ["No.","Description","Mode","Unit","Quantity","Unit Price","Lump Sum","Amount","Status"]]); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.body.addWidget(self.table,1)
        actions=QHBoxLayout(); self.next=QPushButton(translate_text("Advance status")); self.next.clicked.connect(self.advance); actions.addWidget(self.next); actions.addStretch(); self.body.addLayout(actions)
# شرح الدالة refresh_projects: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def refresh_projects(self):
        cur=self.project.currentData(); self.project.blockSignals(True); self.project.clear(); self.project.addItem(translate_text("Select project"),""); conn=get_connection()
        try:
            for r in conn.execute("SELECT project_id,project_name FROM projects ORDER BY project_name").fetchall(): self.project.addItem(r["project_name"],r["project_id"])
        finally: conn.close()
        if cur: self.project.setCurrentIndex(max(0,self.project.findData(cur)))
        self.project.blockSignals(False); self.refresh()
# شرح الدالة refresh: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def refresh(self):
        pid=self.project.currentData(); self.table.setRowCount(0)
        if not pid:return
        rows=list_supplementary(pid); self.table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            vals=[f"SW-{r['work_number']:03d}",r['description'],r['work_mode'],r.get('unit') or '',self._fmt(r.get('quantity')),self._fmt(r.get('unit_price')),self._fmt(r.get('lump_sum_amount')),money(amount_for(r) or 0) if amount_for(r) is not None else translate_text("Pending valuation"),r['status']]
            for c,v in enumerate(vals):
                it=QTableWidgetItem(str(v)); it.setTextAlignment(Qt.AlignmentFlag.AlignCenter); it.setData(Qt.ItemDataRole.UserRole,r['supplementary_id']); self.table.setItem(i,c,it)
# شرح الدالة _fmt: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _fmt(v): return "" if v is None else f"{float(v):,.3f}"
# شرح الدالة add_work: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_work(self):
        pid=self.project.currentData()
        if not pid:return
        dlg=QInputDialog(self); dlg.setWindowTitle(translate_text("Supplementary Work"));
        # Use a compact sequential form through standard dialogs to avoid a new dependency.
        desc,ok=QInputDialog.getText(self,translate_text("Description"),translate_text("Description:"));
        if not ok or not desc.strip():return
        mode,ok=QInputDialog.getItem(self,translate_text("Work mode"),translate_text("Work mode:"),["Measured","Lump Sum","Pending"],0,False)
        if not ok:return
        unit=qty=price=lump=None
        if mode=="Measured":
            unit,ok=QInputDialog.getText(self,translate_text("Unit"),translate_text("Unit:"));
            if not ok:return
            qty,ok=QInputDialog.getDouble(self,translate_text("Quantity"),translate_text("Quantity:"),0,0,1e12,3);
            if not ok:return
            price,ok=QInputDialog.getDouble(self,translate_text("Unit Price"),translate_text("Unit price:"),0,0,1e15,2);
            if not ok:return
        elif mode=="Lump Sum":
            lump,ok=QInputDialog.getDouble(self,translate_text("Lump Sum"),translate_text("Wholesale / lump-sum amount:"),0,0,1e15,2);
            if not ok:return
        try: save_supplementary(pid,desc,unit,qty,price,lump,mode)
        except (ValueError, TypeError, sqlite3.Error, RuntimeError) as e: QMessageBox.critical(self,translate_text("Error"),str(e)); return
        self.refresh()
# شرح الدالة advance: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def advance(self):
        row = self.table.currentRow()
        if row < 0:
            return

        id_item = self.table.item(row, 0)
        status_item = self.table.item(row, 8)
        if id_item is None or status_item is None:
            return

        sid = id_item.data(Qt.ItemDataRole.UserRole)
        status = status_item.text()
        nxt = {
            "Draft": "Submitted",
            "Submitted": "Approved",
            "Approved": "Executed",
            "Executed": "Valued",
            "Valued": "Included",
            "Included": "Paid",
        }.get(status)
        if not nxt:
            return
        try: transition_supplementary(sid,nxt); self.refresh()
        except (ValueError, TypeError, sqlite3.Error, RuntimeError) as e: QMessageBox.warning(self,translate_text("Cannot advance"),str(e))

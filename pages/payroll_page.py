# ============================================================
# شرح الملف: pages/payroll_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Payroll workspace with attendance and site-labor reconciliation."""
from __future__ import annotations

import sqlite3

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.accounting_integration import post_payroll
from services.payroll_service import (
    attendance_totals,
    labor_reconciliation,
    save_payroll,
)

from .base_page import BasePage, money


# شرح الصنف PayrollPage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class PayrollPage(BasePage):
    def __init__(self):
        super().__init__("Payroll", "Payroll, attendance and site-labor reconciliation")
        bar=QHBoxLayout(); self.period=QLineEdit(); self.period.setPlaceholderText(translate_text("Period, e.g. 2026-09")); self.period.setText(__import__('datetime').date.today().strftime('%Y-%m'))
        add=QPushButton(translate_text("+ Create / update payroll")); add.setObjectName("primaryButton"); add.clicked.connect(self.add)
        refresh=QPushButton(translate_text("Refresh")); refresh.clicked.connect(self.load); post=QPushButton(translate_text("Post Payroll")); post.clicked.connect(self.post_selected)
        bar.addWidget(QLabel(translate_text("Period"))); bar.addWidget(self.period,1); bar.addWidget(add); bar.addWidget(refresh); self.body.addLayout(bar)
        info=QGridLayout(); self.att_info=QLabel("0.00 h"); self.alloc_info=QLabel("0.00 h"); self.unalloc_info=QLabel("0.00 h"); self.status_info=QLabel("-")
        for i,(label,w) in enumerate((("Attendance hours",self.att_info),("Allocated site hours",self.alloc_info),("Unallocated hours",self.unalloc_info),("Reconciliation",self.status_info))): info.addWidget(QLabel(translate_text(label)+":"),0,i*2); info.addWidget(w,0,i*2+1)
        self.body.addLayout(info)
        frame,lay=self.panel(); self.table=QTableWidget(0,10); self.table.setHorizontalHeaderLabels([translate_text(x) for x in ["Employee","Period","Present days","Attendance h","Attendance OT","Allocated h","Allocated OT","Base","Net","Reconciliation"]]); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch); lay.addWidget(self.table,1); self.body.addWidget(frame); self.load()

# شرح الدالة load: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def load(self):
        period=self.period.text().strip()
        if not period: return
        c=get_connection()
        try:
            staff=c.execute("SELECT staff_id,full_name FROM staff WHERE status='Active' ORDER BY full_name").fetchall()
            rows=[]
            for st in staff:
                att=attendance_totals(c,st['staff_id'],period); rec=labor_reconciliation(c,st['staff_id'],period)
                pr=c.execute("SELECT base_amount,net_amount FROM payroll_records WHERE staff_id=? AND period=?",(st['staff_id'],period)).fetchone()
                if att['hours'] or att['overtime'] or pr:
                    rows.append((st['full_name'],period,att['present_days'],att['hours'],att['overtime'],rec['allocated_hours'],rec['allocated_overtime'],pr['base_amount'] if pr else 0,pr['net_amount'] if pr else 0,rec['status']))
        finally:c.close()
        self.table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            for j,v in enumerate(row): self.table.setItem(i,j,QTableWidgetItem(money(v) if isinstance(v,(int,float)) and j not in (2,) else str(v)))
        total_att=sum(float(r[3]) for r in rows); total_alloc=sum(float(r[5]) for r in rows); total_un=max(0,total_att-total_alloc); self.att_info.setText(f'{total_att:.2f} h'); self.alloc_info.setText(f'{total_alloc:.2f} h'); self.unalloc_info.setText(f'{total_un:.2f} h'); self.status_info.setText("Reconciled" if rows and total_un < .001 else ("Partially allocated" if total_un > .001 else "-"))

# شرح الدالة add: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def post_selected(self):
        row=self.table.currentRow()
        if row < 0:
            self.error("Select a payroll row first."); return
        employee_item = self.table.item(row, 0)
        period_item = self.table.item(row, 1)
        if employee_item is None or period_item is None:
            self.error("Selected payroll row is incomplete.")
            return

        employee = employee_item.text()
        period = period_item.text()
        c=get_connection()
        try:
            r=c.execute("SELECT pr.payroll_id FROM payroll_records pr JOIN staff s ON s.staff_id=pr.staff_id WHERE s.full_name=? AND pr.period=?",(employee,period)).fetchone()
        finally:c.close()
        if not r: self.error("Payroll record not found."); return
        try:
            post_payroll(r['payroll_id']); self.load()
        except (ValueError, TypeError, sqlite3.Error, RuntimeError) as exc:
            self.error(str(exc))

    def add(self):
        period=self.period.text().strip()
        if not period: self.error("Enter a payroll period such as 2026-09."); return
        c=get_connection()
        try: staff=c.execute("SELECT staff_id,full_name,COALESCE(rate,0) rate,salary_type FROM staff WHERE status='Active' ORDER BY full_name").fetchall()
        finally:c.close()
        if not staff: self.error("No active employees found."); return
        d=QDialog(self); d.setWindowTitle(translate_text("Payroll record")); f=QFormLayout(d); s=LocalizedComboBox(); [s.addItem(x['full_name'],dict(x)) for x in staff]
        summary=QLabel(); base=QDoubleSpinBox(); base.setRange(0,1e15); base.setDecimals(2); overtime=QDoubleSpinBox(); overtime.setRange(0,1e15); overtime.setDecimals(2); bonuses=QDoubleSpinBox(); bonuses.setRange(0,1e15); bonuses.setDecimals(2); deductions=QDoubleSpinBox(); deductions.setRange(0,1e15); deductions.setDecimals(2); advances=QDoubleSpinBox(); advances.setRange(0,1e15); advances.setDecimals(2); multiplier=QDoubleSpinBox(); multiplier.setRange(0,5); multiplier.setDecimals(2); multiplier.setValue(1.5)
        for label,w in [("Employee",s),("Attendance / site labor",summary),("Base amount",base),("Overtime amount",overtime),("Overtime multiplier",multiplier),("Bonuses",bonuses),("Deductions",deductions),("Advances",advances)]: f.addRow(translate_text(label),w)
# شرح الدالة refresh_calc: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
        def refresh_calc():
            emp=s.currentData();
            if not emp: return
            c=get_connection()
            try: att=attendance_totals(c,emp['staff_id'],period); rec=labor_reconciliation(c,emp['staff_id'],period)
            finally:c.close()
            salary_type=(emp['salary_type'] or '').lower(); rate=float(emp['rate'] or 0)
            if salary_type in ('hourly','hour') and base.value()==0: base.setValue(att['hours']*rate)
            elif salary_type in ('daily','day') and base.value()==0: base.setValue(att['present_days']*rate)
            elif salary_type in ('monthly','month') and base.value()==0: base.setValue(rate)
            if salary_type in ('hourly','hour'): overtime.setValue(att['overtime']*rate*multiplier.value())
            summary.setText(f"Attendance: {att['hours']:.2f} h + {att['overtime']:.2f} OT | Site labor: {rec['allocated_hours']:.2f} h + {rec['allocated_overtime']:.2f} OT | {rec['status']}")
        s.currentIndexChanged.connect(refresh_calc); multiplier.valueChanged.connect(refresh_calc); refresh_calc()
        bb=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); f.addRow(bb)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        emp=s.currentData()
        try: save_payroll(emp['staff_id'],period,base.value(),overtime.value(),bonuses.value(),deductions.value(),advances.value(),status='Draft')
        except (ValueError, TypeError, sqlite3.Error, RuntimeError) as exc: self.error(str(exc)); return
        self.load()

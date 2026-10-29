# ============================================================
# شرح الملف: pages/reports_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtWidgets import (
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.report_service import project_summary

from .base_page import BasePage, money


# شرح الصنف ReportsPage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class ReportsPage(BasePage):
    """Printable-ready report center; exports a clean CSV-like text file without
    forcing optional DOCX/PDF libraries into the core installation."""
    def __init__(self):
        super().__init__("Reports", "Operational and financial reports from live database values")
        bar=QHBoxLayout(); self.project=LocalizedComboBox(); self.project.addItem(translate_text("All projects"),"__ALL__")
        for text,slot,obj in [("Project summary",self.project_report,"primaryButton"),("Expense report",self.expense_report,None),("Attendance report",self.attendance_report,None),("BOQ report",self.boq_report,None)]:
            b=QPushButton(translate_text(text)); b.clicked.connect(slot); b.setObjectName(obj or ""); bar.addWidget(b)
        bar.insertWidget(0,self.project,1); self.body.addLayout(bar)
        frame,lay=self.panel(); self.preview=QPlainTextEdit(); self.preview.setReadOnly(True); lay.addWidget(self.preview,1); self.body.addWidget(frame)
        self._projects()

# شرح الدالة _projects: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _projects(self):
        conn=get_connection()
        try:
            for r in conn.execute("SELECT project_id,project_name FROM projects ORDER BY project_name"): self.project.addItem(r["project_name"],r["project_id"])
        finally: conn.close()

# شرح الدالة _selected_project: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _selected_project(self):
        pid=self.project.currentData()
        return None if pid=="__ALL__" else pid

# شرح الدالة _label: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _label(text: str) -> str:
        return translate_text(text)

# شرح الدالة project_report: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def project_report(self):
        pid=self._selected_project()
        if not pid:
            conn=get_connection()
            try:
                rows=conn.execute("""SELECT project_id,project_name,budget_ht,budget_ttc,status,
                    (SELECT COALESCE(SUM(amount),0) FROM expenses e WHERE e.project_id=p.project_id),
                    (SELECT COALESCE(SUM(amount),0) FROM project_payments pp WHERE pp.project_id=p.project_id)
                    FROM projects p ORDER BY project_name""").fetchall()
            finally: conn.close()
            lines=[
                self._label("PROJECT FINANCIAL REPORT"),
                f"{self._label('Generated:')} {datetime.now(timezone.utc).astimezone():%Y-%m-%d %H:%M}",
                "",
            ]
            for r in rows:
                lines.append(
                    f"{r['project_id']} | {r['project_name']} | HT {money(r['budget_ht'])} | "
                    f"{self._label('Expenses:')} {money(r[5])} | "
                    f"{self._label('Received')} {money(r[6])} | "
                    f"{translate_text(str(r['status']))}"
                )
            self.preview.setPlainText("\n".join(lines)); return
        d=project_summary(pid)
        self.preview.setPlainText("\n".join([
            self._label("PROJECT SUMMARY"),
            f"{self._label('Project:')} {d.get('project_name','')}",
            f"{self._label('Contract HT:')} {money(d.get('budget_ht'))}",
            f"{self._label('Contract TTC:')} {money(d.get('budget_ttc'))}",
            f"{self._label('BOQ value:')} {money(d.get('boq_value'))}",
            f"{self._label('Expenses:')} {money(d.get('expenses_calculated'))}",
            f"{self._label('Income received:')} {money(d.get('income_received'))}",
            (f"{self._label('Profit (received - expenses):')} "
            f"{money(float(d.get('income_received') or 0)-float(d.get('expenses_calculated') or 0))}"),
            f"{self._label('Status:')} {translate_text(str(d.get('status','')))}"
        ]))

# شرح الدالة expense_report: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def expense_report(self):
        conn=get_connection()
        try:
            rows=conn.execute("""SELECT e.expense_id,COALESCE(p.project_name,'General'),e.date,e.description,e.category,e.amount,
                COALESCE((SELECT SUM(amount) FROM expense_payments ep WHERE ep.expense_id=e.expense_id),0)
                FROM expenses e LEFT JOIN projects p ON p.project_id=e.project_id ORDER BY e.date DESC""").fetchall()
        finally: conn.close()
        columns = ["ID", "Project", "Date", "Description", "Category", "Amount", "Paid"]
        lines=[self._label("EXPENSE REPORT")," | ".join(self._label(column) for column in columns)]
        lines += [
            f"{r[0]} | {r[1]} | {r[2]} | {r[3]} | "
            f"{translate_text(str(r[4])) if r[4] else '-'} | {money(r[5])} | {money(r[6])}"
            for r in rows
        ]
        self.preview.setPlainText("\n".join(lines))

# شرح الدالة attendance_report: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def attendance_report(self):
        conn=get_connection()
        try:
            rows=conn.execute("""SELECT a.date,s.full_name,COALESCE(p.project_name,'Administration'),a.status,a.working_hours,a.overtime_hours
                                 FROM attendance a JOIN staff s ON s.staff_id=a.staff_id
                                 LEFT JOIN projects p ON p.project_id=a.project_id ORDER BY a.date DESC""").fetchall()
        finally: conn.close()
        columns = ["Date", "Employee", "Project", "Status", "Regular h", "Overtime h"]
        lines=[self._label("ATTENDANCE REPORT")," | ".join(self._label(column) for column in columns)]
        lines += [
            f"{r[0]} | {r[1]} | {r[2]} | {translate_text(str(r[3]))} | "
            f"{r[4]:.2f} | {r[5]:.2f}"
            for r in rows
        ]
        self.preview.setPlainText("\n".join(lines))

# شرح الدالة boq_report: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def boq_report(self):
        conn=get_connection()
        try:
            pid=self._selected_project()
            q="""SELECT p.project_name,m.item_number,m.description,m.unit,m.quantity,m.unit_price,m.amount
                 FROM metre_items m JOIN projects p ON p.project_id=m.project_id"""
            args=()
            if pid:q+=" WHERE m.project_id=?";args=(pid,)
            rows=conn.execute(q+" ORDER BY p.project_name,m.item_number",args).fetchall()
        finally: conn.close()
        columns = ["Project", "No.", "Description", "Unit", "Qty", "Unit price", "Amount"]
        lines=[
            self._label("BOQ / MÉTRÉ REPORT"),
            " | ".join(self._label(column) for column in columns),
        ]
        lines += [f"{r[0]} | {r[1] or '-'} | {r[2]} | {r[3] or '-'} | {r[4]:.3f} | {money(r[5])} | {money(r[6])}" for r in rows]
        self.preview.setPlainText("\n".join(lines))


# ============================================================
# شرح الملف: pages/project_closeout_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Project closeout and final reconciliation workspace."""
from __future__ import annotations

import sqlite3

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from core.i18n import translate_text
from repositories.db import get_connection
from services.project_intelligence_service import project_closeout_checklist
from services.project_service import finalize_project

from .base_page import BasePage, money, set_button


# شرح الصنف ProjectCloseoutPage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class ProjectCloseoutPage(BasePage):
    def __init__(self):
        super().__init__("Project Closeout","Final reconciliation, readiness checks and controlled project completion")
        self._build(); self.refresh()
# شرح الدالة _build: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build(self):
        bar=QHBoxLayout(); self.project=QComboBox(); bar.addWidget(QLabel(translate_text("Project"))); bar.addWidget(self.project,1)
        self.check_btn=QPushButton(translate_text("Run final reconciliation")); set_button(self.check_btn,"primary"); self.check_btn.clicked.connect(self.refresh); bar.addWidget(self.check_btn)
        self.close_btn=QPushButton(translate_text("Close project")); set_button(self.close_btn,"success"); self.close_btn.clicked.connect(self.close_project); bar.addWidget(self.close_btn); self.body.addLayout(bar)
        self.summary=QLabel(); self.summary.setWordWrap(True); self.body.addWidget(self.summary)
        self.table=QTableWidget(0,4); self.table.setHorizontalHeaderLabels([translate_text(x) for x in ["Check","Status","Details","Blocking"]]); self.body.addWidget(self.table,1)
# شرح الدالة _load_projects: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _load_projects(self):
        conn=get_connection()
        try: rows=conn.execute("SELECT project_id,project_name FROM projects WHERE status NOT IN ('Completed','Archived') ORDER BY project_name").fetchall()
        finally: conn.close()
        current=self.project.currentData(); self.project.blockSignals(True); self.project.clear()
        for r in rows:self.project.addItem(f"{r['project_id']} • {r['project_name']}",r['project_id'])
        if current:
            i=self.project.findData(current)
            if i>=0:self.project.setCurrentIndex(i)
        self.project.blockSignals(False)
# شرح الدالة refresh: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def refresh(self):
        self._load_projects(); pid=self.project.currentData()
        if not pid: self.summary.setText(translate_text("No open project is available.")); self.table.setRowCount(0); self.close_btn.setEnabled(False); return
        r=project_closeout_checklist(pid); self.table.setRowCount(len(r['checks']))
        for i,c in enumerate(r['checks']):
            vals=[c['name'],"OK" if c['ok'] else "BLOCKED",c['detail'],"Yes" if c['blocking'] else "No"]
            for j,v in enumerate(vals): self.table.setItem(i,j,QTableWidgetItem(translate_text(str(v))))
        f=r['financial']; self.summary.setText(translate_text(f"Readiness: {'READY' if r['ready'] else 'NOT READY'} • Blocking issues: {r['blocking_count']} • Final forecast cost: {money(f.get('eac',0))} • Forecast margin: {money(f.get('margin',0))}"))
        self.close_btn.setEnabled(r['ready'])
# شرح الدالة close_project: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def close_project(self):
        pid=self.project.currentData()
        if not pid:return
        r=project_closeout_checklist(pid)
        if not r['ready']: QMessageBox.warning(self,translate_text("Project closeout"),translate_text("The project is not ready for closure.")); return
        if QMessageBox.question(self,translate_text("Confirm closure"),translate_text("Close this project after final reconciliation?"))!=QMessageBox.StandardButton.Yes:return
        try:
            finalize_project(pid)
            QMessageBox.information(self,translate_text("Project closed"),translate_text("Project finalized successfully.")); self.refresh()
        except (ValueError, TypeError, sqlite3.Error, RuntimeError) as exc: QMessageBox.warning(self,translate_text("Project closeout"),str(exc))

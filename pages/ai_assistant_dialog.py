# ============================================================
# شرح الملف: pages/ai_assistant_dialog.py
# واجهة المساعد الذكي المحلي للقراءة والتحليل دون ذكاء سحابي.
# ============================================================
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from ai.assistant import BuildOfficeAssistant
from core.i18n import translate_text
from services.settings_service import get_setting


class AIAssistantDialog(QDialog):
    def __init__(self,parent=None,initial_question:str="",open_page=None):
        super().__init__(parent); self.open_page=open_page; self.setObjectName("aiAssistantDialog"); self.setWindowTitle(translate_text("BuildOffice AI")); self.resize(820,600); self.setMinimumSize(680,500); self._build()
        if initial_question: self.question.setText(initial_question); self.ask()
        else: self.question.setFocus()
    def _build(self):
        root=QVBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(10)
        hero=QFrame(); hero.setObjectName("aiHero"); hb=QVBoxLayout(hero); title=QLabel("🤖  "+translate_text("BuildOffice AI")); title.setObjectName("aiTitle"); sub=QLabel(translate_text("Local intelligence • Read-only • No cloud AI")); sub.setObjectName("aiSubtitle"); hb.addWidget(title); hb.addWidget(sub); root.addWidget(hero)
        bar=QHBoxLayout(); self.question=QLineEdit(); self.question.setObjectName("aiQuestion"); self.question.setPlaceholderText(translate_text("Ask about projects, costs, progress, payroll, attendance, debts, vehicles, documents…")); self.question.returnPressed.connect(self.ask); bar.addWidget(self.question,1); b=QPushButton(translate_text("Ask")); b.setObjectName("primaryButton"); b.clicked.connect(self.ask); bar.addWidget(b); root.addLayout(bar)
        self.answer=QTextEdit(); self.answer.setReadOnly(True); self.answer.setObjectName("aiAnswer"); self.answer.setMaximumHeight(155); root.addWidget(self.answer)
        self.table=QTableWidget(0,3); self.table.setHorizontalHeaderLabels([translate_text("Field"),translate_text("Value"),translate_text("Details")]); self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); root.addWidget(self.table,1)
        actions=QHBoxLayout(); self.page_button=QPushButton(translate_text("Open related page")); self.page_button.setEnabled(False); self.page_button.clicked.connect(self._open_page); actions.addWidget(self.page_button); actions.addStretch(); close=QPushButton(translate_text("Close")); close.clicked.connect(self.accept); actions.addWidget(close); root.addLayout(actions)
    def ask(self):
        text=self.question.text().strip()
        if not text:return
        try:
            r=BuildOfficeAssistant().ask(text); self.answer.setPlainText(r.answer); self.table.setRowCount(0)
            limit = max(5, min(50, int(float(get_setting("ai_max_results", "20")))))
            for row in r.rows[:limit]:
                if not isinstance(row,dict): row={"Result":row}
                vals=list(row.items())[:3]; idx=self.table.rowCount(); self.table.insertRow(idx)
                for c,(k,v) in enumerate(vals): self.table.setItem(idx,c,QTableWidgetItem(f"{k}: {v}"))
            self.page_button.setEnabled(bool(r.open_page and self.open_page)); self.page_button.setProperty("target_page",r.open_page or ""); self.setWindowTitle("🤖 "+translate_text(r.title))
        except (ValueError, TypeError, KeyError, RuntimeError, OSError) as exc:
            self.answer.setPlainText(translate_text("The local assistant could not complete the query.")+"\n\n"+str(exc)); self.table.setRowCount(0); self.page_button.setEnabled(False)
    def _open_page(self):
        page=self.page_button.property("target_page")
        if callable(self.open_page) and page:self.accept(); self.open_page(str(page))

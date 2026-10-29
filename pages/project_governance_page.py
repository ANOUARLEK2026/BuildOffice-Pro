# ============================================================
# شرح الملف: pages/project_governance_page.py
# واجهة حوكمة المشروع في المرحلة الخامسة.
# ============================================================
"""Project governance workspace: milestones, risks and corrective actions."""
from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from core.i18n import translate_text
from repositories.db import get_connection
from services.project_governance_service import list_projects, project_governance

from .base_page import BasePage, set_button
from .id_service import next_sequence_id


class ProjectGovernancePage(BasePage):
    def __init__(self):
        super().__init__("Project Governance", "Milestones, risks, corrective actions and executive readiness")
        self._build()
        self.refresh()

    def _build(self):
        bar = QHBoxLayout()
        self.project = QComboBox()
        bar.addWidget(QLabel(translate_text("Project")))
        bar.addWidget(self.project, 1)
        refresh = QPushButton(translate_text("Refresh governance"))
        set_button(refresh, "primary")
        refresh.clicked.connect(self.refresh)
        bar.addWidget(refresh)
        add_m = QPushButton(translate_text("Add milestone"))
        add_m.clicked.connect(self.add_milestone)
        bar.addWidget(add_m)
        add_r = QPushButton(translate_text("Add risk"))
        add_r.clicked.connect(self.add_risk)
        bar.addWidget(add_r)
        add_a = QPushButton(translate_text("Add action"))
        add_a.clicked.connect(self.add_action)
        bar.addWidget(add_a)
        self.body.addLayout(bar)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.body.addWidget(self.summary)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([translate_text(x) for x in ["Type", "Title", "Priority / Score", "Owner", "Due date", "Status"]])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.body.addWidget(self.table, 1)

    def _load_projects(self):
        current = self.project.currentData()
        self.project.blockSignals(True)
        self.project.clear()
        for r in list_projects():
            self.project.addItem(f"{r['project_id']} • {r['project_name']}", r['project_id'])
        if current:
            idx = self.project.findData(current)
            if idx >= 0:
                self.project.setCurrentIndex(idx)
        self.project.blockSignals(False)

    def refresh(self):
        self._load_projects()
        pid = self.project.currentData()
        if not pid:
            self.summary.setText(translate_text("No project available."))
            self.table.setRowCount(0)
            return
        data = project_governance(pid)
        rows = []
        for r in data["milestones"]:
            rows.append(("Milestone", r["name"], r["priority"], "", r["planned_date"], r["status"]))
        for r in data["risks"]:
            rows.append(("Risk", r["title"], r["score"], r["owner"] or "", r["due_date"] or "", r["status"]))
        for r in data["actions"]:
            rows.append(("Action", r["title"], r["priority"], r["owner"] or "", r["due_date"] or "", r["status"]))
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(translate_text(str(value))))
        self.summary.setText(translate_text(
            f"Governance score: {data['score']}/100 • Overdue milestones: {data['overdue_milestones']} • "
            f"Overdue actions: {data['overdue_actions']} • High risks: {data['open_high_risks']}"
        ))

    def add_milestone(self):
        pid = self.project.currentData()
        if not pid:
            return
        name, ok = QInputDialog.getText(self, translate_text("Milestone"), translate_text("Milestone name:"))
        if not ok or not name.strip():
            return
        planned, ok = QInputDialog.getText(self, translate_text("Milestone"), translate_text("Planned date (YYYY-MM-DD):"), text=datetime.now(timezone.utc).date().isoformat())
        if not ok or not planned.strip():
            return
        priority, ok = QInputDialog.getInt(self, translate_text("Priority"), translate_text("Priority (1-5):"), 3, 1, 5)
        if not ok:
            return
        conn = get_connection()
        try:
            mid = next_sequence_id(conn, "MS", digits=8)
            conn.execute("INSERT INTO project_milestones(milestone_id,project_id,name,planned_date,status,priority) VALUES(?,?,?,?,?,?)", (mid,pid,name.strip(),planned.strip(),"Open",priority))
            conn.commit()
        finally:
            conn.close()
        self.refresh()

    def add_risk(self):
        pid = self.project.currentData()
        if not pid:
            return
        title, ok = QInputDialog.getText(self, translate_text("Risk"), translate_text("Risk title:"))
        if not ok or not title.strip():
            return
        probability, ok = QInputDialog.getInt(self, translate_text("Probability"), translate_text("Probability (1-5):"), 3, 1, 5)
        if not ok:
            return
        impact, ok = QInputDialog.getInt(self, translate_text("Impact"), translate_text("Impact (1-5):"), 3, 1, 5)
        if not ok:
            return
        owner, ok = QInputDialog.getText(self, translate_text("Risk owner"), translate_text("Owner:"))
        if not ok:
            return
        conn = get_connection()
        try:
            rid = next_sequence_id(conn, "RSK", digits=8)
            conn.execute("INSERT INTO project_risks(risk_id,project_id,title,category,probability,impact,score,status,owner,created_at) VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", (rid,pid,title.strip(),"General",probability,impact,probability*impact,"Open",owner.strip()))
            conn.commit()
        finally:
            conn.close()
        self.refresh()

    def add_action(self):
        pid = self.project.currentData()
        if not pid:
            return
        title, ok = QInputDialog.getText(self, translate_text("Action"), translate_text("Action title:"))
        if not ok or not title.strip():
            return
        due, ok = QInputDialog.getText(self, translate_text("Action"), translate_text("Due date (YYYY-MM-DD):"), text=datetime.now(timezone.utc).date().isoformat())
        if not ok:
            return
        owner, ok = QInputDialog.getText(self, translate_text("Action owner"), translate_text("Owner:"))
        if not ok:
            return
        conn = get_connection()
        try:
            aid = next_sequence_id(conn, "ACT", digits=8)
            conn.execute("INSERT INTO governance_actions(action_id,project_id,title,owner,due_date,status,priority,created_at) VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", (aid,pid,title.strip(),owner.strip(),due.strip(),"Open",3))
            conn.commit()
        finally:
            conn.close()
        self.refresh()

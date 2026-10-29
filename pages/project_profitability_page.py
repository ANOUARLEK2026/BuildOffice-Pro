# ============================================================
# شرح الملف: pages/project_profitability_page.py
# واجهة تحليل ربحية المشروع ومراكز التكلفة.
# ============================================================
from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.i18n import translate_text
from repositories.db import get_connection
from services.project_profitability_service import project_profitability

from .base_page import BasePage, money


class ProjectProfitabilityPage(BasePage):
    """Dense but readable live job-costing dashboard for a selected project."""

    def __init__(self):
        super().__init__("Project Profitability", "Live job costing, forecast margin and cost-center control")
        self._build()
        self._load_projects()

    def _build(self):
        bar = QHBoxLayout()
        self.project = QComboBox()
        self.project.setMinimumWidth(360)
        bar.addWidget(QLabel(translate_text("Project")))
        bar.addWidget(self.project, 1)
        refresh = QPushButton(translate_text("Refresh"))
        refresh.clicked.connect(self.refresh)
        bar.addWidget(refresh)
        export = QPushButton(translate_text("Export CSV"))
        export.clicked.connect(self.export_csv)
        bar.addWidget(export)
        self.body.addLayout(bar)

        cards = QHBoxLayout()
        self.cards = {}
        for key, title in [
            ("contract_ht", "Contract HT"), ("earned_value", "Earned Value"),
            ("direct_cost", "Actual Cost"), ("margin", "Margin"),
            ("eac", "Forecast Cost"), ("receivable", "Receivable"),
        ]:
            frame = QFrame(); frame.setProperty("panel", True)
            lay = QVBoxLayout(frame); label = QLabel(translate_text(title)); value = QLabel("0.00")
            value.setObjectName("pageTitle")
            lay.addWidget(label); lay.addWidget(value)
            cards.addWidget(frame, 1); self.cards[key] = value
        self.body.addLayout(cards)

        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.body.addWidget(self.summary)

        self.cost_table = QTableWidget(0, 4)
        self.cost_table.setHorizontalHeaderLabels([translate_text("Cost Type"), translate_text("Amount"), translate_text("% of Cost"), translate_text("Rank")])
        self.cost_table.horizontalHeader().setStretchLastSection(True)
        self.body.addWidget(self.cost_table, 1)

        cc_frame, cc_lay = self.panel()
        cc_lay.addWidget(QLabel(translate_text("Cost Centers")))
        self.cc_table = QTableWidget(0, 6)
        self.cc_table.setHorizontalHeaderLabels([translate_text("Code"), translate_text("Name"), translate_text("Budget"), translate_text("Actual"), translate_text("Variance"), translate_text("Utilization %")])
        self.cc_table.horizontalHeader().setStretchLastSection(True)
        cc_lay.addWidget(self.cc_table)
        self.body.addWidget(cc_frame, 1)

    def _load_projects(self):
        current = self.project.currentData()
        self.project.blockSignals(True)
        self.project.clear()
        conn = get_connection()
        try:
            for row in conn.execute("SELECT project_id,project_name FROM projects ORDER BY project_name"):
                self.project.addItem(str(row["project_name"]), row["project_id"])
        finally:
            conn.close()
        self.project.blockSignals(False)
        if current:
            idx = self.project.findData(current)
            if idx >= 0: self.project.setCurrentIndex(idx)
        self.refresh()

    def refresh(self):
        pid = self.project.currentData()
        if not pid:
            return
        data = project_profitability(str(pid))
        for key, label in self.cards.items():
            label.setText(money(data.get(key, 0)))
        self.summary.setText(translate_text(
            f"Health: {data['health']} | Progress: {data['progress']:.1f}% | Cost: {data['cost_pct']:.1f}% | "
            f"CPI: {data['cpi']:.2f} | ETC: {money(data['etc'])} | As of: {data['as_of']}"
        ))
        ranked = data["ranked_components"]
        total = data["direct_cost"]
        self.cost_table.setRowCount(len(ranked))
        for i, (name, value) in enumerate(ranked):
            vals = [name, money(value), f"{(value/total*100 if total else 0):.1f}%", str(i + 1)]
            for c, val in enumerate(vals): self.cost_table.setItem(i, c, QTableWidgetItem(str(val)))

        centers = data["cost_centers"]
        self.cc_table.setRowCount(len(centers))
        for i, r in enumerate(centers):
            vals = [r["code"], r["name"], money(r["budget"]), money(r["actual"]), money(r["variance"]), f"{r['utilization']:.1f}%"]
            for c, val in enumerate(vals): self.cc_table.setItem(i, c, QTableWidgetItem(str(val)))

    def export_csv(self):
        pid = self.project.currentData()
        if not pid: return
        data = project_profitability(str(pid))
        path, ok = QFileDialog.getSaveFileName(self, translate_text("Export profitability"), "Project_Profitability.csv", "CSV (*.csv)")
        if not ok or not path: return
        try:
            with Path(path).open("w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.writer(fh)
                writer.writerow(["Project", data["project_name"]])
                writer.writerow(["Metric", "Value"])
                for key in ("contract_ht","contract_ttc","boq_value","earned_value","progress","direct_cost","remaining_budget","cost_pct","margin","margin_pct","cpi","eac","etc","received","invoiced","invoice_paid","receivable"):
                    writer.writerow([key, data.get(key, 0)])
                writer.writerow([]); writer.writerow(["Cost Type", "Amount", "Share %"])
                total = data["direct_cost"]
                for name, value in data["ranked_components"]:
                    writer.writerow([name, value, (value/total*100 if total else 0)])
                writer.writerow([]); writer.writerow(["Code","Name","Budget","Actual","Variance","Utilization %"])
                for r in data["cost_centers"]:
                    writer.writerow([r["code"],r["name"],r["budget"],r["actual"],r["variance"],r["utilization"]])
            QMessageBox.information(self, translate_text("Export"), translate_text("Profitability report exported successfully."))
        except (OSError, csv.Error) as exc:
            QMessageBox.critical(self, translate_text("Export"), str(exc))

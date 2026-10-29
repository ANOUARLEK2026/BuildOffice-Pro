# ============================================================
# شرح الملف: pages/project_control_page.py
# مركز تحكم موحّد للمشروع يقرأ البيانات من الصفحات والخدمات الأخرى.
# لا ينشئ مصدر بيانات جديدًا ولا يكرر إدخال المعلومات.
# ============================================================
"""Project Control Center: integrated read-only project command center."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.project_control_service import (
    project_control_cost_breakdown,
    project_control_snapshot,
    project_control_timeline,
)
from services.settings_service import money_display

from .analytics_widgets import AnalyticsCard, AnalyticsChart
from .base_page import BasePage, percent


class ProjectControlPage(BasePage):
    """Integrated, read-only control center for one selected project."""

    def __init__(self, parent=None):
        super().__init__(
            "Project Control Center",
            "Contract, BOQ, progress, cost, workforce, payments and forecast in one view",
        )
        self._project_id: str | None = None
        self._project_selector = LocalizedComboBox()
        self._content = QWidget()
        self._content.setObjectName("projectControlContent")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(10)
        self._build_ui()
        self._load_projects()

    def _build_ui(self) -> None:
        """Build the page using BasePage's existing header and body layout."""
        selector_card = QFrame()
        selector_card.setObjectName("panelCard")
        selector_layout = QHBoxLayout(selector_card)
        selector_layout.setContentsMargins(12, 9, 12, 9)
        selector_layout.setSpacing(8)

        label = QLabel(translate_text("Project to control"))
        label.setObjectName("sectionTitle")
        selector_layout.addWidget(label)

        self._project_selector.setMinimumHeight(38)
        self._project_selector.setMinimumWidth(320)
        self._project_selector.currentIndexChanged.connect(self._project_changed)
        selector_layout.addWidget(self._project_selector, 1)

        refresh = QPushButton(translate_text("Refresh"))
        refresh.clicked.connect(self.refresh_page)
        selector_layout.addWidget(refresh)

        self.body.addWidget(selector_card)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self._content)
        self.body.addWidget(scroll, 1)

    def _load_projects(self) -> None:
        """Load project choices without modifying project data."""
        current = self._project_id
        self._project_selector.blockSignals(True)
        self._project_selector.clear()
        conn = get_connection()
        try:
            rows = conn.execute(
                """SELECT project_id, project_name, status
                   FROM projects
                   ORDER BY CASE WHEN status='Active' THEN 0 ELSE 1 END,
                            project_name"""
            ).fetchall()
        finally:
            conn.close()

        for row in rows:
            status = translate_text(str(row["status"] or ""))
            self._project_selector.addItem(
                f"{row['project_name']} • {row['project_id']} [{status}]",
                row["project_id"],
            )

        if current:
            index = self._project_selector.findData(current)
            if index >= 0:
                self._project_selector.setCurrentIndex(index)
        self._project_selector.blockSignals(False)

        if self._project_selector.count():
            self._project_id = self._project_selector.currentData()
            self.refresh()
        else:
            self._show_empty_state()

    def _project_changed(self, index: int) -> None:
        """Refresh the control view for the selected project."""
        self._project_id = self._project_selector.itemData(index)
        self.refresh()

    @staticmethod
    def _money(value: Any) -> str:
        return money_display(value)

    def _clear_content(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item is None:
                continue

            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
                continue

            child_layout = item.layout()
            if child_layout is not None:
                while child_layout.count():
                    child = child_layout.takeAt(0)
                    if child is None:
                        continue
                    child_widget = child.widget()
                    if child_widget is not None:
                        child_widget.deleteLater()

    def _show_empty_state(self) -> None:
        self._clear_content()
        card = QFrame()
        card.setObjectName("panelCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 22, 20, 22)
        title = QLabel(translate_text("No project selected"))
        title.setObjectName("sectionTitle")
        message = QLabel(translate_text("Select a project to open its integrated control view."))
        message.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(message)
        self._content_layout.addWidget(card)
        self._content_layout.addStretch(1)

    def _metric_card(self, label: str, value: str, detail: str, role: str) -> QFrame:
        card = QFrame()
        card.setObjectName("kpiCard")
        card.setProperty("accentRole", role)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(3)

        title = QLabel(translate_text(label))
        title.setObjectName("kpiLabel")
        value_label = QLabel(value)
        value_label.setObjectName("kpiValue")
        value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        detail_label = QLabel(translate_text(detail))
        detail_label.setObjectName("kpiSubtitle")
        detail_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(value_label)
        layout.addWidget(detail_label)
        return card

    def _metrics(self, snapshot: dict[str, Any]) -> QGridLayout:
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        cards = [
            ("Contract Budget HT", self._money(snapshot["budget"]), "Approved contract baseline", "primary"),
            ("Earned Value", self._money(snapshot["earned"]), "Approved / paid executed value", "success"),
            ("Actual Controlled Cost", self._money(snapshot["controlled_cost"]), "Expenses + labor + equipment + materials + subcontractors", "danger"),
            ("Forecast EAC", self._money(snapshot["eac"]), "Estimated final project cost", "warning"),
            ("Physical Progress", percent(snapshot["physical_progress"]), "Earned value against BOQ value", "success"),
            ("Cost Consumption", percent(snapshot["cost_consumption"]), "Controlled cost against budget", "warning"),
            ("CPI", f"{snapshot['cpi']:.2f}", "Cost efficiency: EV / controlled cost", "info"),
            ("SPI", f"{snapshot['spi']:.2f}", "Schedule efficiency: actual / planned", "info"),
        ]
        for index, item in enumerate(cards):
            grid.addWidget(self._metric_card(*item), index // 4, index % 4)
        return grid

    def _status_banner(self, snapshot: dict[str, Any]) -> QFrame:
        card = QFrame()
        card.setObjectName("panelCard")
        card.setProperty("accentRole", "danger" if snapshot["health"] == "Critical" else "warning" if snapshot["health"] == "Watch" else "success")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 9, 14, 9)
        layout.setSpacing(12)

        health = QLabel(translate_text(snapshot["health"]).upper())
        health.setObjectName("statusBadge")
        health.setMinimumWidth(110)
        health.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(health)

        text_box = QVBoxLayout()
        title = QLabel(str(snapshot["project_name"]))
        title.setObjectName("sectionTitle")
        title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        summary = QLabel(self._summary_text(snapshot))
        summary.setWordWrap(True)
        text_box.addWidget(title)
        text_box.addWidget(summary)
        layout.addLayout(text_box, 1)
        return card

    def _summary_text(self, snapshot: dict[str, Any]) -> str:
        if snapshot["health"] == "Critical":
            return translate_text("Immediate management attention is recommended. Cost or schedule control is outside the safe range.")
        if snapshot["health"] == "Watch":
            return translate_text("The project is operational, but one or more control indicators require review.")
        return translate_text("The available project data is currently within the defined control thresholds.")

    def _table_card(self, title: str, headers: list[str], rows: list[list[str]]) -> QFrame:
        card = QFrame()
        card.setObjectName("panelCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 9, 12, 10)
        heading = QLabel(translate_text(title))
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)

        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels([translate_text(h) for h in headers])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(max(120, min(230, 34 + len(rows) * 28)))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(r, c, item)
        layout.addWidget(table)
        return card

    def _management_card(self, snapshot: dict[str, Any]) -> QFrame:
        card = QFrame()
        card.setObjectName("panelCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 9, 12, 10)
        title = QLabel(translate_text("Management Interpretation"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        findings: list[str] = []
        if snapshot["cpi"] < 1:
            findings.append(translate_text("Cost efficiency is below 1.00. Review the main cost drivers before the margin deteriorates further."))
        if snapshot["spi"] < 1:
            findings.append(translate_text("Schedule efficiency is below 1.00. Compare physical progress with the planned schedule."))
        if snapshot["receivable"] > 0:
            findings.append(translate_text("There is earned value that has not yet been collected. Review client collection and pending situations."))
        if snapshot["payable"] > 0:
            findings.append(translate_text("Some recorded expenses remain unpaid. Review supplier and expense-payment commitments."))
        if snapshot["labor_gap"] > 0.5:
            findings.append(translate_text("Attendance hours exceed recorded labor allocation hours. Reconcile workforce allocation."))
        if snapshot["expired_documents"]:
            findings.append(translate_text("One or more project documents are expired. Update compliance records."))
        if snapshot["cost_variance"] < 0:
            findings.append(translate_text("Controlled cost is above the contract budget. Investigate the variance immediately."))
        if not findings:
            findings.append(translate_text("No major control exception was detected from the available project data."))

        for finding in findings:
            label = QLabel("• " + finding)
            label.setWordWrap(True)
            layout.addWidget(label)
        return card

    def _build_control_rows(self, snapshot: dict[str, Any]) -> list[list[str]]:
        return [
            [translate_text("Contract"), str(snapshot["contract_code"] or "-"), self._money(snapshot["budget"]), translate_text(str(snapshot["status"] or "-"))],
            [translate_text("Schedule"), f"{snapshot['elapsed_days']} / {snapshot['planned_days']} {translate_text('days')}", percent(snapshot["planned_progress"]), percent(snapshot["physical_progress"])],
            [translate_text("BOQ"), str(snapshot["boq_items"]), self._money(snapshot["boq_value"]), translate_text("Calculated BOQ value")],
            [translate_text("Situations"), str(snapshot["situations"]), str(snapshot["approved_situations"]), str(snapshot["pending_situations"])],
            [translate_text("Cash"), self._money(snapshot["payments"]), self._money(snapshot["receivable"]), self._money(snapshot["payable"])],
            [translate_text("Workforce"), f"{snapshot['staff_count']} {translate_text('staff')}", f"{snapshot['labor_hours']:.1f} h", f"{snapshot['attendance_hours']:.1f} h"],
            [translate_text("Materials"), f"{snapshot['material_quantity']:.2f}", self._money(snapshot["materials"]), translate_text("Consumption cost")],
            [translate_text("Documents"), str(snapshot["documents"]), str(snapshot["expired_documents"]), str(snapshot["supplementary_pending"])],
        ]

    def refresh_page(self) -> None:
        """Refresh project choices and the selected project's control view."""
        self._load_projects()

    def refresh(self) -> None:
        """Recalculate and render the integrated control view."""
        if not self._project_id:
            self._show_empty_state()
            return

        snapshot = project_control_snapshot(str(self._project_id))
        if not snapshot:
            self._show_empty_state()
            return

        self._clear_content()
        self._content_layout.addWidget(self._status_banner(snapshot))
        self._content_layout.addLayout(self._metrics(snapshot))

        chart_row = QHBoxLayout()
        chart_row.setSpacing(10)

        timeline_card = AnalyticsCard(
            translate_text("Monthly Value vs Cost"),
            translate_text("Approved earned value versus direct expenses by month"),
        )
        timeline_rows = project_control_timeline(str(self._project_id))
        chart_rows = [(month, earned - cost) for month, earned, cost in timeline_rows]
        timeline_chart = AnalyticsChart(
            "line", chart_rows, value_suffix="", interaction_hint=translate_text("Monthly control movement")
        )
        timeline_card.add_chart(timeline_chart)
        chart_row.addWidget(timeline_card, 1)

        cost_card = AnalyticsCard(
            translate_text("Cost Structure"),
            translate_text("Controlled project cost composition"),
        )
        cost_rows = project_control_cost_breakdown(str(self._project_id))
        cost_chart = AnalyticsChart(
            "donut", cost_rows, value_suffix="", interaction_hint=translate_text("Cost component")
        )
        cost_card.add_chart(cost_chart)
        chart_row.addWidget(cost_card, 1)
        self._content_layout.addLayout(chart_row)

        self._content_layout.addWidget(
            self._table_card(
                "Integrated Control Matrix",
                ["Domain", "Primary", "Control", "Signal"],
                self._build_control_rows(snapshot),
            )
        )
        self._content_layout.addWidget(self._management_card(snapshot))

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        bottom.addWidget(
            self._table_card(
                "Financial Position",
                ["Indicator", "Value"],
                [
                    [translate_text("Earned Value"), self._money(snapshot["earned"])],
                    [translate_text("Controlled Cost"), self._money(snapshot["controlled_cost"])],
                    [translate_text("Cost Variance"), self._money(snapshot["cost_variance"])],
                    [translate_text("Receivable"), self._money(snapshot["receivable"])],
                    [translate_text("Expense Payable"), self._money(snapshot["payable"])],
                    [translate_text("ETC"), self._money(snapshot["etc"])],
                ],
            ),
        )
        bottom.addWidget(
            self._table_card(
                "Operational Control",
                ["Indicator", "Value"],
                [
                    [translate_text("Labor Hours"), f"{snapshot['labor_hours']:.1f}"],
                    [translate_text("Attendance Hours"), f"{snapshot['attendance_hours']:.1f}"],
                    [translate_text("Labor Gap"), f"{snapshot['labor_gap']:.1f}"],
                    [translate_text("Material Quantity"), f"{snapshot['material_quantity']:.2f}"],
                    [translate_text("Expired Documents"), str(snapshot["expired_documents"])],
                    [translate_text("Pending Situations"), str(snapshot["pending_situations"])],
                ],
            ),
        )
        self._content_layout.addLayout(bottom)
        self._content_layout.addStretch(1)

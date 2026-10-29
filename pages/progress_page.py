# ============================================================
# شرح الملف: pages/progress_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
"""Progress/Situations workspace for project execution tracking."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QUrl
from PySide6.QtGui import QDesktopServices
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
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.report_service import project_progress_report, situation_report
from services.situation_service import (
    delete_situation,
    finalize_project,
    save_situation,
    transition_situation,
)
from services.supplementary_service import include_approved_in_situation

from .base_page import BasePage, money


# شرح الصنف ProgressPage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class ProgressPage(BasePage):
    """Track BOQ execution, situations, document packages, and finalization."""

    def __init__(self):
        super().__init__(
            "Progress / Situations",
            "Track executed quantities, payment situations and project completion",
        )
        self._project_status = None
        self._build_ui()
        self.refresh_projects()

# شرح الدالة _build_ui: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_ui(self) -> None:
        project_bar = QHBoxLayout()
        project_bar.addWidget(QLabel(translate_text("Project")))
        self.project = LocalizedComboBox()
        self.project.currentIndexChanged.connect(self.load)
        project_bar.addWidget(self.project, 1)

        self.new_button = QPushButton(translate_text("+ New situation"))
        self.new_button.setObjectName("primaryButton")
        self.new_button.clicked.connect(self.add_situation)
        project_bar.addWidget(self.new_button)

        refresh_button = QPushButton(translate_text("Refresh"))
        refresh_button.clicked.connect(self.refresh_projects)
        project_bar.addWidget(refresh_button)
        self.body.addLayout(project_bar)

        frame, layout = self.panel()

        overview = QHBoxLayout()
        self.summary = QLabel(translate_text("Select a project to review its situations."))
        self.summary.setObjectName("pageSubtitle")
        self.summary.setWordWrap(True)
        overview.addWidget(self.summary, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 10000)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0.00%")
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedWidth(220)
        overview.addWidget(self.progress_bar)
        layout.addLayout(overview)

        actions = QHBoxLayout()
        self.edit_button = QPushButton(translate_text("Edit"))
        self.edit_button.clicked.connect(self.edit_situation)
        actions.addWidget(self.edit_button)

        self.delete_button = QPushButton(translate_text("Delete"))
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(self.remove_situation)
        actions.addWidget(self.delete_button)

        self.submit_button = QPushButton(translate_text("Submit"))
        self.submit_button.clicked.connect(lambda: self.change_status("Submitted"))
        actions.addWidget(self.submit_button)

        self.approve_button = QPushButton(translate_text("Approve"))
        self.approve_button.clicked.connect(lambda: self.change_status("Approved"))
        actions.addWidget(self.approve_button)

        self.paid_button = QPushButton(translate_text("Mark Paid"))
        self.paid_button.clicked.connect(lambda: self.change_status("Paid"))
        actions.addWidget(self.paid_button)

        self.include_supp_button = QPushButton(translate_text("Include Supplementary Works"))
        self.include_supp_button.clicked.connect(self.include_supplementary)
        actions.addWidget(self.include_supp_button)

        self.folder_button = QPushButton(translate_text("Open Documents"))
        self.folder_button.clicked.connect(self.open_situation_folder)
        actions.addWidget(self.folder_button)

        self.finalize_button = QPushButton(translate_text("Finalize Project"))
        self.finalize_button.setObjectName("primaryButton")
        self.finalize_button.clicked.connect(self.finalize_selected_project)
        actions.addWidget(self.finalize_button)
        layout.addLayout(actions)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                translate_text("Situation"),
                translate_text("Date"),
                translate_text("Status"),
                translate_text("Current"),
                translate_text("Cumulative"),
                translate_text("Remaining"),
                translate_text("Progress"),
            ]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.doubleClicked.connect(lambda *_: self.edit_situation())
        self.table.itemSelectionChanged.connect(self._refresh_action_state)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        for col in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(col)
            if item is not None:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.table, 1)
        self.body.addWidget(frame)
        self._set_action_state(False)

# شرح الدالة showEvent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_projects()

# شرح الدالة refresh_projects: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def refresh_projects(self) -> None:
        current = self.project.currentData() if hasattr(self, "project") else None
        self.project.blockSignals(True)
        self.project.clear()
        self.project.addItem(translate_text("Select project"), "")
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT project_id, project_name, status FROM projects ORDER BY project_name"
            ).fetchall()
            for row in rows:
                self.project.addItem(row["project_name"], row["project_id"])
        finally:
            conn.close()
        if current:
            idx = self.project.findData(current)
            self.project.setCurrentIndex(max(idx, 0))
        else:
            self.project.setCurrentIndex(0)
        self.project.blockSignals(False)
        self.load()

# شرح الدالة load: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def load(self) -> None:
        pid = self.project.currentData() if hasattr(self, "project") else None
        if not pid:
            self._project_status = None
            self.table.setRowCount(0)
            self.summary.setText(translate_text("Select a project to review its situations."))
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("0.00%")
            self._set_action_state(False)
            return

        try:
            report = project_progress_report(str(pid))
        except (sqlite3.Error, TypeError, ValueError) as exc:
            self.error(str(exc))
            return
        if not report:
            self.table.setRowCount(0)
            self._set_action_state(False)
            return

        self._project_status = str(report["project"].get("status") or "")
        self.table.setRowCount(len(report["situations"]))
        for row_index, row in enumerate(report["situations"]):
            values = [
                f"N°{row['situation_number']}",
                row["situation_date"],
                row["status"],
                money(row["period_value"]),
                money(self._cumulative_until(report, row["situation_number"])),
                money(self._remaining_until(report, row["situation_number"])),
                f"{self._progress_until(report, row['situation_number']):.2f}%",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row["situation_id"])
                self.table.setItem(row_index, col, item)

        summary = translate_text(
            f"BOQ value: {money(report['boq_value'])} • "
            f"Executed: {money(report['executed_value'])} • "
            f"Remaining: {money(report['remaining_value'])} • "
            f"Progress: {report['progress_percent']:.2f}%"
        )
        if self._project_status == "Completed":
            summary += " • " + translate_text("Project finalized")
        elif self._project_status == "Archived":
            summary += " • " + translate_text("Project archived")
        self.summary.setText(translate_text(summary))
        self.progress_bar.setValue(round(report["progress_percent"] * 100))
        self.progress_bar.setFormat(f"{report['progress_percent']:.2f}%")
        self._refresh_action_state()

# شرح الدالة _cumulative_until: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _cumulative_until(report: dict, number: int) -> float:
        return sum(
            float(row.get("period_value") or 0)
            for row in report["situations"]
            if int(row["situation_number"]) <= int(number)
        )

# شرح الدالة _remaining_until: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _remaining_until(report: dict, number: int) -> float:
        return max(0.0, float(report["boq_value"]) - ProgressPage._cumulative_until(report, number))

# شرح الدالة _progress_until: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _progress_until(report: dict, number: int) -> float:
        boq = float(report["boq_value"] or 0)
        return min(100.0, max(0.0, ProgressPage._cumulative_until(report, number) / boq * 100.0)) if boq else 0.0

# شرح الدالة selected_situation_id: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def selected_situation_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return str(value) if value else None

# شرح الدالة _refresh_action_state: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _refresh_action_state(self) -> None:
        """Refresh contextual action buttons after table selection changes."""
        self._set_action_state(bool(self.table.rowCount()))

# شرح الدالة _set_action_state: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _set_action_state(self, has_situations: bool) -> None:
        sid = self.selected_situation_id() if has_situations else None
        status = None
        if sid:
            try:
                status = str(situation_report(sid)["situation"]["status"])
            except (KeyError, TypeError, ValueError, sqlite3.Error):
                status = None
        editable = bool(sid and status == "Draft" and self._project_status not in ("Completed", "Archived"))
        self.edit_button.setEnabled(editable)
        self.delete_button.setEnabled(editable)
        self.submit_button.setEnabled(bool(sid and status == "Draft"))
        self.approve_button.setEnabled(bool(sid and status == "Submitted"))
        self.paid_button.setEnabled(bool(sid and status == "Approved"))
        self.folder_button.setEnabled(bool(sid))
        self.finalize_button.setEnabled(bool(self.project.currentData()) and self._project_status not in ("Completed", "Archived"))
        self.new_button.setEnabled(self._project_status not in ("Completed", "Archived"))

# شرح الدالة add_situation: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_situation(self) -> None:
        pid = self.project.currentData()
        if not pid:
            self.error("Select a project first.")
            return
        self._situation_dialog(str(pid), None)

# شرح الدالة edit_situation: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def edit_situation(self) -> None:
        sid = self.selected_situation_id()
        if not sid:
            self.error("Select a situation first.")
            return
        try:
            existing = situation_report(sid)
        except (KeyError, TypeError, ValueError, sqlite3.Error) as exc:
            self.error(str(exc))
            return
        if not existing or existing["situation"]["status"] != "Draft":
            self.error("Only Draft situations can be edited.")
            return
        self._situation_dialog(str(existing["situation"]["project_id"]), sid)

# شرح الدالة remove_situation: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def remove_situation(self) -> None:
        sid = self.selected_situation_id()
        if not sid:
            self.error("Select a situation first.")
            return
        if not self.confirm("Delete this Draft situation?", "Delete situation"):
            return
        try:
            delete_situation(sid)
            self.load()
        except (sqlite3.Error, TypeError, ValueError) as exc:
            self.error(str(exc))

# شرح الدالة include_supplementary: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def include_supplementary(self) -> None:
        """إدراج الأشغال الإضافية المقيّمة في الوضعية الحالية."""
        sid = self.selected_situation_id()
        if not sid:
            self.error(translate_text("Select a situation first."))
            return

        try:
            count = include_approved_in_situation(sid)
            self.load()
            if count:
                self.success(
                    translate_text(
                        f"{count} supplementary work(s) included in the selected situation."
                    )
                )
            else:
                QMessageBox.information(
                    self,
                    translate_text("Information"),
                    translate_text(
                        "No valued supplementary works are available for inclusion."
                    ),
                )
        except (sqlite3.Error, TypeError, ValueError) as exc:
            self.error(str(exc))

# شرح الدالة change_status: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def change_status(self, target_status: str) -> None:
        sid = self.selected_situation_id()
        if not sid:
            self.error("Select a situation first.")
            return
        try:
            transition_situation(sid, target_status)
            self.load()
        except (sqlite3.Error, TypeError, ValueError) as exc:
            self.error(str(exc))

# شرح الدالة open_situation_folder: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def open_situation_folder(self) -> None:
        sid = self.selected_situation_id()
        if not sid:
            self.error("Select a situation first.")
            return
        try:
            data = situation_report(sid)
            project_id = str(data["situation"]["project_id"])
            number = int(data["situation"]["situation_number"])
            from services.situation_document_service import SITUATION_OUTPUT_DIR

            folder = Path(SITUATION_OUTPUT_DIR) / project_id / f"Situation-{number:03d}"
            folder.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        except (OSError, TypeError, ValueError, KeyError) as exc:
            self.error(str(exc))

# شرح الدالة finalize_selected_project: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def finalize_selected_project(self) -> None:
        pid = self.project.currentData()
        if not pid:
            self.error("Select a project first.")
            return
        try:
            report = project_progress_report(str(pid))
        except (sqlite3.Error, TypeError, ValueError) as exc:
            self.error(str(exc))
            return
        if not report["can_finalize"]:
            blockers = []
            if report["outstanding_items"]:
                blockers.append(translate_text(f"{len(report['outstanding_items'])} BOQ item(s) still have remaining quantities."))
            if report["draft_count"]:
                blockers.append(translate_text(f"{report['draft_count']} situation(s) are still Draft."))
            for row in report["situations"]:
                if row["status"] not in ("Approved", "Paid"):
                    blockers.append(translate_text(f"Situation N°{row['situation_number']} is not Approved/Paid."))
            if not report["situations"]:
                blockers.append(translate_text("No situations exist for this project."))
            self.error(translate_text("The project is not ready for finalization.") + "\n\n" + "\n".join(dict.fromkeys(blockers)))
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(translate_text("Finalize Project"))
        dialog.resize(520, 250)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        completion_date = QDateEdit(QDate.currentDate())
        completion_date.setCalendarPopup(True)
        form.addRow(translate_text("Completion date"), completion_date)
        layout.addLayout(form)

        message = QLabel(
            translate_text(
                f"Final progress: {report['progress_percent']:.2f}% • "
                f"Executed: {money(report['executed_value'])} • "
                f"Remaining: {money(report['remaining_value'])}"
            )
        )
        message.setWordWrap(True)
        layout.addWidget(message)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            finalize_project(str(pid), completion_date.date().toString("yyyy-MM-dd"))
            self.load()
            self.success(translate_text("Project finalized successfully."))
        except (sqlite3.Error, TypeError, ValueError) as exc:
            self.error(str(exc))

# شرح الدالة _situation_dialog: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _situation_dialog(self, project_id: str, situation_id: str | None) -> None:
        if situation_id:
            data = situation_report(situation_id)
            title_text = str(data["situation"].get("title") or f"Situation N°{data['situation']['situation_number']}")
            number = int(data["situation"]["situation_number"])
            date_text = str(data["situation"]["situation_date"])
            notes_text = str(data["situation"].get("notes") or "")
            item_rows = data["items"]
        else:
            report = project_progress_report(project_id)
            number = 1 + max((int(row["situation_number"]) for row in report["situations"]), default=0)
            title_text = f"Situation N°{number}"
            date_text = QDate.currentDate().toString("yyyy-MM-dd")
            notes_text = ""
            item_rows = report["items"]

        dialog = QDialog(self)
        dialog.setWindowTitle(translate_text("Edit Situation") if situation_id else translate_text("New Situation"))
        dialog.resize(1150, 700)
        root = QVBoxLayout(dialog)

        meta = QFormLayout()
        date_edit = QDateEdit(QDate.fromString(date_text, "yyyy-MM-dd"))
        if not date_edit.date().isValid():
            date_edit.setDate(QDate.currentDate())
        date_edit.setCalendarPopup(True)
        title_edit = QLineEdit(title_text)
        notes_edit = QPlainTextEdit(notes_text)
        notes_edit.setMaximumHeight(90)
        meta.addRow(translate_text("Date"), date_edit)
        meta.addRow(translate_text("Title"), title_edit)
        meta.addRow(translate_text("Notes"), notes_edit)
        root.addLayout(meta)

        table = QTableWidget(len(item_rows), 7)
        table.setHorizontalHeaderLabels(
            [
                translate_text("No."),
                translate_text("Description"),
                translate_text("Unit"),
                translate_text("BOQ Qty"),
                translate_text("Previous"),
                translate_text("Current"),
                translate_text("Amount"),
            ]
        )
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        for row_index, item in enumerate(item_rows):
            item_id = str(item["item_id"])
            contract_qty = float(item.get("contract_quantity", item.get("quantity", 0)) or 0)
            previous = float(item.get("previous_quantity", item.get("cumulative_quantity", 0)) or 0)
            current = float(item.get("current_quantity", 0) or 0)
            unit_price = float(item.get("unit_price", 0) or 0)

            no_item = QTableWidgetItem(str(item.get("item_number") or "-"))
            no_item.setData(Qt.ItemDataRole.UserRole, item_id)
            table.setItem(row_index, 0, no_item)
            table.setItem(row_index, 1, QTableWidgetItem(str(item.get("description") or "")))
            table.setItem(row_index, 2, QTableWidgetItem(str(item.get("unit") or "")))
            table.setItem(row_index, 3, QTableWidgetItem(f"{contract_qty:.3f}"))
            table.setItem(row_index, 4, QTableWidgetItem(f"{previous:.3f}"))

            remaining_for_row = max(0.0, contract_qty - previous)
            spin = QDoubleSpinBox()
            spin.setDecimals(3)
            spin.setRange(0.0, remaining_for_row if not situation_id else remaining_for_row + current)
            spin.setValue(min(current, spin.maximum()))
            table.setCellWidget(row_index, 5, spin)
            amount_item = QTableWidgetItem(f"{spin.value() * unit_price:,.2f}")
            table.setItem(row_index, 6, amount_item)

            spin.valueChanged.connect(
                lambda value, target=amount_item, price=unit_price: target.setText(f"{value * price:,.2f}")
            )

        root.addWidget(table, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        root.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        quantities: dict[str, float] = {}
        for row_index in range(table.rowCount()):
            item = table.item(row_index, 0)
            spin = table.cellWidget(row_index, 5)
            if item is None or not isinstance(spin, QDoubleSpinBox):
                continue
            item_id = str(item.data(Qt.ItemDataRole.UserRole) or "")
            if item_id:
                quantities[item_id] = spin.value()

        try:
            save_situation(
                project_id,
                date_edit.date().toString("yyyy-MM-dd"),
                title_edit.text().strip() or None,
                notes_edit.toPlainText().strip() or None,
                quantities,
                situation_id=situation_id,
            )
            self.load()
        except (sqlite3.Error, TypeError, ValueError) as exc:
            self.error(str(exc))

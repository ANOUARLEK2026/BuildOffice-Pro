"""Reusable automation UI for BuildOffice Pro."""
from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.i18n import translate_text
from database.database import get_connection
from services.automation_service import (
    generate_one_click_report,
    import_rows,
    parse_rows,
    suggest_mapping,
)


class AutomationCenterDialog(QDialog):
    """One-click automation center: import, render and inspect the app state."""
    def __init__(self, parent=None, preferred_project_id: str | None = None):
        super().__init__(parent)
        self.preferred_project_id = preferred_project_id
        self.setWindowTitle(translate_text("Automation Center"))
        self.resize(900, 650)
        root = QVBoxLayout(self)
        intro = QLabel(translate_text("Automate repetitive work instead of re-entering data."))
        intro.setWordWrap(True)
        root.addWidget(intro)

        actions = QHBoxLayout()
        self.import_button = QPushButton(translate_text("📥 Batch Import CSV / Excel"))
        self.import_button.clicked.connect(self.batch_import)
        actions.addWidget(self.import_button)
        self.report_button = QPushButton(translate_text("📄 One-Click Project Report"))
        self.report_button.clicked.connect(self.report)
        actions.addWidget(self.report_button)
        actions.addStretch()
        root.addLayout(actions)

        self.preview = QTableWidget(0, 3)
        self.preview.setHorizontalHeaderLabels([translate_text("Automation"), translate_text("What it does"), translate_text("Status")])
        for row in [
            ("Smart defaults", "Uses current date, recent values and current project context", "ACTIVE"),
            ("Computed fields", "Recalculates derived amounts, dates and ratios automatically", "ACTIVE"),
            ("Batch import", "Reads CSV/XLSX and maps columns before inserting", "ACTIVE"),
            ("Event automation", "Allows post-save and status-change workflows", "ACTIVE"),
            ("One-click rendering", "Reuses existing report/document generators", "ACTIVE"),
        ]:
            r = self.preview.rowCount(); self.preview.insertRow(r)
            for c, value in enumerate(row): self.preview.setItem(r, c, QTableWidgetItem(value))
        root.addWidget(self.preview, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def batch_import(self):
            path, _ = QFileDialog.getOpenFileName(self, translate_text("Choose import file"), "", "CSV (*.csv);;Excel (*.xlsx *.xlsm)")
            if not path:
                return
            try:
                headers, rows = parse_rows(path)
                dialog = ImportMappingDialog(path, headers, rows, self)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return
                result = dialog.result
                QMessageBox.information(self, translate_text("Import completed"), translate_text(f"Imported {result['inserted']} row(s). Skipped: {len(result['skipped'])}."))
            except Exception as exc:  # noqa: BLE001
                # Fallback to prevent UI crash and display error to the user
                QMessageBox.critical(self, translate_text("Import failed"), str(exc))
                
    def report(self):
            kind = "project_financial" if self.preferred_project_id else "expense"
            try:
                paths = generate_one_click_report(kind, project_id=self.preferred_project_id, fmt="CSV")
                QMessageBox.information(self, translate_text("Report generated"), "\n".join(str(p) for p in paths))
            except Exception as exc:  # noqa: BLE001
                # Fallback to prevent UI crash and display error to the user
                QMessageBox.critical(self, translate_text("Report failed"), str(exc))


class ImportMappingDialog(QDialog):
    def __init__(self, path: str, headers: list[Any], rows: list[list[Any]], parent=None):
        super().__init__(parent)
        self.path, self.headers, self.rows = path, headers, rows
        self.result: dict[str, Any] = {}
        self.setWindowTitle(translate_text("Batch Import Mapping"))
        self.resize(850, 640)
        root = QVBoxLayout(self)
        info = QLabel(translate_text(f"Detected {len(rows)} data row(s). Map the columns once, then import the batch."))
        root.addWidget(info)
        form = QFormLayout()
        self.table = QComboBox()
        conn = get_connection()
        try:
            names = [str(r[0]) for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        finally:
            conn.close()
        self.table.addItems(names)
        form.addRow(translate_text("Target table"), self.table)
        root.addLayout(form)

        self.mapping = QTableWidget()
        self.mapping.setColumnCount(2)
        self.mapping.setHorizontalHeaderLabels([translate_text("Target column"), translate_text("Source column")])
        root.addWidget(self.mapping, 1)
        self.table.currentTextChanged.connect(self.refresh_mapping)
        self.refresh_mapping(self.table.currentText())

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept_import)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def refresh_mapping(self, table: str):
        conn = get_connection()
        try:
            columns = [str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})")]
        finally:
            conn.close()
        auto = suggest_mapping(self.headers, columns)
        self.mapping.setRowCount(len(columns))
        for r, col in enumerate(columns):
            self.mapping.setItem(r, 0, QTableWidgetItem(col))
            combo = QComboBox(); combo.addItem(""); combo.addItems([str(h) for h in self.headers])
            if col in auto:
                idx = combo.findText(auto[col]);
                if idx >= 0: combo.setCurrentIndex(idx)
            self.mapping.setCellWidget(r, 1, combo)

    def accept_import(self):
            mapping: dict[str, str] = {}
            for r in range(self.mapping.rowCount()):
                # Safely get target text by checking for None first
                item = self.mapping.item(r, 0)
                target = item.text() if item is not None else ""
                
                # Safely verify widget is a QComboBox before accessing currentText
                widget = self.mapping.cellWidget(r, 1)
                source = widget.currentText() if isinstance(widget, QComboBox) else ""
                
                if source:
                    mapping[target] = source
            try:
                self.result = import_rows(self.table.currentText(), self.headers, self.rows, mapping)
            except Exception as exc:  # noqa: BLE001
                # Fallback to prevent UI crash and display error to the user
                QMessageBox.critical(self, translate_text("Import failed"), str(exc))
                return
            self.accept()

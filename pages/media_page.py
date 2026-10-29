# ============================================================
# شرح الملف: pages/media_page.py
# مركز موحد للصور والمستندات والمرفقات في BuildOffice Pro.
# ============================================================
from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from core.i18n import translate_text
from repositories.db import get_connection
from services.audit_service import audit
from services.media_service import add_media, delete_media

from .base_page import BasePage, set_button


class MediaPage(BasePage):
    """Central media/attachment registry with generic owner linking."""

    TYPES: ClassVar[dict[str, str]] = {
        "Photo": "Photo",
        "Document": "Document",
        "Receipt": "Receipt",
        "Other": "Other",
    }
    OWNERS: ClassVar[dict[str, str]] = {
        "Company": "company",
        "Project": "project",
        "Partner": "partner",
        "Staff": "staff",
        "Vehicle": "vehicle",
        "Expense": "expense",
        "Invoice": "invoice",
        "Purchase": "purchase",
        "Other": "other",
    }

    def __init__(self):
        super().__init__(
            "Photos & Attachments",
            "One managed library for photos, receipts and documents linked to business records.",
        )
        self._build()
        self.refresh()

    def _build(self):
        # BasePage.body is already a QVBoxLayout, so do not wrap it in another layout.
        root = self.body
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(9)

        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(translate_text("Search file name or description"))
        self.search.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search, 1)

        self.type_box = QComboBox()
        self.type_box.addItem(translate_text("All types"), "All")
        for label, value in self.TYPES.items():
            self.type_box.addItem(translate_text(label), value)
        self.type_box.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.type_box)

        self.owner_box = QComboBox()
        self.owner_box.addItem(translate_text("All owners"), "All")
        for label, value in self.OWNERS.items():
            self.owner_box.addItem(translate_text(label), value)
        self.owner_box.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.owner_box)

        add = QPushButton(translate_text("Add attachment"))
        set_button(add, "primary")
        add.clicked.connect(self.add_attachment)
        toolbar.addWidget(add)

        open_btn = QPushButton(translate_text("Open"))
        set_button(open_btn, "secondary")
        open_btn.clicked.connect(self.open_selected)
        toolbar.addWidget(open_btn)

        delete = QPushButton(translate_text("Delete"))
        set_button(delete, "danger")
        delete.clicked.connect(self.remove_selected)
        toolbar.addWidget(delete)

        root.addLayout(toolbar)

        hint = QLabel(translate_text(
            "Files are copied into BuildOffice Pro's managed media folder; the original file is not modified."
        ))
        hint.setObjectName("secondaryText")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            translate_text("File"), translate_text("Type"), translate_text("Owner"),
            translate_text("Owner ID"), translate_text("Size"), translate_text("Created"),
            translate_text("Description"),
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(lambda *_: self.open_selected())
        root.addWidget(self.table, 1)

        self.status = QLabel()
        self.status.setObjectName("secondaryText")
        root.addWidget(self.status)

    def refresh(self, *_):
        text = self.search.text().strip()
        media_type = self.type_box.currentData()
        owner = self.owner_box.currentData()
        conn = get_connection()
        try:
            sql = """SELECT media_id,file_name,media_type,owner_type,owner_id,
                            file_size,created_at,description,file_path
                     FROM media_items WHERE 1=1"""
            params=[]
            if media_type != "All":
                sql += " AND media_type=?"; params.append(media_type)
            if owner != "All":
                sql += " AND owner_type=?"; params.append(owner)
            if text:
                sql += " AND (file_name LIKE ? OR description LIKE ?)"
                q=f"%{text}%"; params += [q,q]
            sql += " ORDER BY created_at DESC"
            rows=conn.execute(sql,params).fetchall()
        finally:
            conn.close()

        self.table.setRowCount(len(rows))
        for r,row in enumerate(rows):
            size = row["file_size"] or 0
            if size >= 1024*1024:
                size_text=f"{size/(1024*1024):.1f} MB"
            elif size >= 1024:
                size_text=f"{size/1024:.1f} KB"
            else:
                size_text=f"{size} B"
            vals=[
                row["file_name"], row["media_type"], row["owner_type"],
                row["owner_id"] or "", size_text, row["created_at"] or "",
                row["description"] or "",
            ]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(str(v)))

            file_item = self.table.item(r, 0)
            if file_item is not None:
                file_item.setData(
                    256,
                    (row["media_id"], row["file_path"]),
                )
        self.status.setText(translate_text(f"{len(rows)} attachments"))

    def add_attachment(self):
        path,_=QFileDialog.getOpenFileName(
            self, translate_text("Select attachment"), "",
            translate_text("All files (*)")
        )
        if not path:
            return

        dialog = QMessageBox(self)
        dialog.setWindowTitle(translate_text("Attachment details"))
        dialog.setText(translate_text("Choose attachment type, then continue."))
        # Use a compact custom selection through a child widget instead of
        # introducing a second permanent page.
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout
        d=QDialog(self)
        d.setWindowTitle(translate_text("Attachment details"))
        form=QFormLayout(d)
        type_box=QComboBox()
        for label,value in self.TYPES.items():
            type_box.addItem(translate_text(label),value)
        owner_box=QComboBox()
        for label,value in self.OWNERS.items():
            owner_box.addItem(translate_text(label),value)
        owner_id=QLineEdit()
        owner_id.setPlaceholderText(translate_text("Optional record ID, e.g. PRG-007"))
        desc=QLineEdit()
        form.addRow(translate_text("Type"),type_box)
        form.addRow(translate_text("Owner"),owner_box)
        form.addRow(translate_text("Owner ID"),owner_id)
        form.addRow(translate_text("Description"),desc)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(d.accept); buttons.rejected.connect(d.reject)
        form.addRow(buttons)
        if d.exec()!=QDialog.DialogCode.Accepted:
            return
        try:
            mid=add_media(owner_box.currentData(), owner_id.text().strip() or None,
                          path, type_box.currentData(), desc.text().strip())
            audit("CREATE","media",mid,f"Added attachment {Path(path).name}")
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.critical(
                self,
                translate_text("Database error"),
                str(exc),
            )
            return
        self.refresh()

    def _selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None

        item = self.table.item(rows[0].row(), 0)
        if item is None:
            return None

        return item.data(256)

    def open_selected(self):
        data=self._selected()
        if not data: return
        _,path=data
        if Path(path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.warning(self,translate_text("File not found"),
                                translate_text("The managed file is missing from disk."))

    def remove_selected(self):
        data=self._selected()
        if not data: return
        mid,_=data
        if QMessageBox.question(self,translate_text("Delete"),
            translate_text("Delete this attachment from the managed library?")) != QMessageBox.StandardButton.Yes:
            return
        try:
            delete_media(mid)
            audit("DELETE","media",mid,"Deleted managed attachment")
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.critical(
                self,
                translate_text("Database error"),
                str(exc),
            )
            return
        self.refresh()

# ============================================================
# شرح الملف: contacts_page.py
# دليل العملاء والموردين لأساس المرحلة الأولى من BuildOffice Pro.
# الواجهة تبقى منفصلة عن منطق قاعدة البيانات لتسهيل التوسع المحاسبي لاحقًا.
# ============================================================
from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.i18n import translate_text
from repositories.db import get_connection
from theme import set_theme_style


class PartnerDialog(QDialog):
    """Create or edit one client/supplier master record."""

    def __init__(self, parent: QWidget | None = None, row=None):
        super().__init__(parent)
        self.setWindowTitle(translate_text("Business Partner"))
        self.setMinimumWidth(520)

        form = QFormLayout(self)
        form.setSpacing(9)

        self.type_box = QComboBox()
        self.type_box.addItem(translate_text("Client"), "Client")
        self.type_box.addItem(translate_text("Supplier"), "Supplier")
        self.type_box.addItem(translate_text("Both"), "Both")

        self.name = QLineEdit()
        self.display = QLineEdit()
        self.contact = QLineEdit()
        self.phone = QLineEdit()
        self.phone2 = QLineEdit()
        self.email = QLineEdit()
        self.address = QLineEdit()
        self.wilaya = QLineEdit()
        self.tax_id = QLineEdit()
        self.nis = QLineEdit()
        self.rc = QLineEdit()
        self.ai = QLineEdit()
        self.rib = QLineEdit()
        self.bank = QLineEdit()
        self.terms = QLineEdit()
        self.notes = QLineEdit()

        fields = [
            ("Type", self.type_box),
            ("Legal name", self.name),
            ("Display name", self.display),
            ("Contact person", self.contact),
            ("Phone", self.phone),
            ("Phone 2", self.phone2),
            ("Email", self.email),
            ("Address", self.address),
            ("Wilaya", self.wilaya),
            ("Tax ID / NIF", self.tax_id),
            ("NIS", self.nis),
            ("Commercial register / RC", self.rc),
            ("AI", self.ai),
            ("RIB", self.rib),
            ("Bank", self.bank),
            ("Payment terms (days)", self.terms),
            ("Notes", self.notes),
        ]
        for label, widget in fields:
            form.addRow(translate_text(label), widget)

        if row:
            values = dict(row)
            idx = self.type_box.findData(values.get("partner_type"))
            if idx >= 0:
                self.type_box.setCurrentIndex(idx)
            mapping = {
                "legal_name": self.name, "display_name": self.display,
                "contact_person": self.contact, "phone": self.phone,
                "phone_2": self.phone2, "email": self.email,
                "address": self.address, "wilaya": self.wilaya,
                "tax_id": self.tax_id, "nis": self.nis, "rc": self.rc,
                "ai": self.ai, "rib": self.rib, "bank_name": self.bank,
                "payment_terms_days": self.terms, "notes": self.notes,
            }
            for key, widget in mapping.items():
                value = values.get(key)
                if value is not None:
                    widget.setText(str(value))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def payload(self) -> dict:
        terms = self.terms.text().strip() or "0"
        try:
            terms_value = max(0, int(terms))
        except ValueError:
            terms_value = 0
        return {
            "partner_type": self.type_box.currentData(),
            "legal_name": self.name.text().strip(),
            "display_name": self.display.text().strip() or None,
            "contact_person": self.contact.text().strip() or None,
            "phone": self.phone.text().strip() or None,
            "phone_2": self.phone2.text().strip() or None,
            "email": self.email.text().strip() or None,
            "address": self.address.text().strip() or None,
            "wilaya": self.wilaya.text().strip() or None,
            "tax_id": self.tax_id.text().strip() or None,
            "nis": self.nis.text().strip() or None,
            "rc": self.rc.text().strip() or None,
            "ai": self.ai.text().strip() or None,
            "rib": self.rib.text().strip() or None,
            "bank_name": self.bank.text().strip() or None,
            "payment_terms_days": terms_value,
            "notes": self.notes.text().strip() or None,
        }


class ContactsPage(QWidget):
    """Central directory for clients and suppliers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_id: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        title = QLabel(translate_text("Clients & Suppliers"))
        title.setObjectName("pageTitle")
        root.addWidget(title)

        intro = QLabel(translate_text(
            "One master directory for parties used by projects, purchasing and future accounting."
        ))
        intro.setWordWrap(True)
        intro.setObjectName("secondaryText")
        root.addWidget(intro)

        toolbar = QHBoxLayout()
        self.filter = QComboBox()
        self.filter.addItem(translate_text("All"), "All")
        self.filter.addItem(translate_text("Clients"), "Client")
        self.filter.addItem(translate_text("Suppliers"), "Supplier")
        self.filter.addItem(translate_text("Both"), "Both")
        self.filter.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.filter)

        self.search = QLineEdit()
        self.search.setPlaceholderText(translate_text("Search by name, phone, NIF or RC"))
        self.search.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search, 1)

        add = QPushButton(translate_text("Add"))
        add.clicked.connect(self.add_partner)
        toolbar.addWidget(add)

        edit = QPushButton(translate_text("Edit"))
        edit.clicked.connect(self.edit_partner)
        toolbar.addWidget(edit)

        delete = QPushButton(translate_text("Deactivate"))
        delete.clicked.connect(self.deactivate_partner)
        toolbar.addWidget(delete)

        root.addLayout(toolbar)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            translate_text("Name"),
            translate_text("Type"),
            translate_text("Contact"),
            translate_text("Phone"),
            translate_text("Wilaya"),
            translate_text("NIF"),
            translate_text("Status"),
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(lambda *_: self.edit_partner())
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, 1)

        self.status = QLabel()
        self.status.setObjectName("secondaryText")
        root.addWidget(self.status)

        set_theme_style(self, """
            QTableWidget { border: 1px solid @border@; border-radius: 10px; }
            QLineEdit, QComboBox { min-height: 34px; }
        """)
        self.refresh()

    def refresh(self, *_):
        query = self.search.text().strip()
        ptype = self.filter.currentData()
        conn = get_connection()
        try:
            sql = """
                SELECT partner_id, partner_type, legal_name, contact_person,
                       phone, wilaya, tax_id, status
                FROM business_partners
                WHERE 1=1
            """
            params = []
            if ptype != "All":
                sql += " AND partner_type=?"
                params.append(ptype)
            if query:
                sql += """ AND (
                    legal_name LIKE ? OR display_name LIKE ? OR
                    phone LIKE ? OR tax_id LIKE ? OR rc LIKE ?
                )"""
                q = f"%{query}%"
                params.extend([q, q, q, q, q])
            sql += " ORDER BY legal_name COLLATE NOCASE"
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()

        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            vals = [
                row["legal_name"],
                row["partner_type"],
                row["contact_person"] or "",
                row["phone"] or "",
                row["wilaya"] or "",
                row["tax_id"] or "",
                row["status"],
            ]
            for c, value in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(str(value)))
            for c, value in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(str(value)))

            item = self.table.item(r, 0)
            if item is not None:
                item.setData(Qt.ItemDataRole.UserRole, row["partner_id"])
        self.status.setText(translate_text(f"{len(rows)} business partners"))

    def _selected_id(self) -> str | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None

        item = self.table.item(rows[0].row(), 0)
        if item is None:
            return None

        value = item.data(Qt.ItemDataRole.UserRole)
        return str(value) if value is not None else None

    def add_partner(self):
        dialog = PartnerDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.payload()
        if not data["legal_name"]:
            QMessageBox.warning(self, translate_text("Validation"), translate_text("Legal name is required."))
            return
        partner_id = f"BP-{self._next_number()}"
        conn = get_connection()
        try:
            conn.execute("""
                INSERT INTO business_partners (
                    partner_id, partner_type, legal_name, display_name,
                    contact_person, phone, phone_2, email, address, wilaya,
                    postal_code, tax_id, nis, rc, ai, rib, bank_name,
                    payment_terms_days, notes
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                partner_id, data["partner_type"], data["legal_name"],
                data["display_name"], data["contact_person"], data["phone"],
                data["phone_2"], data["email"], data["address"], data["wilaya"],
                None, data["tax_id"], data["nis"], data["rc"], data["ai"],
                data["rib"], data["bank_name"], data["payment_terms_days"],
                data["notes"],
            ))
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            QMessageBox.critical(self, translate_text("Database error"), str(exc))
            return
        finally:
            conn.close()
        self.refresh()

    def _next_number(self) -> str:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTR(partner_id,4) AS INTEGER)),0)+1 FROM business_partners WHERE partner_id LIKE 'BP-%'"
            ).fetchone()
            return f"{int(row[0]):05d}"
        finally:
            conn.close()

    def edit_partner(self):
        partner_id = self._selected_id()
        if not partner_id:
            return
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM business_partners WHERE partner_id=?", (partner_id,)
            ).fetchone()
        finally:
            conn.close()
        if not row:
            return

        dialog = PartnerDialog(self, row)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.payload()
        if not data["legal_name"]:
            QMessageBox.warning(self, translate_text("Validation"), translate_text("Legal name is required."))
            return

        conn = get_connection()
        try:
            conn.execute("""
                UPDATE business_partners SET
                    partner_type=?, legal_name=?, display_name=?, contact_person=?,
                    phone=?, phone_2=?, email=?, address=?, wilaya=?, tax_id=?,
                    nis=?, rc=?, ai=?, rib=?, bank_name=?, payment_terms_days=?,
                    notes=?, updated_at=CURRENT_TIMESTAMP
                WHERE partner_id=?
            """, (
                data["partner_type"], data["legal_name"], data["display_name"],
                data["contact_person"], data["phone"], data["phone_2"],
                data["email"], data["address"], data["wilaya"], data["tax_id"],
                data["nis"], data["rc"], data["ai"], data["rib"], data["bank_name"],
                data["payment_terms_days"], data["notes"], partner_id,
            ))
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            QMessageBox.critical(self, translate_text("Database error"), str(exc))
            return
        finally:
            conn.close()
        self.refresh()

    def deactivate_partner(self):
        partner_id = self._selected_id()
        if not partner_id:
            return
        answer = QMessageBox.question(
            self,
            translate_text("Deactivate"),
            translate_text("Deactivate this business partner? Existing records will be preserved."),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE business_partners SET status='Inactive', updated_at=CURRENT_TIMESTAMP WHERE partner_id=?",
                (partner_id,),
            )
            conn.commit()
        finally:
            conn.close()
        self.refresh()

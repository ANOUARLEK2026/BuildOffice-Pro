# ============================================================
# شرح الملف: pages/administration_page.py
# إدارة المستخدمين والصلاحيات الأساسية وسجل التدقيق.
# ============================================================
from __future__ import annotations

import sqlite3

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.i18n import translate_text
from repositories.db import get_connection
from services.audit_service import audit
from services.license_service import create_user

from .base_page import BasePage, set_button


class UserDialog(QDialog):
    ROLES=("Administrator","Accountant","Project Manager","Site Manager","HR","Employee","Viewer")
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle(translate_text("Add user"))
        form=QFormLayout(self)
        self.username=QLineEdit()
        self.password=QLineEdit(); self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm=QLineEdit(); self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.role=QComboBox()
        for role in self.ROLES: self.role.addItem(translate_text(role),role)
        form.addRow(translate_text("Username"),self.username)
        form.addRow(translate_text("Password"),self.password)
        form.addRow(translate_text("Confirm password"),self.confirm)
        form.addRow(translate_text("Role"),self.role)
        b=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        b.accepted.connect(self._validate); b.rejected.connect(self.reject)
        form.addRow(b)

    def _validate(self):
        if len(self.username.text().strip())<3:
            QMessageBox.warning(self,translate_text("Validation"),translate_text("Username must contain at least 3 characters.")); return
        if len(self.password.text())<8:
            QMessageBox.warning(self,translate_text("Validation"),translate_text("Password must contain at least 8 characters.")); return
        if self.password.text()!=self.confirm.text():
            QMessageBox.warning(self,translate_text("Validation"),translate_text("Passwords do not match.")); return
        self.accept()


class AdministrationPage(BasePage):
    def __init__(self):
        super().__init__("Administration","Users, roles and audit trail")
        self._build()
        self.refresh_users()
        self.refresh_audit()

    def _build(self):
        tabs=QTabWidget()
        users=QWidget(); ul=QVBoxLayout(users)
        toolbar=QHBoxLayout()
        add=QPushButton(translate_text("Add user")); set_button(add,"primary"); add.clicked.connect(self.add_user)
        toggle=QPushButton(translate_text("Activate / Deactivate")); set_button(toggle,"secondary"); toggle.clicked.connect(self.toggle_user)
        toolbar.addWidget(add); toolbar.addWidget(toggle); toolbar.addStretch(1)
        ul.addLayout(toolbar)
        self.users=QTableWidget(0,5)
        self.users.setHorizontalHeaderLabels([translate_text("Username"),translate_text("Role"),translate_text("Active"),translate_text("Created"),translate_text("Last login")])
        self.users.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.users.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.users.horizontalHeader().setStretchLastSection(True)
        ul.addWidget(self.users,1)
        tabs.addTab(users,translate_text("Users"))

        audit_tab=QWidget(); al=QVBoxLayout(audit_tab)
        ar=QHBoxLayout()
        self.audit_search=QLineEdit(); self.audit_search.setPlaceholderText(translate_text("Search audit trail"))
        self.audit_search.textChanged.connect(self.refresh_audit)
        ar.addWidget(self.audit_search,1)
        ref=QPushButton(translate_text("Refresh")); ref.clicked.connect(self.refresh_audit); ar.addWidget(ref)
        al.addLayout(ar)
        self.audit_table=QTableWidget(0,6)
        self.audit_table.setHorizontalHeaderLabels([translate_text("Date"),translate_text("User"),translate_text("Action"),translate_text("Entity"),translate_text("ID"),translate_text("Description")])
        self.audit_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.audit_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.audit_table.horizontalHeader().setStretchLastSection(True)
        al.addWidget(self.audit_table,1)
        tabs.addTab(audit_tab,translate_text("Audit trail"))
        self.body.addWidget(tabs)

    def _current_user(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return {}
        return app.property("buildoffice_current_user") or {}

    def _is_admin(self):
        return str(self._current_user().get("role","")).lower() in {"administrator","developer"}

    def _selected_user(self):
        rows = self.users.selectionModel().selectedRows()
        if not rows:
            return None

        item = self.users.item(rows[0].row(), 0)
        if item is None:
            return None

        return item.data(256)

    def refresh_users(self, *_):
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT user_id,username,role,active,created_at,last_login_at "
                "FROM app_users ORDER BY username"
            ).fetchall()
        finally:
            conn.close()

        self.users.setRowCount(len(rows))

        for r, row in enumerate(rows):
            vals = [
                row["username"],
                row["role"],
                "Yes" if row["active"] else "No",
                row["created_at"] or "",
                row["last_login_at"] or "",
            ]

            for c, value in enumerate(vals):
                self.users.setItem(r, c, QTableWidgetItem(str(value)))

            item = self.users.item(r, 0)
            if item is not None:
                item.setData(256, row["user_id"])

    def add_user(self):
        if not self._is_admin():
            QMessageBox.warning(
                self,
                translate_text("Permission denied"),
                translate_text("Only an administrator can manage users."),
            )
            return

        d = UserDialog(self)
        if d.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            create_user(
                d.username.text(),
                d.password.text(),
                d.role.currentData(),
            )

            conn = get_connection()
            try:
                row = conn.execute(
                    "SELECT user_id FROM app_users "
                    "WHERE username=? COLLATE NOCASE",
                    (d.username.text().strip(),),
                ).fetchone()
            finally:
                conn.close()

            audit(
                "CREATE",
                "user",
                row["user_id"] if row else None,
                f"Created user {d.username.text().strip()}",
            )

        except (sqlite3.Error, ValueError, TypeError, OSError, RuntimeError) as exc:
            QMessageBox.critical(
                self,
                translate_text("Cannot create user"),
                str(exc),
            )
            return

        self.refresh_users()

    def toggle_user(self):
        if not self._is_admin():
            QMessageBox.warning(self,translate_text("Permission denied"),translate_text("Only an administrator can manage users.")); return
        uid=self._selected_user()
        if not uid:return
        current=self._current_user()
        if uid==current.get("user_id"):
            QMessageBox.warning(self,translate_text("Not allowed"),translate_text("You cannot deactivate the currently signed-in account.")); return
        conn=get_connection()
        try:
            row=conn.execute("SELECT active,username FROM app_users WHERE user_id=?",(uid,)).fetchone()
            if not row:return
            new=0 if row["active"] else 1
            conn.execute("UPDATE app_users SET active=? WHERE user_id=?",(new,uid)); conn.commit()
        finally: conn.close()
        audit("UPDATE","user",uid,f"{'Activated' if new else 'Deactivated'} user {row['username']}")
        self.refresh_users()

    def refresh_audit(self,*_):
        q=self.audit_search.text().strip()
        conn=get_connection()
        try:
            if q:
                like=f"%{q}%"
                rows=conn.execute("""SELECT occurred_at,user_name,action,entity,entity_id,description
                    FROM audit_log WHERE user_name LIKE ? OR action LIKE ? OR entity LIKE ?
                    OR entity_id LIKE ? OR description LIKE ? ORDER BY occurred_at DESC LIMIT 1000""",
                    (like,like,like,like,like)).fetchall()
            else:
                rows=conn.execute("""SELECT occurred_at,user_name,action,entity,entity_id,description
                    FROM audit_log ORDER BY occurred_at DESC LIMIT 1000""").fetchall()
        finally: conn.close()
        self.audit_table.setRowCount(len(rows))
        for r,row in enumerate(rows):
            for c,key in enumerate(("occurred_at","user_name","action","entity","entity_id","description")):
                self.audit_table.setItem(r,c,QTableWidgetItem(str(row[key] or "")))

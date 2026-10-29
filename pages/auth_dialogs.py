# ============================================================
# شرح الملف: pages/auth_dialogs.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: واجهة تسجيل الدخول وتفعيل BuildOffice Pro.
"""Commercial-style activation, first-run setup, and login dialogs."""
from __future__ import annotations

import sqlite3
from binascii import Error as BinasciiError

from cryptography.exceptions import InvalidSignature
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from core.i18n import translate_text
from services.license_service import (
    activate_license,
    authenticate,
    create_user,
    device_id,
    license_status,
    user_count,
)
from theme.qss import resolve_style, set_theme_style


# شرح الدالة _button: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _button(text: str) -> QPushButton:
    btn = QPushButton(translate_text(text))
    btn.setMinimumHeight(40)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


# شرح الصنف SecurityDialog: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class SecurityDialog(QDialog):
    """Base dialog shared by the security screens."""

    def __init__(self, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translate_text(title))
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setObjectName("securityDialog")

        root = QVBoxLayout(self)
        root.setContentsMargins(34, 30, 34, 30)
        root.setSpacing(14)

        brand = QLabel("BO")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setFixedSize(68, 68)
        set_theme_style(
            brand,
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 @components.navigation.navigation@, "
            "stop:1 @components.navigation.navigation_accent@); color:@components.theme.on_colored_surface@; "
            "border-radius:20px; font-size:26px; font-weight:700;"
        )
        root.addWidget(brand, 0, Qt.AlignmentFlag.AlignHCenter)

        heading = QLabel(translate_text(title))
        heading.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(heading)

        desc = QLabel(translate_text(subtitle))
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setObjectName("securitySubtitle")
        root.addWidget(desc)

        self.body = QVBoxLayout()
        self.body.setSpacing(12)
        root.addLayout(self.body)


# شرح الصنف ActivationDialog: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class ActivationDialog(SecurityDialog):
    """Collect and verify a signed BuildOffice Pro license key."""

    def __init__(self, parent=None):
        super().__init__(
            "Activate BuildOffice Pro",
            "Enter the license key supplied with your purchase to activate this installation.",
            parent,
        )
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText(translate_text("BOP1.…"))
        self.key_edit.setMinimumHeight(44)
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        self.body.addWidget(QLabel(translate_text("License key")))
        self.body.addWidget(self.key_edit)

        device_label = QLabel(
            translate_text("Device ID: ") + device_id()[:12].upper() + "…"
        )
        device_label.setObjectName("securityDevice")
        self.body.addWidget(device_label)

        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setObjectName("securityError")
        self.body.addWidget(self.error_label)

        row = QHBoxLayout()
        cancel = _button("Exit")
        activate = _button("Activate")
        activate.setDefault(True)
        cancel.clicked.connect(self.reject)
        activate.clicked.connect(self._activate)
        self.key_edit.returnPressed.connect(self._activate)
        row.addWidget(cancel)
        row.addWidget(activate)
        self.body.addLayout(row)

        self.license = None

# شرح الدالة _activate: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _activate(self):
        try:
            self.license = activate_license(self.key_edit.text())
        except (ValueError, TypeError, KeyError, OSError, sqlite3.Error, InvalidSignature, BinasciiError) as exc:
            self.error_label.setText(translate_text(str(exc)))
            self.key_edit.selectAll()
            self.key_edit.setFocus()
            return
        self.accept()


# شرح الصنف SetupDialog: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class SetupDialog(SecurityDialog):
    """Create the first local administrator after license activation."""

    def __init__(self, parent=None):
        super().__init__(
            "Create administrator",
            "Set the account used to sign in to this BuildOffice Pro installation.",
            parent,
        )
        form = QFormLayout()
        form.setSpacing(10)

        self.username = QLineEdit()
        self.username.setMinimumHeight(42)
        self.username.setPlaceholderText(translate_text("Administrator"))
        form.addRow(translate_text("Username"), self.username)

        self.password = QLineEdit()
        self.password.setMinimumHeight(42)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(translate_text("Password"), self.password)

        self.confirm = QLineEdit()
        self.confirm.setMinimumHeight(42)
        self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(translate_text("Confirm password"), self.confirm)

        self.body.addLayout(form)

        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setObjectName("securityError")
        self.body.addWidget(self.error_label)

        create = _button("Create administrator")
        create.setDefault(True)
        create.clicked.connect(self._create)
        self.body.addWidget(create)

        self.username.setFocus()

# شرح الدالة _create: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _create(self):
        if self.password.text() != self.confirm.text():
            self.error_label.setText(translate_text("Passwords do not match."))
            return
        try:
            create_user(self.username.text(), self.password.text())
        except (ValueError, TypeError, KeyError, OSError, sqlite3.Error, InvalidSignature, BinasciiError) as exc:
            self.error_label.setText(translate_text(str(exc)))
            return
        self.accept()


# شرح الصنف LoginDialog: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class LoginDialog(SecurityDialog):
    """Authenticate an existing local user before opening the application."""

    def __init__(self, parent=None):
        status = license_status()
        customer = (status or {}).get("customer_name", "Licensed customer")
        super().__init__(
            "Sign in to BuildOffice Pro",
            f"{translate_text('Licensed to')}: {customer}",
            parent,
        )
        form = QFormLayout()
        form.setSpacing(10)

        self.username = QLineEdit()
        self.username.setMinimumHeight(42)
        self.username.setPlaceholderText(translate_text("Username"))
        form.addRow(translate_text("Username"), self.username)

        self.password = QLineEdit()
        self.password.setMinimumHeight(42)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setMinimumHeight(42)
        form.addRow(translate_text("Password"), self.password)

        self.body.addLayout(form)

        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setObjectName("securityError")
        self.body.addWidget(self.error_label)

        row = QHBoxLayout()
        exit_btn = _button("Exit")
        login = _button("Sign in")
        login.setDefault(True)
        exit_btn.clicked.connect(self.reject)
        login.clicked.connect(self._login)
        self.password.returnPressed.connect(self._login)
        row.addWidget(exit_btn)
        row.addWidget(login)
        self.body.addLayout(row)

        self.user = None
        self.username.setFocus()

# شرح الدالة _login: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _login(self):
        self.user = authenticate(self.username.text(), self.password.text())
        if not self.user:
            self.error_label.setText(
                translate_text("Invalid username or password.")
            )
            self.password.selectAll()
            self.password.setFocus()
            return
        self.accept()


# شرح الدالة apply_security_style: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def apply_security_style(app) -> None:
    """Add only dialog-specific styling; the main application theme remains unchanged."""
    current = app.styleSheet()
    extra = """
        QDialog#securityDialog {
            background: @background@;
        }
        QDialog#securityDialog QLineEdit {
            border: 1px solid @components.forms.input_border@;
            border-radius: 12px;
            padding: 10px 14px;
            background: @surface@;
            font-size: 14px;
        }
        QDialog#securityDialog QLineEdit:focus {
            border: 1px solid @primary@;
        }
        QDialog#securityDialog QPushButton {
            border: 0;
            border-radius: 12px;
            padding: 10px 18px;
            background: @components.navigation.navigation@;
            color: @components.theme.on_colored_surface@;
            font-weight: 600;
            font-size: 13px;
        }
        QDialog#securityDialog QPushButton:hover {
            background: @components.navigation.nav_hover_alt@;
        }
        QDialog#securityDialog QPushButton:default {
            background: @primary@;
            color: @components.buttons.button_text@;
            font-weight: 700;
        }
        QDialog#securityDialog QPushButton:default:hover {
            background: @components.buttons.primary_hover@;
        }
        QLabel#securitySubtitle, QLabel#securityDevice {
            color: @text_secondary@;
            font-size: 13px;
        }
        QLabel#securityError {
            color: @danger@;
            padding: 5px;
        }
    """
    app.setStyleSheet(current + resolve_style(extra))


# شرح الدالة run_security_gate: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def run_security_gate(app) -> dict | None:
    """Run activation/setup/login in the correct order."""
    apply_security_style(app)

    if not license_status():
        activation = ActivationDialog()
        if activation.exec() != QDialog.DialogCode.Accepted:
            return None

    if user_count() == 0:
        setup = SetupDialog()
        if setup.exec() != QDialog.DialogCode.Accepted:
            return None

    login = LoginDialog()
    if login.exec() != QDialog.DialogCode.Accepted:
        return None
    return login.user

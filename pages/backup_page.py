# ============================================================
# شرح الملف: pages/backup_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
import sqlite3
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.i18n import translate_text

# عدّل هذا الاستيراد فقط إذا كانت دوال النسخ الاحتياطي
# موجودة في وحدة مختلفة داخل مشروعك.
from services.backup_service import (
    create_backup,
    restore_backup,
    validate_database,
)

from .base_page import BasePage


# شرح الصنف BackupPage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class BackupPage(BasePage):
    def __init__(self):
        super().__init__(
            "Backup & Restore",
            "Protect local company data and validate database backups",
        )

        # إنشاء الحاوية الرئيسية والـ layout بشكل صريح
        # لتجنب تعارض النوع مع self.panel().
        frame = QFrame()
        frame.setObjectName("sectionCard")

        content_layout = QVBoxLayout(frame)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(10)

        info = QLabel(
            translate_text(
                "Backups use SQLite's online backup API. "
                "Restoring first creates a safety backup of the current database."
            )
        )
        info.setWordWrap(True)
        info.setObjectName("sectionSubtitle")

        content_layout.addWidget(info)

        # أزرار النسخ الاحتياطي والاستعادة والتحقق
        row = QHBoxLayout()
        row.setSpacing(8)

        buttons = [
            ("Create backup", self.backup, "primaryButton"),
            ("Restore backup", self.restore, "dangerButton"),
            ("Validate backup", self.validate, "secondaryButton"),
        ]

        for text, slot, object_name in buttons:
            button = QPushButton(translate_text(text))
            button.clicked.connect(slot)
            button.setObjectName(object_name)
            row.addWidget(button)

        content_layout.addLayout(row)

        # قائمة سجل النسخ الاحتياطية
        self.history = QListWidget()
        self.history.setObjectName("backupHistory")
        content_layout.addWidget(self.history, 1)

        self.body.addWidget(frame)

        self.load_history()

# شرح الدالة _backup_folder: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _backup_folder(self) -> Path:
        """إرجاع مجلد النسخ الاحتياطية."""
        return Path(__file__).resolve().parent.parent / "backups"

# شرح الدالة load_history: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def load_history(self):
        """تحميل النسخ الاحتياطية الموجودة إلى القائمة."""
        folder = self._backup_folder()

        if not folder.exists():
            return

        self.history.clear()

        backups = sorted(
            folder.glob("*.db"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        self.history.addItems([str(path) for path in backups])

# شرح الدالة backup: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def backup(self):
        """إنشاء نسخة احتياطية جديدة من قاعدة البيانات."""
        folder = self._backup_folder()

        try:
            p = create_backup(folder)

            self.history.insertItem(0, str(p))

            QMessageBox.information(
                self,
                translate_text("BuildOffice Pro"),
                translate_text(f"Backup created:\n{p}"),
            )

        except (
            OSError,
            sqlite3.Error,
            ValueError,
            RuntimeError,
        ):
            self.error("Backup failed. The current database was not changed.")

# شرح الدالة validate: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def validate(self):
        """التحقق من سلامة ملف النسخة الاحتياطية."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            translate_text("Select backup"),
            "",
            "SQLite database (*.db)",
        )

        if not path:
            return

        try:
            valid = validate_database(path)

            if valid:
                self.success("Backup integrity: VALID.")
            else:
                self.error("Backup integrity: INVALID.")

        except (
            OSError,
            sqlite3.Error,
            ValueError,
            RuntimeError,
        ):
            self.error("Backup validation failed.")

# شرح الدالة restore: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def restore(self):
        """استعادة قاعدة البيانات بعد إنشاء نسخة أمان."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            translate_text("Select backup"),
            "",
            "SQLite database (*.db)",
        )

        if not path:
            return

        if not self.confirm(
            "A safety backup will be created before replacing "
            "the current database. Continue?",
            "Restore backup",
        ):
            return

        try:
            safety = restore_backup(path)

            QMessageBox.information(
                self,
                translate_text("BuildOffice Pro"),
                translate_text(
                    f"Restore completed.\n"
                    f"Safety backup:\n{safety}\n\n"
                    f"Restart the application to reload all pages."
                ),
            )

        except (
            OSError,
            sqlite3.Error,
            ValueError,
            RuntimeError,
        ):
            self.error("Restore failed. The current database was not replaced.")

# ============================================================
# شرح الملف: core/ux_features.py
# هذا الملف جزء من المكوّنات الأساسية المشتركة في التطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: طبقة تحسين تجربة الاستخدام، معزولة عن منطق الأعمال وقاعدة البيانات.
"""Low-risk UX features for BuildOffice Pro.

The module intentionally stays above the existing pages/services layer. It adds
navigation, search, notifications, recent/favorite projects and activity views
without changing business tables or existing page contracts.
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from database.database import get_connection
from services.settings_service import money_display
from theme import set_theme_style


# شرح الصنف UXStore: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class UXStore:
    """حفظ تفضيلات UX الصغيرة خارج مخطط قاعدة البيانات."""

    def __init__(self, path: Path):
        self.path = path
        self.data: dict[str, Any] = {"recent_projects": [], "favorite_projects": []}
        self.load()

# شرح الدالة load: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def load(self) -> None:
        try:
            if self.path.exists():
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self.data.update(raw)
        except (OSError, ValueError, TypeError):
            self.data = {"recent_projects": [], "favorite_projects": []}

# شرح الدالة save: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

# شرح الدالة _push: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _push(self, key: str, value: str, limit: int = 12) -> None:
        items = [str(x) for x in self.data.get(key, []) if str(x) != value]
        items.insert(0, value)
        self.data[key] = items[:limit]
        self.save()

# شرح الدالة add_recent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_recent(self, project_id: str) -> None:
        self._push("recent_projects", project_id)

# شرح الدالة toggle_favorite: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def toggle_favorite(self, project_id: str) -> bool:
        items = [str(x) for x in self.data.get("favorite_projects", [])]
        if project_id in items:
            items.remove(project_id)
            result = False
        else:
            items.insert(0, project_id)
            result = True
        self.data["favorite_projects"] = items[:50]
        self.save()
        return result

# شرح الدالة is_favorite: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def is_favorite(self, project_id: str) -> bool:
        return str(project_id) in [str(x) for x in self.data.get("favorite_projects", [])]



# شرح الدالة _query: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    conn = get_connection()
    try:
        return list(conn.execute(sql, params).fetchall())
    finally:
        conn.close()


# شرح الصنف _BaseDialog: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class _BaseDialog(QDialog):
    """حوار موحد للمظهر والأبعاد."""

    def __init__(self, parent=None, title: str = "BuildOffice Pro"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(860, 560)
        self.setModal(True)


# شرح الصنف NotificationCenterDialog: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class NotificationCenterDialog(_BaseDialog):
    """مركز إشعارات يقرأ السجل الموجود ويضيف تنبيهات آمنة مشتقة من البيانات."""

    def __init__(self, parent=None):
        super().__init__(parent, "Notification Center")
        root = QVBoxLayout(self)
        root.setSpacing(10)
        title = QLabel("🔔  Notification Center")
        title.setObjectName("dialogTitle")
        root.addWidget(title)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Severity", "Title", "Message", "Date"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

        row = QHBoxLayout()
        mark = QPushButton("✓ Mark all as read")
        mark.clicked.connect(self.mark_all_read)
        row.addWidget(mark)
        row.addStretch()
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        root.addLayout(row)
        self.populate()

# Function description: Executes a logical step related to this file's functionality.
    def populate(self):
        self._ensure_derived_notifications()
        rows = _query(
            "SELECT notification_id, severity, title, message, created_at "
            "FROM notifications ORDER BY is_read ASC, created_at DESC LIMIT 100"
        )
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [str(row[1] or "Info"), str(row[2]), str(row[3]), str(row[4])]
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(value))
            
            # Safely check if the item exists before setting data
            item = self.table.item(r, 0)
            if item is not None:
                item.setData(Qt.ItemDataRole.UserRole, row[0])
                
        self.table.resizeColumnsToContents()
        if self.table.columnWidth(2) < 260:
            self.table.setColumnWidth(2, 420)

# Function description: Executes a logical step related to this file's functionality.
    @staticmethod
    def _ensure_derived_notifications() -> None:
        """إنشاء تنبيهات مشتقة فقط عند الحاجة، مع منع التكرار."""
        conn = get_connection()
        try:
            overdue_expenses = conn.execute(
                "SELECT expense_id, description, due_date FROM expenses "
                "WHERE due_date IS NOT NULL AND due_date < date('now') "
                "AND payment_status != 'Paid' LIMIT 20"
            ).fetchall()
            for row in overdue_expenses:
                exists = conn.execute(
                    "SELECT 1 FROM notifications WHERE entity='Expense' AND entity_id=? "
                    "AND title='Overdue expense' LIMIT 1", (str(row[0]),)
                ).fetchone()
                if not exists:
                    conn.execute(
                        "INSERT INTO notifications(title,message,severity,entity,entity_id) "
                        "VALUES(?,?,?,?,?)",
                        ("Overdue expense", f"{row[1]} • due {row[2]}", "Warning", "Expense", str(row[0])),
                    )
            overdue_debts = conn.execute(
                "SELECT debt_id, lender, due_date FROM debt "
                "WHERE due_date IS NOT NULL AND due_date < date('now') "
                "AND status NOT IN ('Paid','Closed') LIMIT 20"
            ).fetchall()
            for row in overdue_debts:
                exists = conn.execute(
                    "SELECT 1 FROM notifications WHERE entity='Debt' AND entity_id=? "
                    "AND title='Overdue debt' LIMIT 1", (str(row[0]),)
                ).fetchone()
                if not exists:
                    conn.execute(
                        "INSERT INTO notifications(title,message,severity,entity,entity_id) "
                        "VALUES(?,?,?,?,?)",
                        ("Overdue debt", f"{row[1]} • due {row[2]}", "Critical", "Debt", str(row[0])),
                    )
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
        finally:
            conn.close()

# شرح الدالة mark_all_read: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def mark_all_read(self):
        conn = get_connection()
        try:
            conn.execute("UPDATE notifications SET is_read=1 WHERE is_read=0")
            conn.commit()
        finally:
            conn.close()
        self.populate()


# شرح الصنف ActivityLogDialog: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class ActivityLogDialog(_BaseDialog):
    """واجهة قراءة فقط لسجل التدقيق الموجود."""

    def __init__(self, parent=None):
        super().__init__(parent, "Activity Log")
        root = QVBoxLayout(self)
        title = QLabel("🧾  Activity Log")
        title.setObjectName("dialogTitle")
        root.addWidget(title)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter activity…")
        self.search.textChanged.connect(self.populate)
        root.addWidget(self.search)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Date", "User", "Action", "Entity", "ID", "Description"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        root.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
        self.populate()

# شرح الدالة populate: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def populate(self):
        term = self.search.text().strip()
        like = f"%{term}%"
        rows = _query(
            "SELECT occurred_at,user_name,action,entity,entity_id,description FROM audit_log "
            "WHERE ?='' OR occurred_at LIKE ? OR user_name LIKE ? OR action LIKE ? OR entity LIKE ? "
            "OR COALESCE(entity_id,'') LIKE ? OR COALESCE(description,'') LIKE ? "
            "ORDER BY occurred_at DESC LIMIT 500",
            (term, like, like, like, like, like, like),
        )
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(str(value or "")))
        self.table.resizeColumnsToContents()


# شرح الصنف ProjectQuickViewDialog: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class ProjectQuickViewDialog(_BaseDialog):
    """بطاقة تفاصيل سريعة للمشروع بدون تعديل بيانات المشروع."""

    def __init__(self, parent, project_id: str, store: UXStore, open_page: Callable[[str], None]):
        self.project_id = project_id
        self.store = store
        self.open_page = open_page
        super().__init__(parent, f"Project • {project_id}")
        root = QVBoxLayout(self)
        row = _query(
            "SELECT project_id,project_name,contracting_authority,contract_code,start_date,end_date,"
            "period,budget_ht,tva_percent,budget_ttc,expenses,revenue,status FROM projects WHERE project_id=?",
            (project_id,),
        )
        if not row:
            root.addWidget(QLabel("Project not found."))
            close = QPushButton("Close")
            close.clicked.connect(self.reject)
            root.addWidget(close)
            return
        p = row[0]
        title = QLabel(f"🏗  {p[1] or p[0]}")
        title.setObjectName("dialogTitle")
        root.addWidget(title)
        subtitle = QLabel(f"{p[0]}  •  {p[12] or 'Active'}")
        root.addWidget(subtitle)

        grid = QTableWidget(0, 2)
        grid.setHorizontalHeaderLabels(["Metric", "Value"])
        grid.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        grid.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        metrics = [
            ("Contract", p[3]), ("Authority", p[2]), ("Start", p[4]), ("End", p[5]),
            ("Duration", p[6]), ("Budget HT", money_display(p[7])),
            ("TVA", f"{float(p[8] or 0):.0f}%"), ("Budget TTC", money_display(p[9])),
            ("Expenses", money_display(p[10])), ("Revenue", money_display(p[11])),
        ]
        grid.setRowCount(len(metrics))
        for r, (label, value) in enumerate(metrics):
            grid.setItem(r, 0, QTableWidgetItem(str(label)))
            grid.setItem(r, 1, QTableWidgetItem(str(value or "-")))
        grid.resizeColumnsToContents()
        root.addWidget(grid, 1)

        buttons = QHBoxLayout()
        fav = QPushButton("★  Unfavorite" if store.is_favorite(project_id) else "☆  Favorite")
        fav.clicked.connect(lambda: self._toggle_favorite(fav))
        buttons.addWidget(fav)
        open_btn = QPushButton("Open Project")
        open_btn.clicked.connect(self._open)
        buttons.addWidget(open_btn)
        exp = QPushButton("Open Expenses")
        exp.clicked.connect(lambda: self._open_page("Expenses"))
        buttons.addWidget(exp)
        buttons.addStretch()
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        root.addLayout(buttons)

# شرح الدالة _toggle_favorite: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _toggle_favorite(self, button: QPushButton):
        state = self.store.toggle_favorite(self.project_id)
        button.setText("★  Unfavorite" if state else "☆  Favorite")

# شرح الدالة _open: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _open(self):
        self.store.add_recent(self.project_id)
        self.open_page("Projects")
        self.accept()

# شرح الدالة _open_page: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _open_page(self, name: str):
        self.store.add_recent(self.project_id)
        self.open_page(name)
        self.accept()


# شرح الصنف RecentFavoritesDialog: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class RecentFavoritesDialog(_BaseDialog):
    """مشاريع حديثة ومفضلة في نافذة واحدة."""

    def __init__(self, parent, store: UXStore, open_page: Callable[[str], None]):
        self.store = store
        self.open_page = open_page
        super().__init__(parent, "Projects • Recent & Favorites")
        root = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._open_selected)
        root.addWidget(self.list, 1)
        hint = QLabel("Double-click a project to open its quick view.")
        root.addWidget(hint)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        root.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
        self.populate()

# شرح الدالة populate: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def populate(self):
        self.list.clear()
        ids = []
        for pid in self.store.data.get("favorite_projects", []):
            if pid not in ids:
                ids.append(pid)
        for pid in self.store.data.get("recent_projects", []):
            if pid not in ids:
                ids.append(pid)
        if not ids:
            self.list.addItem("No recent or favorite projects yet.")
            return
        rows = {}
        for row in _query(
            f"SELECT project_id,project_name,status,budget_ht,expenses "
            f"FROM projects WHERE project_id IN ({','.join('?' * len(ids))})",
            tuple(ids),
        ):
            rows[str(row[0])] = row
        for pid in ids:
            row = rows.get(str(pid))
            if not row:
                continue
            marker = "★" if self.store.is_favorite(pid) else "•"
            item = QListWidgetItem(f"{marker}  {row[0]}  |  {row[1]}  |  {row[2]}  |  Expenses: {money_display(row[4])}")
            item.setData(Qt.ItemDataRole.UserRole, str(row[0]))
            self.list.addItem(item)

# شرح الدالة _open_selected: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _open_selected(self, item: QListWidgetItem):
        pid = item.data(Qt.ItemDataRole.UserRole)
        if pid:
            ProjectQuickViewDialog(self, pid, self.store, self.open_page).exec()
            self.populate()


# شرح الصنف CommandPaletteDialog: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class CommandPaletteDialog(_BaseDialog):
    """بحث سريع في أوامر التطبيق والمشاريع."""

    def __init__(self, parent, menu: list[tuple[str, Any, str, str]], store: UXStore, open_page: Callable[[str], None], open_notifications: Callable[[], None], open_activity: Callable[[], None], open_recent: Callable[[], None]):
        self.menu = menu
        self.store = store
        self.open_page = open_page
        self.open_notifications = open_notifications
        self.open_activity = open_activity
        self.open_recent = open_recent
        super().__init__(parent, "Command Palette")
        self.resize(720, 520)
        root = QVBoxLayout(self)
        title = QLabel("⌘  Command Palette")
        title.setObjectName("dialogTitle")
        root.addWidget(title)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Type a page, command, or project ID…")
        self.edit.textChanged.connect(self.populate)
        self.edit.returnPressed.connect(self.activate_current)
        root.addWidget(self.edit)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _: self.activate_current())
        root.addWidget(self.list, 1)
        root.addWidget(QLabel("Enter / double-click to run • Esc to close"))
        self.actions: list[tuple[str, Callable[[], None]]] = []
        self.populate()
        self.edit.setFocus()

# شرح الدالة populate: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def populate(self):
        term = self.edit.text().strip().lower()
        self.list.clear()
        self.actions = []
        actions: list[tuple[str, Callable[[], None]]] = []
        for name, _, _, _ in self.menu:
            actions.append((f"Open  ›  {name}", lambda n=name: self.open_page(n)))
        actions.extend([
            ("🔎  Global Search", lambda: self._search_hint()),
            ("🔔  Notification Center", self.open_notifications),
            ("🧾  Activity Log", self.open_activity),
            ("★  Recent & Favorites", self.open_recent),
            ("↻  Refresh Current Page", lambda: getattr(self.parent(), "refresh_current", lambda: None)()),
        ])
        if term:
            rows = _query(
                "SELECT project_id,project_name,status FROM projects WHERE project_id LIKE ? OR project_name LIKE ? LIMIT 20",
                (f"%{term}%", f"%{term}%"),
            )
            for row in rows:
                pid = str(row[0])
                actions.insert(0, (f"🏗  Project  {pid}  •  {row[1]}", lambda p=pid: self._project(p)))
        for label, callback in actions:
            if not term or term in label.lower():
                item = QListWidgetItem(label)
                self.list.addItem(item)
                self.actions.append((label, callback))
        if self.list.count():
            self.list.setCurrentRow(0)

# شرح الدالة activate_current: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def activate_current(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.actions):
            callback = self.actions[row][1]
            self.accept()
            QTimer.singleShot(0, callback)

# شرح الدالة _project: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _project(self, project_id: str):
        self.store.add_recent(project_id)
        ProjectQuickViewDialog(self.parent(), project_id, self.store, self.open_page).exec()

# شرح الدالة _search_hint: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
# Executes a logical step related to this file's functionality.
    def _search_hint(self):
        self.accept()
        parent = self.parent()
        if parent is not None and hasattr(parent, "global_search_dialog"):
            # Standard access satisfies Ruff, type: ignore satisfies Pylance
            callback = parent.global_search_dialog   # type: ignore
            QTimer.singleShot(0, callback)


# شرح الدالة open_project_quick_view: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def open_project_quick_view(parent, project_id: str, store: UXStore, open_page: Callable[[str], None]) -> None:
    store.add_recent(project_id)
    ProjectQuickViewDialog(parent, project_id, store, open_page).exec()


# شرح الدالة install_shortcuts: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def install_shortcuts(window) -> list[QShortcut]:
    """تثبيت الاختصارات العامة دون تغيير اختصارات الصفحات الحالية."""
    shortcuts: list[QShortcut] = []
    definitions = [
        ("Ctrl+K", window.show_command_palette),
        ("Ctrl+Shift+F", window.global_search_dialog),
        ("Ctrl+Shift+N", window.show_notifications),
        ("Ctrl+Shift+A", window.show_activity_log),
        ("Ctrl+Shift+R", window.show_recent_favorites),
        ("F5", window.refresh_current),
        ("Ctrl+B", window.toggle_sidebar),
    ]
    for sequence, callback in definitions:
        shortcut = QShortcut(QKeySequence(sequence), window)
        shortcut.activated.connect(callback)
        shortcuts.append(shortcut)
    return shortcuts


# شرح الدالة show_toast: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def show_toast(parent, message: str, timeout: int = 2200) -> None:
    """إظهار رسالة نجاح صغيرة دون مقاطعة سير العمل."""
    toast = QFrame(parent)
    toast.setObjectName("buildOfficeToast")
    set_theme_style(toast, "QFrame#buildOfficeToast { padding:10px 16px; border-radius:14px; background:@surface@; color:@text_primary@; border:1px solid @primary@; } QFrame#buildOfficeToast QLabel { background:transparent; border:0; color:@text_primary@; font-weight:600; }")
    label = QLabel(message, toast)
    label.setStyleSheet("background:transparent;")
    lay = QHBoxLayout(toast)
    lay.setContentsMargins(12, 8, 12, 8)
    lay.addWidget(label)
    toast.adjustSize()
    x = max(10, parent.width() - toast.width() - 28)
    y = max(10, parent.height() - toast.height() - 28)
    toast.move(x, y)
    toast.show()
    toast.raise_()
    QTimer.singleShot(timeout, toast.deleteLater)

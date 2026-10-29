# ============================================================
# شرح الملف: dev_tools/visual_dev_kit.py
# هذا الملف جزء من أدوات التطوير والتشخيص ومراقبة الأداء.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""أدوات التطوير المرئية الموحدة لبرنامج BuildOffice Pro.
نسخة مستقلة من Visual Dev Kit بدون Color Inspector، مع فحص متقدم
ومعاينة وتحديد مصدر الكود للعنصر المحدد.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

# Make the project root importable when this module is run directly from
# the dev_tools directory instead of imported as part of the application.

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QPainter,
    QPalette,
    QPen,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from theme.colors import DEV_KIT_COLORS, DEV_TOOL_COLORS, DEV_TOOL_GRID

TOOLS = [
    ("overview", "⌂", "Overview"),
    ("inspector", "◉", "Inspector"),
    ("spacing", "↔", "Spacing"),
    ("size", "↗", "Size"),
    ("typography", "A", "Typography"),
    ("layout", "▦", "Layout"),
    ("states", "◎", "States"),
    ("responsive", "▣", "Responsive"),
    ("grid", "#", "Grid"),
    ("source", "</>", "Code Source"),
]


# شرح الصنف PreviewStore: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class PreviewStore:
    """إدارة المعاينات والتغييرات المحفوظة دون لمس منطق الصفحات."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.path = self.root / "data" / "devkit_visual_overrides.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.saved = self._load()
        self.originals: dict[int, dict] = {}
        self.pending: dict[str, dict] = {}

# شرح الدالة _load: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _load(self):
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except (OSError, ValueError):
            return {}

# شرح الدالة _write: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _write(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self.saved, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self.path)

# شرح الدالة key: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def key(widget: QWidget) -> str:
        name = widget.objectName().strip()
        if name:
            return f"name:{name}"

        parts = []
        current = widget
        while current is not None and isinstance(current, QWidget):
            cls = current.metaObject().className()
            parent = current.parentWidget()
            siblings = (
                [
                    w
                    for w in parent.findChildren(
                        QWidget,
                        options=Qt.FindChildOption.FindDirectChildrenOnly,
                    )
                    if w.metaObject().className() == cls
                ]
                if parent is not None
                else []
            )
            idx = siblings.index(current) if current in siblings else 0
            parts.append(f"{cls}[{idx}]")
            current = current.parentWidget()

        return "path:" + "/".join(reversed(parts))

# شرح الدالة capture: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def capture(self, widget: QWidget):
        wid = id(widget)
        if wid not in self.originals:
            self.originals[wid] = {
                "style": widget.styleSheet(),
                "font": QFont(widget.font()),
                "minimum": widget.minimumSize(),
                "maximum": widget.maximumSize(),
                "geometry": widget.geometry(),
                "enabled": widget.isEnabled(),
            }

# شرح الدالة preview: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def preview(self, widget: QWidget, values: dict):
        self.capture(widget)
        self.pending[self.key(widget)] = deepcopy(values)
        self.apply_values(widget, values)

# شرح الدالة apply_values: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def apply_values(self, widget: QWidget, values: dict):
        if "font_size" in values:
            font = QFont(widget.font())
            font.setPointSize(max(1, int(values["font_size"])))
            widget.setFont(font)

        if "minimum_width" in values:
            widget.setMinimumWidth(max(0, int(values["minimum_width"])))

        if "minimum_height" in values:
            widget.setMinimumHeight(max(0, int(values["minimum_height"])))

        style_parts = []
        if values.get("background"):
            style_parts.append(f"background-color: {values['background']};")
        if values.get("text_color"):
            style_parts.append(f"color: {values['text_color']};")
        if values.get("border_radius") is not None:
            style_parts.append(
                f"border-radius: {int(values['border_radius'])}px;"
            )
        if values.get("padding") is not None:
            style_parts.append(f"padding: {int(values['padding'])}px;")

        if style_parts:
            base = widget.property("_bo_devkit_base_style")
            if not isinstance(base, str):
                base = widget.styleSheet() or ""
                widget.setProperty("_bo_devkit_base_style", base)

            selector = (
                f"{widget.metaObject().className()}#{widget.objectName()}"
                if widget.objectName()
                else widget.metaObject().className()
            )
            extra = (
                "\n/* BuildOffice Visual Dev Kit */\n"
                f"{selector} {{ {' '.join(style_parts)} }}"
            )
            widget.setStyleSheet(base + extra)

# شرح الدالة restore: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def restore(self, widget: QWidget):
        original = self.originals.pop(id(widget), None)
        self.pending.pop(self.key(widget), None)
        if not original:
            return

        widget.setStyleSheet(original["style"])
        widget.setFont(original["font"])
        widget.setMinimumSize(original["minimum"])
        widget.setMaximumSize(original["maximum"])
        widget.setEnabled(original["enabled"])

# شرح الدالة save: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def save(self, widget: QWidget):
        key = self.key(widget)
        values = self.pending.get(key)
        if values is None:
            return False

        self.saved[key] = deepcopy(values)
        self._write()

        self.capture(widget)
        original = self.originals.get(id(widget))
        if original is not None:
            original["style"] = widget.styleSheet()
            original["font"] = QFont(widget.font())
            original["minimum"] = widget.minimumSize()
            original["maximum"] = widget.maximumSize()
            original["geometry"] = widget.geometry()
            original["enabled"] = widget.isEnabled()

        self.pending.pop(key, None)
        return True

# شرح الدالة discard_all: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def discard_all(self, widget: QWidget | None = None):
        if widget is not None:
            self.restore(widget)
        else:
            self.pending.clear()

# شرح الدالة apply_saved: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def apply_saved(self, root_widget: QWidget):
        for widget in root_widget.findChildren(QWidget):
            values = self.saved.get(self.key(widget))
            if isinstance(values, dict):
                self.apply_values(widget, values)


# شرح الصنف MeasurementOverlay: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class MeasurementOverlay(QWidget):
    """طبقة شفافة لعرض حدود العنصر والقياسات."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.target = None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.hide()

# شرح الدالة set_target: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def set_target(self, widget):
        self.target = widget
        if widget is not None:
            window = widget.window()
            if self.parentWidget() is not window:
                self.setParent(window)
            self.setGeometry(window.rect())
            self.show()
            self.raise_()
            self.update()

# شرح الدالة paintEvent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def paintEvent(self, event):
        del event
        target = self.target
        if target is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        try:
            # استخدم الإحداثيات العالمية لتجنب أخطاء mapTo عند تغيّر علاقة الوالد أثناء التشغيل.
            global_pos = target.mapToGlobal(target.rect().topLeft())
            pos = self.mapFromGlobal(global_pos)
        except (RuntimeError, AttributeError):
            return
        rect = target.rect().translated(pos)

        painter.setPen(
            QPen(
                QColor(DEV_TOOL_COLORS["overlay_accent"]),
                2,
                Qt.PenStyle.DashLine,
            )
        )
        painter.drawRect(rect.adjusted(0, 0, -1, -1))

        painter.setPen(
            QPen(QColor(DEV_TOOL_COLORS["overlay_measure"]), 1)
        )
        painter.drawLine(
            rect.left(),
            rect.top() - 8,
            rect.right(),
            rect.top() - 8,
        )
        painter.drawLine(
            rect.left() - 8,
            rect.top(),
            rect.left() - 8,
            rect.bottom(),
        )

        painter.setPen(QColor(DEV_TOOL_COLORS["overlay_text"]))
        painter.drawText(
            rect.left(),
            max(12, rect.top() - 12),
            f"{rect.width()} × {rect.height()} px",
        )


# شرح الصنف GridOverlay: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class GridOverlay(QWidget):
    """شبكة محاذاة مستقلة عن صفحات Dev Kit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.hide()

# شرح الدالة sync: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def sync(self):
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
            self.raise_()
            self.update()

# شرح الدالة paintEvent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(QPen(QColor(*DEV_TOOL_GRID), 1))

        step = 8
        for x in range(0, self.width(), step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), step):
            painter.drawLine(0, y, self.width(), y)


# شرح الصنف ToolPage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class ToolPage(QWidget):
    def __init__(self, title, description=""):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(7)

        heading = QLabel(title)
        heading_font = QFont(heading.font())
        heading_font.setPointSize(15)
        heading_font.setWeight(QFont.Weight.Bold)
        heading.setFont(heading_font)
        layout.addWidget(heading)

        if description:
            desc = QLabel(description)
            desc.setWordWrap(True)
            layout.addWidget(desc)

        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        layout.addLayout(self.body, 1)


# شرح الصنف VisualDevKit: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class VisualDevKit(QMainWindow):
    """نافذة موحدة للفحص والمعاينة والحفظ ومشاهدة مصدر الكود."""

    def __init__(self, main_window, project_root=None):
        super().__init__(main_window)

        self.main_window = main_window
        self.project_root = Path(
            project_root or Path(__file__).resolve().parent.parent
        )
        self.preview = PreviewStore(self.project_root)
        self.selected_widget: QWidget | None = None
        self._original_main_size = (
            main_window.width(),
            main_window.height(),
        )

        self.overlay = MeasurementOverlay(main_window)
        self.grid_overlay = GridOverlay(main_window)

        self.setObjectName("visualDevKit")
        self.setWindowTitle("BuildOffice Pro | Visual Dev Kit")
        self.setMinimumSize(560, 380)
        self.resize(680, 450)
        self._force_light_palette()

        self._build_ui()
        self._install_filter()
        self._refresh_selection()
        self.preview.apply_saved(main_window)

        self.shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), main_window)
        self.shortcut.activated.connect(self.show_kit)
        # The central developer manager owns the application-wide shortcut.
        # This legacy shortcut remains for standalone Visual Dev Kit usage.
        manager = getattr(main_window, "_dev_manager", None)
        if manager is not None:
            self.shortcut.setEnabled(False)

    # ============================================================
    # تثبيت مظهر فاتح مستقل عن مظهر التطبيق
    # ============================================================

# شرح الدالة _force_light_palette: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _force_light_palette(self):
        palette = QPalette()

        colors = {
            QPalette.ColorRole.Window: DEV_KIT_COLORS["background"],
            QPalette.ColorRole.WindowText: DEV_KIT_COLORS["text"],
            QPalette.ColorRole.Base: DEV_KIT_COLORS["surface"],
            QPalette.ColorRole.AlternateBase: DEV_KIT_COLORS["alternate"],
            QPalette.ColorRole.Text: DEV_KIT_COLORS["text"],
            QPalette.ColorRole.Button: DEV_KIT_COLORS["surface"],
            QPalette.ColorRole.ButtonText: DEV_KIT_COLORS["text"],
            QPalette.ColorRole.BrightText: DEV_KIT_COLORS["text"],
            QPalette.ColorRole.Highlight: DEV_KIT_COLORS["accent"],
            QPalette.ColorRole.HighlightedText: DEV_KIT_COLORS["text"],
            QPalette.ColorRole.ToolTipBase: DEV_KIT_COLORS["surface"],
            QPalette.ColorRole.ToolTipText: DEV_KIT_COLORS["text"],
            QPalette.ColorRole.PlaceholderText: DEV_KIT_COLORS["muted"],
        }

        # Set every palette group so inactive and disabled controls do not
        # inherit dark colors from the application or operating system theme.
        for group in (
            QPalette.ColorGroup.Active,
            QPalette.ColorGroup.Inactive,
            QPalette.ColorGroup.Disabled,
        ):
            for role, color in colors.items():
                palette.setColor(group, role, QColor(color))

        self.setPalette(palette)
        self.setAutoFillBackground(True)

    # ============================================================
    # بناء الواجهة
    # ============================================================

# شرح الدالة _build_ui: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("devKitCentral")

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("devKitHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(6)

        title = QLabel("🛠 Visual Dev Kit")
        title_font = QFont(title.font())
        title_font.setPointSize(11)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        header_layout.addWidget(title)

        self.selected_label = QLabel("No widget selected")
        self.selected_label.setObjectName("selectionSummary")
        header_layout.addWidget(self.selected_label, 1)

        self.pick_check = QCheckBox("🎯 Pick")
        self.pick_check.setChecked(True)
        header_layout.addWidget(self.pick_check)

        self.save_btn = QPushButton("💾 Save")
        self.save_btn.clicked.connect(self.save_current)
        header_layout.addWidget(self.save_btn)

        self.restore_btn = QPushButton("↩ Restore")
        self.restore_btn.clicked.connect(self.restore_current)
        header_layout.addWidget(self.restore_btn)

        root.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        nav = QListWidget()
        nav.setObjectName("devKitNavigation")
        nav.setMinimumWidth(145)
        nav.setMaximumWidth(175)
        nav.setSpacing(1)

        for key, icon, label in TOOLS:
            item = QListWidgetItem(f"{icon}  {label}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            nav.addItem(item)

        nav.currentRowChanged.connect(self._tool_changed)
        splitter.addWidget(nav)
        self.nav = nav

        self.stack = QStackedWidget()
        self.stack.setObjectName("devKitStack")
        splitter.addWidget(self.stack)
        splitter.setSizes([155, 525])

        root.addWidget(splitter, 1)

        self._build_global_style()

        self.pages: dict[str, QWidget] = {}
        self._make_overview()
        self._make_inspector()
        self._make_spacing()
        self._make_size()
        self._make_typography()
        self._make_layout()
        self._make_states()
        self._make_responsive()
        self._make_grid()
        self._make_source()

        self.setCentralWidget(central)
        nav.setCurrentRow(0)

# شرح الدالة _build_global_style: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_global_style(self):
        style = """
            QMainWindow#visualDevKit, QWidget#devKitCentral {
                background: __background__;
                color: __text__;
            }

            QFrame#devKitHeader {
                background: __surface__;
                color: __text__;
                border-bottom: 1px solid __border__;
            }

            QLabel {
                color: __text__;
                background: transparent;
            }

            QLabel#selectionSummary {
                color: __muted__;
                background: transparent;
                padding: 5px 8px;
            }

            QListWidget#devKitNavigation {
                background: __surface__;
                color: __text__;
                border: 1px solid __border__;
                border-radius: 8px;
                padding: 6px;
            }

            QListWidget#devKitNavigation::item {
                padding: 9px 12px;
                border: 1px solid transparent;
                border-radius: 8px;
                color: __text__;
                background: transparent;
            }

            QListWidget#devKitNavigation::item:hover {
                background: __hover__;
                border: 1px solid __input_border__;
                color: __text__;
            }

            QListWidget#devKitNavigation::item:selected {
                background: __selected__;
                border: 2px solid __accent__;
                color: __text__;
                font-weight: 800;
            }

            QListWidget#devKitNavigation::item:selected:hover {
                background: __selected_hover__;
                border: 2px solid __accent_dark__;
            }

            QStackedWidget#devKitStack {
                background: __background__;
                border: none;
            }

            QFrame#devSection {
                background: __surface__;
                color: __text__;
                border: 1px solid __border__;
                border-radius: 12px;
            }

            QFrame#devCard {
                background: __card__;
                color: __text__;
                border: 1px solid __card_border__;
                border-radius: 10px;
            }

            QLineEdit, QComboBox, QSpinBox {
                background: __surface__;
                color: __text__;
                border: 1px solid __input_border__;
                border-radius: 6px;
                selection-background-color: __accent__;
                selection-color: __text__;
                min-height: 30px;
                padding: 3px 7px;
            }

            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid __accent__;
            }

            QPushButton {
                background: __surface__;
                color: __text__;
                border: 1px solid __input_border__;
                border-radius: 7px;
                padding: 5px 10px;
            }

            QPushButton:hover {
                background: __hover__;
                color: __text__;
            }

            QPushButton:pressed {
                background: __pressed__;
                color: __text__;
            }

            QPushButton:disabled {
                background: __disabled__;
                color: __disabled_text__;
                border-color: __card_border__;
            }

            QCheckBox {
                color: __text__;
                background: transparent;
                spacing: 6px;
            }

            QComboBox QAbstractItemView {
                background: __surface__;
                color: __text__;
                selection-background-color: __accent__;
                selection-color: __text__;
                border: 1px solid __input_border__;
            }

            QPlainTextEdit#sourceEditor {
                background: __surface__;
                color: __text__;
                border: 1px solid __input_border__;
                border-radius: 8px;
                selection-background-color: __accent__;
                selection-color: __text__;
                font-family: Consolas, "Cascadia Mono", monospace;
                font-size: 9pt;
            }

            QPlainTextEdit {
                background: __surface__;
                color: __text__;
                border: 1px solid __input_border__;
                border-radius: 8px;
                selection-background-color: __accent__;
                selection-color: __text__;
            }
            """
        for name, value in DEV_KIT_COLORS.items():
            style = style.replace(f"__{name}__", value)
        self.setStyleSheet(style)

    # ============================================================
    # Tool pages
    # ============================================================

# شرح الدالة _add_page: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _add_page(self, key, page):
        self.pages[key] = page
        self.stack.addWidget(page)

# شرح الدالة _make_overview: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _make_overview(self):
        p = ToolPage(
            "Overview",
            "Select a widget in the application, then inspect it without losing the selection.",
        )
        self.overview_info = QLabel("No widget selected.")
        self.overview_info.setWordWrap(True)
        p.body.addWidget(self.overview_info)

        actions = QHBoxLayout()
        focus_source = QPushButton("Open Code Source")
        focus_source.clicked.connect(lambda: self.show_kit("source"))
        actions.addWidget(focus_source)

        focus_inspector = QPushButton("Open Inspector")
        focus_inspector.clicked.connect(lambda: self.show_kit("inspector"))
        actions.addWidget(focus_inspector)
        actions.addStretch()
        p.body.addLayout(actions)

        self._add_page("overview", p)

# شرح الدالة _make_inspector: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _make_inspector(self):
        p = ToolPage(
            "Inspector",
            "Detailed information about the selected widget, including Qt properties, geometry and stylesheet state.",
        )

        self.inspector_view = QPlainTextEdit()
        self.inspector_view.setReadOnly(True)
        self.inspector_view.setMinimumHeight(360)
        p.body.addWidget(self.inspector_view, 1)

        self._add_page("inspector", p)

# شرح الدالة _make_spacing: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _make_spacing(self):
        p = ToolPage(
            "Spacing",
            "Inspect the selected widget's position inside its parent and the available surrounding space.",
        )

        self.spacing_values = QLabel("No widget selected.")
        self.spacing_values.setWordWrap(True)
        p.body.addWidget(self.spacing_values)

        self._add_page("spacing", p)

# شرح الدالة _make_size: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _make_size(self):
        p = ToolPage(
            "Size",
            "Preview minimum size, border radius and padding without changing page logic.",
        )

        form = QFormLayout()

        self.w_spin = QSpinBox()
        self.w_spin.setRange(0, 3000)

        self.h_spin = QSpinBox()
        self.h_spin.setRange(0, 2000)

        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(0, 100)

        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 100)

        form.addRow("Minimum width", self.w_spin)
        form.addRow("Minimum height", self.h_spin)
        form.addRow("Border radius", self.radius_spin)
        form.addRow("Padding", self.padding_spin)
        p.body.addLayout(form)

        for spin in (
            self.w_spin,
            self.h_spin,
            self.radius_spin,
            self.padding_spin,
        ):
            spin.valueChanged.connect(self._preview_size)

        self._add_page("size", p)

# شرح الدالة _make_typography: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _make_typography(self):
        p = ToolPage(
            "Typography",
            "Inspect the selected widget's font hierarchy and preview a new font size.",
        )

        self.font_info = QLabel("No widget selected.")
        self.font_info.setWordWrap(True)
        p.body.addWidget(self.font_info)

        self.font_size = QSpinBox()
        self.font_size.setRange(6, 72)
        self.font_size.valueChanged.connect(self._preview_typography)

        p.body.addWidget(QLabel("Preview font size"))
        p.body.addWidget(self.font_size)

        self._add_page("typography", p)

# شرح الدالة _make_layout: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _make_layout(self):
        p = ToolPage(
            "Layout",
            "Inspect hierarchy, alignment and geometry. Overlay is visual only and does not alter page structure.",
        )

        self.bounds_check = QCheckBox("Show selected widget bounds")
        self.bounds_check.setChecked(True)
        self.bounds_check.toggled.connect(self._toggle_overlay)
        p.body.addWidget(self.bounds_check)

        self.layout_info = QLabel("No widget selected.")
        self.layout_info.setWordWrap(True)
        p.body.addWidget(self.layout_info)

        self._add_page("layout", p)

# شرح الدالة _make_states: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _make_states(self):
        p = ToolPage(
            "Interaction States",
            "Preview common interactive states on the selected widget.",
        )

        self.state_combo = QComboBox()
        self.state_combo.addItems(
            ["Normal", "Hover", "Pressed", "Focus", "Disabled"]
        )
        self.state_combo.currentTextChanged.connect(self._preview_state)

        p.body.addWidget(QLabel("Preview state"))
        p.body.addWidget(self.state_combo)

        self.state_info = QLabel("Select an interactive widget.")
        self.state_info.setWordWrap(True)
        p.body.addWidget(self.state_info)

        self._add_page("states", p)

# شرح الدالة _make_responsive: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _make_responsive(self):
        p = ToolPage(
            "Responsive",
            "Test the main application window at controlled sizes.",
        )

        row = QHBoxLayout()

        self.res_w = QSpinBox()
        self.res_w.setRange(620, 3000)
        self.res_w.setValue(self.main_window.width())

        self.res_h = QSpinBox()
        self.res_h.setRange(420, 2000)
        self.res_h.setValue(self.main_window.height())

        row.addWidget(QLabel("Width"))
        row.addWidget(self.res_w)
        row.addWidget(QLabel("Height"))
        row.addWidget(self.res_h)

        apply_btn = QPushButton("Preview")
        apply_btn.clicked.connect(self._preview_window_size)
        row.addWidget(apply_btn)

        p.body.addLayout(row)

        restore = QPushButton("Restore application size")
        restore.clicked.connect(
            lambda: self.main_window.resize(*self._original_main_size)
        )
        p.body.addWidget(restore)

        self._add_page("responsive", p)

# شرح الدالة _make_grid: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _make_grid(self):
        p = ToolPage(
            "Grid & Guides",
            "A lightweight 8 px alignment grid for visual inspection.",
        )

        self.grid_check = QCheckBox("Show 8 px grid")
        self.grid_check.toggled.connect(self._toggle_grid)
        p.body.addWidget(self.grid_check)

        p.body.addWidget(
            QLabel(
                "The grid is drawn as an overlay and does not modify saved files or styles."
            )
        )

        self._add_page("grid", p)

# شرح الدالة _make_source: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _make_source(self):
        p = ToolPage(
            "Code Source",
            "Locate the Python source related to the selected widget and inspect it directly.",
        )

        source_toolbar = QHBoxLayout()

        self.source_path = QLabel("No source located.")
        self.source_path.setWordWrap(True)
        source_toolbar.addWidget(self.source_path, 1)

        self.copy_source_btn = QPushButton("Copy")
        self.copy_source_btn.clicked.connect(self._copy_source)
        source_toolbar.addWidget(self.copy_source_btn)

        self.open_source_btn = QPushButton("Open File")
        self.open_source_btn.clicked.connect(self._open_source_file)
        source_toolbar.addWidget(self.open_source_btn)

        self.open_vscode_btn = QPushButton("Open in VS Code")
        self.open_vscode_btn.clicked.connect(self._open_source_in_vscode)
        source_toolbar.addWidget(self.open_vscode_btn)

        p.body.addLayout(source_toolbar)

        self.source_range = QLabel("")
        p.body.addWidget(self.source_range)

        self.source_editor = QPlainTextEdit()
        self.source_editor.setObjectName("sourceEditor")
        self.source_editor.setReadOnly(True)
        self.source_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        p.body.addWidget(self.source_editor, 1)

        self.source_hint = QLabel(
            "Source matching uses objectName first, then selected widget class and visible text."
        )
        self.source_hint.setWordWrap(True)
        p.body.addWidget(self.source_hint)

        self._source_file: Path | None = None
        self._source_line: int | None = None

        self._add_page("source", p)

    # ============================================================
    # Selection / source detection
    # ============================================================

# شرح الدالة _install_filter: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _install_filter(self):
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

# شرح الدالة eventFilter: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def eventFilter(self, watched, event):
        if watched is self.main_window and event.type() == QEvent.Type.Resize:
            self.overlay.setGeometry(self.main_window.rect())
            self.grid_overlay.sync()
            if self.grid_check.isChecked():
                self.grid_overlay.show()
            self.overlay.update()

        if (
            event.type() == QEvent.Type.MouseButtonPress
            and self.isVisible()
            and self.pick_check.isChecked()
        ):
            try:
                pos = event.globalPosition().toPoint()
                widget = QApplication.widgetAt(pos)
            except (AttributeError, RuntimeError):
                widget = None

            if (
                isinstance(widget, QWidget)
                and widget.window() is self.main_window
            ):
                self.select_widget(widget)
                return False

        return super().eventFilter(watched, event)

# شرح الدالة select_widget: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def select_widget(self, widget):
        if widget is self or self.isAncestorOf(widget):
            return

        self.selected_widget = widget

        self.selected_label.setText(
            f"{widget.metaObject().className()}  •  "
            f"{widget.objectName() or '(no object name)'}"
        )

        self._refresh_selection()
        self.overlay.set_target(widget)

        if self.grid_check.isChecked():
            self.grid_overlay.sync()

# شرح الدالة _refresh_selection: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _refresh_selection(self):
        w = self.selected_widget
        if w is None:
            return

        self.overview_info.setText(
            f"Class: {w.metaObject().className()}\n"
            f"Object: {w.objectName() or '(none)'}\n"
            f"Geometry: {w.width()} × {w.height()}\n"
            f"Position: {w.x()}, {w.y()}\n"
            f"Visible: {'Yes' if w.isVisible() else 'No'}\n"
            f"Enabled: {'Yes' if w.isEnabled() else 'No'}"
        )

        self.spacing_values.setText(self._spacing_text(w))

        parent = w.parentWidget()
        parent_name = (
            parent.metaObject().className() if parent is not None else "-"
        )
        self.layout_info.setText(
            f"Parent: {parent_name}\n"
            f"Size policy: "
            f"{w.sizePolicy().horizontalPolicy().name} / "
            f"{w.sizePolicy().verticalPolicy().name}\n"
            f"Layout direction: {w.layoutDirection().name}\n"
            f"Layout: "
            f"{parent.layout().__class__.__name__ if parent and parent.layout() else '-'}"
        )

        self.w_spin.blockSignals(True)
        self.h_spin.blockSignals(True)
        self.radius_spin.blockSignals(True)
        self.padding_spin.blockSignals(True)

        self.w_spin.setValue(w.minimumWidth())
        self.h_spin.setValue(w.minimumHeight())
        self.radius_spin.setValue(0)
        self.padding_spin.setValue(0)

        self.w_spin.blockSignals(False)
        self.h_spin.blockSignals(False)
        self.radius_spin.blockSignals(False)
        self.padding_spin.blockSignals(False)

        self.font_size.blockSignals(True)
        self.font_size.setValue(max(1, w.font().pointSize()))
        self.font_size.blockSignals(False)

        font = w.font()
        self.font_info.setText(
            f"Family: {font.family()}\n"
            f"Size: {font.pointSize()} pt\n"
            f"Weight: {font.weight()}\n"
            f"Italic: {'Yes' if font.italic() else 'No'}\n"
            f"Bold: {'Yes' if font.bold() else 'No'}"
        )

        self.state_info.setText(
            f"Selected: {w.metaObject().className()}"
        )

        self.inspector_view.setPlainText(self._inspector_text(w))
        self._refresh_source()

# شرح الدالة _spacing_text: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _spacing_text(w):
        p = w.parentWidget()
        if p is None:
            return "No parent widget."

        rect = w.geometry()
        return (
            f"Distance to parent edges: "
            f"left {rect.left()} px, top {rect.top()} px, "
            f"right {max(0, p.width() - rect.right() - 1)} px, "
            f"bottom {max(0, p.height() - rect.bottom() - 1)} px.\n"
            f"Parent size: {p.width()} × {p.height()} px"
        )

# شرح الدالة _inspector_text: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _inspector_text(w):
        palette = w.palette()
        base_color = palette.color(w.backgroundRole()).name()
        text_color = palette.color(w.foregroundRole()).name()

        return (
            f"Qt class: {w.metaObject().className()}\n"
            f"Object name: {w.objectName() or '(none)'}\n"
            f"Widget text: {w.text() if hasattr(w, 'text') else '(not available)'}\n"
            f"Enabled: {w.isEnabled()}\n"
            f"Visible: {w.isVisible()}\n"
            f"Geometry: {w.geometry().getRect()}\n"
            f"Minimum size: {w.minimumSize().width()} × {w.minimumSize().height()}\n"
            f"Maximum size: {w.maximumSize().width()} × {w.maximumSize().height()}\n"
            f"Size policy: {w.sizePolicy().horizontalPolicy().name} / "
            f"{w.sizePolicy().verticalPolicy().name}\n"
            f"Font: {w.font().family()} {w.font().pointSize()} pt\n"
            f"Style sheet length: {len(w.styleSheet())} chars\n"
            f"Palette background: {base_color}\n"
            f"Palette text: {text_color}\n"
        )

# شرح الدالة _refresh_source: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _refresh_source(self):
        path, line, snippet = self._locate_source(self.selected_widget)

        self._source_file = path
        self._source_line = line

        if path is None:
            self.source_path.setText("No source located.")
            self.source_range.setText("")
            self.source_editor.setPlainText(
                "No matching Python source was found under the project root."
            )
            self.open_source_btn.setEnabled(False)
            self.open_vscode_btn.setEnabled(False)
            self.copy_source_btn.setEnabled(False)
            return

        self.source_path.setText(str(path))
        self.source_range.setText(
            f"Likely source line: {line if line else 'unknown'}"
        )
        self.source_editor.setPlainText(snippet)
        self.open_source_btn.setEnabled(True)
        self.open_vscode_btn.setEnabled(line is not None)
        self.copy_source_btn.setEnabled(bool(snippet))

# شرح الدالة _locate_source: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _locate_source(self, widget):
        if widget is None or not self.project_root.exists():
            return None, None, ""

        python_files = [
            p
            for p in self.project_root.rglob("*.py")
            if "__pycache__" not in p.parts
            and ".venv" not in p.parts
            and "venv" not in p.parts
        ]

        object_name = widget.objectName().strip()
        class_name = widget.metaObject().className()

        visible_text = ""
        for attr in ("text", "title"):
            try:
                value = getattr(widget, attr)()
            except (AttributeError, TypeError, RuntimeError):
                value = ""
            if isinstance(value, str) and value.strip():
                visible_text = value.strip()
                break

        # Priority 1: exact objectName in Python source.
        if object_name:
            result = self._search_files(
                python_files,
                [object_name],
                object_name,
            )
            if result[0] is not None:
                return result

        # Priority 2: exact class plus objectName.
        if object_name and class_name:
            result = self._search_files(
                python_files,
                [class_name, object_name],
                object_name,
            )
            if result[0] is not None:
                return result

        # Priority 3: visible text, preferably in UI setter/constructor lines.
        if visible_text:
            candidates = [
                visible_text,
                visible_text.replace('"', '\\"'),
                visible_text.replace("'", "\\'"),
            ]
            result = self._search_files(
                python_files,
                candidates,
                visible_text,
                prefer_ui=True,
            )
            if result[0] is not None:
                return result

        # Priority 4: class name as a weaker fallback.
        if class_name:
            result = self._search_files(
                python_files,
                [class_name],
                class_name,
            )
            if result[0] is not None:
                return result

        return None, None, ""

# شرح الدالة _search_files: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _search_files(self, files, terms, anchor, prefer_ui=False):
        best = None
        lines = []

        for path in files:
            try:
                lines = path.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).splitlines()
            except OSError:
                continue

            for idx, line in enumerate(lines):
                if not all(term in line for term in terms):
                    continue

                score = 0
                if prefer_ui and any(
                    token in line
                    for token in (
                        "setText(",
                        "setWindowTitle(",
                        "setPlaceholderText(",
                        "QLabel(",
                        "QPushButton(",
                        "QCheckBox(",
                        "QRadioButton(",
                        "addItem(",
                        "addItems(",
                    )
                ):
                    score += 10

                # objectName assignments are stronger than generic occurrences.
                if "setObjectName" in line:
                    score += 20
                if anchor and anchor in line:
                    score += 5

                candidate = (score, path, idx + 1)
                if best is None or candidate[0] > best[0]:
                    best = candidate

        if best is None:
            return None, None, ""

        _, path, line_no = best

        start = max(0, line_no - 8)
        end = min(len(lines), line_no + 8)
        selected_lines = []
        # Re-read after selecting the path so the snippet is tied to the right file.
        try:
            selected_lines = path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()
        except OSError:
            return None, None, ""

        start = max(0, line_no - 9)
        end = min(len(selected_lines), line_no + 8)

        numbered = []
        for n in range(start, end):
            marker = ">>" if n + 1 == line_no else "  "
            numbered.append(
                f"{marker} {n + 1:4d} | {selected_lines[n]}"
            )

        return path, line_no, "\n".join(numbered)

    # ============================================================
    # Preview tools
    # ============================================================

# شرح الدالة _preview_size: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _preview_size(self):
        w = self.selected_widget
        if w is None:
            return

        self.preview.preview(
            w,
            {
                "minimum_width": self.w_spin.value(),
                "minimum_height": self.h_spin.value(),
                "border_radius": self.radius_spin.value(),
                "padding": self.padding_spin.value(),
            },
        )
        self.overlay.update()

# شرح الدالة _preview_typography: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _preview_typography(self, value):
        if self.selected_widget is None:
            return

        self.preview.preview(
            self.selected_widget,
            {"font_size": value},
        )
        self._refresh_selection()

# شرح الدالة _preview_state: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _preview_state(self, state):
        w = self.selected_widget
        if w is None:
            return

        if state == "Disabled":
            w.setEnabled(False)
        else:
            w.setEnabled(True)
            if state == "Focus":
                w.setFocus()

        self.state_info.setText(f"Temporary state: {state}")

# شرح الدالة _preview_window_size: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _preview_window_size(self):
        self.main_window.resize(
            self.res_w.value(),
            self.res_h.value(),
        )

# شرح الدالة _toggle_overlay: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _toggle_overlay(self, enabled):
        if enabled and self.selected_widget is not None:
            self.overlay.set_target(self.selected_widget)
        else:
            self.overlay.hide()

# شرح الدالة _toggle_grid: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _toggle_grid(self, enabled):
        if enabled:
            self.grid_overlay.sync()
            self.grid_overlay.show()
            self.grid_overlay.raise_()
        else:
            self.grid_overlay.hide()

    # ============================================================
    # Code source actions
    # ============================================================

# شرح الدالة _copy_source: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _copy_source(self):
        text = self.source_editor.toPlainText().strip()
        if not text:
            return
        QApplication.clipboard().setText(text)

# شرح الدالة _open_source_file: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _open_source_file(self):
        if self._source_file is None:
            return

        try:
            import os

            os.startfile(str(self._source_file))
        except (AttributeError, OSError):
            QMessageBox.information(
                self,
                "Code Source",
                str(self._source_file),
            )

# شرح الدالة _open_source_in_vscode: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _open_source_in_vscode(self):
        """فتح ملف المصدر في VS Code مباشرة عند السطر المكتشف."""
        if self._source_file is None or self._source_line is None:
            return

        target = f"{self._source_file}:{self._source_line}"

        # ابحث أولاً عن أمر VS Code في PATH، ثم عن التثبيتات الشائعة في Windows.
        vscode_command = (
            shutil.which("code")
            or shutil.which("code.cmd")
            or self._find_vscode_executable()
        )

        if vscode_command is None:
            QMessageBox.warning(
                self,
                "VS Code",
                "VS Code could not be located on this computer.\n\n"
                "Please make sure Visual Studio Code is installed.",
            )
            return

        try:
            subprocess.Popen(
                [str(vscode_command), "--goto", target],
                shell=False,
            )
        except (FileNotFoundError, OSError) as exc:
            QMessageBox.warning(
                self,
                "VS Code",
                f"Could not open VS Code.\n\n{exc}",
            )

# شرح الدالة _find_vscode_executable: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _find_vscode_executable():
        """العثور على ملف تشغيل VS Code في مسارات Windows الشائعة."""
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("PROGRAMFILES", "")
        program_files_x86 = os.environ.get("PROGRAMFILES(X86)", "")

        candidates = [
            Path(local_app_data) / "Programs" / "Microsoft VS Code" / "Code.exe",
            Path(program_files) / "Microsoft VS Code" / "Code.exe",
            Path(program_files_x86) / "Microsoft VS Code" / "Code.exe",
        ]

        for candidate in candidates:
            if candidate.is_file():
                return candidate

        return None

    # ============================================================
    # Save / restore
    # ============================================================

# شرح الدالة save_current: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def save_current(self):
        w = self.selected_widget

        if w is not None and self.preview.save(w):
            QMessageBox.information(
                self,
                "Visual Dev Kit",
                "The selected widget preview has been saved.",
            )
            return

        QMessageBox.information(
            self,
            "Visual Dev Kit",
            "There are no pending visual changes.",
        )

# شرح الدالة restore_current: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def restore_current(self):
        if self.selected_widget is None:
            return

        self.preview.restore(self.selected_widget)
        self._refresh_selection()
        self.overlay.update()

    # ============================================================
    # Navigation / lifecycle
    # ============================================================

# شرح الدالة _tool_changed: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _tool_changed(self, row):
        if row < 0:
            return

        key = self.nav.item(row).data(Qt.ItemDataRole.UserRole)
        page = self.pages.get(key)

        if page is not None:
            self.stack.setCurrentWidget(page)

        if key == "source":
            self._refresh_source()

# شرح الدالة show_kit: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def show_kit(self, tool="overview"):
        self.show()
        self.raise_()
        self.activateWindow()

        if tool:
            for i in range(self.nav.count()):
                if self.nav.item(i).data(Qt.ItemDataRole.UserRole) == tool:
                    self.nav.setCurrentRow(i)
                    break

# شرح الدالة closeEvent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def closeEvent(self, event):
        self.overlay.hide()
        self.grid_overlay.hide()
        event.ignore()
        self.hide()

# شرح الدالة hideEvent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def hideEvent(self, event):
        self.overlay.hide()
        self.grid_overlay.hide()
        super().hideEvent(event)


# شرح الدالة install_visual_dev_kit: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def install_visual_dev_kit(main_window, project_root=None):
    existing = getattr(main_window, "_visual_dev_kit", None)

    if existing is not None:
        return existing

    kit = VisualDevKit(main_window, project_root)
    main_window._visual_dev_kit = kit
    return kit


__all__ = ["VisualDevKit", "install_visual_dev_kit"]

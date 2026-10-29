# ============================================================
# شرح الملف: dev_tools/ui_color_inspector.py
# هذا الملف جزء من أدوات التطوير والتشخيص ومراقبة الأداء.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""BuildOffice Pro - UI Color Inspector.

Modern Inspector version based on:
- An interface that follows the active application theme.
- More accurate tracking of the clicked widget.
- Show only colors that directly apply to the selected widget.
- Do not mix parent or global window colors with widget colors.
- Link Hex colors to Theme Tokens when possible.
- Keep Ctrl+Shift+I and install_color_inspector as the public application interface.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QColor, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from theme.colors import INSPECTOR_PALETTE
from theme.metrics import UI_FONT_FAMILY

# التكامل مع نظام السمات اختياري لأداة الفحص، لكن فشل جزء واحد لا يعطل الأجزاء الأخرى.
try:
    from theme import ThemeStore
except (ImportError, AttributeError, ModuleNotFoundError):
    ThemeStore = None

try:
    from theme.themes import get_token_palette
except (ImportError, AttributeError, ModuleNotFoundError):
    get_token_palette = None

try:
    from theme.token_metadata import describe_token
except (ImportError, AttributeError, ModuleNotFoundError):

# شرح الدالة describe_token: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def describe_token(token: str) -> dict[str, str]:
        return {"category": "unknown", "label": token, "role": token}


try:
    from theme.qss import resolve_style as lightify
    from theme.qss import selector_token
except (ImportError, AttributeError, ModuleNotFoundError):

# شرح الدالة lightify: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def lightify(
        style: str, theme: str | None = None, store: Any = None
    ) -> str:
        return style

# شرح الدالة selector_token: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def selector_token(selector: str, property_name: str) -> str | None:
        return None


HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}(?![0-9A-Fa-f])")
PROPERTY_RE = re.compile(
    r"(?P<property>[A-Za-z_-]+)\s*:\s*(?P<value>[^;{}]+)", re.IGNORECASE
)
BLOCK_RE = re.compile(r"(?P<selectors>[^{}]+)\{(?P<body>[^{}]*)\}", re.DOTALL)
ATTR_RE = re.compile(
    r"\[\s*(?P<name>[A-Za-z_][\w-]*)\s*(?:=\s*[\"']?(?P<value>[^\"'\]]+)[\"']?)?\s*\]"
)
PSEUDO_RE = re.compile(
    r":(?:hover|pressed|checked|unchecked|disabled|enabled|focus|selected|on|off|open|closed)(?:\([^)]*\))?",
    re.IGNORECASE,
)
EXTENSIONS = {".py", ".qss", ".css"}
SKIP_DIRS = {"__pycache__", ".git", ".venv", "venv", "build", "dist", "node_modules"}


# ------------------------------------------------------------
# Discovered color record
# ------------------------------------------------------------
# شرح الصنف ColorRecord: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
@dataclass(frozen=True)
class ColorRecord:
    color: str
    role: str
    property_name: str
    selector: str
    source_kind: str
    state: str
    token: str = ""
    token_role: str = ""


# شرح الصنف _IndexWorker: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class _IndexWorker(QObject):
    finished = Signal(dict)

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root

# شرح الدالة run: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @Slot()
    def run(self) -> None:
        index: dict[str, list[str]] = {}
        try:
            if not self.root.exists():
                self.finished.emit(index)
                return
            for path in self.root.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                    continue
                if any(part in SKIP_DIRS for part in path.parts):
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                rel = str(path.relative_to(self.root))
                for line_no, line in enumerate(text.splitlines(), 1):
                    for color in HEX_RE.findall(line):
                        index.setdefault(color.upper(), []).append(
                            f"{rel}:{line_no}    {line.strip()}"
                        )
        finally:
            self.finished.emit(index)


# شرح الصنف ColorInspectorDialog: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class ColorInspectorDialog(QWidget):
    """مكوّن فحص الألوان القابل للعرض داخل Dev Kit أو كواجهة مستقلة."""

    THEME_QSS = r"""
    QWidget#uiColorInspector {
        background: @background@;
        color: @components.tooltip.tooltip@;
        font-family: "__UI_FONT_FAMILY__";
    }
    QFrame#inspectorHeader, QFrame#selectionCard, QFrame#colorsCard,
    QFrame#detailsCard, QFrame#sourceCard {
        background: @surface@;
        border: 1px solid @components.inspector.inspector_border@;
        border-radius: 12px;
    }
    QLabel#inspectorTitle { color: @components.tooltip.tooltip@; font-size: 22px; font-weight: 900; }
    QLabel#inspectorSubtitle, QLabel#mutedText { color: @components.inspector.inspector_muted@; font-size: 11px; }
    QLabel#themeChip, QLabel#selectionChip {
        background: @components.inspector.inspector_selected@; color: @components.inspector.inspector_badge_text@;
        border: 1px solid @components.inspector.inspector_accent_border@; border-radius: 8px;
        padding: 6px 10px; font-weight: 800;
    }
    QLabel#sectionTitle { color: @text_secondary@; font-size: 13px; font-weight: 900; }
    QLabel#fieldLabel { color: @components.inspector.inspector_label@; font-size: 10px; font-weight: 800; }
    QLabel#fieldValue { color: @components.tooltip.tooltip@; font-size: 12px; font-weight: 700; }
    QFrame#trackingFrame {
        background: @components.inspector.inspector_surface@; border: 1px solid @components.inspector.inspector_card_border@; border-radius: 10px;
    }
    QLineEdit#quickFilter {
        background: @components.inspector.inspector_surface@; color: @components.tooltip.tooltip@;
        border: 1px solid @components.inspector.inspector_field_border@; border-radius: 8px; padding: 7px 9px;
    }
    QLineEdit#quickFilter:focus { border: 1px solid @primary@; }
    QListWidget#colorList {
        background: @components.inspector.inspector_surface@; border: 1px solid @components.inspector.inspector_field_border@;
        border-radius: 9px; outline: 0; padding: 3px;
    }
    QListWidget#colorList::item { border-bottom: 1px solid @components.inspector.inspector_list_divider@; padding: 0; }
    QListWidget#colorList::item:selected { background: @components.inspector.inspector_selected@; color: @components.tooltip.tooltip@; border-left: 3px solid @primary@; }
    QLabel#swatch { border: 1px solid @components.inspector.inspector_swatch_border@; border-radius: 6px; }
    QLabel#hexValue { color: @components.tooltip.tooltip@; font-size: 12px; font-weight: 900; }
    QLabel#roleValue { color: @text_secondary@; font-size: 10px; }
    QLabel#tokenBadge {
        background: @components.inspector.inspector_badge_bg@; color: @components.buttons.button_text_muted@; border: 1px solid @components.inspector.inspector_badge_border@;
        border-radius: 6px; padding: 3px 6px; font-size: 9px; font-weight: 800;
    }
    QLabel#emptyState { color: @components.inspector.inspector_empty@; font-size: 12px; }
    QLabel#detailsValue { color: @text_secondary@; font-size: 11px; }
    QFrame#oldSwatch, QFrame#newSwatch { border: 1px solid @components.inspector.inspector_swatch_border@; border-radius: 7px; }
    QPushButton {
        background: @surface@; color: @components.buttons.button_text@;
        border: 1px solid @components.inspector.inspector_input_border@; border-radius: 8px;
        padding: 7px 11px; font-weight: 800;
    }
    QPushButton:hover { background: @hover@; border-color: @primary@; }
    QPushButton:pressed { background: @components.inspector.inspector_pressed@; }
    QPushButton#primaryAction { background: @primary@; color: @components.tooltip.tooltip@; border-color: @components.buttons.primary_border@; }
    QPushButton#primaryAction:hover { background: @components.buttons.primary_hover@; }
    QPushButton#dangerAction { color: @components.states.danger_text@; }
    QCheckBox { color: @components.buttons.button_text@; font-weight: 800; spacing: 6px; }
    QTextEdit, QPlainTextEdit {
        background: @components.inspector.inspector_surface@; color: @components.forms.input_text@;
        border: 1px solid @components.inspector.inspector_field_border@; border-radius: 9px; padding: 6px;
    }
    QScrollBar:vertical { background: @components.inspector.inspector_scroll_bg@; width: 9px; border: 0; }
    QScrollBar::handle:vertical { background: @components.inspector.inspector_scroll@; border-radius: 4px; min-height: 24px; }
    QScrollBar::handle:vertical:hover { background: @components.inspector.inspector_scroll_hover@; }
    """

    # اسم التوافق يحافظ على أي كود قديم يشير إلى LIGHT_QSS.
    LIGHT_QSS = THEME_QSS

    def __init__(self, parent=None, project_root=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
        )
        self.setObjectName("uiColorInspector")
        self._force_light_palette()
        self.selected_theme = "Light"
        self.setStyleSheet(self._resolved_inspector_style())
        self.project_root = Path(project_root or Path.cwd()).resolve()

        self.index: dict[str, list[str]] = {}
        self.current_widget: QWidget | None = None
        self.records: list[ColorRecord] = []
        self.filtered_records: list[ColorRecord] = []
        self.selected_record: ColorRecord | None = None
        self.new_color = ""
        self.preview_original = ""
        self.preview_active = False
        self._outline: QFrame | None = None
        self._thread = None
        self._worker = None
        self._token_colors: dict[str, dict[str, str]] = {}
        self._build_token_index()
        self._build_ui()
        self.request_index()

    # ------------------------------------------------------------
    # Theme / token integration
    # ------------------------------------------------------------
# شرح الدالة _force_light_palette: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _force_light_palette(self) -> None:
        palette = QPalette()
        colors = {
            QPalette.ColorRole.Window: INSPECTOR_PALETTE["background"],
            QPalette.ColorRole.WindowText: INSPECTOR_PALETTE["text"],
            QPalette.ColorRole.Base: INSPECTOR_PALETTE["surface"],
            QPalette.ColorRole.AlternateBase: INSPECTOR_PALETTE["alternate"],
            QPalette.ColorRole.Text: INSPECTOR_PALETTE["text"],
            QPalette.ColorRole.Button: INSPECTOR_PALETTE["surface"],
            QPalette.ColorRole.ButtonText: INSPECTOR_PALETTE["text"],
            QPalette.ColorRole.BrightText: INSPECTOR_PALETTE["text"],
            QPalette.ColorRole.Highlight: INSPECTOR_PALETTE["accent"],
            QPalette.ColorRole.HighlightedText: INSPECTOR_PALETTE["text"],
            QPalette.ColorRole.ToolTipBase: INSPECTOR_PALETTE["surface"],
            QPalette.ColorRole.ToolTipText: INSPECTOR_PALETTE["text"],
            QPalette.ColorRole.PlaceholderText: INSPECTOR_PALETTE["placeholder"],
        }
        for group in (
            QPalette.ColorGroup.Active,
            QPalette.ColorGroup.Inactive,
            QPalette.ColorGroup.Disabled,
        ):
            for role, color in colors.items():
                palette.setColor(group, role, QColor(color))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

# شرح الدالة _current_theme: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _current_theme(self) -> str:
        return "Light"

# شرح الدالة _theme_store: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _theme_store(self):
        # استخدام مخزن السمة الموجود في التطبيق، وإن تعذر فإيجاد مخزن محلي آمن.
        app = QApplication.instance()
        if app is not None:
            try:
                value = app.property("buildoffice_theme_store")
                if ThemeStore is not None and isinstance(value, ThemeStore):
                    return value
            except RuntimeError:
                pass
        if ThemeStore is None:
            return None
        try:
            return ThemeStore(None, auto_load=False)
        except (TypeError, ValueError, RuntimeError):
            return None

# شرح الدالة _resolved_inspector_style: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _resolved_inspector_style(self) -> str:
        # حل جميع رموز السمة قبل تمرير CSS إلى Qt حتى لا تظهر أخطاء محلل QSS.
        store = self._theme_store()
        theme = "Light"
        self.selected_theme = theme
        if store is None:
            return self.THEME_QSS.replace("__UI_FONT_FAMILY__", UI_FONT_FAMILY)
        return lightify(self.THEME_QSS, theme=theme, store=store).replace(
            "__UI_FONT_FAMILY__", UI_FONT_FAMILY
        )

# شرح الدالة _resolve_inspector_fragment: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _resolve_inspector_fragment(self, style: str) -> str:
        # حل أي تنسيق محلي مع السمة نفسها قبل تطبيقه على عنصر محدد.
        store = self._theme_store()
        theme = self._current_theme()
        self.selected_theme = theme
        if store is None:
            return style
        return lightify(style, theme=theme, store=store)

# شرح الدالة _apply_local_theme_style: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _apply_local_theme_style(self, widget: QWidget, style: str) -> None:
        # حفظ القالب الأصلي وإعادة حله كلما احتجنا إلى تحديث السمة.
        widget.setProperty("_bo_theme_style", style)
        widget.setStyleSheet(self._resolve_inspector_fragment(style))

# شرح الدالة _build_token_index: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_token_index(self) -> None:
        self._token_colors = {}
        try:
            for theme in ("Dark", "Light"):
                colors: dict[str, str] = {}
                try:
                    import theme.colors as theme_colors

                    all_tokens = tuple(getattr(theme_colors, "ALL_TOKENS", ()))
                except (ImportError, AttributeError, ModuleNotFoundError):
                    all_tokens = ()
                if ThemeStore is not None:
                    try:
                        store = ThemeStore(None, auto_load=False)
                        for token in all_tokens:
                            colors[token] = store.get_color(theme, token).upper()
                    except (TypeError, ValueError, RuntimeError, AttributeError):
                        pass
                if not colors:
                    try:
                        if get_token_palette is not None:
                            for token in all_tokens:
                                colors[token] = get_token_palette(theme, token)[
                                    "option_1"
                                ].upper()
                    except (TypeError, ValueError, KeyError, AttributeError):
                        colors = {}
                self._token_colors[theme] = colors
        except (TypeError, ValueError, AttributeError, RuntimeError):
            self._token_colors = {"Dark": {}, "Light": {}}

# شرح الدالة _token_for_color: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _token_for_color(self, theme: str, color: str) -> tuple[str, str]:
        color = str(color).upper()
        matches = [
            token
            for token, value in self._token_colors.get(theme, {}).items()
            if value == color
        ]
        if len(matches) == 1:
            meta = describe_token(matches[0])
            return matches[0], meta.get("role", "")
        if matches:
            return " / ".join(matches[:3]), "Multiple Tokens share the same value"
        return "", ""

    # ------------------------------------------------------------
    # UI
    # ------------------------------------------------------------
# شرح الدالة _build_ui: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        header = QFrame()
        header.setObjectName("inspectorHeader")
        h = QHBoxLayout(header)
        h.setContentsMargins(14, 12, 14, 12)
        title_box = QVBoxLayout()
        title = QLabel("UI Color Inspector")
        title.setObjectName("inspectorTitle")
        subtitle = QLabel(
            "Detect the actual color of the selected widget and link it to the central color system"
        )
        subtitle.setObjectName("inspectorSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        h.addLayout(title_box, 1)
        self.theme_chip = QLabel("☀ Inspector UI • Light")
        self.theme_chip.setObjectName("themeChip")
        h.addWidget(self.theme_chip, 0, Qt.AlignmentFlag.AlignTop)
        root.addWidget(header)

        selection = QFrame()
        selection.setObjectName("selectionCard")
        grid = QGridLayout(selection)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(7)
        self._add_field(grid, 0, 0, "Qt Type", "-")
        self._add_field(grid, 0, 2, "Identifier", "-")
        self._add_field(grid, 1, 0, "Object name", "-")
        self._add_field(grid, 1, 2, "Widget Nature", "-")
        self.type_value = self._grid_widget(grid, 0, 1)
        self.name_value = self._grid_widget(grid, 0, 3)
        self.object_value = self._grid_widget(grid, 1, 1)
        self.nature_value = self._grid_widget(grid, 1, 3)
        self.selection_chip = QLabel("No widget selected")
        self.selection_chip.setObjectName("selectionChip")
        grid.addWidget(self.selection_chip, 0, 4, 2, 1)
        root.addWidget(selection)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(7)
        root.addWidget(splitter, 1)

        left = QFrame()
        left.setObjectName("colorsCard")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 10, 10, 10)
        top = QHBoxLayout()
        label = QLabel("🎨 Colors in Selected Widget")
        label.setObjectName("sectionTitle")
        top.addWidget(label)
        top.addStretch()
        self.count_label = QLabel("0")
        self.count_label.setObjectName("mutedText")
        top.addWidget(self.count_label)
        ll.addLayout(top)
        self.quick_filter = QLineEdit()
        self.quick_filter.setObjectName("quickFilter")
        self.quick_filter.setPlaceholderText("Search within widget colors…")
        self.quick_filter.textChanged.connect(self._apply_filter)
        ll.addWidget(self.quick_filter)
        self.colors = QListWidget()
        self.colors.setObjectName("colorList")
        self.colors.setSpacing(1)
        self.colors.itemSelectionChanged.connect(self._record_selected)
        ll.addWidget(self.colors, 1)
        splitter.addWidget(left)

        right = QFrame()
        right.setObjectName("detailsCard")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(12, 10, 12, 10)
        rhead = QHBoxLayout()
        detail_title = QLabel("🔎 Color Details")
        detail_title.setObjectName("sectionTitle")
        rhead.addWidget(detail_title)
        rhead.addStretch()
        self.detail_state = QLabel("-")
        self.detail_state.setObjectName("mutedText")
        rhead.addWidget(self.detail_state)
        rl.addLayout(rhead)

        info = QGridLayout()
        info.setHorizontalSpacing(14)
        info.setVerticalSpacing(8)
        self.hex_value = self._add_info_row(info, 0, "Hex", "-")
        self.role_value = self._add_info_row(info, 1, "Role", "-")
        self.property_value = self._add_info_row(info, 2, "Property", "-")
        self.selector_value = self._add_info_row(info, 3, "Selector", "-")
        self.state_value = self._add_info_row(info, 4, "State", "-")
        self.token_value = self._add_info_row(info, 5, "Token", "Not linked")
        self.token_role_value = self._add_info_row(info, 6, "Token Meaning", "-")
        rl.addLayout(info)

        compare = QFrame()
        compare.setObjectName("trackingFrame")
        cl = QVBoxLayout(compare)
        cl.setContentsMargins(10, 8, 10, 8)
        ct = QLabel("Comparison")
        ct.setObjectName("fieldLabel")
        cl.addWidget(ct)
        cr = QHBoxLayout()
        self.old_swatch = QFrame()
        self.old_swatch.setObjectName("oldSwatch")
        self.old_swatch.setFixedSize(56, 36)
        self.old_hex = QLabel("-")
        self.old_hex.setObjectName("fieldValue")
        arrow = QLabel("→")
        arrow.setObjectName("mutedText")
        self.new_swatch = QFrame()
        self.new_swatch.setObjectName("newSwatch")
        self.new_swatch.setFixedSize(56, 36)
        self.new_hex = QLabel("-")
        self.new_hex.setObjectName("fieldValue")
        cr.addWidget(self.old_swatch)
        cr.addWidget(self.old_hex)
        cr.addSpacing(8)
        cr.addWidget(arrow)
        cr.addSpacing(8)
        cr.addWidget(self.new_swatch)
        cr.addWidget(self.new_hex)
        cr.addStretch()
        cl.addLayout(cr)
        rl.addWidget(compare)

        actions = QHBoxLayout()
        self.pick_button = QPushButton("🎨 Change Color")
        self.pick_button.setObjectName("primaryAction")
        self.pick_button.clicked.connect(self.pick_color)
        self.preview_button = QPushButton("👁 Preview")
        self.preview_button.clicked.connect(self.preview_color_change)
        self.reset_button = QPushButton("↩ Restore")
        self.reset_button.setObjectName("dangerAction")
        self.reset_button.clicked.connect(self.reset_preview)
        self.pick_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.reset_button.setEnabled(False)
        actions.addWidget(self.pick_button)
        actions.addWidget(self.preview_button)
        actions.addWidget(self.reset_button)
        actions.addStretch()
        rl.addLayout(actions)
        splitter.addWidget(right)
        splitter.setSizes([520, 560])

        source = QFrame()
        source.setObjectName("sourceCard")
        sl = QVBoxLayout(source)
        sl.setContentsMargins(10, 8, 10, 8)
        sh = QHBoxLayout()
        st = QLabel("📍 Source of the rule applied to the widget")
        st.setObjectName("sectionTitle")
        sh.addWidget(st)
        sh.addStretch()
        self.copy_button = QPushButton("Copy")
        self.copy_button.clicked.connect(self.copy_source)
        self.copy_button.setEnabled(False)
        sh.addWidget(self.copy_button)
        sl.addLayout(sh)
        self.source_label = QLabel("Select a widget to view only the matching rules.")
        self.source_label.setObjectName("detailsValue")
        self.source_label.setWordWrap(True)
        self.source_label.setMinimumHeight(0)
        sl.addWidget(self.source_label)
        root.addWidget(source)

        bottom = QHBoxLayout()
        self.inspect_check = QCheckBox("🎯 Track Clicks")
        self.inspect_check.setChecked(True)
        bottom.addWidget(self.inspect_check)
        refresh = QPushButton("↻ Refresh Index")
        refresh.clicked.connect(self.request_index)
        bottom.addWidget(refresh)
        bottom.addStretch()
        self.status = QLabel("Ready")
        self.status.setObjectName("mutedText")
        bottom.addWidget(self.status)
        close = QPushButton("Close")
        close.clicked.connect(self.hide)
        bottom.addWidget(close)
        root.addLayout(bottom)

# شرح الدالة _grid_widget: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _grid_widget(grid: QGridLayout, row: int, col: int) -> QLabel | None:
        item = grid.itemAtPosition(row, col)
        if item is None:
            return None
        widget = item.widget()
        return widget if isinstance(widget, QLabel) else None

# شرح الدالة _add_field: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _add_field(
        grid: QGridLayout, row: int, col: int, label: str, value: str
    ) -> None:
        l = QLabel(label)
        l.setObjectName("fieldLabel")
        v = QLabel(value)
        v.setObjectName("fieldValue")
        v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        grid.addWidget(l, row, col)
        grid.addWidget(v, row, col + 1)

# شرح الدالة _add_info_row: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _add_info_row(grid: QGridLayout, row: int, label: str, value: str) -> QLabel:
        l = QLabel(label)
        l.setObjectName("fieldLabel")
        v = QLabel(value)
        v.setObjectName("detailsValue")
        v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v.setWordWrap(True)
        grid.addWidget(l, row, 0)
        grid.addWidget(v, row, 1)
        return v

    # ------------------------------------------------------------
    # Widget tracking
    # ------------------------------------------------------------
# شرح الدالة _widget_nature: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _widget_nature(widget: QWidget) -> str:
        name = widget.metaObject().className()
        if name in {
            "QLabel",
            "QLineEdit",
            "QTextEdit",
            "QPlainTextEdit",
            "QTextBrowser",
        }:
            return "📝 Text / Content"
        if name in {"QPushButton", "QToolButton", "QCommandLinkButton"}:
            return "🔘 Button / Interactive Control"
        if name == "QCheckBox":
            return "☑️ Check Box"
        if name == "QRadioButton":
            return "🔘 Radio Option"
        if name == "QComboBox":
            return "📋 Drop-down List"
        if name in {"QTableWidget", "QTableView"}:
            return "📊 Table"
        if name in {"QTreeWidget", "QTreeView"}:
            return "🌳 Tree"
        if name in {"QListWidget", "QListView"}:
            return "📃 List"
        if name in {"QDateEdit", "QTimeEdit", "QDateTimeEdit", "QCalendarWidget"}:
            return "📅 Date / Time"
        if name in {"QSpinBox", "QDoubleSpinBox"}:
            return "🔢 Numeric Field"
        if name == "QProgressBar":
            return "📈 Progress Bar"
        if name in {"QSlider", "QDial"}:
            return "🎚️ Control"
        if name in {
            "QFrame",
            "QGroupBox",
            "QScrollArea",
            "QStackedWidget",
            "QTabWidget",
        }:
            return "⬛ Container / Shape"
        return "🧩 General UI Element"

# شرح الدالة _classes: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _classes(widget: QWidget) -> set[str]:
        values = set()
        meta = widget.metaObject()
        while meta is not None:
            values.add(meta.className())
            meta = meta.superClass()
        return values

# شرح الدالة _strip_states: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _strip_states(selector: str) -> tuple[str, str]:
        states = PSEUDO_RE.findall(selector)
        clean = PSEUDO_RE.sub("", selector)
        state = ", ".join(s.lstrip(":") for s in states) if states else "Normal"
        return clean.strip(), state

# شرح الدالة _simple_matches: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _simple_matches(self, simple: str, widget: QWidget) -> bool:
        simple = simple.strip()
        if not simple:
            return False
        attrs = ATTR_RE.findall(simple)
        for name, value in attrs:
            current = widget.property(name)
            if value is None:
                if current is None:
                    return False
            else:
                normalized = str(value).strip().strip("\"'")
                if str(current).lower() != normalized.lower():
                    return False
        simple = ATTR_RE.sub("", simple).strip()
        if "#" in simple:
            type_part, object_name = simple.split("#", 1)
            if object_name and widget.objectName() != object_name:
                return False
            simple = type_part
        if "." in simple:
            pieces = simple.split(".")
            simple = pieces[0]
            for css_class in pieces[1:]:
                current = widget.property(css_class)
                if current is not True and str(current).lower() != "true":
                    return False
        return not (simple and simple != "*" and simple not in self._classes(widget))

# شرح الدالة _selector_matches: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _selector_matches(self, selector: str, widget: QWidget) -> tuple[bool, str]:
        selector, state = self._strip_states(selector)
        if not selector:
            return False, state
        # Conservative support for > and space.
        tokens = [t for t in re.split(r"\s*>\s*|\s+", selector) if t]
        if not tokens or not self._simple_matches(tokens[-1], widget):
            return False, state
        ancestor = widget.parentWidget()
        for wanted in reversed(tokens[:-1]):
            found = False
            while ancestor is not None:
                if self._simple_matches(wanted, ancestor):
                    found = True
                    ancestor = ancestor.parentWidget()
                    break
                ancestor = ancestor.parentWidget()
            if not found:
                return False, state
        return True, state

# شرح الدالة _color_role: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _color_role(prop: str) -> str:
        p = prop.lower().strip()
        if p in {"color", "selection-color", "placeholder-text-color"}:
            return "Text Color"
        if p in {
            "background",
            "background-color",
            "selection-background-color",
            "alternate-background-color",
        }:
            return "Background Color"
        if p == "border" or p.startswith("border-"):
            return "Border Color"
        if p == "outline" or p.startswith("outline-"):
            return "Outline"
        if "icon" in p:
            return "Icon Color"
        return f"Property Color {prop}"

# شرح الدالة _extract_rules: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _extract_rules(
        self, stylesheet: str, widget: QWidget, source_kind: str
    ) -> list[ColorRecord]:
        results: list[ColorRecord] = []
        if not stylesheet:
            return results
        for match in BLOCK_RE.finditer(stylesheet):
            selector_text = match.group("selectors").strip()
            body = match.group("body")
            selectors = [s.strip() for s in selector_text.split(",") if s.strip()]
            matched = [
                (selector, self._selector_matches(selector, widget))
                for selector in selectors
            ]
            matched = [(selector, state) for selector, (ok, state) in matched if ok]
            if not matched:
                continue
            for prop_match in PROPERTY_RE.finditer(body):
                prop = prop_match.group("property").strip()
                value = prop_match.group("value").strip()
                colors = HEX_RE.findall(value)
                if not colors:
                    continue
                role = self._color_role(prop)
                for selector, state in matched:
                    for color in colors:
                        token = selector_token(selector, prop) or ""
                        if token:
                            meta = describe_token(token)
                            token_role = meta.get("role", token)
                        else:
                            token, token_role = self._token_for_color(
                                self.selected_theme, color
                            )
                        results.append(
                            ColorRecord(
                                color=color.upper(),
                                role=role,
                                property_name=prop,
                                selector=selector,
                                source_kind=source_kind,
                                state=state,
                                token=token,
                                token_role=token_role,
                            )
                        )
        return results

# شرح الدالة _effective_colors: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _effective_colors(self, widget: QWidget) -> list[ColorRecord]:
        theme = self.selected_theme
        app = QApplication.instance()
        records: list[ColorRecord] = []
        try:
            local = widget.styleSheet() or ""
        except RuntimeError:
            local = ""
        records.extend(self._extract_rules(local, widget, "Widget style"))

        if isinstance(app, QApplication):
            try:
                app_style = app.styleSheet() or ""
            except RuntimeError:
                app_style = ""
            records.extend(self._extract_rules(app_style, widget, "Application style"))

        # If no direct rule exists, use _bo_dark_style only as a locally preserved source.
        if not records:
            try:
                dark_style = widget.property("_bo_dark_style")
            except RuntimeError:
                dark_style = ""
            if isinstance(dark_style, str) and dark_style:
                active = lightify(dark_style) if theme == "Light" else dark_style
                records.extend(
                    self._extract_rules(active, widget, "Saved widget style")
                )

        # Remove duplicates while preserving distinct effective selectors.
        unique: list[ColorRecord] = []
        seen = set()
        for record in records:
            key = (
                record.color,
                record.property_name.lower(),
                record.selector,
                record.state,
                record.source_kind,
            )
            if key not in seen:
                seen.add(key)
                unique.append(record)
        # Logical order: text, background, borders, states, then custom.
        order = {
            "Text Color": 0,
            "Background Color": 1,
            "Border Color": 2,
            "Outline": 3,
        }
        unique.sort(key=lambda r: (order.get(r.role, 4), r.color, r.selector))
        return unique

    # ------------------------------------------------------------
    # Selection / display
    # ------------------------------------------------------------
# شرح الدالة inspect_widget: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def inspect_widget(self, widget: QWidget) -> None:
        if widget is None or widget is self or self.isAncestorOf(widget):
            return
        try:
            if isinstance(widget.window(), QColorDialog):
                return
        except RuntimeError:
            return
        self.current_widget = widget
        self.selected_theme = self._current_theme()
        if self.preview_active:
            self.reset_preview()
        else:
            self._clear_preview_state()
        self._update_selection_header(widget)
        self.records = self._effective_colors(widget)
        self._apply_filter()
        self._draw_outline(widget)
        self.status.setText(
            f"Tracking {widget.objectName() or widget.metaObject().className()} • {len(self.records)} direct colors"
        )

# شرح الدالة _update_selection_header: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _update_selection_header(self, widget: QWidget) -> None:
        widget_type = widget.metaObject().className()
        object_name = widget.objectName() or "(No objectName)"
        nature = self._widget_nature(widget)
        if self.type_value is not None:
            self.type_value.setText(widget_type)
        if self.name_value is not None:
            self.name_value.setText(widget.objectName() or widget_type)
        if self.object_value is not None:
            self.object_value.setText(object_name)
        if self.nature_value is not None:
            self.nature_value.setText(nature)
        if self.selection_chip is not None:
            self.selection_chip.setText(f"🎯 {object_name} • {widget_type}")
        if self.detail_state is not None:
            self.detail_state.setText(f"☀ {self.selected_theme}")

# شرح الدالة _apply_filter: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _apply_filter(self) -> None:
        term = (
            self.quick_filter.text().strip().lower()
            if hasattr(self, "quick_filter")
            else ""
        )
        self.filtered_records = [
            r
            for r in self.records
            if not term
            or term in r.color.lower()
            or term in r.role.lower()
            or term in r.token.lower()
            or term in r.property_name.lower()
        ]
        self.colors.blockSignals(True)
        self.colors.clear()
        for idx, record in enumerate(self.filtered_records):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, idx)
            item.setSizeHint(self._row_widget(record).sizeHint())
            self.colors.addItem(item)
            self.colors.setItemWidget(item, self._row_widget(record))
        self.colors.blockSignals(False)
        self.count_label.setText(f"{len(self.filtered_records)} / {len(self.records)}")
        if self.filtered_records:
            self.colors.setCurrentRow(0)
        else:
            self._clear_details()

# شرح الدالة _row_widget: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _row_widget(self, record: ColorRecord) -> QWidget:
        row = QWidget()
        row.setMinimumHeight(54)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(9, 7, 8, 7)
        lay.setSpacing(8)
        swatch = QLabel()
        swatch.setObjectName("swatch")
        swatch.setFixedSize(32, 32)
        self._apply_local_theme_style(
            swatch,
            f"QLabel#swatch {{ background:{record.color}; border:1px solid @components.inspector.inspector_swatch_border@; border-radius:6px; }}",
        )
        lay.addWidget(swatch)
        text = QVBoxLayout()
        line = QHBoxLayout()
        hex_label = QLabel(record.color)
        hex_label.setObjectName("hexValue")
        line.addWidget(hex_label)
        line.addSpacing(5)
        role = QLabel(record.role)
        role.setObjectName("roleValue")
        line.addWidget(role)
        line.addStretch()
        text.addLayout(line)
        meta_text = f"{record.property_name}  •  {record.state}"
        meta = QLabel(meta_text)
        meta.setObjectName("roleValue")
        text.addWidget(meta)
        lay.addLayout(text, 1)
        if record.token:
            badge = QLabel(record.token)
            badge.setObjectName("tokenBadge")
            lay.addWidget(badge)
        return row

# شرح الدالة _record_selected: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _record_selected(self) -> None:
        item = self.colors.currentItem()
        if item is None:
            return
        idx = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(idx, int) or idx < 0 or idx >= len(self.filtered_records):
            return
        self.selected_record = self.filtered_records[idx]
        self._show_record(self.selected_record)

# شرح الدالة _show_record: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _show_record(self, record: ColorRecord) -> None:
        self.hex_value.setText(record.color)
        self.role_value.setText(record.role)
        self.property_value.setText(record.property_name)
        self.selector_value.setText(record.selector)
        self.state_value.setText(record.state)
        self.token_value.setText(record.token or "Not linked directly")
        self.token_role_value.setText(record.token_role or "No unique mapping")
        self.old_hex.setText(record.color)
        self.new_hex.setText(self.new_color or record.color)
        self._set_box(self.old_swatch, record.color)
        self._set_box(self.new_swatch, self.new_color or record.color)
        self.pick_button.setEnabled(True)
        self.preview_button.setEnabled(
            bool(self.new_color and self.new_color != record.color)
        )
        self.reset_button.setEnabled(self.preview_active)

        source = (
            f"{record.source_kind}\n"
            f"Selector: {record.selector}\n"
            f"Property: {record.property_name}\n"
            f"Role: {record.role}"
        )
        locations = self.index.get(record.color, [])
        if locations:
            relevant = [
                line
                for line in locations
                if record.selector.split()[-1].replace("#", "") in line
            ]
            if relevant:
                source += "\n\n" + "\n".join(relevant[:5])
        self.source_label.setText(source)
        self.copy_button.setEnabled(True)
        self.status.setText(f"{record.color} • {record.role} • {record.property_name}")

# شرح الدالة _clear_details: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _clear_details(self) -> None:
        for attr in (
            "hex_value",
            "role_value",
            "property_value",
            "selector_value",
            "state_value",
            "token_value",
            "token_role_value",
        ):
            if hasattr(self, attr):
                getattr(self, attr).setText("-")
        self.pick_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.reset_button.setEnabled(False)
        self.copy_button.setEnabled(False)
        self.source_label.setText("No direct colors match this widget.")

# شرح الدالة _set_box: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _set_box(self, frame: QFrame, color: str) -> None:
        # تطبيق تنسيق المعاينة عبر محرك السمات حتى تبقى الألوان متوافقة مع السمة النشطة.
        self._apply_local_theme_style(
            frame,
            f"QFrame#{frame.objectName()} {{ background:{color}; border:1px solid @components.inspector.inspector_swatch_border@; border-radius:7px; }}",
        )

    # ------------------------------------------------------------
    # Preview / color picker
    # ------------------------------------------------------------
# شرح الدالة pick_color: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def pick_color(self) -> None:
        if not self.selected_record:
            return
        current = QColor(self.new_color or self.selected_record.color)
        picker = QColorDialog(current, self)
        picker.setWindowTitle("Choose a New Color")
        picker.setModal(True)
        self._picker_open = True
        try:
            if picker.exec() != QDialog.DialogCode.Accepted:
                return
            color = picker.selectedColor()
        finally:
            self._picker_open = False
            picker.deleteLater()
        if not color.isValid():
            return
        self.new_color = color.name(QColor.NameFormat.HexRgb).upper()
        self._show_record(self.selected_record)

# شرح الدالة preview_color_change: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def preview_color_change(self) -> None:
        if (
            not self.selected_record
            or not self.new_color
            or self.new_color == self.selected_record.color
        ):
            return
        widget = self.current_widget
        if widget is None:
            return
        try:
            original = widget.styleSheet() or ""
            if not self.preview_active:
                self.preview_original = original
            modified = re.sub(
                re.escape(self.selected_record.color),
                self.new_color,
                original,
                flags=re.IGNORECASE,
            )
            if modified == original:
                # No local value exists; add only the property found by the Inspector.
                prop = self.selected_record.property_name
                modified = (
                    f"{original}\nQWidget#{widget.objectName()} {{ {prop}: {self.new_color}; }}"
                    if widget.objectName()
                    else f"{original}\n{widget.metaObject().className()} {{ {prop}: {self.new_color}; }}"
                )
            widget.setStyleSheet(modified)
            self.preview_active = True
            self._show_record(self.selected_record)
            self.status.setText(
                f"👁 Temporary Preview • {self.selected_record.color} → {self.new_color}"
            )
        except RuntimeError:
            pass

# شرح الدالة reset_preview: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def reset_preview(self) -> None:
        widget = self.current_widget
        if widget is not None and self.preview_active:
            try:
                widget.setStyleSheet(self.preview_original)
            except RuntimeError:
                pass
        self._clear_preview_state()
        if self.selected_record:
            self._show_record(self.selected_record)

# شرح الدالة _clear_preview_state: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _clear_preview_state(self) -> None:
        # تصفير حالة المعاينة فقط، بينما استرجاع تنسيق العنصر يتم في reset_preview.
        self.preview_original = ""
        self.new_color = ""
        self.preview_active = False

    # ------------------------------------------------------------
    # Selection outline
    # ------------------------------------------------------------
# شرح الدالة _draw_outline: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _draw_outline(self, widget: QWidget) -> None:
        self._remove_outline()
        try:
            frame = QFrame(widget)
            frame.setObjectName("uiInspectorOutline")
            frame.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._apply_local_theme_style(
                frame,
                "QFrame#uiInspectorOutline { background: transparent; border: 2px solid @primary@; border-radius: 2px; }",
            )
            frame.setGeometry(widget.rect().adjusted(0, 0, -1, -1))
            frame.show()
            frame.raise_()
            self._outline = frame
        except RuntimeError:
            self._outline = None

# شرح الدالة _remove_outline: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _remove_outline(self) -> None:
        if self._outline is not None:
            try:
                self._outline.deleteLater()
            except RuntimeError:
                pass
            self._outline = None

    # ------------------------------------------------------------
    # Source / index
    # ------------------------------------------------------------
# شرح الدالة copy_source: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def copy_source(self) -> None:
        QApplication.clipboard().setText(self.source_label.text())

# شرح الدالة request_index: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def request_index(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        self.status.setText("Indexing color sources…")
        self._thread = QThread(self)
        self._worker = _IndexWorker(self.project_root)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._index_ready)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

# شرح الدالة _index_ready: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @Slot(dict)
    def _index_ready(self, index: dict) -> None:
        self.index = index
        self.status.setText(f"Index complete • {len(index):,} unique colors")
        self._thread = None
        self._worker = None
        if self.current_widget is not None:
            self.inspect_widget(self.current_widget)

    # ------------------------------------------------------------
    # Window lifecycle
    # ------------------------------------------------------------
# شرح الدالة changeEvent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def changeEvent(self, event) -> None:
        if (
            event.type() == QEvent.Type.WindowStateChange
            and self.windowState() & Qt.WindowState.WindowMinimized
        ):
            self.showNormal()
            self.raise_()
        super().changeEvent(event)

# شرح الدالة showEvent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def showEvent(self, event) -> None:
        # إعادة حل قالب السمة عند العرض حتى يطابق الحالة الحالية للتطبيق.
        self._force_light_palette()
        self.setStyleSheet(self._resolved_inspector_style())
        super().showEvent(event)

# شرح الدالة closeEvent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def closeEvent(self, event) -> None:
        self._remove_outline()
        self.reset_preview()
        event.ignore()
        self.hide()

# شرح الدالة hideEvent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def hideEvent(self, event) -> None:
        # إخفاء صفحة الألوان لا يلغي المعاينة، حتى يمكن التنقل بين الأدوات ثم العودة إليها.
        self._remove_outline()
        super().hideEvent(event)


# شرح الصنف UIColorInspector: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class UIColorInspector(QObject):
    def __init__(self, main_window, project_root=None) -> None:
        super().__init__(main_window)
        self.main_window = main_window
        # الوضع الاحتياطي مستقل فقط عندما لا يكون Dev Kit موجوداً بعد.
        self.dialog = ColorInspectorDialog(
            parent=None,
            project_root=project_root or Path(__file__).resolve().parent.parent,
        )
        self._picker_open = False
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self.shortcut = QShortcut(QKeySequence("Ctrl+Shift+I"), main_window)
        self.shortcut.activated.connect(self.show)

# شرح الدالة show: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def show(self) -> None:
        self.dialog.showNormal()
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

# شرح الدالة eventFilter: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def eventFilter(self, watched, event):
        if event.type() != QEvent.Type.MouseButtonPress:
            return super().eventFilter(watched, event)
        if not self.dialog.isVisible() or not self.dialog.inspect_check.isChecked():
            return super().eventFilter(watched, event)
        if getattr(self.dialog, "_picker_open", False):
            return super().eventFilter(watched, event)
        try:
            active_modal = QApplication.activeModalWidget()
            if active_modal is not None and isinstance(active_modal, QColorDialog):
                return super().eventFilter(watched, event)
        except RuntimeError:
            pass
        if event.button() != Qt.MouseButton.LeftButton:
            return super().eventFilter(watched, event)
        try:
            pos = event.globalPosition().toPoint()
            widget = QApplication.widgetAt(pos)
        except (AttributeError, RuntimeError):
            widget = watched if isinstance(watched, QWidget) else None
        if not isinstance(widget, QWidget):
            return False
        try:
            if widget is self.dialog or self.dialog.isAncestorOf(widget):
                return super().eventFilter(watched, event)
            if isinstance(widget.window(), QColorDialog):
                return super().eventFilter(watched, event)
        except RuntimeError:
            return super().eventFilter(watched, event)
        self.dialog.inspect_widget(widget)
        return False


# شرح الدالة install_color_inspector: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def install_color_inspector(main_window, project_root=None):
    # عند وجود Dev Kit موحّد لا ننشئ نافذة ثانية، بل نعيد نفس المضيف.
    kit = getattr(main_window, "_visual_dev_kit", None)
    if kit is not None:
        kit.show_kit("colors")
        return kit

    existing = getattr(main_window, "_ui_color_inspector", None)
    if existing is not None:
        return existing
    inspector = UIColorInspector(main_window, project_root)
    main_window._ui_color_inspector = inspector
    return inspector


__all__ = ["ColorInspectorDialog", "UIColorInspector", "install_color_inspector"]

# ============================================================
# شرح الملف: theme/qss.py
# هذا الملف جزء من نظام الألوان والثيمات وأنماط الواجهة.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Qt stylesheet engine for BuildOffice Pro."""
from __future__ import annotations

import re
from typing import Any

import shiboken6
from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QHeaderView, QTableWidget, QWidget

from .mappings import SELECTOR_PROPERTY_TOKENS
from .selectors import APPLICATION_SELECTORS
from .store import ThemeStore

# صيغة الرمز: اسم الرمز بين علامتي @ لقيمة اللون كما هي، وإضافة |18 قبل العلامة الأخيرة لنفس اللون بشفافية 18% (تُحوَّل إلى rgba).
TOKEN_RE = re.compile(r"@([A-Za-z0-9_.-]+)(?:\|(\d{1,3}))?@")


def _with_alpha(color: str, percent: str | None) -> str:
    """حوّل لون HEX إلى rgba(...) بنسبة معتمة محددة؛ تُعاد القيمة كما هي عند غياب النسبة."""
    if not percent:
        return color
    value = color.strip().lstrip("#")
    if len(value) != 6:
        return color
    try:
        red, green, blue = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return color
    alpha = max(0, min(255, round(255 * min(100, int(percent)) / 100)))
    return f"rgba({red},{green},{blue},{alpha})"


class _TableFitFilter(QObject):
    """Keep data tables within their page viewport without destroying readable widths."""

    def eventFilter(self, watched, event):
        if isinstance(watched, QTableWidget) and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            if not shiboken6.isValid(watched):
                return False
            if watched.property("bo_auto_fit") is True:
                # Do not keep a stale C++ QWidget wrapper alive in the queued callback.
                # The table can be destroyed before the zero-delay timer fires,
                # especially when switching pages such as Statistics.
                QTimer.singleShot(0, lambda table=watched: _fit_table(table))
        return False


def _fit_table(table: QTableWidget) -> None:
    # PySide6 Python wrappers may outlive their underlying C++ QWidget.
    # Always validate the C++ object before touching any Qt property/method.
    if table is None or not shiboken6.isValid(table):
        return
    try:
        if table.property("bo_auto_fit") is False:
            return
    except RuntimeError:
        return
    try:
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        columns = table.columnCount()
        if columns <= 0 or table.viewport().width() <= 20:
            return
        # First let Qt measure content, then compress proportionally only when
        # the measured table would exceed the viewport.
        for col in range(columns):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        table.resizeColumnsToContents()
        widths = [max(54, header.sectionSize(i)) for i in range(columns)]
        available = max(1, table.viewport().width() - 2)
        total = sum(widths)
        if total <= available:
            # Give spare room to the last meaningful text column.
            target = min(columns - 1, max(0, columns // 2))
            widths[target] += available - total
            for i, width in enumerate(widths):
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                table.setColumnWidth(i, width)
            return
        minimum_total = 54 * columns
        if minimum_total >= available:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            return
        scale = available / total
        for i, width in enumerate(widths):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            table.setColumnWidth(i, max(54, int(width * scale)))
    except (RuntimeError, TypeError, ValueError):
        return


def _install_table_fit_filter(app: QApplication) -> None:
    current = app.property("buildoffice_table_fit_filter")
    if isinstance(current, _TableFitFilter):
        return
    filt = _TableFitFilter(app)
    app.setProperty("buildoffice_table_fit_filter", filt)
    # Newly-created page tables do not exist when the initial theme is applied.
    # A lightweight timer therefore discovers them automatically, while the
    # per-table event filter handles immediate resize/show events.
    timer = QTimer(app)
    timer.setInterval(700)
    timer.timeout.connect(lambda: _refresh_all_tables(app))
    timer.start()
    app.setProperty("buildoffice_table_fit_timer", timer)


def _refresh_all_tables(app: QApplication) -> None:
    for widget in app.allWidgets():
        if not isinstance(widget, QTableWidget) or widget.property("bo_auto_fit") is not True:
            continue
        try:
            if not shiboken6.isValid(widget):
                continue
            width = widget.viewport().width()
            if width <= 20:
                continue
            if widget.property("_bo_table_fit_width") != width:
                widget.setProperty("_bo_table_fit_width", width)
                filt = app.property("buildoffice_table_fit_filter")
                if isinstance(filt, _TableFitFilter) and widget.property("_bo_table_fit_installed") is not True:
                    widget.installEventFilter(filt)
                    widget.setProperty("_bo_table_fit_installed", True)
                _fit_table(widget)
        except RuntimeError:
            continue

# شرح الدالة current_theme: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def current_theme() -> str:
    app = QApplication.instance()
    if app is None:
        return "Dark"
    value = app.property("buildoffice_theme")
    return "Light" if str(value).strip().lower() == "light" else "Dark"

# شرح الدالة _store_from_app: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _store_from_app() -> ThemeStore | None:
    app = QApplication.instance()
    if app is None:
        return None
    value = app.property("buildoffice_theme_store")
    return value if isinstance(value, ThemeStore) else None

# شرح الدالة resolve_style: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def resolve_style(style: str, theme: str | None = None, store: ThemeStore | None = None) -> str:
    active_store = store or _store_from_app()
    if not style or active_store is None:
        return style or ""
    active_theme = theme or current_theme()
# شرح الدالة repl: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def repl(match: re.Match[str]) -> str:
        token = match.group(1)
        try:
            return _with_alpha(active_store.get_color(active_theme, token), match.group(2))
        except KeyError as exc:
            raise KeyError(f"Unknown theme token in QSS: {token}") from exc
    return TOKEN_RE.sub(repl, style)


# شرح الدالة selector_token: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def selector_token(selector: str, property_name: str) -> str | None:
    """Return the centrally-owned theme token for a selector property."""
    wanted = str(selector).strip()
    prop = str(property_name).strip().lower()
    props = SELECTOR_PROPERTY_TOKENS.get(wanted)
    if props and prop in props:
        return props[prop]
    # Registry entries may intentionally group comma-separated selectors.
    for registered, mapping in SELECTOR_PROPERTY_TOKENS.items():
        parts = [part.strip() for part in registered.split(",") if part.strip()]
        if wanted in parts and prop in mapping:
            return mapping[prop]
    return None


# شرح الدالة validate_selector_registry: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def validate_selector_registry(store: ThemeStore | None = None) -> list[str]:
    """Validate selector ownership metadata against the active token catalog."""
    active_store = store or _store_from_app()
    if active_store is None:
        return ["ThemeStore is not available"]
    errors: list[str] = []
    for selector, properties in SELECTOR_PROPERTY_TOKENS.items():
        for property_name, token in properties.items():
            try:
                active_store.validate_token(token)
            except KeyError:
                errors.append(f"{selector} :: {property_name} -> {token}")
    return errors

# شرح الدالة theme_color: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def theme_color(token: str, theme: str | None = None, store: ThemeStore | None = None) -> str:
    active_store = store or _store_from_app()
    if active_store is None:
        raise RuntimeError("ThemeStore is not available")
    return active_store.get_color(theme or current_theme(), token)

# شرح الدالة theme_qcolor: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def theme_qcolor(token_or_color: str, theme: str | None = None, store: ThemeStore | None = None) -> QColor:
    value = str(token_or_color).strip()
    match = TOKEN_RE.fullmatch(value)
    if match:
        color = QColor(theme_color(match.group(1), theme, store))
        if match.group(2):
            color.setAlpha(max(0, min(255, round(255 * min(100, int(match.group(2))) / 100))))
        return color
    return QColor(value)

# شرح الدالة resolve_token_value: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def resolve_token_value(value: Any, theme: str | None = None, store: ThemeStore | None = None) -> Any:
    if isinstance(value, str):
        match = TOKEN_RE.fullmatch(value.strip())
        if match:
            return theme_color(match.group(1), theme, store)
    return value

# شرح الدالة set_theme_style: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def set_theme_style(widget: QWidget, style: str) -> None:
    widget.setProperty("_bo_theme_style", style)
    widget.setStyleSheet(resolve_style(style))

# شرح الدالة set_theme_property: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def set_theme_property(widget: QWidget, property_name: str, token_placeholder: str) -> None:
    widget.setProperty(f"_bo_{property_name}_token", token_placeholder)
    widget.setProperty(property_name, resolve_token_value(token_placeholder))

# شرح الدالة apply_widget_theme: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _apply_base_palette(app: QApplication, theme: str, store: ThemeStore) -> None:
    """Set Qt's fallback palette so unstyled/native widgets never revert to white/black."""
    palette = QPalette()
    bg = theme_qcolor("@background@", theme, store)
    surface = theme_qcolor("@surface@", theme, store)
    text = theme_qcolor("@text_primary@", theme, store)
    muted = theme_qcolor("@text_muted@", theme, store)
    border = theme_qcolor("@border@", theme, store)
    selected = theme_qcolor("@selection_background@", theme, store)
    selected_text = theme_qcolor("@selection_text@", theme, store)
    palette.setColor(QPalette.ColorRole.Window, bg)
    palette.setColor(QPalette.ColorRole.Base, surface)
    palette.setColor(QPalette.ColorRole.AlternateBase, theme_qcolor("@surface_alt@", theme, store))
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Button, surface)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.ToolTipBase, theme_qcolor("@components.navigation.sidebar@", theme, store))
    palette.setColor(QPalette.ColorRole.ToolTipText, theme_qcolor("@components.navigation.sidebar_text_primary@", theme, store))
    palette.setColor(QPalette.ColorRole.Highlight, selected)
    palette.setColor(QPalette.ColorRole.HighlightedText, selected_text)
    palette.setColor(QPalette.ColorRole.PlaceholderText, muted)
    palette.setColor(QPalette.ColorRole.Mid, border)
    palette.setColor(QPalette.ColorRole.Midlight, border)
    palette.setColor(QPalette.ColorRole.Dark, border)
    app.setPalette(palette)


def apply_widget_theme(theme: str, store: ThemeStore | None = None) -> None:
    app = QApplication.instance()
    if app is None or not isinstance(app, QApplication):
        return
    active_store = store or _store_from_app()
    app.setProperty("buildoffice_theme", "Light" if str(theme).lower() == "light" else "Dark")
    if active_store is not None:
        app.setProperty("buildoffice_theme_store", active_store)
        _apply_base_palette(app, theme, active_store)
    _install_table_fit_filter(app)
    for widget in app.allWidgets():
        try:
            if isinstance(widget, QTableWidget):
                filt = app.property("buildoffice_table_fit_filter")
                if isinstance(filt, _TableFitFilter) and widget.property("bo_auto_fit") is True:
                    if widget.property("_bo_table_fit_installed") is not True:
                        widget.installEventFilter(filt)
                        widget.setProperty("_bo_table_fit_installed", True)
                    _fit_table(widget)
            local = widget.property("_bo_theme_style")
            if isinstance(local, str):
                widget.setStyleSheet(resolve_style(local, theme, active_store))
            else:
                # A few legacy/basic pages still assign tokenized QSS directly.
                # Resolve those styles on every theme change instead of leaving
                # literal theme placeholders in Qt's stylesheet engine.
                current_style = widget.styleSheet()
                if current_style and TOKEN_RE.search(current_style):
                    widget.setProperty("_bo_theme_style", current_style)
                    widget.setStyleSheet(resolve_style(current_style, theme, active_store))
            for prop_name in ("accent",):
                token = widget.property(f"_bo_{prop_name}_token")
                if isinstance(token, str):
                    widget.setProperty(prop_name, resolve_token_value(token, theme, active_store))
                    widget.style().unpolish(widget)
                    widget.style().polish(widget)
            widget.update()
        except RuntimeError:
            continue
    app.processEvents()

def apply_card_shadow(widget: QWidget, *, blur: int = 26, offset_y: int = 6, alpha: int = 46) -> None:
    """أضف ظلاً ناعماً لبطاقة صغيرة لمنحها عمقًا بصريًا.

    يُستخدم للبطاقات المدمجة فقط (مؤشرات KPI ونحوها)؛ لا يُطبَّق على الحاويات التي تضم جداول
    كبيرة لأن تأثيرات الرسم تُجبر Qt على رسم الحاوية في صورة وسيطة وتبطئ التمرير.
    الدالة آمنة: أي فشل في إنشاء التأثير يتجاهل الظل ولا يؤثر على سلوك الصفحة.
    """
    try:
        if widget is None or not shiboken6.isValid(widget) or widget.graphicsEffect() is not None:
            return
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(blur)
        effect.setOffset(0, offset_y)
        effect.setColor(QColor(5, 12, 28, alpha))
        widget.setGraphicsEffect(effect)
    except (RuntimeError, TypeError):
        return


# شرح الدالة build_application_style: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def build_application_style(store: ThemeStore, theme: str) -> str:
    return resolve_style(APPLICATION_SELECTORS, theme=theme, store=store)

# شرح الدالة validate_qss: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def validate_qss(qss: str) -> list[str]:
    errors=[]
    if qss.count("{") != qss.count("}"):
        errors.append("Unbalanced braces")
    unresolved=[match.group(1) for match in TOKEN_RE.finditer(qss)]
    if unresolved:
        errors.append("Unresolved tokens: " + ", ".join(sorted(set(unresolved))))
    return errors

__all__=["APPLICATION_SELECTORS", "apply_card_shadow", "apply_widget_theme", "build_application_style", "resolve_style", "resolve_token_value", "selector_token", "set_theme_property", "set_theme_style", "theme_color", "theme_qcolor", "validate_qss", "validate_selector_registry"]

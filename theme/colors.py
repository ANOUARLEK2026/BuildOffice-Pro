# ============================================================
# شرح الملف: theme/colors.py
# هذا الملف جزء من نظام الألوان والثيمات وأنماط الواجهة.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Semantic color vocabulary for BuildOffice Pro.

This module intentionally contains no Qt code and no UI logic.
Hex values are only values. The keys below are semantic meanings.
"""
from __future__ import annotations

from typing import Final

OPTION_1: Final[str] = "option_1"
OPTION_2: Final[str] = "option_2"
OPTION_3: Final[str] = "option_3"
OPTION_4: Final[str] = "option_4"
OPTIONS: Final[tuple[str, ...]] = (OPTION_1, OPTION_2, OPTION_3, OPTION_4)

# ---------------------------------------------------------------------------
# Semantic UI tokens
# ---------------------------------------------------------------------------
SEMANTIC_TOKENS: Final[tuple[str, ...]] = (
    "background",
    "surface",
    "surface_alt",
    "text_primary",
    "text_secondary",
    "text_muted",
    "border",
    "divider",
    "hover",
    "pressed",
    "disabled",
    "selection_background",
    "selection_text",
)

BRAND_TOKENS: Final[tuple[str, ...]] = (
    "primary",
    "accent",
    "gold",
)

STATUS_TOKENS: Final[tuple[str, ...]] = (
    "success",
    "warning",
    "danger",
    "info",
)

# Component tokens are kept explicit so a component can evolve without
# polluting the semantic layer with one-off colors.
COMPONENT_TOKENS: Final[dict[str, tuple[str, ...]]] = {
    "kpi": ("positive", "negative", "neutral", "warning", "highlight"),
    "charts": tuple(f"series_{i}" for i in range(1, 9)),
    "tables": ("background", "alternate_background", "text", "header_background", "header_text", "border", "grid", "hover", "selected_background", "selected_text"),
    "branding": ("brand_arabic", "brand_border", "brand_panel"),
    "buttons": ("button", "button_border", "button_danger", "button_danger_text", "button_hover", "button_secondary", "button_secondary_text", "button_success", "button_success_text", "button_text", "button_text_muted", "primary_border", "primary_hover"),
    "forms": ("combo_popup", "input_border", "input_text", "search", "search_border", "search_text"),
    "kpi_detail": ("kpi_border", "kpi_subtitle", "kpi_title"),
    "inspector": ("inspector_accent_border", "inspector_badge_bg", "inspector_badge_border", "inspector_badge_text", "inspector_border", "inspector_card_border", "inspector_empty", "inspector_field_border", "inspector_input_border", "inspector_label", "inspector_list_divider", "inspector_muted", "inspector_pressed", "inspector_scroll", "inspector_scroll_bg", "inspector_scroll_hover", "inspector_selected", "inspector_surface", "inspector_swatch_border"),
    "navigation": ("nav_hover_alt", "nav_hover_border", "nav_text", "navigation", "navigation_accent", "navigation_alt", "navigation_deep", "scrollbar", "scrollbar_handle", "sidebar", "sidebar_border", "sidebar_footer", "sidebar_footer_border", "sidebar_search", "topbar_border", "sidebar_text_primary", "sidebar_text_secondary", "sidebar_text_muted", "sidebar_selected_text", "sidebar_hover_text"),
    "progress": ("progress", "progress_border"),
    "status_ui": ("status_background", "status_border"),
    "states": ("danger_border", "danger_text"),
    "tabs": ("tab", "tab_text", "tabs"),
    "theme": ("theme_checked_background", "theme_checked_hover", "theme_text", "on_colored_surface", "on_colored_surface_muted", "on_colored_surface_border", "on_primary", "on_accent", "on_success", "on_warning", "on_danger", "on_info", "on_selection", "on_theme_checked", "on_light_surface", "on_dark_surface"),
    "tooltip": ("tooltip",),
    "labels": ("label_text",),
    "dialogs": ("dialog",),
}

# Additional component roles used by charts and the Color Inspector.
CHART_EXTRA_TOKENS: Final[tuple[str, ...]] = (
    "axis", "axis_light", "surface", "surface_alt",
)

INSPECTOR_TOKENS: Final[tuple[str, ...]] = (
    "accent_border", "badge_bg", "badge_border", "badge_text",
    "border", "card_border", "empty", "field_border", "input_border",
    "label", "list_divider", "muted", "pressed", "scroll",
    "scroll_bg", "scroll_hover", "selected", "surface", "swatch_border",
    "primary_border", "primary_hover", "button_hover", "button_text",
    "button_text_muted", "danger_text", "details_text", "role_text",
    "section_text", "tooltip",
)

# الفهرس المركزي لجميع أسماء الألوان الدلالية والمكونات المستخدمة في التطبيق.
ALL_TOKENS: Final[tuple[str, ...]] = (
    *SEMANTIC_TOKENS,
    *BRAND_TOKENS,
    *STATUS_TOKENS,
    *(f"kpi.{x}" for x in COMPONENT_TOKENS["kpi"]),
    *(f"charts.{x}" for x in COMPONENT_TOKENS["charts"]),
    *(f"charts.{x}" for x in CHART_EXTRA_TOKENS),
    *(f"tables.{x}" for x in COMPONENT_TOKENS["tables"]),
    *(f"components.{group}.{x}" for group, values in COMPONENT_TOKENS.items() if group not in {"charts", "tables", "kpi"} for x in values),
)

# ألوان أدوات التطوير القديمة محفوظة مركزيًا دون تغيير قيمها المرئية.
DEV_TOOL_COLORS: Final[dict[str, str]] = {
    "overlay_accent": "#16a34a",
    "overlay_measure": "#64748b",
    "overlay_text": "#334155",
}

PROJECT_DIALOG_PALETTES: Final[dict[str, dict[str, str]]] = {
    "Light": {
        "dialog": "#F5F7FB", "section": "#FFFFFF", "header": "#EAF2FB",
        "text": "#17324D", "muted": "#60758A", "border": "#CBD5E1",
        "input": "#FFFFFF", "input_hover": "#F8FBFF", "accent": "#0879D1",
        "accent_soft": "#E7F2FC", "selection_text": "#FFFFFF",
    },
    "Dark": {
        "dialog": "#111827", "section": "#182231", "header": "#1D2A3A",
        "text": "#E8F1FA", "muted": "#9DB0C3", "border": "#344457",
        "input": "#202D3D", "input_hover": "#26374A", "accent": "#36A3FF",
        "accent_soft": "#193B58", "selection_text": "#FFFFFF",
    },
}

DEV_KIT_COLORS: Final[dict[str, str]] = {
    "background": "#F7F9FC", "text": "#17324D", "surface": "#FFFFFF",
    "alternate": "#F3F7FA", "border": "#D5E0EA", "muted": "#587087",
    "input_border": "#C9D7E3", "hover": "#EEF3F7", "selected": "#FFF6D9",
    "accent": "#DCA936", "selected_hover": "#FFF2C4", "accent_dark": "#C89418",
    "card": "#F9FBFD", "card_border": "#DCE5ED", "pressed": "#E3EAF0",
    "disabled": "#F1F4F7", "disabled_text": "#9AAABD",
}

DEV_TOOL_GRID: Final[tuple[int, int, int, int]] = (100, 116, 139, 45)

THEME_PREVIEW_PALETTES: Final[dict[str, dict[str, str]]] = {
    "Dark": {
        "card": "#111C2E", "border": "#334155", "text": "#F8FAFC",
        "indicator": "#94A3B8", "indicator_bg": "#17243A", "accent": "#4F8CFF",
        "description": "#CBD5E1", "preview": "#0B1220", "rail": "#07101D",
    },
    "Light": {
        "card": "#FFFFFF", "border": "#CBD5E1", "text": "#172033",
        "indicator": "#596A82", "indicator_bg": "#EEF3F9", "accent": "#245FC7",
        "description": "#3D4C63", "preview": "#F4F7FB", "rail": "#0B1B32",
    },
}

INSPECTOR_PALETTE: Final[dict[str, str]] = {
    "background": "#F7F9FC", "text": "#17324D", "surface": "#FFFFFF",
    "alternate": "#F3F7FA", "accent": "#DCA936", "placeholder": "#7890A5",
}

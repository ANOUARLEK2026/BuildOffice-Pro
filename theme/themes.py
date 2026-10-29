# ============================================================
# شرح الملف: theme/themes.py
# هذا الملف جزء من نظام الألوان والثيمات وأنماط الواجهة.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Dark/Light theme palettes for BuildOffice Pro.

Each token has four independently selectable professional options per theme.
Option 1 is the default visual baseline.
"""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Final, TypedDict

Palette = dict[str, str]
TokenBucket = dict[str, Palette]
ComponentGroups = dict[str, TokenBucket]

class ThemeDefinition(TypedDict):
    semantic: TokenBucket
    brand: TokenBucket
    status: TokenBucket
    components: ComponentGroups


from .colors import (
    ALL_TOKENS,
    OPTION_1,
    OPTION_2,
    OPTION_3,
    OPTION_4,
    OPTIONS,
)

# ---------------------------------------------------------------------------
# Semantic UI palette
# ---------------------------------------------------------------------------
DARK: Final[dict[str, dict[str, str]]] = {
    "background": {OPTION_1: "#061726", OPTION_2: "#0B1220", OPTION_3: "#111827"},
    "surface": {OPTION_1: "#0E304C", OPTION_2: "#142B40", OPTION_3: "#1B3145"},
    "surface_alt": {OPTION_1: "#103754", OPTION_2: "#162F46", OPTION_3: "#1E3A50"},
    "text_primary": {OPTION_1: "#F7FAFC", OPTION_2: "#F1F5F9", OPTION_3: "#E5E7EB"},
    "text_secondary": {OPTION_1: "#C2D1DE", OPTION_2: "#B8C7D5", OPTION_3: "#AFC0CF"},
    "text_muted": {OPTION_1: "#AFC1CE", OPTION_2: "#91A8BC", OPTION_3: "#8298AA"},
    "border": {OPTION_1: "#2A526D", OPTION_2: "#334155", OPTION_3: "#3B4D5F"},
    "divider": {OPTION_1: "#214761", OPTION_2: "#263B4D", OPTION_3: "#30485B"},
    "hover": {OPTION_1: "#0D2C47", OPTION_2: "#15344D", OPTION_3: "#1D4059"},
    "pressed": {OPTION_1: "#123A58", OPTION_2: "#19425E", OPTION_3: "#214B68"},
    "disabled": {OPTION_1: "#395366", OPTION_2: "#334155", OPTION_3: "#465464"},
    "selection_background": {OPTION_1: "#3D5260", OPTION_2: "#315A74", OPTION_3: "#2F5F80"},
    "selection_text": {OPTION_1: "#FFFFFF", OPTION_2: "#FFFFFF", OPTION_3: "#FFFFFF"},
}

LIGHT: Final[dict[str, dict[str, str]]] = {
    "background": {OPTION_1: "#E8EEF4", OPTION_2: "#F4F7FA", OPTION_3: "#EEF2F6"},
    "surface": {OPTION_1: "#FFFFFF", OPTION_2: "#F8FAFC", OPTION_3: "#F1F5F9"},
    "surface_alt": {OPTION_1: "#F7F9FC", OPTION_2: "#F1F5F9", OPTION_3: "#E8EEF4"},
    "text_primary": {OPTION_1: "#122536", OPTION_2: "#172B3A", OPTION_3: "#1E293B"},
    "text_secondary": {OPTION_1: "#40586B", OPTION_2: "#475D70", OPTION_3: "#52677A"},
    "text_muted": {OPTION_1: "#4C6476", OPTION_2: "#63798D", OPTION_3: "#718096"},
    "border": {OPTION_1: "#C7D4DF", OPTION_2: "#CBD5E1", OPTION_3: "#B8C5D1"},
    "divider": {OPTION_1: "#D5DEE6", OPTION_2: "#DCE3EA", OPTION_3: "#E2E8F0"},
    "hover": {OPTION_1: "#E8EEF4", OPTION_2: "#E2E8F0", OPTION_3: "#DDE6EE"},
    "pressed": {OPTION_1: "#DCE7EF", OPTION_2: "#D5E0E8", OPTION_3: "#CBD8E3"},
    "disabled": {OPTION_1: "#C8D3DD", OPTION_2: "#D1D9E1", OPTION_3: "#DCE2E8"},
    "selection_background": {OPTION_1: "#D9E6F2", OPTION_2: "#DDE8F1", OPTION_3: "#E2EBF3"},
    "selection_text": {OPTION_1: "#172B3A", OPTION_2: "#172B3A", OPTION_3: "#1E293B"},
}

# ---------------------------------------------------------------------------
# Brand and status palette
# ---------------------------------------------------------------------------
BRAND_DARK: Final[dict[str, dict[str, str]]] = {
    "primary": {OPTION_1: "#D9A441", OPTION_2: "#C9912F", OPTION_3: "#E0B04F"},
    "accent": {OPTION_1: "#D9A441", OPTION_2: "#2F80ED", OPTION_3: "#16B8A6"},
    "gold": {OPTION_1: "#D9A441", OPTION_2: "#E8C16B", OPTION_3: "#F4D58D"},
}

BRAND_LIGHT: Final[dict[str, dict[str, str]]] = {
    "primary": {OPTION_1: "#D9A441", OPTION_2: "#B8841E", OPTION_3: "#C79527"},
    "accent": {OPTION_1: "#D9A441", OPTION_2: "#2369C9", OPTION_3: "#119884"},
    "gold": {OPTION_1: "#B8841E", OPTION_2: "#C99629", OPTION_3: "#D8A83B"},
}

STATUS_DARK: Final[dict[str, dict[str, str]]] = {
    "success": {OPTION_1: "#35C98B", OPTION_2: "#2E8B68", OPTION_3: "#32B57E"},
    "warning": {OPTION_1: "#F0A33A", OPTION_2: "#D88928", OPTION_3: "#E3A047"},
    "danger": {OPTION_1: "#E45B67", OPTION_2: "#D95D67", OPTION_3: "#C94C4C"},
    "info": {OPTION_1: "#2F80ED", OPTION_2: "#42B8D5", OPTION_3: "#39739D"},
}

STATUS_LIGHT: Final[dict[str, dict[str, str]]] = {
    "success": {OPTION_1: "#17785F", OPTION_2: "#167A5B", OPTION_3: "#21845F"},
    "warning": {OPTION_1: "#B86F14", OPTION_2: "#A96812", OPTION_3: "#A9771C"},
    "danger": {OPTION_1: "#B93240", OPTION_2: "#BE3F4D", OPTION_3: "#A9313E"},
    "info": {OPTION_1: "#2369C9", OPTION_2: "#238FA8", OPTION_3: "#2E668A"},
}

# ---------------------------------------------------------------------------
# Component palettes
# ---------------------------------------------------------------------------
KPI_DARK: Final[dict[str, dict[str, str]]] = {
    "positive": {OPTION_1: "#35C98B", OPTION_2: "#2E8B68", OPTION_3: "#32B57E"},
    "negative": {OPTION_1: "#E45B67", OPTION_2: "#D95D67", OPTION_3: "#C94C4C"},
    "neutral": {OPTION_1: "#8EA6BA", OPTION_2: "#8298AA", OPTION_3: "#718096"},
    "warning": {OPTION_1: "#F0A33A", OPTION_2: "#D88928", OPTION_3: "#E3A047"},
    "highlight": {OPTION_1: "#D9A441", OPTION_2: "#E8C16B", OPTION_3: "#F4D58D"},
}

KPI_LIGHT: Final[dict[str, dict[str, str]]] = {
    "positive": {OPTION_1: "#17785F", OPTION_2: "#167A5B", OPTION_3: "#21845F"},
    "negative": {OPTION_1: "#B93240", OPTION_2: "#BE3F4D", OPTION_3: "#A9313E"},
    "neutral": {OPTION_1: "#63798D", OPTION_2: "#718096", OPTION_3: "#52677A"},
    "warning": {OPTION_1: "#B86F14", OPTION_2: "#A96812", OPTION_3: "#A9771C"},
    "highlight": {OPTION_1: "#B8841E", OPTION_2: "#C99629", OPTION_3: "#D8A83B"},
}

# Eight-series palettes are deliberately colorblind-friendlier than the old
# mixed page constants while remaining distinct on dark and light surfaces.
CHARTS_DARK: Final[dict[str, dict[str, str]]] = {
    "series_1": {OPTION_1: "#3B82F6", OPTION_2: "#60A5FA", OPTION_3: "#2F80ED"},
    "series_2": {OPTION_1: "#2DD4BF", OPTION_2: "#5EEAD4", OPTION_3: "#16B8A6"},
    "series_3": {OPTION_1: "#A78BFA", OPTION_2: "#C4B5FD", OPTION_3: "#8B6FC7"},
    "series_4": {OPTION_1: "#F59E0B", OPTION_2: "#FBBF24", OPTION_3: "#F0A33A"},
    "series_5": {OPTION_1: "#F43F5E", OPTION_2: "#FB7185", OPTION_3: "#E45B67"},
    "series_6": {OPTION_1: "#22C55E", OPTION_2: "#4ADE80", OPTION_3: "#35C98B"},
    "series_7": {OPTION_1: "#38BDF8", OPTION_2: "#67E8F9", OPTION_3: "#42B8D5"},
    "series_8": {OPTION_1: "#E879F9", OPTION_2: "#F0ABFC", OPTION_3: "#D875A5"},
}

CHARTS_LIGHT: Final[dict[str, dict[str, str]]] = {
    "series_1": {OPTION_1: "#2563EB", OPTION_2: "#1D4ED8", OPTION_3: "#2369C9"},
    "series_2": {OPTION_1: "#0F766E", OPTION_2: "#0D9488", OPTION_3: "#119884"},
    "series_3": {OPTION_1: "#7C3AED", OPTION_2: "#6D28D9", OPTION_3: "#6F55B7"},
    "series_4": {OPTION_1: "#B45309", OPTION_2: "#A16207", OPTION_3: "#B86F14"},
    "series_5": {OPTION_1: "#BE123C", OPTION_2: "#9F1239", OPTION_3: "#B93240"},
    "series_6": {OPTION_1: "#15803D", OPTION_2: "#166534", OPTION_3: "#17785F"},
    "series_7": {OPTION_1: "#0369A1", OPTION_2: "#0E7490", OPTION_3: "#238FA8"},
    "series_8": {OPTION_1: "#A21CAF", OPTION_2: "#86198F", OPTION_3: "#A34C86"},
}

TABLES_DARK: Final[dict[str, dict[str, str]]] = {
    "background": {OPTION_1: "#0A2942", OPTION_2: "#0E304C", OPTION_3: "#142B40"},
    "alternate_background": {OPTION_1: "#103A58", OPTION_2: "#123650", OPTION_3: "#1B3145"},
    "text": {OPTION_1: "#F3F8FB", OPTION_2: "#F1F5F9", OPTION_3: "#E5E7EB"},
    "header_background": {OPTION_1: "#17415E", OPTION_2: "#153B55", OPTION_3: "#1B4965"},
    "header_text": {OPTION_1: "#FFD76A", OPTION_2: "#E8C16B", OPTION_3: "#F4D58D"},
    "border": {OPTION_1: "#214761", OPTION_2: "#2A526D", OPTION_3: "#334155"},
    "grid": {OPTION_1: "#2B526B", OPTION_2: "#315A74", OPTION_3: "#3B4D5F"},
    "hover": {OPTION_1: "#15344D", OPTION_2: "#1D4059", OPTION_3: "#214B68"},
    "selected_background": {OPTION_1: "#3D5260", OPTION_2: "#315A74", OPTION_3: "#2F5F80"},
    "selected_text": {OPTION_1: "#FFFFFF", OPTION_2: "#FFFFFF", OPTION_3: "#FFFFFF"},
}

TABLES_LIGHT: Final[dict[str, dict[str, str]]] = {
    "background": {OPTION_1: "#FFFFFF", OPTION_2: "#F8FAFC", OPTION_3: "#F1F5F9"},
    "alternate_background": {OPTION_1: "#F7F9FC", OPTION_2: "#F1F5F9", OPTION_3: "#E8EEF4"},
    "text": {OPTION_1: "#172B3A", OPTION_2: "#1E293B", OPTION_3: "#122536"},
    "header_background": {OPTION_1: "#EEF3F8", OPTION_2: "#E2E8F0", OPTION_3: "#DDE6EE"},
    "header_text": {OPTION_1: "#8B6413", OPTION_2: "#6D4F10", OPTION_3: "#7C5A10"},
    "border": {OPTION_1: "#C7D4DF", OPTION_2: "#CBD5E1", OPTION_3: "#B8C5D1"},
    "grid": {OPTION_1: "#D5DEE6", OPTION_2: "#DCE3EA", OPTION_3: "#E2E8F0"},
    "hover": {OPTION_1: "#E8EEF4", OPTION_2: "#E2E8F0", OPTION_3: "#DDE6EE"},
    "selected_background": {OPTION_1: "#D9E6F2", OPTION_2: "#DDE8F1", OPTION_3: "#E2EBF3"},
    "selected_text": {OPTION_1: "#172B3A", OPTION_2: "#172B3A", OPTION_3: "#1E293B"},
}

UI_COMPONENT_DARK: Final[dict[str, dict[str, str]]] = {
    "sidebar": {OPTION_1: "#04111E", OPTION_2: "#081521", OPTION_3: "#0A1826"},
    "navigation": {OPTION_1: "#12324D", OPTION_2: "#153A55", OPTION_3: "#1A425D"},
    "search": {OPTION_1: "#0A2A44", OPTION_2: "#0E304C", OPTION_3: "#142B40"},
    "progress": {OPTION_1: "#2F80ED", OPTION_2: "#16B8A6", OPTION_3: "#35C98B"},
    "tabs": {OPTION_1: "#17415E", OPTION_2: "#153B55", OPTION_3: "#1B4965"},
    "dialog": {OPTION_1: "#092238", OPTION_2: "#0E283D", OPTION_3: "#142B40"},
    "tooltip": {OPTION_1: "#172B3A", OPTION_2: "#1F3447", OPTION_3: "#263B4D"},
    "scrollbar": {OPTION_1: "#214761", OPTION_2: "#2A526D", OPTION_3: "#334155"},
}

UI_COMPONENT_LIGHT: Final[dict[str, dict[str, str]]] = {
    "sidebar": {OPTION_1: "#061B33", OPTION_2: "#081F3A", OPTION_3: "#0B2746"},
    "navigation": {OPTION_1: "#0E3B6E", OPTION_2: "#104879", OPTION_3: "#145384"},
    "search": {OPTION_1: "#FFFFFF", OPTION_2: "#F8FAFC", OPTION_3: "#F1F5F9"},
    "progress": {OPTION_1: "#2369C9", OPTION_2: "#119884", OPTION_3: "#17785F"},
    "tabs": {OPTION_1: "#103B66", OPTION_2: "#12446F", OPTION_3: "#155078"},
    "dialog": {OPTION_1: "#FFFFFF", OPTION_2: "#F8FAFC", OPTION_3: "#F1F5F9"},
    "tooltip": {OPTION_1: "#122536", OPTION_2: "#172B3A", OPTION_3: "#1E293B"},
    "scrollbar": {OPTION_1: "#C7D4DF", OPTION_2: "#CBD5E1", OPTION_3: "#B8C5D1"},
}


CHART_EXTRA_DARK = {
    "axis": {OPTION_1: "#9FB3C8", OPTION_2: "#AFC0D1", OPTION_3: "#8FA6BC"},
    "axis_light": {OPTION_1: "#60758A", OPTION_2: "#52677A", OPTION_3: "#718096"},
    "surface": {OPTION_1: "#0A2135", OPTION_2: "#102A40", OPTION_3: "#172F43"},
    "surface_alt": {OPTION_1: "#0D2941", OPTION_2: "#14324A", OPTION_3: "#1A3A52"},
}
CHART_EXTRA_LIGHT = {
    "axis": {OPTION_1: "#60758A", OPTION_2: "#52677A", OPTION_3: "#718096"},
    "axis_light": {OPTION_1: "#94A3B8", OPTION_2: "#8298AA", OPTION_3: "#A0AEC0"},
    "surface": {OPTION_1: "#FFFFFF", OPTION_2: "#F8FAFC", OPTION_3: "#F1F5F9"},
    "surface_alt": {OPTION_1: "#F7F9FC", OPTION_2: "#EEF3F8", OPTION_3: "#E8EEF4"},
}

# Specialized UI tokens that are genuinely component-specific.
INSPECTOR_PALETTE = {
    "inspector_accent_border": {OPTION_1: "#B8841E", OPTION_2: "#A9771C", OPTION_3: "#C79527"},
    "inspector_badge_bg": {OPTION_1: "#FFF7E3", OPTION_2: "#FFF3D4", OPTION_3: "#F8EED5"},
    "inspector_badge_border": {OPTION_1: "#D9C58C", OPTION_2: "#CDB986", OPTION_3: "#E4D7AB"},
    "inspector_badge_text": {OPTION_1: "#6D4F10", OPTION_2: "#5E450D", OPTION_3: "#7C5A10"},
    "inspector_border": {OPTION_1: "#CBD5E1", OPTION_2: "#C7D4DF", OPTION_3: "#B8C5D1"},
    "inspector_card_border": {OPTION_1: "#D5DEE6", OPTION_2: "#CBD5E1", OPTION_3: "#E2E8F0"},
    "inspector_empty": {OPTION_1: "#64748B", OPTION_2: "#718096", OPTION_3: "#52677A"},
    "inspector_field_border": {OPTION_1: "#CBD5E1", OPTION_2: "#C7D4DF", OPTION_3: "#B8C5D1"},
    "inspector_input_border": {OPTION_1: "#CBD5E1", OPTION_2: "#C7D4DF", OPTION_3: "#B8C5D1"},
    "inspector_label": {OPTION_1: "#52677A", OPTION_2: "#40586B", OPTION_3: "#63798D"},
    "inspector_list_divider": {OPTION_1: "#E2E8F0", OPTION_2: "#DCE3EA", OPTION_3: "#E8EEF4"},
    "inspector_muted": {OPTION_1: "#60778B", OPTION_2: "#5B7184", OPTION_3: "#657D92"},
    "inspector_pressed": {OPTION_1: "#F8E9BE", OPTION_2: "#F4DFAD", OPTION_3: "#FFF0CB"},
    "inspector_scroll": {OPTION_1: "#B5C3D0", OPTION_2: "#A6B6C5", OPTION_3: "#C4CED8"},
    "inspector_scroll_bg": {OPTION_1: "#EEF3F7", OPTION_2: "#E8EEF4", OPTION_3: "#F4F7FA"},
    "inspector_scroll_hover": {OPTION_1: "#9AAEBD", OPTION_2: "#8FA5B5", OPTION_3: "#A8BAC8"},
    "inspector_selected": {OPTION_1: "#FFF6DD", OPTION_2: "#FFF0C2", OPTION_3: "#F8EED5"},
    "inspector_surface": {OPTION_1: "#FFFFFF", OPTION_2: "#F8FAFC", OPTION_3: "#F1F5F9"},
    "inspector_swatch_border": {OPTION_1: "#B8C5D1", OPTION_2: "#AEBECC", OPTION_3: "#CBD5E1"},
}

# Specialized UI roles used by the application and developer inspector.
UI_COMPONENT_EXTRA_DARK = {
 'sidebar_text_primary': {'option_1': '#F8FAFC', 'option_2': '#F8FAFC', 'option_3': '#F8FAFC'},
 'sidebar_text_secondary': {'option_1': '#CBD5E1', 'option_2': '#CBD5E1', 'option_3': '#CBD5E1'},
 'sidebar_text_muted': {'option_1': '#94A3B8', 'option_2': '#94A3B8', 'option_3': '#94A3B8'},
 'sidebar_selected_text': {'option_1': '#FFFFFF', 'option_2': '#FFFFFF', 'option_3': '#FFFFFF'},
 'sidebar_hover_text': {'option_1': '#FFFFFF', 'option_2': '#FFFFFF', 'option_3': '#FFFFFF'},'brand_arabic': {'option_1': '#FFFFFF', 'option_2': '#F1F5F9', 'option_3': '#E5E7EB'},
 'brand_border': {'option_1': '#315A74', 'option_2': '#3B6680', 'option_3': '#456F88'},
 'brand_panel': {'option_1': '#0B2236', 'option_2': '#102B40', 'option_3': '#15344A'},
 'button': {'option_1': '#D9A441', 'option_2': '#C9912F', 'option_3': '#E0B04F'},
 'button_border': {'option_1': '#3A6079', 'option_2': '#456E86', 'option_3': '#52758A'},
 'button_danger': {'option_1': '#B93240', 'option_2': '#BE3F4D', 'option_3': '#A9313E'},
 'button_danger_text': {'option_1': '#FFFFFF', 'option_2': '#FFFFFF', 'option_3': '#FFFFFF'},
 'button_hover': {'option_1': '#E8C16B', 'option_2': '#D9A441', 'option_3': '#F0C968'},
 'button_secondary': {'option_1': '#12324D', 'option_2': '#173B55', 'option_3': '#1E465F'},
 'button_secondary_text': {'option_1': '#E8F0F5', 'option_2': '#F1F5F9', 'option_3': '#FFFFFF'},
 'button_success': {'option_1': '#35C98B', 'option_2': '#2EAD78', 'option_3': '#32B57E'},
 'button_success_text': {'option_1': '#071B2E', 'option_2': '#071B2E', 'option_3': '#071B2E'},
 'button_text': {'option_1': '#071B2E', 'option_2': '#0B2030', 'option_3': '#122536'},
 'button_text_muted': {'option_1': '#AFC1CE', 'option_2': '#91A8BC', 'option_3': '#8298AA'},
 'combo_popup': {'option_1': '#0A2942', 'option_2': '#102F47', 'option_3': '#17364D'},
 'danger_border': {'option_1': '#A9404A', 'option_2': '#B94A55', 'option_3': '#C94C4C'},
 'danger_text': {'option_1': '#FFD3D7', 'option_2': '#FFC4CA', 'option_3': '#FFE0E4'},
 'input_border': {'option_1': '#3A6079', 'option_2': '#456E86', 'option_3': '#52758A'},
 'input_text': {'option_1': '#F5F9FC', 'option_2': '#F1F5F9', 'option_3': '#FFFFFF'},
 'kpi_border': {'option_1': '#315A74', 'option_2': '#3A6079', 'option_3': '#456E86'},
 'kpi_subtitle': {'option_1': '#AFC1CE', 'option_2': '#91A8BC', 'option_3': '#8298AA'},
 'kpi_title': {'option_1': '#D8E6F0', 'option_2': '#C2D1DE', 'option_3': '#B8C7D5'},
 'label_text': {'option_1': '#E8F0F5', 'option_2': '#F1F5F9', 'option_3': '#FFFFFF'},
 'nav_hover_alt': {'option_1': '#153A55', 'option_2': '#1B4561', 'option_3': '#214D69'},
 'nav_hover_border': {'option_1': '#2A526D', 'option_2': '#315A74', 'option_3': '#3B6680'},
 'nav_text': {'option_1': '#D4E1EB', 'option_2': '#C2D1DE', 'option_3': '#E8F0F5'},
 'navigation_alt': {'option_1': '#0C2943', 'option_2': '#102F47', 'option_3': '#16364D'},
 'navigation_deep': {'option_1': '#071B2E', 'option_2': '#091E30', 'option_3': '#0E2638'},
 'primary_border': {'option_1': '#D9A441', 'option_2': '#C9912F', 'option_3': '#E0B04F'},
 'primary_hover': {'option_1': '#E8C16B', 'option_2': '#D9A441', 'option_3': '#F0C968'},
 'progress_border': {'option_1': '#2F80ED', 'option_2': '#16B8A6', 'option_3': '#35C98B'},
 'scrollbar_handle': {'option_1': '#214761', 'option_2': '#2A526D', 'option_3': '#334155'},
 'search_border': {'option_1': '#345E78', 'option_2': '#426B84', 'option_3': '#52758A'},
 'search_text': {'option_1': '#F5F9FC', 'option_2': '#F1F5F9', 'option_3': '#FFFFFF'},
 'sidebar_border': {'option_1': '#1B3B56', 'option_2': '#244962', 'option_3': '#2D556E'},
 'sidebar_footer': {'option_1': '#071B2E', 'option_2': '#0B2135', 'option_3': '#10293D'},
 'sidebar_footer_border': {'option_1': '#1B3B56', 'option_2': '#244962', 'option_3': '#2D556E'},
 'sidebar_search': {'option_1': '#0A243B', 'option_2': '#102D44', 'option_3': '#17364D'},
 'status_background': {'option_1': '#103754', 'option_2': '#153E57', 'option_3': '#1A465F'},
 'status_border': {'option_1': '#2A526D', 'option_2': '#315A74', 'option_3': '#3B6680'},
 'tab': {'option_1': '#17415E', 'option_2': '#153B55', 'option_3': '#1B4965'},
 'tab_text': {'option_1': '#FFD76A', 'option_2': '#E8C16B', 'option_3': '#F4D58D'},
 'theme_checked_background': {'option_1': '#D9A441', 'option_2': '#C9912F', 'option_3': '#E0B04F'},
 'theme_checked_hover': {'option_1': '#E8C16B', 'option_2': '#D9A441', 'option_3': '#F0C968'},
 'theme_text': {'option_1': '#E8EFF4', 'option_2': '#F1F5F9', 'option_3': '#FFFFFF'},
 'on_colored_surface': {'option_1': '#FFFFFF', 'option_2': '#FFFFFF', 'option_3': '#FFFFFF'},
 'on_colored_surface_muted': {'option_1': '#D7E3EC', 'option_2': '#C9D8E3', 'option_3': '#BFD0DC'},
 'on_colored_surface_border': {'option_1': '#FFFFFF', 'option_2': '#F3F7FA', 'option_3': '#E7EEF3'},
 'on_primary': {'option_1': '#07111F', 'option_2': '#07111F', 'option_3': '#07111F'},
 'on_accent': {'option_1': '#07111F', 'option_2': '#07111F', 'option_3': '#07111F'},
 'on_success': {'option_1': '#07111F', 'option_2': '#07111F', 'option_3': '#07111F'},
 'on_warning': {'option_1': '#07111F', 'option_2': '#07111F', 'option_3': '#07111F'},
 'on_danger': {'option_1': '#FFFFFF', 'option_2': '#FFFFFF', 'option_3': '#FFFFFF'},
 'on_info': {'option_1': '#07111F', 'option_2': '#07111F', 'option_3': '#07111F'},
 'on_selection': {'option_1': '#FFFFFF', 'option_2': '#FFFFFF', 'option_3': '#FFFFFF'},
 'on_theme_checked': {'option_1': '#07111F', 'option_2': '#07111F', 'option_3': '#07111F'},
 'on_light_surface': {'option_1': '#172033', 'option_2': '#172033', 'option_3': '#172033'},
 'on_dark_surface': {'option_1': '#F8FAFC', 'option_2': '#F8FAFC', 'option_3': '#F8FAFC'},
 'topbar_border': {'option_1': '#1B3B56', 'option_2': '#244962', 'option_3': '#2D556E'},
 'inspector_accent_border': {'option_1': '#B8841E', 'option_2': '#A9771C', 'option_3': '#C79527'},
 'inspector_badge_bg': {'option_1': '#FFF7E3', 'option_2': '#FFF3D4', 'option_3': '#F8EED5'},
 'inspector_badge_border': {'option_1': '#D9C58C', 'option_2': '#CDB986', 'option_3': '#E4D7AB'},
 'inspector_badge_text': {'option_1': '#6D4F10', 'option_2': '#5E450D', 'option_3': '#7C5A10'},
 'inspector_border': {'option_1': '#CBD5E1', 'option_2': '#C7D4DF', 'option_3': '#B8C5D1'},
 'inspector_card_border': {'option_1': '#D5DEE6', 'option_2': '#CBD5E1', 'option_3': '#E2E8F0'},
 'inspector_empty': {'option_1': '#64748B', 'option_2': '#718096', 'option_3': '#52677A'},
 'inspector_field_border': {'option_1': '#CBD5E1', 'option_2': '#C7D4DF', 'option_3': '#B8C5D1'},
 'inspector_input_border': {'option_1': '#CBD5E1', 'option_2': '#C7D4DF', 'option_3': '#B8C5D1'},
 'inspector_label': {'option_1': '#52677A', 'option_2': '#40586B', 'option_3': '#63798D'},
 'inspector_list_divider': {'option_1': '#E2E8F0', 'option_2': '#DCE3EA', 'option_3': '#E8EEF4'},
 'inspector_muted': {'option_1': '#60778B', 'option_2': '#5B7184', 'option_3': '#657D92'},
 'inspector_pressed': {'option_1': '#F8E9BE', 'option_2': '#F4DFAD', 'option_3': '#FFF0CB'},
 'inspector_scroll': {'option_1': '#B5C3D0', 'option_2': '#A6B6C5', 'option_3': '#C4CED8'},
 'inspector_scroll_bg': {'option_1': '#EEF3F7', 'option_2': '#E8EEF4', 'option_3': '#F4F7FA'},
 'inspector_scroll_hover': {'option_1': '#9AAEBD', 'option_2': '#8FA5B5', 'option_3': '#A8BAC8'},
 'inspector_selected': {'option_1': '#FFF6DD', 'option_2': '#FFF0C2', 'option_3': '#F8EED5'},
 'inspector_surface': {'option_1': '#FFFFFF', 'option_2': '#F8FAFC', 'option_3': '#F1F5F9'},
 'inspector_swatch_border': {'option_1': '#B8C5D1', 'option_2': '#AEBECC', 'option_3': '#CBD5E1'}}

UI_COMPONENT_EXTRA_LIGHT = {'brand_arabic': {'option_1': '#FFFFFF', 'option_2': '#F1F5F9', 'option_3': '#E5E7EB'},
 'brand_border': {'option_1': '#D5DEE7', 'option_2': '#CAD3DB', 'option_3': '#E0E9F3'},
 'brand_panel': {'option_1': '#092847', 'option_2': '#0C3155', 'option_3': '#103B61'},
 'button': {'option_1': '#FFFFFF', 'option_2': '#F8FAFC', 'option_3': '#F1F5F9'},
 'button_border': {'option_1': '#C5D2DE', 'option_2': '#BBC8D3', 'option_3': '#CFDCE9'},
 'button_danger': {'option_1': '#B93240', 'option_2': '#BE3F4D', 'option_3': '#A9313E'},
 'button_danger_text': {'option_1': '#FFFFFF', 'option_2': '#FFFFFF', 'option_3': '#FFFFFF'},
 'button_hover': {'option_1': '#EEF3F8', 'option_2': '#E5EDF4', 'option_3': '#DCE6EF'},
 'button_secondary': {'option_1': '#EEF3F8', 'option_2': '#E4ECF3', 'option_3': '#DDE6EE'},
 'button_secondary_text': {'option_1': '#30495C', 'option_2': '#263F52', 'option_3': '#1E3447'},
 'button_success': {'option_1': '#17785F', 'option_2': '#167A5B', 'option_3': '#21845F'},
 'button_success_text': {'option_1': '#FFFFFF', 'option_2': '#FFFFFF', 'option_3': '#FFFFFF'},
 'button_text': {'option_1': '#122536', 'option_2': '#122536', 'option_3': '#122536'},
 'button_text_muted': {'option_1': '#2E566F', 'option_2': '#2C5269', 'option_3': '#305A75'},
 'combo_popup': {'option_1': '#FFFFFF', 'option_2': '#F8FAFC', 'option_3': '#F1F5F9'},
 'danger_border': {'option_1': '#D99AA3', 'option_2': '#C98994', 'option_3': '#E3B0B7'},
 'danger_text': {'option_1': '#B93240', 'option_2': '#A72F3C', 'option_3': '#C53D4B'},
 'input_border': {'option_1': '#C7D4DF', 'option_2': '#B8C8D6', 'option_3': '#D5DEE6'},
 'input_text': {'option_1': '#172B3A', 'option_2': '#223B4D', 'option_3': '#30495C'},
 'kpi_border': {'option_1': '#C7D4DF', 'option_2': '#B8C8D6', 'option_3': '#D5DEE6'},
 'kpi_subtitle': {'option_1': '#63798D', 'option_2': '#526A7C', 'option_3': '#718799'},
 'kpi_title': {'option_1': '#40586B', 'option_2': '#344D60', 'option_3': '#52677A'},
 'label_text': {'option_1': '#243C4F', 'option_2': '#30495C', 'option_3': '#1E3447'},
 'nav_hover_alt': {'option_1': '#15518A', 'option_2': '#185D98', 'option_3': '#1B679F'},
 'nav_hover_border': {'option_1': '#2B6FA3', 'option_2': '#367EB0', 'option_3': '#438AB9'},
 'nav_text': {'option_1': '#DDEBFA', 'option_2': '#E7F1FA', 'option_3': '#FFFFFF'},
 'sidebar_text_primary': {'option_1': '#F8FAFC', 'option_2': '#F8FAFC', 'option_3': '#F8FAFC'},
 'sidebar_text_secondary': {'option_1': '#CBD5E1', 'option_2': '#CBD5E1', 'option_3': '#CBD5E1'},
 'sidebar_text_muted': {'option_1': '#94A3B8', 'option_2': '#94A3B8', 'option_3': '#94A3B8'},
 'sidebar_selected_text': {'option_1': '#FFFFFF', 'option_2': '#FFFFFF', 'option_3': '#FFFFFF'},
 'sidebar_hover_text': {'option_1': '#FFFFFF', 'option_2': '#FFFFFF', 'option_3': '#FFFFFF'},
 'navigation_alt': {'option_1': '#0E3B6E', 'option_2': '#104879', 'option_3': '#145384'},
 'navigation_deep': {'option_1': '#061A31', 'option_2': '#081F3A', 'option_3': '#0B2746'},
 'primary_border': {'option_1': '#C28F26', 'option_2': '#B88824', 'option_3': '#CC9628'},
 'primary_hover': {'option_1': '#B8841E', 'option_2': '#C18F26', 'option_3': '#C79527'},
 'progress_border': {'option_1': '#D2DEE8', 'option_2': '#C8D3DC', 'option_3': '#DCE9F4'},
 'scrollbar_handle': {'option_1': '#B5C3D0', 'option_2': '#A6B6C5', 'option_3': '#C4CED8'},
 'search_border': {'option_1': '#C7D4DF', 'option_2': '#B8C8D6', 'option_3': '#D5DEE6'},
 'search_text': {'option_1': '#30495C', 'option_2': '#263F52', 'option_3': '#1E3447'},
 'sidebar_border': {'option_1': '#D7E0E9', 'option_2': '#CCD5DD', 'option_3': '#E2EBF5'},
 'sidebar_footer': {'option_1': '#071E38', 'option_2': '#0A2644', 'option_3': '#0D2F50'},
 'sidebar_footer_border': {'option_1': '#1B4568', 'option_2': '#245576', 'option_3': '#2C6386'},
 'sidebar_search': {'option_1': '#0A2947', 'option_2': '#0D3356', 'option_3': '#103B61'},
 'status_background': {'option_1': '#F3E9CF', 'option_2': '#E7DDC5', 'option_3': '#FFF5D9'},
 'status_border': {'option_1': '#D9C58C', 'option_2': '#CDB986', 'option_3': '#E4D7AB'},
 'tab': {'option_1': '#EEF3F8', 'option_2': '#E2E8F0', 'option_3': '#DDE6EE'},
 'tab_text': {'option_1': '#30495C', 'option_2': '#263F52', 'option_3': '#1E3447'},
 'theme_checked_background': {'option_1': '#FFF3D4', 'option_2': '#FFF0C2', 'option_3': '#FFF7E3'},
 'theme_checked_hover': {'option_1': '#F8E6B6', 'option_2': '#F4DFAD', 'option_3': '#FFF0CB'},
 'on_colored_surface': {'option_1': '#FFFFFF', 'option_2': '#FFFFFF', 'option_3': '#FFFFFF'},
 'on_colored_surface_muted': {'option_1': '#D7E3EC', 'option_2': '#C9D8E3', 'option_3': '#BFD0DC'},
 'on_colored_surface_border': {'option_1': '#FFFFFF', 'option_2': '#F3F7FA', 'option_3': '#E7EEF3'},
 'on_primary': {'option_1': '#07111F', 'option_2': '#07111F', 'option_3': '#07111F'},
 'on_accent': {'option_1': '#07111F', 'option_2': '#07111F', 'option_3': '#07111F'},
 'on_success': {'option_1': '#07111F', 'option_2': '#07111F', 'option_3': '#07111F'},
 'on_warning': {'option_1': '#07111F', 'option_2': '#07111F', 'option_3': '#07111F'},
 'on_danger': {'option_1': '#FFFFFF', 'option_2': '#FFFFFF', 'option_3': '#FFFFFF'},
 'on_info': {'option_1': '#07111F', 'option_2': '#07111F', 'option_3': '#07111F'},
 'on_selection': {'option_1': '#FFFFFF', 'option_2': '#FFFFFF', 'option_3': '#FFFFFF'},
 'on_theme_checked': {'option_1': '#07111F', 'option_2': '#07111F', 'option_3': '#07111F'},
 'on_light_surface': {'option_1': '#172033', 'option_2': '#172033', 'option_3': '#172033'},
 'on_dark_surface': {'option_1': '#F8FAFC', 'option_2': '#F8FAFC', 'option_3': '#F8FAFC'},
 'theme_text': {'option_1': '#FFFFFF', 'option_2': '#FFFFFF', 'option_3': '#FFFFFF'},
 'topbar_border': {'option_1': '#C7D4DF', 'option_2': '#B8C8D6', 'option_3': '#D5DEE6'},
 'inspector_accent_border': {'option_1': '#B8841E', 'option_2': '#A9771C', 'option_3': '#C79527'},
 'inspector_badge_bg': {'option_1': '#FFF7E3', 'option_2': '#FFF3D4', 'option_3': '#F8EED5'},
 'inspector_badge_border': {'option_1': '#D9C58C', 'option_2': '#CDB986', 'option_3': '#E4D7AB'},
 'inspector_badge_text': {'option_1': '#6D4F10', 'option_2': '#5E450D', 'option_3': '#7C5A10'},
 'inspector_border': {'option_1': '#CBD5E1', 'option_2': '#C7D4DF', 'option_3': '#B8C5D1'},
 'inspector_card_border': {'option_1': '#D5DEE6', 'option_2': '#CBD5E1', 'option_3': '#E2E8F0'},
 'inspector_empty': {'option_1': '#64748B', 'option_2': '#718096', 'option_3': '#52677A'},
 'inspector_field_border': {'option_1': '#CBD5E1', 'option_2': '#C7D4DF', 'option_3': '#B8C5D1'},
 'inspector_input_border': {'option_1': '#CBD5E1', 'option_2': '#C7D4DF', 'option_3': '#B8C5D1'},
 'inspector_label': {'option_1': '#52677A', 'option_2': '#40586B', 'option_3': '#63798D'},
 'inspector_list_divider': {'option_1': '#E2E8F0', 'option_2': '#DCE3EA', 'option_3': '#E8EEF4'},
 'inspector_muted': {'option_1': '#60778B', 'option_2': '#5B7184', 'option_3': '#657D92'},
 'inspector_pressed': {'option_1': '#F8E9BE', 'option_2': '#F4DFAD', 'option_3': '#FFF0CB'},
 'inspector_scroll': {'option_1': '#B5C3D0', 'option_2': '#A6B6C5', 'option_3': '#C4CED8'},
 'inspector_scroll_bg': {'option_1': '#EEF3F7', 'option_2': '#E8EEF4', 'option_3': '#F4F7FA'},
 'inspector_scroll_hover': {'option_1': '#9AAEBD', 'option_2': '#8FA5B5', 'option_3': '#A8BAC8'},
 'inspector_selected': {'option_1': '#FFF6DD', 'option_2': '#FFF0C2', 'option_3': '#F8EED5'},
 'inspector_surface': {'option_1': '#FFFFFF', 'option_2': '#F8FAFC', 'option_3': '#F1F5F9'},
 'inspector_swatch_border': {'option_1': '#B8C5D1', 'option_2': '#AEBECC', 'option_3': '#CBD5E1'}}



# شرح الدالة _componentize_palette: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _componentize_palette(*palettes: dict[str, dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    # تجميع ألوان المكونات في مجالات واضحة.
    groups: dict[str, dict[str, dict[str, str]]] = {}
    for palette in palettes:
        for key, options in palette.items():
            if key.startswith("brand_"): group = "branding"
            elif key.startswith("button") or key in {"primary_border", "primary_hover"}: group = "buttons"
            elif key.startswith(("input_", "search", "combo_popup")): group = "forms"
            elif key.startswith("kpi_"): group = "kpi_detail"
            elif key.startswith("inspector_"): group = "inspector"
            elif key.startswith(("nav_", "navigation", "sidebar", "scrollbar", "topbar_border")): group = "navigation"
            elif key.startswith("progress"): group = "progress"
            elif key.startswith("status_"): group = "status_ui"
            elif key.startswith("tab"): group = "tabs"
            elif key.startswith(("theme_", "on_")) or key in {"on_colored_surface", "on_colored_surface_muted", "on_colored_surface_border"}: group = "theme"
            elif key == "tooltip": group = "tooltip"
            elif key.startswith("danger_"): group = "states"
            elif key == "label_text": group = "labels"
            elif key == "dialog": group = "dialogs"
            else: group = "components"
            groups.setdefault(group, {})[key] = deepcopy(options)
    return groups


# ---------------------------------------------------------------------------
# Professional palette profiles
# ---------------------------------------------------------------------------
# The three options are intentionally different visual identities, not merely
# lighter/darker variants. Every profile keeps semantic text/background pairs
# in high-contrast ranges so readability survives theme and palette changes.

_PRO_PALETTES = {
    "Dark": {
        OPTION_1: {
            "bg": "#0B1220", "surface": "#111C2E", "alt": "#17243A",
            "primary": "#4F8CFF", "accent": "#2DD4BF", "gold": "#D6A84F",
            "text": "#F8FAFC", "secondary": "#CBD5E1", "muted": "#94A3B8",
            "border": "#2F4466", "divider": "#223149", "hover": "#172C4C",
            "pressed": "#1D3553", "selection": "#2457A6",
            "success": "#34D399", "warning": "#FBBF24", "danger": "#FB7185",
            "info": "#60A5FA",
            "sidebar": "#07101D", "nav": "#10233B", "nav_alt": "#15304D",
            "deep": "#050B14", "search": "#0D1A2B", "dialog": "#0F1B2D",
            "table": "#0E1A2A", "table_alt": "#132238", "header": "#19314D",
        },
        OPTION_2: {
            "bg": "#101614", "surface": "#17201C", "alt": "#1E2B25",
            "primary": "#35B779", "accent": "#5EE0A1", "gold": "#D8B46A",
            "text": "#F4FAF7", "secondary": "#C7D9CF", "muted": "#91AAA0",
            "border": "#35483F", "divider": "#293A33", "hover": "#1B3027",
            "pressed": "#244234", "selection": "#276B4D",
            "success": "#43D19A", "warning": "#F2C66D", "danger": "#F27786",
            "info": "#67B7E8",
            "sidebar": "#0A110F", "nav": "#142A22", "nav_alt": "#1B382C",
            "deep": "#060B09", "search": "#101C17", "dialog": "#15201B",
            "table": "#101C18", "table_alt": "#17271F", "header": "#204033",
        },
        OPTION_3: {
            "bg": "#12121C", "surface": "#1B1B29", "alt": "#242437",
            "primary": "#8B7CF6", "accent": "#38BDF8", "gold": "#D8B36A",
            "text": "#F8FAFC", "secondary": "#D0D1DF", "muted": "#9A9CAF",
            "border": "#3B3B52", "divider": "#2C2C40", "hover": "#24243A",
            "pressed": "#303052", "selection": "#5146A6",
            "success": "#4ADE80", "warning": "#FBBF24", "danger": "#FB7185",
            "info": "#60A5FA",
            "sidebar": "#0A0A12", "nav": "#18182A", "nav_alt": "#20203A",
            "deep": "#06060B", "search": "#11111D", "dialog": "#171724",
            "table": "#11111C", "table_alt": "#191927", "header": "#282842",
        },
        OPTION_4: {
            "bg": "#101A24", "surface": "#172633", "alt": "#203544",
            "primary": "#3E78B2", "accent": "#C58B4A", "gold": "#D8A45B",
            "text": "#F7FAFC", "secondary": "#C8D5E0", "muted": "#91A5B6",
            "border": "#385064", "divider": "#293E50", "hover": "#1D3242",
            "pressed": "#28465C", "selection": "#2F5D86",
            "success": "#42C58A", "warning": "#F0B35A", "danger": "#E06B78",
            "info": "#56A8D8",
            "sidebar": "#08131E", "nav": "#102A3E", "nav_alt": "#173A52",
            "deep": "#050C13", "search": "#0F1D29", "dialog": "#14222E",
            "table": "#0F1D29", "table_alt": "#152737", "header": "#1E3B52",
        },
    },
    "Light": {
        OPTION_1: {
            "bg": "#F4F7FB", "surface": "#FFFFFF", "alt": "#EEF3F9",
            "primary": "#245FC7", "accent": "#087F73", "gold": "#9A6A12",
            "text": "#172033", "secondary": "#3D4C63", "muted": "#596A82",
            "border": "#CBD5E1", "divider": "#DCE4ED", "hover": "#E8F0FA",
            "pressed": "#DDE9F7", "selection": "#CFE0FA",
            "success": "#13795B", "warning": "#8A5A00", "danger": "#B4233C",
            "info": "#185FA7",
            "sidebar": "#0B1B32", "nav": "#12345A", "nav_alt": "#19456F",
            "deep": "#071323", "search": "#F8FAFD", "dialog": "#FFFFFF",
            "table": "#FFFFFF", "table_alt": "#F5F8FC", "header": "#E7EEF7",
        },
        OPTION_2: {
            "bg": "#F3F7F5", "surface": "#FFFFFF", "alt": "#EAF3EE",
            "primary": "#087A52", "accent": "#087F73", "gold": "#8A6315",
            "text": "#14231C", "secondary": "#3D554A", "muted": "#587066",
            "border": "#C8D8D0", "divider": "#DCE8E2", "hover": "#E5F1EB",
            "pressed": "#D7E9DF", "selection": "#C9E5D6",
            "success": "#087A52", "warning": "#8A5A00", "danger": "#B4233C",
            "info": "#176B9F",
            "sidebar": "#0A2118", "nav": "#123D2E", "nav_alt": "#18533D",
            "deep": "#06140E", "search": "#F8FCFA", "dialog": "#FFFFFF",
            "table": "#FFFFFF", "table_alt": "#F3F8F5", "header": "#E2EEE8",
        },
        OPTION_3: {
            "bg": "#F6F5FB", "surface": "#FFFFFF", "alt": "#F0EFF8",
            "primary": "#6246C7", "accent": "#087AA6", "gold": "#936A18",
            "text": "#1B1A2A", "secondary": "#4B4A60", "muted": "#65647A",
            "border": "#D4D2E2", "divider": "#E3E1EC", "hover": "#ECEAF8",
            "pressed": "#E1DEF4", "selection": "#DAD5F5",
            "success": "#16704D", "warning": "#8A5A00", "danger": "#B4233C",
            "info": "#176B9F",
            "sidebar": "#121126", "nav": "#28224C", "nav_alt": "#342C61",
            "deep": "#0B0A18", "search": "#FBFAFF", "dialog": "#FFFFFF",
            "table": "#FFFFFF", "table_alt": "#F7F6FB", "header": "#E9E7F4",
        },
        OPTION_4: {
            "bg": "#F4F7FA", "surface": "#FFFFFF", "alt": "#EAF0F5",
            "primary": "#255E91", "accent": "#A86D2D", "gold": "#9A681E",
            "text": "#182733", "secondary": "#405666", "muted": "#607687",
            "border": "#C8D5DF", "divider": "#DCE5EB", "hover": "#E6EEF4",
            "pressed": "#D8E5EE", "selection": "#CBDDEC",
            "success": "#167052", "warning": "#8A5A00", "danger": "#B52E43",
            "info": "#1A6997",
            "sidebar": "#0B2033", "nav": "#123954", "nav_alt": "#194C6C",
            "deep": "#07121D", "search": "#F8FBFD", "dialog": "#FFFFFF",
            "table": "#FFFFFF", "table_alt": "#F3F7FA", "header": "#E4ECF2",
        },
    },
}

# ألوان إضافية لكل هوية: "hi" لون التفاعل (hover) للأزرار الأساسية، و"nav_accent" نهاية تدرّج
# رؤوس الصفحات والبانر. كل قيمة تحقق تباين 4.5:1 على الأقل مع النص الموضوع فوقها.
_PRO_EXTRAS = {
    "Dark": {
        OPTION_1: {"hi": "#7FAAFF", "nav_accent": "#2B66D9"},
        OPTION_2: {"hi": "#5FD39A", "nav_accent": "#1B7F54"},
        OPTION_3: {"hi": "#A99CFA", "nav_accent": "#5B4BC4"},
        OPTION_4: {"hi": "#3E78B2", "nav_accent": "#2F6EA8"},
    },
    "Light": {
        OPTION_1: {"hi": "#1B4EA8", "nav_accent": "#2F6FD6"},
        OPTION_2: {"hi": "#066842", "nav_accent": "#13875F"},
        OPTION_3: {"hi": "#5236B0", "nav_accent": "#6D52D6"},
        OPTION_4: {"hi": "#1C4D79", "nav_accent": "#2F77A8"},
    },
}

def _set_options(mapping, values):
    for opt in OPTIONS:
        if opt in mapping:
            mapping[opt] = values[opt]

def _apply_professional_profiles():
    """Apply one coherent visual system to every semantic/component token."""
    for theme_name in ("Dark", "Light"):
        profiles = _PRO_PALETTES[theme_name]
        dark = theme_name == "Dark"

        # Semantic layer
        for opt, p in profiles.items():
            semantic = DARK if dark else LIGHT
            semantic["background"][opt] = p["bg"]
            semantic["surface"][opt] = p["surface"]
            semantic["surface_alt"][opt] = p["alt"]
            semantic["text_primary"][opt] = p["text"]
            semantic["text_secondary"][opt] = p["secondary"]
            semantic["text_muted"][opt] = p["muted"]
            semantic["border"][opt] = p["border"]
            semantic["divider"][opt] = p["divider"]
            semantic["hover"][opt] = p["hover"]
            semantic["pressed"][opt] = p["pressed"]
            semantic["disabled"][opt] = "#334155" if dark else "#D8E0E8"
            semantic["selection_background"][opt] = p["selection"] 
            semantic["selection_text"][opt] = "#FFFFFF" if dark else p["text"]

            brand = BRAND_DARK if dark else BRAND_LIGHT
            brand["primary"][opt] = p["primary"]
            brand["accent"][opt] = p["accent"]
            brand["gold"][opt] = p["gold"]

            status = STATUS_DARK if dark else STATUS_LIGHT
            status["success"][opt] = p["success"]
            status["warning"][opt] = p["warning"]
            status["danger"][opt] = p["danger"]
            status["info"][opt] = p["info"]

            kpi = KPI_DARK if dark else KPI_LIGHT
            kpi["positive"][opt] = p["success"]
            kpi["negative"][opt] = p["danger"]
            kpi["neutral"][opt] = p["muted"]
            kpi["warning"][opt] = p["warning"]
            kpi["highlight"][opt] = p["gold"]

            charts = CHARTS_DARK if dark else CHARTS_LIGHT
            chart_sets_dark = ["#60A5FA","#2DD4BF","#A78BFA","#FBBF24","#FB7185","#34D399","#38BDF8","#E879F9"]
            chart_sets_light = ["#245FC7","#087F73","#6246C7","#8A5A00","#B4233C","#13795B","#176B9F","#A21CAF"]
            for i, key in enumerate(f"series_{n}" for n in range(1, 9)):
                charts[key][opt] = (chart_sets_dark if dark else chart_sets_light)[i]

            tables = TABLES_DARK if dark else TABLES_LIGHT
            tables["background"][opt] = p["table"]
            tables["alternate_background"][opt] = p["table_alt"]
            tables["text"][opt] = p["text"] 
            tables["header_background"][opt] = p["header"]
            tables["header_text"][opt] = p["gold"] 
            tables["border"][opt] = p["border"]
            tables["grid"][opt] = p["divider"]
            tables["hover"][opt] = p["hover"]
            tables["selected_background"][opt] = p["selection"]
            tables["selected_text"][opt] = "#FFFFFF" if dark else p["text"]

            ui = UI_COMPONENT_DARK if dark else UI_COMPONENT_LIGHT
            ui["sidebar"][opt] = p["sidebar"]
            ui["navigation"][opt] = p["nav"]
            ui["search"][opt] = p["search"]
            ui["progress"][opt] = p["primary"]
            ui["tabs"][opt] = p["nav_alt"]
            ui["dialog"][opt] = p["dialog"]
            ui["tooltip"][opt] = p["deep"] if dark else p["text"]
            ui["scrollbar"][opt] = "#334155" if dark else p["border"]

            extra = UI_COMPONENT_EXTRA_DARK if dark else UI_COMPONENT_EXTRA_LIGHT
            # Brand
            extra["brand_arabic"][opt] = "#FFFFFF" 
            extra["brand_border"][opt] = p["border"]
            extra["brand_panel"][opt] = p["nav"]
            # Buttons
            # الزر العادي (بلا objectName) ناعم ومحايد؛ الزر الأساسي وحده يحمل لون العلامة.
            extra["button"][opt] = p["alt"] if dark else p["surface"]
            extra["button_border"][opt] = p["border"]
            extra["button_hover"][opt] = p["hover"]
            extra["button_text"][opt] = ("#FFFFFF" if opt == OPTION_4 else "#07111F") if dark else "#FFFFFF"
            extra["button_text_muted"][opt] = p["muted"]
            extra["button_secondary"][opt] = p["nav_alt"] if dark else p["header"]
            extra["button_secondary_text"][opt] = "#FFFFFF" if dark else p["text"]
            extra["button_success"][opt] = p["success"]
            extra["button_success_text"][opt] = "#07111F" if dark else "#FFFFFF"
            extra["button_danger"][opt] = p["danger"]
            extra["button_danger_text"][opt] = "#07111F" if dark else "#FFFFFF"
            extra["primary_border"][opt] = p["primary"]
            extra["primary_hover"][opt] = _PRO_EXTRAS[theme_name][opt]["hi"]
            # Forms / KPI detail
            extra["combo_popup"][opt] = p["surface"] if dark else "#FFFFFF"
            extra["input_border"][opt] = p["border"]
            extra["input_text"][opt] = p["text"]
            extra["search_border"][opt] = p["border"]
            extra["search_text"][opt] = p["text"]
            extra["kpi_border"][opt] = p["border"]
            extra["kpi_subtitle"][opt] = p["muted"]
            extra["kpi_title"][opt] = p["secondary"]
            extra["label_text"][opt] = p["text"]
            # Navigation
            extra["nav_hover_alt"][opt] = p["nav_alt"]
            extra["nav_hover_border"][opt] = p["primary"]
            # Navigation foregrounds are tied to the actual sidebar surface,
            # not to the global Dark/Light text system. The sidebar remains a
            # dark surface in both application themes, so its text stays light.
            extra["nav_text"][opt] = "#E7EEF7" if dark else "#EAF2FA"
            extra["sidebar_text_primary"][opt] = "#F8FAFC"
            extra["sidebar_text_secondary"][opt] = "#CBD5E1"
            extra["sidebar_text_muted"][opt] = "#94A3B8"
            extra["sidebar_selected_text"][opt] = "#07111F" if dark else "#FFFFFF"
            extra["sidebar_hover_text"][opt] = "#FFFFFF"
            extra["navigation_alt"][opt] = p["nav_alt"]
            extra["navigation_deep"][opt] = p["deep"]
            extra.setdefault("navigation_accent", {})[opt] = _PRO_EXTRAS[theme_name][opt]["nav_accent"]
            extra["scrollbar_handle"][opt] = "#3F5872" if dark else p["border"]
            extra["sidebar_border"][opt] = p["border"]
            extra["sidebar_footer"][opt] = p["deep"]
            extra["sidebar_footer_border"][opt] = p["border"]
            extra["sidebar_search"][opt] = p["search"] if dark else p["nav"]
            extra["topbar_border"][opt] = p["border"]
            # Status / tabs / theme
            extra["status_background"][opt] = p["selection"] if dark else p["alt"]
            extra["status_border"][opt] = p["border"]
            extra["progress_border"][opt] = p["border"]
            extra["danger_border"][opt] = p["danger"]
            extra["danger_text"][opt] = "#FFD3D7" if dark else p["danger"]
            extra["tab"][opt] = p["nav_alt"] if dark else p["alt"]
            extra["tab_text"][opt] = "#FFFFFF" if dark else p["text"]
            extra["theme_checked_background"][opt] = p["primary"] if dark else p["selection"]
            extra["theme_checked_hover"][opt] = _PRO_EXTRAS[theme_name][opt]["hi"] if dark else p["hover"]
            extra["theme_text"][opt] = "#FFFFFF" if dark else p["text"]
            extra["on_colored_surface"][opt] = "#FFFFFF"
            extra["on_colored_surface_muted"][opt] = "#D7E3EC" if dark else "#E7EEF5"
            extra["on_colored_surface_border"][opt] = "#FFFFFF"
            # Foreground roles for known colored surfaces. These are explicit
            # so no component has to guess text color from the global theme.
            extra["on_primary"][opt] = ("#FFFFFF" if opt == OPTION_4 else "#07111F") if dark else "#FFFFFF"
            extra["on_accent"][opt] = ("#07111F" if dark else ("#000000" if opt == OPTION_4 else "#FFFFFF"))
            extra["on_success"][opt] = "#07111F" if dark else "#FFFFFF"
            extra["on_warning"][opt] = "#07111F" if dark else "#FFFFFF"
            extra["on_danger"][opt] = "#07111F" if dark else "#FFFFFF"
            extra["on_info"][opt] = "#07111F" if dark else "#FFFFFF"
            extra["on_selection"][opt] = "#FFFFFF" if dark else p["text"]
            extra["on_theme_checked"][opt] = ("#FFFFFF" if opt == OPTION_4 else "#07111F") if dark else p["text"]
            extra["on_light_surface"][opt] = p["text"]
            extra["on_dark_surface"][opt] = "#F8FAFC"

            # Specialized inspector stays legible while inheriting the profile.
            INSPECTOR_PALETTE["inspector_accent_border"][opt] = p["gold"]
            INSPECTOR_PALETTE["inspector_badge_bg"][opt] = p["selection"] if dark else p["alt"]
            INSPECTOR_PALETTE["inspector_badge_border"][opt] = p["border"]
            INSPECTOR_PALETTE["inspector_badge_text"][opt] = "#FFFFFF" if dark else p["gold"]
            INSPECTOR_PALETTE["inspector_border"][opt] = p["border"]
            INSPECTOR_PALETTE["inspector_card_border"][opt] = p["border"]
            INSPECTOR_PALETTE["inspector_empty"][opt] = p["muted"]
            INSPECTOR_PALETTE["inspector_field_border"][opt] = p["border"]
            INSPECTOR_PALETTE["inspector_input_border"][opt] = p["border"]
            INSPECTOR_PALETTE["inspector_label"][opt] = p["secondary"]
            INSPECTOR_PALETTE["inspector_list_divider"][opt] = p["divider"]
            INSPECTOR_PALETTE["inspector_muted"][opt] = p["muted"]
            INSPECTOR_PALETTE["inspector_pressed"][opt] = p["pressed"]
            INSPECTOR_PALETTE["inspector_scroll"][opt] = "#52677A" if dark else p["border"]
            INSPECTOR_PALETTE["inspector_scroll_bg"][opt] = p["alt"]
            INSPECTOR_PALETTE["inspector_scroll_hover"][opt] = p["primary"]
            INSPECTOR_PALETTE["inspector_selected"][opt] = p["selection"]
            INSPECTOR_PALETTE["inspector_surface"][opt] = p["surface"]
            INSPECTOR_PALETTE["inspector_swatch_border"][opt] = p["border"]

            # Chart surfaces/axes
            chart_extra = CHART_EXTRA_DARK if dark else CHART_EXTRA_LIGHT
            chart_extra["axis"][opt] = p["muted"]
            chart_extra["axis_light"][opt] = p["secondary"]
            chart_extra["surface"][opt] = p["surface"]
            chart_extra["surface_alt"][opt] = p["alt"]

_apply_professional_profiles()

# ---------------------------------------------------------------------------
# Theme registry
# ---------------------------------------------------------------------------
THEMES: Final[dict[str, ThemeDefinition]] = {
    "Dark": {
        "semantic": deepcopy(DARK),
        "brand": deepcopy(BRAND_DARK),
        "status": deepcopy(STATUS_DARK),
        "components": {
            "kpi": deepcopy(KPI_DARK),
            "charts": {**deepcopy(CHARTS_DARK), **deepcopy(CHART_EXTRA_DARK)},
            "tables": deepcopy(TABLES_DARK),
            **_componentize_palette(UI_COMPONENT_DARK, UI_COMPONENT_EXTRA_DARK, INSPECTOR_PALETTE),
        },
    },
    "Light": {
        "semantic": deepcopy(LIGHT),
        "brand": deepcopy(BRAND_LIGHT),
        "status": deepcopy(STATUS_LIGHT),
        "components": {
            "kpi": deepcopy(KPI_LIGHT),
            "charts": {**deepcopy(CHARTS_LIGHT), **deepcopy(CHART_EXTRA_LIGHT)},
            "tables": deepcopy(TABLES_LIGHT),
            **_componentize_palette(UI_COMPONENT_LIGHT, UI_COMPONENT_EXTRA_LIGHT, INSPECTOR_PALETTE),
        },
    },
}

DEFAULT_SELECTION: Final[dict[str, dict[str, str]]] = {
    "Dark": {token: OPTION_1 for token in ALL_TOKENS},
    "Light": {token: OPTION_1 for token in ALL_TOKENS},
}

# شرح الدالة get_token_palette: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def get_token_palette(theme_name: str, token: str) -> dict[str, str]:
    normalized = "Light" if str(theme_name).strip().lower() == "light" else "Dark"
    if token.startswith("kpi."):
        return dict(THEMES[normalized]["components"]["kpi"][token.split(".",1)[1]])
    if token.startswith("charts."):
        key = token.split(".", 1)[1]
        if key in THEMES[normalized]["components"]["charts"]:
            return dict(THEMES[normalized]["components"]["charts"][key])
        raise KeyError(key)
    if token.startswith("tables."):
        return dict(THEMES[normalized]["components"]["tables"][token.split(".",1)[1]])
    if token.startswith("components."):
        parts = token.split(".", 2)
        if len(parts) != 3:
            raise KeyError(token)
        _, component_group, key = parts
        palette = THEMES[normalized]["components"].get(component_group, {})
        if key in palette:
            return dict(palette[key])
        raise KeyError(token)
    for bucket in ("semantic", "brand", "status"):
        if token in THEMES[normalized][bucket]:
            return dict(THEMES[normalized][bucket][token])
    raise KeyError(f"Unknown theme token: {token}")

# شرح الدالة resolve_color: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def resolve_color(theme_name: str, token: str, selection: dict[str, str] | None = None) -> str:
    normalized = "Light" if str(theme_name).strip().lower() == "light" else "Dark"
    active=selection or DEFAULT_SELECTION[normalized]
    option=active.get(token,OPTION_1)
    if option not in OPTIONS: option=OPTION_1
    return get_token_palette(normalized, token)[option]

# شرح الدالة validate_themes: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def validate_themes() -> list[str]:
    errors=[]
    for theme_name in ("Dark","Light"):
        for token in ALL_TOKENS:
            try: palette=get_token_palette(theme_name,token)
            except KeyError: errors.append(f"Missing token: {theme_name}.{token}"); continue
            if set(palette)!=set(OPTIONS): errors.append(f"Options mismatch: {theme_name}.{token}")
            for option,value in palette.items():
                if not isinstance(value,str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}",value): errors.append(f"Invalid hex: {theme_name}.{token}.{option}={value!r}")
    return errors

__all__=["BRAND_DARK", "BRAND_LIGHT", "CHARTS_DARK", "CHARTS_LIGHT", "DARK", "DEFAULT_SELECTION", "KPI_DARK", "KPI_LIGHT", "LIGHT", "STATUS_DARK", "STATUS_LIGHT", "TABLES_DARK", "TABLES_LIGHT", "THEMES", "UI_COMPONENT_DARK", "UI_COMPONENT_LIGHT", "get_token_palette", "resolve_color", "validate_themes"]

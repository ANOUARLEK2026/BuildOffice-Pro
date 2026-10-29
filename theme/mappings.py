# ============================================================
# شرح الملف: theme/mappings.py
# هذا الملف جزء من نظام الألوان والثيمات وأنماط الواجهة.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Central selector -> property -> semantic token ownership registry.

This file contains no palette values. Actual color values live in theme/themes.py.
"""
from __future__ import annotations

from typing import Final

SELECTOR_PROPERTY_TOKENS: Final[dict[str, dict[str, str]]] = {
    "QMainWindow, QWidget#appRoot, QWidget#businessPage": {
        "background": "background",
        "color": "text_primary",
    },
    "QWidget#mainContent": {"background": "background"},
    "QFrame#sidebar": {
        "background": "components.navigation.sidebar",
        "border-right": "components.navigation.sidebar_border",
    },
    "QFrame#brandPanel": {
        "background": "components.branding.brand_panel",
        "border": "components.branding.brand_border",
    },
    "QLabel#brandName": {"color": "components.navigation.sidebar_text_primary"},
    "QLabel#brandApp": {"color": "primary"},
    "QLabel#brandArabic": {"color": "components.branding.brand_arabic"},
    "QLabel#brandType": {"color": "primary"},
    "QLabel#sidebarClock": {"color": "components.navigation.sidebar_text_muted"},
    "QLineEdit#sidebarSearch": {
        "background": "components.navigation.sidebar_search",
        "color": "components.forms.search_text",
        "border": "components.forms.search_border",
    },
    "QPushButton#navButton": {"color": "components.navigation.sidebar_text_secondary"},
    "QPushButton#navButton:hover": {
        "background": "components.navigation.nav_hover_alt",
        "color": "components.navigation.sidebar_hover_text",
        "border-color": "components.navigation.nav_hover_border",
    },
    "QPushButton#navButton:checked": {
        "background": "info",
        "color": "components.navigation.sidebar_selected_text",
        "border-color": "components.buttons.primary_hover",
    },
    "QFrame#sidebarFooter": {
        "background": "components.navigation.sidebar_footer",
        "border": "components.navigation.sidebar_footer_border",
    },
    "QLabel#onlineDot": {"color": "success"},
    "QLabel#footer": {"color": "components.navigation.sidebar_text_muted"},
    "QFrame#topBar": {
        "background": "surface",
        "border-bottom": "components.navigation.topbar_border",
    },
    "QFrame#profileCard": {"background": "surface_alt", "border": "border"},
    "QLabel#profileName": {"color": "text_primary"},
    "QLabel#profileRole": {"color": "text_muted"},
    "QLabel#profileAvatar": {"color": "components.theme.on_info", "background": "info"},
    "QLabel#topTitle": {"color": "text_primary"},
    "QLabel#topMeta": {"color": "text_muted"},
    "QFrame#pageHeader, QFrame#pageToolbar, QFrame#panel, QFrame#sectionCard": {
        "background": "surface",
        "border": "divider",
    },
    "QLabel#pageMark": {
        "background": "primary",
        "color": "components.buttons.button_text",
    },
    "QLabel#pageTitle": {"color": "components.theme.on_colored_surface"},
    "QLabel#pageSubtitle": {"color": "text_secondary"},
    "QLabel#pageStatus": {
        "color": "text_primary",
        "background": "components.status_ui.status_background",
        "border": "components.status_ui.status_border",
    },
    "QLabel#sectionTitle": {"color": "text_primary"},
    "QLabel#sectionSubtitle": {"color": "text_secondary"},
    "QPushButton#documentCategoryCard": {
        "background": "surface_alt",
        "color": "text_primary",
        "border": "border",
    },
    "QLabel#documentCategoryTitle": {"color": "text_primary"},
    "QLabel#documentCategoryCount": {"color": "primary"},
    "QFrame#kpiCard": {
        "background": "surface_alt",
        "border": "components.kpi_detail.kpi_border",
        "border-left": "primary",
    },
    "QLabel#kpiIcon": {
        "background": "primary",
        "color": "components.buttons.button_text",
    },
    "QLabel#kpiTitle": {"color": "components.kpi_detail.kpi_title"},
    "QLabel#kpiValue": {"color": "text_primary"},
    "QLabel#kpiSubtitle": {"color": "components.kpi_detail.kpi_subtitle"},
    "QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QPlainTextEdit": {
        "background": "components.forms.search",
        "color": "components.forms.input_text",
        "border": "components.forms.input_border",
        "selection-background-color": "primary",
        "selection-color": "components.buttons.button_text",
    },
    "QComboBox QAbstractItemView": {
        "background": "components.forms.combo_popup",
        "color": "components.forms.search_text",
        "selection-background-color": "primary",
        "selection-color": "components.buttons.button_text",
    },
    "QPushButton": {
        "background": "components.buttons.button",
        "color": "text_primary",
        "border": "components.buttons.button_border",
    },
    "QPushButton:hover": {
        "background": "components.buttons.button_hover",
        "border-color": "components.buttons.primary_hover",
    },
    "QPushButton#primaryButton, QPushButton#goldButton": {
        "background": "primary",
        "color": "components.buttons.button_text",
        "border-color": "components.buttons.primary_hover",
    },
    "QPushButton#primaryButton:hover, QPushButton#goldButton:hover": {
        "background": "components.buttons.primary_hover",
        "color": "components.buttons.button_text",
    },
    "QPushButton#successButton": {
        "background": "components.buttons.button_success",
        "color": "components.buttons.button_success_text",
        "border-color": "success",
    },
    "QPushButton#successButton:hover": {
        "background": "components.buttons.button_success",
        "color": "components.buttons.button_success_text",
        "border-color": "success",
    },
    "QPushButton#secondaryButton": {
        "background": "components.buttons.button_secondary",
        "color": "components.buttons.button_secondary_text",
    },
    "QPushButton#dangerButton": {
        "background": "components.buttons.button_danger",
        "color": "components.buttons.button_danger_text",
        "border-color": "components.states.danger_border",
    },
    "QPushButton#dangerButton:hover": {
        "background": "components.buttons.button_danger",
        "color": "components.buttons.button_danger_text",
        "border-color": "components.states.danger_border",
    },
    "QTableWidget": {
        "background": "tables.background",
        "alternate-background-color": "tables.alternate_background",
        "color": "tables.text",
        "border": "divider",
        "gridline-color": "tables.grid",
        "selection-background-color": "tables.selected_background",
        "selection-color": "tables.selected_text",
    },
    "QHeaderView::section": {
        "background": "tables.header_background",
        "color": "tables.header_text",
    },
    "QGroupBox": {
        "background": "surface",
        "border": "divider",
        "color": "text_primary",
    },
    "QGroupBox::title": {
        "color": "text_primary",
        "background": "surface",
    },
    "QTabWidget::pane": {
        "border": "divider",
        "background": "surface",
    },
    "QTabBar::tab": {
        "background": "components.tabs.tab",
        "color": "components.tabs.tab_text",
    },
    "QTabBar::tab:selected": {
        "background": "primary",
        "color": "components.buttons.button_text",
    },
    "QProgressBar": {
        "background": "background",
        "border": "components.progress.progress_border",
        "color": "text_primary",
    },
    "QProgressBar::chunk": {"background": "primary"},
    "QScrollArea": {"background": "background"},
    "QWidget#navHost": {"background": "components.branding.brand_panel"},
    "QScrollBar::handle:vertical": {"background": "components.navigation.scrollbar_handle"},
    "QPushButton#themeToggle": {
        "background": "surface_alt",
        "color": "text_primary",
        "border": "border",
    },
    "QToolTip": {
        "background": "components.navigation.sidebar",
        "color": "components.navigation.sidebar_text_primary",
        "border": "primary",
    },

    "QLineEdit#sidebarSearch:focus": {"border": "primary"},
    "QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QPlainTextEdit:focus": {"border": "primary"},
    'QFrame#kpiCard[accentRole="info"]': {"border-left-color": "info"},
    'QFrame#kpiCard[accentRole="charts.series_2"]': {"border-left-color": "charts.series_2"},
    'QFrame#kpiCard[accentRole="success"]': {"border-left-color": "success"},
    'QFrame#kpiCard[accentRole="danger"]': {"border-left-color": "danger"},
    'QFrame#kpiCard[accentRole="warning"]': {"border-left-color": "warning"},
    'QFrame#kpiCard[accentRole="charts.series_3"]': {"border-left-color": "charts.series_3"},
    'QFrame#kpiCard[accentRole="charts.series_7"]': {"border-left-color": "charts.series_7"},
    "QScrollBar::handle:vertical:hover": {"background": "primary"},
    "QPushButton#themeToggle:hover": {"background": "components.navigation.nav_hover_alt", "border-color": "primary", "color": "components.navigation.sidebar_text_primary"},
    "QPushButton#themeToggle:checked": {"background": "components.theme.theme_checked_background", "color": "components.theme.on_theme_checked", "border": "primary"},
    "QPushButton#themeToggle:checked:hover": {"background": "components.theme.theme_checked_hover", "color": "components.theme.on_theme_checked"},
    "QDialog": {"background": "components.dialogs.dialog", "color": "text_primary"},
    "QLabel": {"color": "components.labels.label_text"},
}

__all__ = ["SELECTOR_PROPERTY_TOKENS"]

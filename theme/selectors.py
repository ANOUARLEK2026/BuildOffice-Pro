# ============================================================
# شرح الملف: theme/selectors.py
# هذا الملف جزء من نظام الألوان والثيمات وأنماط الواجهة.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Central UI selectors for BuildOffice Pro.

All UI colors are represented by semantic/theme tokens.
"""
from __future__ import annotations

from pathlib import Path

from .metrics import (
    FONT_SIZE_BODY,
    FONT_SIZE_BRAND,
    FONT_SIZE_HEADING,
    FONT_SIZE_KPI,
    FONT_SIZE_ROOT,
    FONT_SIZE_SECTION,
    FONT_SIZE_SMALL,
    FONT_SIZE_SUBTITLE,
    FONT_SIZE_TINY,
    FONT_SIZE_TITLE,
    FONT_WEIGHT_BLACK,
    FONT_WEIGHT_BOLD,
    FONT_WEIGHT_EXTRABOLD,
    FONT_WEIGHT_HEAVY,
    UI_FONT_FAMILY,
)

# أقسام الأنماط: الغلاف والشريط العلوي، الشاشة الرئيسية، رأس الصفحة والبطاقات، عناصر الإدخال والأزرار،
# الجداول وأشرطة التمرير، صفحات المشاريع، ثم أدوار النصوص المشتركة. (لا تُوضع تعليقات داخل النص؛
# اختبار السجل يدمجها مع اسم المحدد التالي.)
APPLICATION_SELECTORS = r"""* { font-family: "__UI_FONT_FAMILY__"; }
QMainWindow, QWidget#appRoot, QWidget#businessPage {
    background: @background@;
    color: @text_primary@;
    font-size: __FONT_SIZE_ROOT__px;
}
QWidget#mainContent { background: @background@; }

QFrame#sidebar {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 @components.navigation.sidebar@, stop:1 @components.navigation.navigation_deep@);
    border-right: 1px solid @components.navigation.sidebar_border@;
}
QFrame#sidebar QLabel { color: @components.navigation.sidebar_text_primary@; }
QFrame#sidebar QLabel#brandName { color: @components.navigation.sidebar_text_primary@; }
QFrame#sidebar QLabel#brandApp { color: @primary@; }
QFrame#sidebar QLabel#brandArabic { color: @components.branding.brand_arabic@; }
QFrame#sidebar QLabel#brandType { color: @primary@; }
QFrame#sidebar QLabel#sidebarClock { color: @components.navigation.sidebar_text_muted@; }
QFrame#sidebar QLabel#footer { color: @components.navigation.sidebar_text_muted@; }
QFrame#sidebar QPushButton#navButton { color: @components.navigation.sidebar_text_secondary@; }
QFrame#sidebar QPushButton#navButton:hover { background: @components.navigation.nav_hover_alt@; color: @components.navigation.sidebar_hover_text@; }
QFrame#sidebar QPushButton#navButton:checked { background: @info@; color: @components.navigation.sidebar_selected_text@; }

QFrame#brandPanel {
    background: @components.branding.brand_panel@;
    border: 1px solid @components.branding.brand_border@;
    border-radius: 16px;
}
QLabel#brandName { color: @components.navigation.sidebar_text_primary@; font-size: __FONT_SIZE_BRAND__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QLabel#brandApp { color: @primary@; font-size: __FONT_SIZE_SMALL__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QLabel#brandArabic { color: @components.branding.brand_arabic@; font-size: __FONT_SIZE_SMALL__px; font-weight: __FONT_WEIGHT_BOLD__; }
QLabel#brandType { color: @primary@; font-size: __FONT_SIZE_TINY__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; letter-spacing: 1px; }
QLabel#sidebarClock { color: @components.navigation.sidebar_text_muted@; font-size: __FONT_SIZE_SMALL__px; font-weight: __FONT_WEIGHT_BOLD__; }
QLineEdit#sidebarSearch {
    background: @components.navigation.sidebar_search@; color: @components.forms.search_text@; border: 1px solid @components.forms.search_border@;
    border-radius: 12px; padding: 8px 12px; min-height: 20px;
}
QLineEdit#sidebarSearch:focus { border: 1px solid @primary@; }
QPushButton#navButton {
    text-align: left; background: transparent; color: @components.navigation.sidebar_text_secondary@; border: 1px solid transparent;
    border-radius: 11px; padding: 8px 12px; min-height: 21px; font-weight: __FONT_WEIGHT_BOLD__;
}
QPushButton#navButton:hover { background: @components.navigation.nav_hover_alt@; color: @components.navigation.sidebar_hover_text@; border-color: @components.navigation.nav_hover_border@; }
QPushButton#navButton:checked {
    background: @info@; color: @components.navigation.sidebar_selected_text@; border-color: @components.buttons.primary_hover@; font-weight: __FONT_WEIGHT_BLACK__;
}
QFrame#sidebarFooter { background: @components.navigation.sidebar_footer@; border: 1px solid @components.navigation.sidebar_footer_border@; border-radius: 13px; }
QLabel#onlineDot { color: @success@; font-size: __FONT_SIZE_BODY__px; }
QLabel#footer { color: @components.navigation.sidebar_text_muted@; font-size: __FONT_SIZE_SMALL__px; }

QFrame#topBar { background: @surface@; border-bottom: 1px solid @components.navigation.topbar_border@; }
QLabel#topTitle { color: @text_primary@; font-size: __FONT_SIZE_HEADING__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QLabel#topMeta { color: @text_muted@; font-size: __FONT_SIZE_SMALL__px; }
QPushButton#backButton { background: transparent; color: @text_primary@; border: 1px solid transparent; border-radius: 11px; font-size: 22px; font-weight: 700; padding: 2px 8px; }
QPushButton#backButton:hover { background: @hover@; color: @text_primary@; border-color: @border@; }
QPushButton#backButton:pressed { background: @pressed@; }
QPushButton#topIconButton {
    background: @surface_alt@; color: @text_primary@; border: 1px solid @border@;
    border-radius: 11px; padding: 0px; font-size: 15px; font-weight: __FONT_WEIGHT_BOLD__;
}
QPushButton#topIconButton:hover { background: @hover@; border-color: @primary@; }
QPushButton#topIconButton:pressed { background: @pressed@; }
QPushButton#aiTopButton {
    background: @primary@; color: @components.buttons.button_text@; border: 1px solid @components.buttons.primary_hover@;
    border-radius: 11px; padding: 0px; font-size: 16px;
}
QPushButton#aiTopButton:hover { background: @components.buttons.primary_hover@; }
QPushButton#aiTopButton:pressed { background: @primary@; border-color: @primary@; }
QLineEdit#globalTopSearch {
    background: @surface_alt@; color: @text_primary@; border: 1px solid @border@;
    border-radius: 12px; padding: 8px 14px; min-height: 22px;
}
QLineEdit#globalTopSearch:hover { border-color: @text_muted@; }
QLineEdit#globalTopSearch:focus { border: 1px solid @primary@; background: @surface@; }
QLabel#profileName { color: @text_primary@; font-weight: __FONT_WEIGHT_EXTRABOLD__; font-size: __FONT_SIZE_BODY__px; }
QLabel#profileRole { color: @text_muted@; font-size: __FONT_SIZE_TINY__px; }
QFrame#profileCard { background: @surface_alt@; border: 1px solid @border@; border-radius: 14px; }
QLabel#profileAvatar { background: @info@; color: @components.theme.on_info@; border-radius: 16px; font-size: __FONT_SIZE_SMALL__px; font-weight: __FONT_WEIGHT_BLACK__; }
QComboBox#languageSelector { min-width: 100px; border-radius: 11px; padding: 7px 12px; background: @surface_alt@; color: @text_primary@; border: 1px solid @border@; }
QComboBox#languageSelector:hover { border-color: @primary@; }
QPushButton#themeToggle { background:@surface_alt@; color:@text_primary@; border:1px solid @border@; border-radius:11px; padding:7px 12px; font-weight: __FONT_WEIGHT_HEAVY__; }
QPushButton#themeToggle:hover { background:@components.navigation.nav_hover_alt@; border-color:@primary@; color:@components.navigation.sidebar_text_primary@; }
QPushButton#themeToggle:checked { background:@components.theme.theme_checked_background@; color:@components.theme.on_theme_checked@; border:1px solid @primary@; }
QPushButton#themeToggle:checked:hover { background:@components.theme.theme_checked_hover@; color:@components.theme.on_theme_checked@; }

QWidget#launcherPage { background: @background@; color: @text_primary@; }
QWidget#launcherContent { background: transparent; }
QScrollArea#launcherScroll { background: transparent; border: 0; }
QWidget#launcherScrollContent { background: transparent; }
QFrame#launcherBanner { background: transparent; border: 0; }
QLabel#launcherTitle { color: @components.theme.on_colored_surface@; font-size: 28px; font-weight: __FONT_WEIGHT_BLACK__; background: transparent; }
QLabel#launcherSubtitle { color: @components.navigation.nav_text@; font-size: __FONT_SIZE_SECTION__px; background: transparent; }
QLabel#launcherVersion {
    color: @components.theme.on_colored_surface@; font-size: __FONT_SIZE_SMALL__px; font-weight: __FONT_WEIGHT_BOLD__;
    background: rgba(255,255,255,30); border: 1px solid rgba(255,255,255,70); border-radius: 10px; padding: 3px 10px;
}
QLabel#launcherHint { color: @text_secondary@; font-size: __FONT_SIZE_SECTION__px; font-weight: __FONT_WEIGHT_BOLD__; }
QLabel#launcherGroupTitle { color: @text_primary@; font-size: __FONT_SIZE_BODY__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; letter-spacing: 0.5px; }
QFrame#launcherGroupLine { background: @divider@; border: 0; max-height: 1px; min-height: 1px; }
QLabel#launcherGroupDot { background: @primary@; border-radius: 4px; min-width: 8px; max-width: 8px; min-height: 8px; max-height: 8px; }
QLabel#launcherGroupDot[navGroup="WORKSPACE"] { background: @charts.series_1@; }
QLabel#launcherGroupDot[navGroup="OPERATIONS"] { background: @charts.series_4@; }
QLabel#launcherGroupDot[navGroup="FINANCE"] { background: @charts.series_6@; }
QLabel#launcherGroupDot[navGroup="PEOPLE"] { background: @charts.series_3@; }
QLabel#launcherGroupDot[navGroup="ASSETS"] { background: @charts.series_7@; }
QLabel#launcherGroupDot[navGroup="DOCUMENTS"] { background: @charts.series_5@; }
QLabel#launcherGroupDot[navGroup="ANALYTICS"] { background: @charts.series_2@; }
QLabel#launcherGroupDot[navGroup="SYSTEM"] { background: @charts.series_8@; }
QPushButton#launcherTile {
    background: @surface@; color: @text_primary@; border: 1px solid @divider@; border-radius: 16px; padding: 0px;
}
QPushButton#launcherTile:hover { background: @hover@; border: 1px solid @primary@; }
QPushButton#launcherTile:pressed { background: @pressed@; }
QPushButton#launcherTile[navGroup="WORKSPACE"]:hover { border-color: @charts.series_1@; }
QPushButton#launcherTile[navGroup="OPERATIONS"]:hover { border-color: @charts.series_4@; }
QPushButton#launcherTile[navGroup="FINANCE"]:hover { border-color: @charts.series_6@; }
QPushButton#launcherTile[navGroup="PEOPLE"]:hover { border-color: @charts.series_3@; }
QPushButton#launcherTile[navGroup="ASSETS"]:hover { border-color: @charts.series_7@; }
QPushButton#launcherTile[navGroup="DOCUMENTS"]:hover { border-color: @charts.series_5@; }
QPushButton#launcherTile[navGroup="ANALYTICS"]:hover { border-color: @charts.series_2@; }
QPushButton#launcherTile[navGroup="SYSTEM"]:hover { border-color: @charts.series_8@; }
QLabel#launcherIcon { background: @primary|16@; color: @primary@; border-radius: 15px; font-size: 25px; font-weight: 700; }
QLabel#launcherIcon[navGroup="WORKSPACE"] { background: @charts.series_1|16@; color: @charts.series_1@; }
QLabel#launcherIcon[navGroup="OPERATIONS"] { background: @charts.series_4|16@; color: @charts.series_4@; }
QLabel#launcherIcon[navGroup="FINANCE"] { background: @charts.series_6|16@; color: @charts.series_6@; }
QLabel#launcherIcon[navGroup="PEOPLE"] { background: @charts.series_3|16@; color: @charts.series_3@; }
QLabel#launcherIcon[navGroup="ASSETS"] { background: @charts.series_7|16@; color: @charts.series_7@; }
QLabel#launcherIcon[navGroup="DOCUMENTS"] { background: @charts.series_5|16@; color: @charts.series_5@; }
QLabel#launcherIcon[navGroup="ANALYTICS"] { background: @charts.series_2|16@; color: @charts.series_2@; }
QLabel#launcherIcon[navGroup="SYSTEM"] { background: @charts.series_8|16@; color: @charts.series_8@; }
QLabel#launcherLabel { color: @text_primary@; font-size: __FONT_SIZE_BODY__px; font-weight: __FONT_WEIGHT_BOLD__; background: transparent; }
QFrame#launcherFooter { background: @background@; border-top: 1px solid @divider@; }
QLabel#launcherFooterBrand { color: @text_primary@; font-weight: __FONT_WEIGHT_EXTRABOLD__; font-size: __FONT_SIZE_BODY__px; }
QLabel#launcherFooterTagline, QLabel#launcherClock { color: @text_muted@; font-size: __FONT_SIZE_SMALL__px; }

QFrame#pageToolbar { padding: 0px; }
QFrame#pageHeader { min-height: 76px; }
QFrame#pageHeader QLabel#pageTitle { letter-spacing: 0px; }
QFrame#metricPanel { background: @surface@; border: 1px solid @divider@; border-radius: 15px; border-top: 3px solid @primary@; }
QFrame#metricPanel[accentRole="info"] { border-top-color: @info@; }
QFrame#metricPanel[accentRole="danger"] { border-top-color: @danger@; }
QFrame#metricPanel[accentRole="charts.series_2"] { border-top-color: @charts.series_2@; }
QFrame#metricPanel[accentRole="success"] { border-top-color: @success@; }
QFrame#sidePanel { background: @surface@; border: 1px solid @divider@; border-radius: 15px; }
QFrame#heroPanel { border: 1px solid @divider@; border-radius: 18px; background: @surface@; }
QLabel#heroTitle { color: @text_primary@; font-size: __FONT_SIZE_TITLE__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QLabel#heroSubtitle { color: @text_secondary@; font-size: __FONT_SIZE_SUBTITLE__px; }
QLabel#metricLabel { color: @text_muted@; font-size: __FONT_SIZE_SMALL__px; font-weight: __FONT_WEIGHT_BOLD__; }
QLabel#metricValue { color: @text_primary@; font-size: __FONT_SIZE_KPI__px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#sideTitle { color: @text_primary@; font-size: __FONT_SIZE_BRAND__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QLabel#sideMuted { color: @text_muted@; font-size: __FONT_SIZE_SMALL__px; }
QFrame#pageHeader, QFrame#pageToolbar, QFrame#panel, QFrame#sectionCard {
    background: @surface@; border: 1px solid @divider@; border-radius: 16px;
}
QLabel#pageMark {
    background: @primary@; color: @components.buttons.button_text@; border-radius: 14px; font-size: __FONT_SIZE_SUBTITLE__px; font-weight: __FONT_WEIGHT_BLACK__;
}
QLabel#pageTitle { color: @components.theme.on_colored_surface@; font-size: __FONT_SIZE_TITLE__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QLabel#pageSubtitle { color: @text_secondary@; font-size: __FONT_SIZE_SUBTITLE__px; }
QLabel#pageStatus {
    color: @text_primary@; background: @components.status_ui.status_background@; border: 1px solid @components.status_ui.status_border@;
    border-radius: 11px; padding: 6px 12px; font-size: __FONT_SIZE_SMALL__px; font-weight: __FONT_WEIGHT_EXTRABOLD__;
}
QLabel#sectionTitle { color: @text_primary@; font-size: __FONT_SIZE_BRAND__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QLabel#sectionSubtitle { color: @text_secondary@; font-size: __FONT_SIZE_BODY__px; }
QPushButton#documentCategoryCard {
    text-align: left; background: @surface_alt@; color: @text_primary@; border: 1px solid @border@;
    border-radius: 14px; padding: 3px; font-weight: __FONT_WEIGHT_EXTRABOLD__;
}
QPushButton#documentCategoryCard:hover { background: @hover@; border-color: @primary@; }
QPushButton#documentCategoryCard[selected="true"] { background: @primary@; color: @components.buttons.button_text@; border-color: @primary@; }
QLabel#documentCategoryTitle { color: @text_primary@; font-size: __FONT_SIZE_BODY__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QLabel#documentCategoryCount { color: @primary@; font-size: __FONT_SIZE_KPI__px; font-weight: __FONT_WEIGHT_BLACK__; }
QPushButton#documentCategoryCard[selected="true"] QLabel#documentCategoryTitle,
QPushButton#documentCategoryCard[selected="true"] QLabel#documentCategoryCount { color: @components.buttons.button_text@; }

QFrame#kpiCard {
    background: @surface_alt@; border: 1px solid @components.kpi_detail.kpi_border@; border-radius: 15px;
    border-left: 4px solid @primary@;
}
QFrame#kpiCard[accentRole="gold"] { border-left-color: @gold@; }
QFrame#kpiCard[accentRole="info"] { border-left-color: @info@; }
QFrame#kpiCard[accentRole="charts.series_2"] { border-left-color: @charts.series_2@; }
QFrame#kpiCard[accentRole="success"] { border-left-color: @success@; }
QFrame#kpiCard[accentRole="danger"] { border-left-color: @danger@; }
QFrame#kpiCard[accentRole="warning"] { border-left-color: @warning@; }
QFrame#kpiCard[accentRole="charts.series_3"] { border-left-color: @charts.series_3@; }
QFrame#kpiCard[accentRole="charts.series_7"] { border-left-color: @charts.series_7@; }
QFrame#kpiCard[accentRole="components.navigation.navigation_deep"] { border-left-color: @components.navigation.navigation_deep@; }
QLabel#kpiIcon { background: @primary@; color: @components.buttons.button_text@; border-radius: 11px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#kpiTitle { color: @components.kpi_detail.kpi_title@; font-size: __FONT_SIZE_SMALL__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; letter-spacing: 0.4px; }
QLabel#kpiValue { color: @text_primary@; font-size: __FONT_SIZE_KPI__px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#kpiSubtitle { color: @components.kpi_detail.kpi_subtitle@; font-size: __FONT_SIZE_SMALL__px; }

QLineEdit, QComboBox, QDateEdit, QTimeEdit, QDateTimeEdit, QDoubleSpinBox, QSpinBox, QPlainTextEdit, QTextEdit {
    background: @components.forms.search@; color: @components.forms.input_text@; border: 1px solid @components.forms.input_border@;
    border-radius: 11px; padding: 8px 12px; min-height: 20px;
    selection-background-color: @primary@; selection-color: @components.buttons.button_text@;
    placeholder-text-color: @text_muted@;
}
QLineEdit:hover, QComboBox:hover, QDateEdit:hover, QTimeEdit:hover, QDateTimeEdit:hover, QDoubleSpinBox:hover, QSpinBox:hover, QPlainTextEdit:hover, QTextEdit:hover { border-color: @text_muted@; }
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QPlainTextEdit:focus, QTextEdit:focus { border: 1px solid @primary@; }
QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled, QTimeEdit:disabled, QDateTimeEdit:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled, QPlainTextEdit:disabled, QTextEdit:disabled { background: @disabled@; color: @text_secondary@; border-color: @border@; }
QLineEdit:read-only { background: @surface_alt@; }
QComboBox QAbstractItemView {
    background: @components.forms.combo_popup@; color: @components.forms.search_text@; border: 1px solid @border@; padding: 4px; outline: 0;
    selection-background-color: @primary@; selection-color: @components.buttons.button_text@;
}
QComboBox QAbstractItemView::item { min-height: 28px; padding: 3px 10px; border-radius: 7px; }
QComboBox QAbstractItemView::item:hover { background: @hover@; color: @text_primary@; }

QPushButton {
    background: @components.buttons.button@; color: @text_primary@; border: 1px solid @components.buttons.button_border@; border-radius: 11px;
    padding: 8px 16px; font-weight: __FONT_WEIGHT_BOLD__; min-height: 20px;
}
QPushButton:hover { background: @components.buttons.button_hover@; border-color: @components.buttons.primary_hover@; }
QPushButton:pressed { background: @pressed@; }
QPushButton:focus { border-color: @primary@; }
QPushButton:disabled { background: @disabled@; color: @text_secondary@; border-color: @border@; }
QPushButton#primaryButton, QPushButton#goldButton {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 @components.buttons.primary_hover@, stop:1 @primary@);
    color: @components.buttons.button_text@; border-color: @components.buttons.primary_hover@; font-weight: __FONT_WEIGHT_BLACK__;
}
QPushButton#primaryButton:hover, QPushButton#goldButton:hover { background: @components.buttons.primary_hover@; color: @components.buttons.button_text@; }
QPushButton#primaryButton:pressed, QPushButton#goldButton:pressed { background: @primary@; }
QPushButton#primaryButton:disabled, QPushButton#goldButton:disabled { background: @disabled@; color: @text_secondary@; border-color: @border@; }
QPushButton#successButton { background: @components.buttons.button_success@; color: @components.buttons.button_success_text@; border-color: @success@; }
QPushButton#successButton:hover { background: @components.buttons.button_success@; color: @components.buttons.button_success_text@; border-color: @success@; }
QPushButton#successButton:pressed { background: @success@; }
QPushButton#secondaryButton { background: @components.buttons.button_secondary@; color: @components.buttons.button_secondary_text@; border-color: @components.buttons.button_border@; }
QPushButton#secondaryButton:hover { background: @hover@; color: @text_primary@; border-color: @primary@; }
QPushButton#secondaryButton:pressed { background: @pressed@; }
QPushButton#dangerButton { background: @components.buttons.button_danger@; color: @components.buttons.button_danger_text@; border-color: @components.states.danger_border@; }
QPushButton#dangerButton:hover { background: @components.buttons.button_danger@; color: @components.buttons.button_danger_text@; border-color: @components.states.danger_border@; }
QPushButton#dangerButton:pressed { background: @danger@; }
QPushButton#secondaryButton:disabled, QPushButton#successButton:disabled, QPushButton#dangerButton:disabled { background: @disabled@; color: @text_secondary@; border-color: @border@; }

QFrame#pageHeader[unified="true"] QPushButton#secondaryButton {
    background: rgba(255,255,255,26); color: @components.theme.on_colored_surface@; border: 1px solid rgba(255,255,255,70);
}
QFrame#pageHeader[unified="true"] QPushButton#secondaryButton:hover { background: rgba(255,255,255,52); color: @components.theme.on_colored_surface@; border-color: rgba(255,255,255,130); }
QFrame#pageHeader[unified="true"] QPushButton#secondaryButton:pressed { background: rgba(255,255,255,74); }

QTableWidget, QTableView, QListWidget, QListView, QTreeWidget, QTreeView {
    background: @tables.background@; alternate-background-color: @tables.alternate_background@; color: @tables.text@;
    border: 1px solid @divider@; border-radius: 13px; gridline-color: @tables.grid@;
    selection-background-color: @tables.selected_background@; selection-color: @tables.selected_text@; outline: 0;
}
QTableWidget::item, QTableView::item { padding: 7px 10px; border: 0; }
QTableWidget::item:hover, QTableView::item:hover { background: @tables.hover@; }
QTableWidget::item:selected, QTableView::item:selected { background: @tables.selected_background@; color: @tables.selected_text@; }
QHeaderView { background: transparent; border: 0; }
QHeaderView::section {
    background: @tables.header_background@; color: @tables.header_text@; border: 0; border-bottom: 1px solid @tables.border@;
    padding: 11px 12px; font-weight: __FONT_WEIGHT_BLACK__; font-size: __FONT_SIZE_BODY__px;
}
QHeaderView::section:first { border-top-left-radius: 12px; }
QHeaderView::section:last { border-top-right-radius: 12px; }
QHeaderView::section:only-one { border-top-left-radius: 12px; border-top-right-radius: 12px; }
QTableCornerButton::section { background: @tables.header_background@; border: 0; border-top-left-radius: 12px; }
QListWidget::item, QListView::item, QTreeWidget::item, QTreeView::item { padding: 6px 8px; border-radius: 7px; }
QListWidget::item:hover, QListView::item:hover, QTreeWidget::item:hover, QTreeView::item:hover { background: @tables.hover@; }
QListWidget::item:selected, QListView::item:selected, QTreeWidget::item:selected, QTreeView::item:selected { background: @tables.selected_background@; color: @tables.selected_text@; }

QGroupBox { background: @surface@; border: 1px solid @divider@; border-radius: 15px; margin-top: 12px; padding-top: 16px; font-weight: __FONT_WEIGHT_EXTRABOLD__; color: @text_primary@; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 8px; color: @text_primary@; background: @surface@; }
QTabWidget::pane { border: 1px solid @divider@; background: @surface@; border-radius: 13px; top: -1px; }
QTabBar::tab { background: @components.tabs.tab@; color: @components.tabs.tab_text@; padding: 9px 18px; margin-right: 4px; border-radius: 10px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QTabBar::tab:hover { background: @hover@; }
QTabBar::tab:selected { background: @primary@; color: @components.buttons.button_text@; }
QProgressBar { background: @background@; border: 1px solid @components.progress.progress_border@; border-radius: 7px; text-align: center; color: @text_primary@; min-height: 14px; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 @primary@, stop:1 @info@); border-radius: 6px; }
QScrollArea, QAbstractScrollArea { background: @background@; border: 0; }
QAbstractScrollArea::viewport { background: @background@; border: 0; }
QScrollArea QWidget#qt_scrollarea_viewport { background: @background@; border: 0; }
QWidget#documentsScrollContent { background: @background@; }
QScrollArea#projectsDashboardScroll { background: @background@; border: 0; }
QScrollArea#projectsDashboardScroll > QWidget { background: @background@; border: 0; }
QScrollArea#projectsDashboardScroll QWidget#qt_scrollarea_viewport { background: @background@; border: 0; }
QWidget#projectsDashboardContent { background: @background@; color: @text_primary@; }
QWidget#projectsDashboardContent QFrame { color: @text_primary@; }
QWidget#projectControlContent { background: @background@; }
QFrame#panelCard { background: @surface@; color: @text_primary@; border: 1px solid @divider@; border-radius: 15px; }
QFrame#panelCard QLabel { color: @text_primary@; }
QFrame#panelCard QLabel#kpiLabel { color: @components.kpi_detail.kpi_title@; font-size: __FONT_SIZE_SMALL__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QFrame#panelCard QLabel#kpiValue { color: @text_primary@; }
QFrame#panelCard QLabel#kpiSubtitle { color: @components.kpi_detail.kpi_subtitle@; }
QLabel#statusBadge { background: @warning@; color: @components.theme.on_warning@; border: 1px solid @warning@; border-radius: 10px; padding: 5px 11px; font-weight: __FONT_WEIGHT_BLACK__; }
QFrame#documentsToolbar { background: @surface@; color: @text_primary@; border: 1px solid @divider@; border-radius: 13px; }
QFrame#documentsToolbar QLabel { color: @text_primary@; }
QWidget#navHost { background: @components.branding.brand_panel@; }

QScrollBar:vertical { background: transparent; width: 12px; margin: 2px; }
QScrollBar::handle:vertical { background: @components.navigation.scrollbar_handle@; border-radius: 4px; min-height: 36px; margin: 0px 2px; }
QScrollBar::handle:vertical:hover { background: @primary@; }
QScrollBar::handle:vertical:pressed { background: @components.buttons.primary_hover@; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 2px; }
QScrollBar::handle:horizontal { background: @components.navigation.scrollbar_handle@; border-radius: 4px; min-width: 36px; margin: 2px 0px; }
QScrollBar::handle:horizontal:hover { background: @primary@; }
QScrollBar::handle:horizontal:pressed { background: @components.buttons.primary_hover@; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0px; height: 0px; background: transparent; border: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QSplitter::handle { background: transparent; }
QSplitter::handle:hover { background: @divider@; }

QToolTip { background: @components.navigation.sidebar@; color: @components.navigation.sidebar_text_primary@; border: 1px solid @primary@; padding: 7px 10px; font-size: __FONT_SIZE_BODY__px; }
QAbstractItemView {
    background: @surface@; color: @text_primary@;
    alternate-background-color: @surface_alt@;
    selection-background-color: @selection_background@; selection-color: @components.theme.on_selection@;
}
QAbstractItemView::item:hover { background: @hover@; color: @text_primary@; }
QListWidget, QListView, QTreeWidget, QTreeView { border: 1px solid @border@; border-radius: 12px; }
QMenu { background: @surface@; color: @text_primary@; border: 1px solid @border@; padding: 6px; }
QMenu::item { background: transparent; color: @text_primary@; padding: 8px 22px; border-radius: 8px; margin: 1px 0px; }
QMenu::item:selected { background: @hover@; color: @text_primary@; }
QMenu::item:disabled { color: @text_muted@; }
QMenu::separator { height: 1px; background: @divider@; margin: 5px 8px; }
QToolButton { background: transparent; color: @text_primary@; border: 1px solid transparent; border-radius: 9px; padding: 5px; }
QToolButton:hover { background: @hover@; border-color: @border@; }
QToolButton:pressed { background: @pressed@; }
QCheckBox, QRadioButton { color: @text_primary@; background: transparent; spacing: 9px; }
QCheckBox::indicator, QRadioButton::indicator { width: 18px; height: 18px; background: @components.forms.search@; border: 2px solid @components.forms.input_border@; }
QCheckBox::indicator { border-radius: 6px; }
QRadioButton::indicator { border-radius: 10px; }
QCheckBox::indicator:hover, QRadioButton::indicator:hover { border-color: @primary@; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked { background: @primary@; border-color: @primary@; }
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled { background: @disabled@; border-color: @border@; }
QCheckBox:disabled, QRadioButton:disabled { color: @text_muted@; }
QCalendarWidget QWidget { background: @surface@; color: @text_primary@; }
QCalendarWidget QAbstractItemView { background: @surface@; color: @text_primary@; selection-background-color: @selection_background@; selection-color: @components.theme.on_selection@; }
QDialog { background: @components.dialogs.dialog@; color: @text_primary@; }
QDialogButtonBox QPushButton { min-width: 92px; }
QMessageBox QLabel { color: @text_primary@; font-size: __FONT_SIZE_ROOT__px; }
QSlider::groove:horizontal { background: @divider@; height: 6px; border-radius: 3px; }
QSlider::sub-page:horizontal { background: @primary@; border-radius: 3px; }
QSlider::handle:horizontal { background: @surface@; border: 2px solid @primary@; width: 14px; height: 14px; margin: -6px 0px; border-radius: 9px; }
QLabel { color: @components.labels.label_text@; }
QStatusBar { background: @surface@; color: @text_muted@; border-top: 1px solid @border@; }

QFrame#projectsWelcomeHero {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 @components.navigation.sidebar@,
        stop:0.55 @components.navigation.navigation@,
        stop:1 @components.navigation.navigation_accent@);
    border: 0;
    border-radius: 18px;
    min-height: 98px;
}
QLabel#projectsWelcomeIcon { background: @warning@; color: @components.theme.on_warning@; border-radius: 14px; font-size: __FONT_SIZE_HEADING__px; padding: 0; }
QLabel#projectsWelcomeTitle { color: @components.theme.on_colored_surface@; font-size: __FONT_SIZE_TITLE__px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#projectsWelcomeSubtitle { color: @components.theme.on_colored_surface@; font-size: __FONT_SIZE_BODY__px; }
QLabel#projectsWelcomeSlogan {
    color: @components.theme.on_colored_surface@; font-size: __FONT_SIZE_BODY__px;
    font-weight: __FONT_WEIGHT_EXTRABOLD__; padding-left: 24px;
    border-left: 1px solid rgba(255,255,255,80); min-width: 170px;
}
QFrame#projectsHero {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 @components.navigation.sidebar@,
        stop:0.58 @components.navigation.navigation@,
        stop:1 @components.navigation.navigation_accent@);
    border: 0;
    border-radius: 18px;
}
QLabel#projectsHeroMark { background: @primary@; color: @components.buttons.button_text@; border-radius: 14px; font-size: __FONT_SIZE_SECTION__px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#projectsHeroTitle { color: @components.theme.on_dark_surface@; font-size: __FONT_SIZE_KPI__px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#projectsHeroSubtitle { color: @components.navigation.nav_text@; font-size: __FONT_SIZE_BODY__px; }
QLabel#projectsHeroSlogan {
    color: @components.theme.on_dark_surface@; font-size: __FONT_SIZE_BODY__px; font-weight: __FONT_WEIGHT_EXTRABOLD__;
    padding-left: 18px; border-left: 1px solid rgba(255,255,255,70);
}
QFrame#projectsMetricCard { background: @surface@; border: 1px solid @divider@; border-radius: 16px; border-top: 4px solid @info@; min-height: 116px; }
QFrame#projectsMetricCard[accentRole="info"] { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 @components.navigation.navigation@, stop:1 @components.navigation.navigation_accent@); border-top-color: @info@; }
QFrame#projectsMetricCard[accentRole="success"] { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 @components.navigation.navigation@, stop:1 @components.buttons.button_success@); border-top-color: @success@; }
QFrame#projectsMetricCard[accentRole="charts.series_3"] { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 @components.navigation.navigation@, stop:1 @charts.series_3@); border-top-color: @charts.series_3@; }
QFrame#projectsMetricCard[accentRole="warning"] { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 @components.navigation.navigation@, stop:1 @warning@); border-top-color: @warning@; }
QLabel#projectsMetricIcon { background: @components.theme.on_colored_surface_muted|22@; color: @components.theme.on_colored_surface@; border: 1px solid @components.theme.on_colored_surface_border|40@; border-radius: 12px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#projectsMetricTitle { color: @components.theme.on_colored_surface@; font-size: __FONT_SIZE_SMALL__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QLabel#projectsMetricValue { color: @components.theme.on_colored_surface@; font-size: __FONT_SIZE_KPI__px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#projectsMetricSubtitle { color: @components.theme.on_colored_surface@; font-size: __FONT_SIZE_SMALL__px; }
QFrame#projectsToolbar { background: transparent; border: 0; }
QLineEdit#projectsSearch, QComboBox#projectsFilter {
    background: @surface@; color: @text_primary@; border: 1px solid @border@; border-radius: 11px;
    padding: 8px 13px; min-height: 20px;
}
QLineEdit#projectsSearch:focus, QComboBox#projectsFilter:focus { border-color: @primary@; }
QFrame#projectsTableCard, QFrame#projectsSideCard, QFrame#projectsSummaryCard { background: @surface@; border: 1px solid @divider@; border-radius: 16px; }
QLabel#projectsSectionTitle { color: @text_primary@; font-size: __FONT_SIZE_SECTION__px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#projectsSectionSubtitle { color: @text_muted@; font-size: __FONT_SIZE_SMALL__px; }
QPushButton#viewModeButton { background: @primary@; color: @components.buttons.button_text@; border: 1px solid @primary@; border-radius: 10px; padding: 7px 14px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QPushButton#viewModeSecondary { background: @surface_alt@; color: @text_secondary@; border: 1px solid @border@; border-radius: 10px; padding: 7px 14px; }
QPushButton#viewModeSecondary:hover { background: @hover@; color: @text_primary@; border-color: @primary@; }
QLabel#projectsSideTitle { color: @text_primary@; font-size: __FONT_SIZE_SECTION__px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#projectsSideText { color: @text_secondary@; font-size: __FONT_SIZE_SMALL__px; }
QLabel#projectsLink { color: @info@; font-size: __FONT_SIZE_SMALL__px; font-weight: __FONT_WEIGHT_BOLD__; }
QLabel#activityTitle { color: @text_primary@; font-size: __FONT_SIZE_SMALL__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QLabel#activityDetail { color: @text_muted@; font-size: __FONT_SIZE_TINY__px; }
QLabel#activityBubble { background: @info@; color: @components.theme.on_info@; border-radius: 15px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#projectsSummaryTitle { color: @text_primary@; font-size: __FONT_SIZE_SMALL__px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#projectsSummaryValue { color: @text_primary@; font-size: __FONT_SIZE_KPI__px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#projectsSummaryDetail { color: @text_muted@; font-size: __FONT_SIZE_TINY__px; }

QComboBox#languageSelector QAbstractItemView {
    background: @surface@; color: @text_primary@;
    selection-background-color: @info@; selection-color: @selection_text@;
}
QFrame#projectsMetricCard QLabel#projectsMetricIcon,
QFrame#projectsMetricCard QLabel#projectsMetricTitle,
QFrame#projectsMetricCard QLabel#projectsMetricValue { color: @components.theme.on_colored_surface@; }
QFrame#projectsMetricCard QLabel#projectsMetricSubtitle { color: @components.theme.on_colored_surface@; }
QFrame#projectsWelcomeHero QLabel#projectsWelcomeTitle,
QFrame#projectsWelcomeHero QLabel#projectsWelcomeSubtitle,
QFrame#projectsWelcomeHero QLabel#projectsWelcomeSlogan { color: @components.theme.on_colored_surface@; }
QScrollArea#projectCardsScroll { background: transparent; border: 0; }
QFrame#projectListCard { background: @surface@; border: 1px solid @divider@; border-radius: 15px; }
QFrame#projectListCard:hover { border-color: @info@; background: @hover@; }
QFrame#projectListCard[selected="true"] { border: 2px solid @info@; background: @selection_background@; }
QLabel#projectListCardId { color: @info@; font-size: __FONT_SIZE_SMALL__px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#projectListCardTitle { color: @text_primary@; font-size: __FONT_SIZE_SECTION__px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#projectListCardMeta { color: @text_secondary@; font-size: __FONT_SIZE_SMALL__px; }
QLabel#projectListCardCaption { color: @text_muted@; font-size: __FONT_SIZE_TINY__px; font-weight: __FONT_WEIGHT_BOLD__; }
QLabel#projectListCardValue { color: @text_primary@; font-size: __FONT_SIZE_SMALL__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QLabel#projectListCardBudget, QLabel#projectListCardTTC { color: @text_primary@; font-size: __FONT_SIZE_BODY__px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#projectListCardStatus { border-radius: 9px; padding: 4px 10px; font-size: __FONT_SIZE_TINY__px; font-weight: __FONT_WEIGHT_BLACK__; color: @components.theme.on_colored_surface@; background: @info@; }
QLabel#projectListCardStatus[statusRole="Active"] { background: @success@; }
QLabel#projectListCardStatus[statusRole="Completed"] { background: @info@; }
QLabel#projectListCardStatus[statusRole="Suspended"] { background: @warning@; color: @text_primary@ }
QLabel#projectListCardStatus[statusRole="Archived"] { background: @danger@; }
QPushButton#viewModeSecondary, QPushButton#viewModeButton { min-height: 34px; }
QLabel#activityBubble[activityRole="project"] { background: @success@; color: @selection_text@; }
QLabel#activityBubble[activityRole="expense"] { background: @charts.series_3@; color: @selection_text@; }
QLabel#activityBubble[activityRole="payment"] { background: @info@; color: @selection_text@; }
QFrame#projectsWelcomeHero QLabel { color: @components.theme.on_colored_surface@; }
QFrame#projectsMetricCard QLabel { color: @components.theme.on_colored_surface@; }
QFrame#projectsMetricCard QLabel#projectsMetricIcon[accentRole="warning"] { color: @components.theme.on_warning@ }
QLineEdit#globalTopSearch, QComboBox#languageSelector { background: @surface_alt@; color: @text_primary@; border-color: @border@; }
QTableWidget#projectsTable::item { padding: 10px 8px; }
QTableWidget#projectsTable::item:selected { background: @selection_background@; color: @text_primary@; }
QStatusBar { background: @surface@; color: @text_muted@; border-top: 1px solid @border@; }

QFrame#pageHeader[unified="true"] {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 @components.navigation.sidebar@,
        stop:0.55 @components.navigation.navigation@,
        stop:1 @components.navigation.navigation_accent@);
    border: 0;
    border-radius: 18px;
    min-height: 88px;
}
QFrame#pageHeader[unified="true"] QLabel#pageTitle {
    color: @components.theme.on_colored_surface@;
    font-size: 24px;
    font-weight: __FONT_WEIGHT_BLACK__;
}
QFrame#pageHeader[unified="true"] QLabel#pageSubtitle { color: @components.navigation.nav_text@; font-size: __FONT_SIZE_SUBTITLE__px; }
QFrame#pageHeader[unified="true"] QLabel#pageMark {
    background: @primary@; color: @components.buttons.button_text@;
    border: 2px solid rgba(255,255,255,70); border-radius: 15px;
    font-size: __FONT_SIZE_SUBTITLE__px; font-weight: __FONT_WEIGHT_BLACK__;
}
QFrame#sectionCard[unified="true"] { background: @surface@; border: 1px solid @divider@; border-radius: 16px; }
QFrame#sectionCard[unified="true"] QLabel#sectionTitle { color: @text_primary@; font-size: __FONT_SIZE_BRAND__px; font-weight: __FONT_WEIGHT_BLACK__; }

QFrame#kpiCard[unified="true"] { background: @surface@; border: 1px solid @divider@; border-top: 3px solid @primary@; border-radius: 15px; }
QFrame#kpiCard[unified="true"][accentRole="primary"] { border-top-color: @primary@; }
QFrame#kpiCard[unified="true"][accentRole="info"] { border-top-color: @info@; }
QFrame#kpiCard[unified="true"][accentRole="charts.series_2"],
QFrame#kpiCard[unified="true"][accentRole="success"] { border-top-color: @success@; }
QFrame#kpiCard[unified="true"][accentRole="charts.series_3"] { border-top-color: @charts.series_3@; }
QFrame#kpiCard[unified="true"][accentRole="charts.series_4"],
QFrame#kpiCard[unified="true"][accentRole="warning"] { border-top-color: @warning@; }
QFrame#kpiCard[unified="true"][accentRole="danger"] { border-top-color: @danger@; }
QFrame#kpiCard[unified="true"][accentRole="charts.series_6"] { border-top-color: @charts.series_6@; }
QFrame#kpiCard[unified="true"][accentRole="charts.series_7"] { border-top-color: @charts.series_7@; }
QFrame#kpiCard[unified="true"][accentRole="charts.series_8"] { border-top-color: @charts.series_8@; }
QFrame#kpiCard[unified="true"] QLabel#kpiIcon { background: @surface_alt@; color: @text_primary@; border: 1px solid @border@; border-radius: 12px; font-weight: __FONT_WEIGHT_BLACK__; }
QFrame#kpiCard[unified="true"] QLabel#kpiTitle { color: @text_secondary@; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QFrame#kpiCard[unified="true"] QLabel#kpiValue { color: @text_primary@; font-weight: __FONT_WEIGHT_BLACK__; }
QFrame#kpiCard[unified="true"] QLabel#kpiSubtitle { color: @text_muted@; }

QScrollArea#documentGenerationScroll { background: transparent; border: none; }
QWidget#documentGenerationContent { background: transparent; }
QFrame#documentCatalogCard, QFrame#documentCategoryCard { background: @surface_alt@; border: 1px solid @divider@; border-radius: 12px; }
QFrame#documentCatalogCard:hover { border-color: @primary@; background: @hover@; }
QLabel#documentCatalogIcon { background: @primary@; color: @components.buttons.button_text@; border-radius: 10px; font-size: __FONT_SIZE_TINY__px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#documentCatalogTitle, QLabel#documentCategoryTitle { color: @text_primary@; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QLabel#documentCatalogDescription, QLabel#documentCategoryItem { color: @text_secondary@; }
QLabel#documentTemplateBadge { background: @warning@; color: @components.buttons.button_text@; border-radius: 9px; padding: 5px 9px; font-size: __FONT_SIZE_TINY__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QLabel#referenceTemplateStatus { background: @surface_alt@; color: @text_secondary@; border: 1px solid @border@; border-radius: 9px; padding: 8px 10px; }

QLabel#dialogTitle { color: @text_primary@; font-size: __FONT_SIZE_HEADING__px; font-weight: __FONT_WEIGHT_BLACK__; }
QLabel#secondaryText { color: @text_secondary@; }
QLabel#mutedText { color: @text_muted@; font-size: __FONT_SIZE_SMALL__px; }
QLabel#formLabel, QLabel#settingsFieldLabel { color: @text_secondary@; font-size: __FONT_SIZE_BODY__px; font-weight: __FONT_WEIGHT_BOLD__; }
QLabel#settingsFieldDescription, QLabel#settingsHint, QLabel#dashboardText { color: @text_muted@; font-size: __FONT_SIZE_SMALL__px; }
QLabel#successText { color: @success@; font-weight: __FONT_WEIGHT_BOLD__; }
QLabel#warningText { color: @warning@; font-weight: __FONT_WEIGHT_BOLD__; }
QFrame#statisticsInnerBox, QFrame#documentPropertiesFrame { background: @surface_alt@; border: 1px solid @divider@; border-radius: 12px; }
QFrame#settingsSection, QFrame#toolCard, QFrame#card { background: @surface@; border: 1px solid @divider@; border-radius: 15px; }
QFrame#toolCard:hover { border-color: @primary@; }
QLabel#toolTitle, QLabel#cardTitle { color: @text_primary@; font-size: __FONT_SIZE_BRAND__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QLabel#toolDescription { color: @text_secondary@; font-size: __FONT_SIZE_BODY__px; }
QLabel#cardValue { color: @text_primary@; font-size: __FONT_SIZE_KPI__px; font-weight: __FONT_WEIGHT_BLACK__; }
QFrame#aiHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 @components.navigation.sidebar@, stop:0.6 @components.navigation.navigation@, stop:1 @components.navigation.navigation_accent@); border: 0; border-radius: 16px; }
QLabel#aiTitle { color: @components.theme.on_colored_surface@; font-size: __FONT_SIZE_HEADING__px; font-weight: __FONT_WEIGHT_BLACK__; background: transparent; }
QLabel#aiSubtitle { color: @components.navigation.nav_text@; font-size: __FONT_SIZE_BODY__px; background: transparent; }
QLineEdit#aiQuestion { border-radius: 14px; padding: 10px 14px; font-size: __FONT_SIZE_ROOT__px; }
QTextEdit#aiAnswer { background: @surface_alt@; color: @text_primary@; border: 1px solid @divider@; border-radius: 14px; padding: 10px 14px; }
QLabel#analyticsCardTitle { color: @text_primary@; font-size: __FONT_SIZE_SECTION__px; font-weight: __FONT_WEIGHT_EXTRABOLD__; }
QLabel#analyticsCardSubtitle { color: @text_muted@; font-size: __FONT_SIZE_SMALL__px; }
"""

ICON_SELECTORS = r"""
QComboBox, QDateEdit, QTimeEdit, QDateTimeEdit { padding-right: 32px; }
QComboBox::drop-down, QDateEdit::drop-down, QTimeEdit::drop-down, QDateTimeEdit::drop-down { subcontrol-origin: padding; subcontrol-position: center right; width: 30px; border: 0; background: transparent; }
QComboBox::down-arrow, QDateEdit::down-arrow, QTimeEdit::down-arrow, QDateTimeEdit::down-arrow { image: url(__ICON_DIR__/chevron-down.png); width: 14px; height: 14px; }
QSpinBox, QDoubleSpinBox { padding-right: 26px; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 22px; border: 0; background: transparent; margin: 3px 3px 0px 0px; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 22px; border: 0; background: transparent; margin: 0px 3px 3px 0px; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url(__ICON_DIR__/chevron-up.png); width: 12px; height: 12px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url(__ICON_DIR__/chevron-down.png); width: 12px; height: 12px; }
QCheckBox::indicator:checked { image: url(__ICON_DIR__/check.png); }
QRadioButton::indicator:checked { image: url(__ICON_DIR__/radio-dot.png); }
"""


# شرح الدالة _resolve_metrics: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _resolve_metrics(css: str) -> str:
    values = {
    "__UI_FONT_FAMILY__": UI_FONT_FAMILY,
        "__FONT_SIZE_ROOT__": str(FONT_SIZE_ROOT),
        "__FONT_SIZE_BRAND__": str(FONT_SIZE_BRAND),
        "__FONT_SIZE_TINY__": str(FONT_SIZE_TINY),
        "__FONT_SIZE_SMALL__": str(FONT_SIZE_SMALL),
        "__FONT_SIZE_BODY__": str(FONT_SIZE_BODY),
        "__FONT_SIZE_SUBTITLE__": str(FONT_SIZE_SUBTITLE),
        "__FONT_SIZE_SECTION__": str(FONT_SIZE_SECTION),
        "__FONT_SIZE_HEADING__": str(FONT_SIZE_HEADING),
        "__FONT_SIZE_TITLE__": str(FONT_SIZE_TITLE),
        "__FONT_SIZE_KPI__": str(FONT_SIZE_KPI),
        "__FONT_WEIGHT_BOLD__": str(FONT_WEIGHT_BOLD),
        "__FONT_WEIGHT_EXTRABOLD__": str(FONT_WEIGHT_EXTRABOLD),
        "__FONT_WEIGHT_BLACK__": str(FONT_WEIGHT_BLACK),
        "__FONT_WEIGHT_HEAVY__": str(FONT_WEIGHT_HEAVY),
    }
    for marker, value in values.items():
        css = css.replace(marker, value)
    return css


def _icon_rules() -> str:
    """أضف قواعد الأيقونات (أسهم، علامة الاختيار) فقط إذا كانت ملفاتها موجودة فعلًا."""
    icon_dir = Path(__file__).resolve().parents[1] / "resources" / "ui"
    required = ("check.png", "radio-dot.png", "chevron-down.png", "chevron-up.png")
    if not all((icon_dir / name).is_file() for name in required):
        return ""
    return ICON_SELECTORS.replace("__ICON_DIR__", icon_dir.as_posix())


APPLICATION_SELECTORS = _resolve_metrics(APPLICATION_SELECTORS) + _icon_rules()

__all__ = ["APPLICATION_SELECTORS", "ICON_SELECTORS"]

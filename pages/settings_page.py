# ============================================================
# شرح الملف: pages/settings_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: صفحة الإعدادات مسؤولة فقط عن إعدادات التطبيق الحالية.
# التصميم منظم إلى أقسام واضحة، مع شريط إجراءات ثابت وأسفل الصفحة قابل للتمرير.

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, ClassVar, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QTabWidget,
    QWidget,
)

from core.i18n import LocalizedComboBox, controller, translate_text
from dev_tools.ui_color_inspector import UIColorInspector
from repositories.db import get_connection
from services.settings_service import clear_settings_cache
from theme import set_theme_style
from theme.colors import OPTIONS, THEME_PREVIEW_PALETTES
from theme.themes import get_token_palette

from .base_page import BasePage, SectionCard, set_button


# شرح الصنف SettingsPage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class SettingsPage(BasePage):
    """صفحة إعدادات منظمة مع الحفاظ على منطق الحفظ الحالي."""

    SETTING_DEFINITIONS: ClassVar[dict[str, dict[str, Any]]] = {
        "language": {
            "label": "Language",
            "description": "Interface language. Layout direction remains unchanged.",
            "type": "combo",
            "options": ["Arabic", "English"],
            "default": "English",
        },
        "currency": {
            "label": "Currency",
            "description": "Currency used for financial amounts.",
            "type": "combo",
            "options": ["DZD", "EUR", "USD", "GBP"],
            "default": "DZD",
        },
        "default_tva": {
            "label": "Default TVA",
            "description": "Default VAT rate used by supported calculations.",
            "type": "combo",
            "options": ["0", "9", "19"],
            "default": "19",
        },
        "date_format": {
            "label": "Date format",
            "description": "Preferred date display format.",
            "type": "combo",
            "options": [
                "yyyy-MM-dd",
                "dd/MM/yyyy",
                "dd-MM-yyyy",
                "MM/dd/yyyy",
            ],
            "default": "yyyy-MM-dd",
        },
        "startup_page": {
            "label": "Startup page",
            "description": "Page selected as the preferred starting screen.",
            "type": "combo",
            "options": [
                "Dashboard",
                "Projects",
                "Métré",
                "Progress / Situations",
                "Expenses",
                "Income / Payments",
                "Debts",
                "Financial Reports",
                "Staff",
                "Attendance",
                "Payroll",
                "Vehicles",
                "Documents",
                "Statistics",
                "Company",
                "Settings",
                "Backup & Restore",
                "Supplementary Works",
                "Management Intelligence",
                "Project Closeout",
            ],
            "default": "Dashboard",
        },
        "backup_on_start": {
            "label": "Safety backup on startup",
            "description": "Create a safety copy before the application starts working with the database.",
            "type": "check", "default": "1",
        },
        "auto_backup_days": {
            "label": "Backup reminder interval",
            "description": "Recommended interval, in days, for reminding the operator to create a backup.",
            "type": "spin", "min": 1, "max": 365, "suffix": " days", "default": "7",
        },
        "alert_document_days": {
            "label": "Document expiry warning",
            "description": "Warn when a document expires within this number of days.",
            "type": "spin", "min": 1, "max": 365, "suffix": " days", "default": "30",
        },
        "alert_progress_gap": {
            "label": "Schedule gap threshold",
            "description": "Flag projects when planned progress is ahead of actual progress by this percentage.",
            "type": "double", "min": 0, "max": 100, "suffix": " %", "default": "15",
        },
        "alert_collection_rate": {
            "label": "Collection risk threshold",
            "description": "Flag low collection when received value falls below this percentage of earned value.",
            "type": "double", "min": 0, "max": 100, "suffix": " %", "default": "50",
        },
        "alert_cost_progress_gap": {
            "label": "Cost vs progress warning",
            "description": "Warn when cost consumption is ahead of physical progress by this percentage.",
            "type": "double", "min": 0, "max": 100, "suffix": " %", "default": "15",
        },
        "ai_assistant_enabled": {
            "label": "Local AI assistant",
            "description": "Enable the lightweight local assistant. It uses BuildOffice intelligence and does not use cloud AI.",
            "type": "check", "default": "1",
        },
        "ai_max_results": {
            "label": "AI result limit",
            "description": "Maximum records displayed by the local assistant.",
            "type": "spin", "min": 5, "max": 50, "default": "20",
        },
        "intelligence_enabled": {
            "label": "Management intelligence",
            "description": "Enable automatic management alerts, reconciliations and explainable project insights.",
            "type": "check", "default": "1",
        },
        "decimal_places": {
            "label": "Financial decimal places",
            "description": "Display precision for financial values. Existing stored values are not changed.",
            "type": "spin", "min": 0, "max": 4, "default": "2",
        },
        "default_retention": {
            "label": "Default retention",
            "description": "Default retention percentage proposed for new situations.",
            "type": "double", "min": 0, "max": 100, "suffix": " %", "default": "0",
        },
        "default_advance_recovery": {
            "label": "Default advance recovery",
            "description": "Default advance-recovery percentage proposed for new situations.",
            "type": "double", "min": 0, "max": 100, "suffix": " %", "default": "0",
        },
        "default_situation_status": {
            "label": "New situation status",
            "description": "Initial workflow status for newly created situations.",
            "type": "combo", "options": ["Draft", "Submitted"], "default": "Draft",
        },
        "confirm_destructive": {
            "label": "Confirm destructive actions",
            "description": "Require confirmation before deleting or archiving important records.",
            "type": "check", "default": "1",
        },
    }

    DEFAULTS: ClassVar[dict[str, str]] = {
        key: definition["default"]
        for key, definition in SETTING_DEFINITIONS.items()
    }
    DEFAULTS["theme"] = "Dark"
    DEFAULTS["color_palette"] = "option_1"

    def __init__(self):
        super().__init__(
            "Settings",
            "Application preferences stored locally and applied safely",
        )
        self.clear_kpis()

        self._controls: dict[str, Any] = {}
        self._theme_group = QButtonGroup(self)
        self._theme_group.setExclusive(True)
        self._palette_group = QButtonGroup(self)
        self._palette_group.setExclusive(True)
        self._palette_cards: dict[str, QFrame] = {}

        self._build_ui()
        self.load()

    # ============================================================
    # بناء الواجهة
    # ============================================================

# شرح الدالة _build_ui: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_ui(self):
        """Build a cleaner settings workspace without changing any setting logic.

        The existing controls, keys, save/reset behavior and helper methods are
        deliberately reused. This pass only changes the visual grouping/order.
        """
        content = QWidget()
        content.setObjectName("settingsContent")
        set_theme_style(
            content,
            """
            QWidget#settingsContent { background: @background@; }
            QFrame#settingsHero {
                background: @surface@; border: 1px solid @border@; border-radius: 16px;
            }
            QLabel#settingsHeroTitle {
                color: @text_primary@; background: transparent; border: none;
                font-size: 18px; font-weight: 700;
            }
            QLabel#settingsHeroSub {
                color: @text_secondary@; background: transparent; border: none;
                font-size: 11px;
            }
            QLabel#settingsHeroBadge {
                color: @components.buttons.button_text@; background: @primary@;
                border-radius: 12px; font-size: 20px; font-weight: 700;
            }
            QTabWidget#settingsTabs::pane {
                background: transparent; border: none; top: -1px;
            }
            QTabWidget#settingsTabs QTabBar::tab {
                background: @surface_alt@; color: @text_secondary@;
                border: 1px solid @border@; border-bottom: none;
                padding: 9px 15px; margin-right: 5px; border-top-left-radius: 9px;
                border-top-right-radius: 9px; font-size: 11px; font-weight: 700;
            }
            QTabWidget#settingsTabs QTabBar::tab:selected {
                background: @surface@; color: @text_primary@;
                border-bottom: 2px solid @primary@;
            }
            QTabWidget#settingsTabs QTabBar::tab:hover {
                color: @text_primary@;
            }
            QFrame#settingsTabSurface {
                background: @surface@; border: 1px solid @border@;
                border-radius: 14px;
            }
            QLabel#settingsTabIntro {
                color: @text_muted@; background: transparent; border: none;
                font-size: 11px;
            }
            QFrame#settingsActions {
                background: @surface@; border: 1px solid @border@; border-radius: 12px;
            }
            QLabel#settingsNote {
                color: @text_muted@; background: transparent; border: none; font-size: 11px;
            }
            """,
        )

        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)

        root = QVBoxLayout(content)
        root.setContentsMargins(2, 2, 8, 8)
        root.setSpacing(8)

        # A compact hero replaces the old large introductory block.
        hero = QFrame()
        hero.setObjectName("settingsHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(16, 13, 16, 13)
        hero_layout.setSpacing(12)

        badge = QLabel("⚙")
        badge.setObjectName("settingsHeroBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(46, 46)
        hero_layout.addWidget(badge)

        text = QVBoxLayout()
        text.setSpacing(2)
        title = QLabel(translate_text("Settings"))
        title.setObjectName("settingsHeroTitle")
        text.addWidget(title)
        subtitle = QLabel(translate_text("Configure BuildOffice Pro by category. Changes are previewed immediately and saved locally."))
        subtitle.setObjectName("settingsHeroSub")
        subtitle.setWordWrap(True)
        text.addWidget(subtitle)
        hero_layout.addLayout(text, 1)

        root.addWidget(hero)

        # Compact single-page settings workspace: two balanced columns with
        # natural-height sections. This avoids the large empty areas created by
        # row-based grids while keeping the whole settings surface scrollable.
        columns = QGridLayout()
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setHorizontalSpacing(10)
        columns.setVerticalSpacing(10)

        def make_section(title, description, accent, builder):
            section = SectionCard(translate_text(title), translate_text(description), accent)
            section.setObjectName("settingsSection")
            builder(section.root_layout)
            return section

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(10)
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(10)

        # Balanced order keeps the two columns visually close in height.
        left.addWidget(make_section(
            "General", "Language, currency, dates and regional preferences.", "@info@", self._add_general_settings
        ))
        left.addWidget(make_section(
            "Application", "Startup behavior and general application preferences.", "@charts.series_3@", self._add_application_settings
        ))
        left.addWidget(make_section(
            "Workflow", "Defaults used when creating situations and presenting financial values.", "@success@", self._add_workflow_settings
        ))
        left.addWidget(make_section(
            "Safety & Backup", "Database protection and safeguards against accidental destructive actions.", "@danger@", self._add_safety_settings
        ))
        left.addStretch(1)

        right.addWidget(make_section(
            "Appearance", "Theme and coordinated application colors.", "@primary@", self._add_appearance_settings
        ))
        right.addWidget(make_section(
            "Management & Control", "AI, management intelligence and operational warning thresholds.", "@warning@", self._add_control_settings
        ))
        right.addStretch(1)

        columns.addLayout(left, 0, 0)
        columns.addLayout(right, 0, 1)
        columns.setColumnStretch(0, 1)
        columns.setColumnStretch(1, 1)
        root.addLayout(columns)

        # Developer tools are intentionally compact and placed after the daily
        # settings instead of consuming a large dedicated tab/page.
        tools = SectionCard(
            translate_text("Developer Tools"),
            translate_text("Diagnostics and visual development utilities."),
            "@warning@",
        )
        tools.setObjectName("settingsSection")
        tools_grid = QGridLayout()
        tools_grid.setContentsMargins(0, 1, 0, 0)
        tools_grid.setHorizontalSpacing(7)
        tools_grid.setVerticalSpacing(7)
        developer_tools = [
            ("Sandbox", "Calculation testing.", lambda: self._open_dev_tool("sandbox")),
            ("Console", "Runtime diagnostics.", lambda: self._open_dev_tool("console")),
            ("UI Inspector", "Inspect widgets and styles.", lambda: self._open_dev_tool("inspector")),
            ("Grid & Boundaries", "Show layout guides.", lambda: self._open_dev_tool("grid")),
            ("Performance HUD", "UI performance metrics.", lambda: self._open_dev_tool("hud")),
            ("Service Profiler", "Trace slow services.", lambda: self._open_dev_tool("profiler")),
            ("Color Inspector", "Inspect UI colors.", self._open_color_inspector),
            ("Visual Dev Kit", "Visual widget tools.", self._open_visual_dev_kit),
            ("Project Validation", "Validate project health.", lambda: self._open_dev_tool("validation")),
            ("Button Audit", "Audit buttons and handlers.", lambda: self._open_dev_tool("button_audit")),
            ("Translation Audit", "Find translation gaps.", lambda: self._open_dev_tool("translation_audit")),
            ("Theme Audit", "Check theme contrast.", lambda: self._open_dev_tool("theme_audit")),
            ("Database Health", "Check SQLite health.", lambda: self._open_dev_tool("database_audit")),
            ("Diagnostic Snapshot", "Capture health report.", lambda: self._open_dev_tool("snapshot")),
            ("Runtime State", "Inspect runtime state.", lambda: self._open_dev_tool("runtime")),
        ]
        for index, (tool_title, description, slot) in enumerate(developer_tools):
            self._add_tool_card(tools_grid, index // 5, index % 5, tool_title, description, slot)
        for column in range(5):
            tools_grid.setColumnStretch(column, 1)
        tools.root_layout.addLayout(tools_grid)
        root.addWidget(tools)

        hint = QLabel(translate_text("Changes are stored locally in the company database."))
        hint.setObjectName("settingsNote")
        hint.setWordWrap(True)
        root.addWidget(hint)

        # Fixed action bar remains outside the tabs so Save/Reset are always visible.
        actions = QFrame()
        actions.setObjectName("settingsActions")
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(14, 9, 14, 9)
        actions_layout.setSpacing(10)

        note = QLabel(translate_text("Changes are saved locally to the company database."))
        note.setObjectName("settingsNote")
        note.setWordWrap(True)
        note.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        actions_layout.addWidget(note, 1)

        self.reset_button = QPushButton(translate_text("Reset defaults"))
        set_button(self.reset_button, "secondary")
        self.reset_button.setMinimumHeight(40)
        self.reset_button.clicked.connect(self.reset_defaults)
        actions_layout.addWidget(self.reset_button)

        self.save_button = QPushButton(translate_text("Save changes"))
        set_button(self.save_button, "primary")
        self.save_button.setMinimumHeight(40)
        self.save_button.setMinimumWidth(150)
        self.save_button.clicked.connect(self.save)
        actions_layout.addWidget(self.save_button)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)
        outer.addWidget(scroll, 1)
        outer.addWidget(actions, 0)
        self.body.addLayout(outer)
    # ============================================================
    # أقسام الإعدادات
    # ============================================================

# شرح الدالة _add_general_settings: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _add_general_settings(self, layout):
        grid = QGridLayout()
        grid.setHorizontalSpacing(9)
        grid.setVerticalSpacing(8)

        definitions = (
            ("language", 0, 0),
            ("currency", 0, 1),
            ("default_tva", 1, 0),
            ("date_format", 1, 1),
        )

        for key, row, col in definitions:
            definition = self.SETTING_DEFINITIONS[key]
            field = QFrame()
            field_layout = QVBoxLayout(field)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(5)

            field_layout.addWidget(self._field_title(definition))
            combo = self._make_combo(definition["options"])
            self._controls[key] = combo
            if key == "language":
                combo.clear()
                combo.addItem(translate_text("Arabic"), "ar")
                combo.addItem(translate_text("English"), "en")
                combo.currentIndexChanged.connect(self._language_changed)
            field_layout.addWidget(combo)
            grid.addWidget(field, row, col)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

# شرح الدالة _add_appearance_settings: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _add_appearance_settings(self, layout):
        """Build theme and coherent application-wide palette selectors."""
        intro = QLabel(translate_text("Choose how BuildOffice Pro should look."))
        intro.setObjectName("settingsFieldDescription")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        theme_grid = QGridLayout()
        theme_grid.setContentsMargins(0, 4, 0, 0)
        theme_grid.setHorizontalSpacing(8)
        theme_grid.setVerticalSpacing(8)
        self._theme_cards = {}
        specs = (("Dark", "Dark", "Dark theme"), ("Light", "Light", "Light theme"))
        for col, (value, title_text, description) in enumerate(specs):
            card = QFrame(); card.setObjectName(f"themeChoice_{value.lower()}")
            card.setMinimumHeight(104)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            box = QVBoxLayout(card); box.setContentsMargins(10, 8, 10, 8); box.setSpacing(5)
            radio = QRadioButton(translate_text(title_text)); radio.setObjectName("themeRadio")
            radio.setProperty("theme_value", value); self._theme_group.addButton(radio); box.addWidget(radio)
            desc = QLabel(translate_text(description)); desc.setObjectName("themeChoiceDescription"); desc.setWordWrap(True); box.addWidget(desc)
            preview = QFrame(); preview.setObjectName("themePreview"); preview.setFixedHeight(42)
            pv = QHBoxLayout(preview); pv.setContentsMargins(10, 10, 10, 10); pv.setSpacing(8)
            rail = QFrame(); rail.setObjectName("themePreviewRail"); rail.setFixedWidth(20); pv.addWidget(rail)
            body = QVBoxLayout(); body.setContentsMargins(0,0,0,0); body.setSpacing(6)
            for role in ("primary", "secondary", "border"):
                strip=QFrame(); strip.setObjectName(f"themePreview_{role}"); strip.setFixedHeight(7); body.addWidget(strip)
            pv.addLayout(body,1); box.addWidget(preview)
            self._apply_static_theme_card_style(card,value); self._apply_static_theme_preview_style(preview,value)
            radio.toggled.connect(lambda checked=False,key=value,ref=card:self._refresh_theme_card(key,ref))
            self._theme_cards[value]=card; theme_grid.addWidget(card,0,col)
        theme_grid.setColumnStretch(0,1); theme_grid.setColumnStretch(1,1); layout.addLayout(theme_grid)

        palette_title = QLabel(translate_text("Color palette")); palette_title.setObjectName("settingsFieldLabel"); layout.addWidget(palette_title)
        palette_hint = QLabel(translate_text("Choose one coordinated palette. It controls the application's accent, navigation, status, KPI and chart colors together."))
        palette_hint.setObjectName("settingsFieldDescription"); palette_hint.setWordWrap(True); layout.addWidget(palette_hint)
        palette_grid = QGridLayout(); palette_grid.setContentsMargins(0,2,0,0); palette_grid.setHorizontalSpacing(8); palette_grid.setVerticalSpacing(8)
        specs = (("option_1","Executive Navy & Gold","Balanced corporate palette"),("option_2","Slate & Teal","Cool analytical palette"),("option_3","Graphite & Emerald","Modern construction palette"),("option_4","Cobalt & Copper","Strong industrial palette"))
        for index,(option,title_text,description) in enumerate(specs):
            row, col = divmod(index, 2)
            card=self._build_palette_card(option,title_text,description); self._palette_cards[option]=card; palette_grid.addWidget(card,row,col)
        for col in range(2): palette_grid.setColumnStretch(col,1)
        layout.addLayout(palette_grid)
        hint=QLabel(translate_text("Theme and palette changes are previewed immediately. Save to keep them for the next startup.")); hint.setObjectName("settingsHint"); hint.setWordWrap(True); layout.addWidget(hint)
        self._theme_group.buttonToggled.connect(self._theme_changed)
        self._palette_group.buttonToggled.connect(self._palette_changed)
        self._controls["theme"] = self._theme_group; self._controls["color_palette"] = self._palette_group

# شرح الدالة _build_palette_card: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_palette_card(self, option, title_text, description):
        """Create a palette choice card using colors from the central theme catalog."""
        card=QFrame(); card.setObjectName(f"paletteChoice_{option}"); card.setMinimumHeight(88); card.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        box=QVBoxLayout(card); box.setContentsMargins(9,7,9,7); box.setSpacing(4)
        radio=QRadioButton(translate_text(title_text)); radio.setObjectName("themeRadio"); radio.setProperty("palette_value",option); self._palette_group.addButton(radio); box.addWidget(radio)
        desc=QLabel(translate_text(description)); desc.setObjectName("themeChoiceDescription"); desc.setWordWrap(True); box.addWidget(desc)
        row=QHBoxLayout(); row.setSpacing(5)
        for token in ("background","surface","primary","accent","success","info"):
            sw=QFrame(); sw.setObjectName("paletteSwatch"); sw.setFixedHeight(14); row.addWidget(sw)
        box.addLayout(row); return card

# شرح الدالة _refresh_palette_cards: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _refresh_palette_cards(self, theme, active_option=None):
        """Refresh swatches and selection borders for the active Light/Dark theme."""
        option=active_option or self._current_palette()
        for palette_option,card in self._palette_cards.items():
            border=get_token_palette(theme,"primary")[palette_option] if palette_option==option else get_token_palette(theme,"border")[palette_option]
            surface=get_token_palette(theme,"surface_alt")[palette_option]
            card.setStyleSheet(f"QFrame#{card.objectName()} {{ background:{surface}; border:{2 if palette_option==option else 1}px solid {border}; border-radius:11px; }}")
            border_color=get_token_palette(theme,"border")[palette_option]
            for swatch,token in zip(card.findChildren(QFrame,"paletteSwatch"),("background","surface","primary","accent","success","info")):
                swatch.setStyleSheet(f"QFrame#paletteSwatch {{ background:{get_token_palette(theme,token)[palette_option]}; border:1px solid {border_color}; border-radius:5px; }}")

# شرح الدالة _current_palette: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _current_palette(self):
        for button in self._palette_group.buttons():
            if button.isChecked(): return str(button.property("palette_value"))
        return self.DEFAULTS["color_palette"]

# شرح الدالة _set_palette_selection: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _set_palette_selection(self, option):
        wanted=str(option).strip() if str(option).strip() in OPTIONS else self.DEFAULTS["color_palette"]
        for button in self._palette_group.buttons():
            button.blockSignals(True); button.setChecked(button.property("palette_value")==wanted); button.blockSignals(False)
        self._refresh_palette_cards(self._current_theme(),wanted)

# شرح الدالة _palette_changed: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _palette_changed(self, button, checked):
        if not checked: return
        option=str(button.property("palette_value") or self.DEFAULTS["color_palette"]); theme=self._current_theme(); window=cast(Any,self.window())
        if window is not None:
            window.color_palette=option; store=getattr(window,"theme_store",None)
            if store is not None: store.set_palette(theme,option,persist=False)
            apply_theme=getattr(window,"apply_theme",None)
            if callable(apply_theme): apply_theme(theme,persist=False)
        self._refresh_palette_cards(theme,option); self.page_status.setText(translate_text("LOCAL • PALETTE PREVIEW"))

# شرح الدالة _apply_static_theme_card_style: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _apply_static_theme_card_style(self, card, theme):
        palette = THEME_PREVIEW_PALETTES[theme]
        style = """
            QFrame#__selector__ { background:__card__; border:1px solid __border__; border-radius:14px; }
            QRadioButton#themeRadio { color:__text__; background:transparent; border:none; font-size:12px; font-weight:700; spacing:8px; }
            QRadioButton#themeRadio::indicator { width:18px; height:18px; }
            QRadioButton#themeRadio::indicator:unchecked { border:2px solid __indicator__; border-radius:9px; background:__indicator_bg__; }
            QRadioButton#themeRadio::indicator:checked { border:2px solid __accent__; border-radius:9px; background:__accent__; }
            QLabel#themeChoiceDescription { color:__description__; background:transparent; border:none; font-size:11px; }
        """
        for name, value in palette.items():
            style = style.replace(f"__{name}__", value)
        style = style.replace("__selector__", f"themeChoice_{theme.lower()}")
        card.setStyleSheet(style)

# شرح الدالة _apply_static_theme_preview_style: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _apply_static_theme_preview_style(self, preview, theme):
        palette = THEME_PREVIEW_PALETTES[theme]
        style = """
            QFrame#themePreview { background:__preview__; border:1px solid __border__; border-radius:9px; }
            QFrame#themePreviewRail { background:__rail__; border-radius:5px; }
            QFrame#themePreview_primary { background:__accent__; border-radius:4px; }
            QFrame#themePreview_secondary { background:__indicator_bg__; border-radius:4px; }
            QFrame#themePreview_border { background:__border__; border-radius:4px; }
        """
        for name, value in palette.items():
            style = style.replace(f"__{name}__", value)
        preview.setStyleSheet(style)

# شرح الدالة _add_application_settings: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _add_application_settings(self, layout):
        field = QFrame()
        form = QVBoxLayout(field)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(6)

        definition = self.SETTING_DEFINITIONS["startup_page"]
        form.addWidget(self._field_title(definition))

        combo = self._make_combo(definition["options"])
        self._controls["startup_page"] = combo
        form.addWidget(combo)
        layout.addWidget(field)

# شرح الدالة _add_control_settings: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _add_control_settings(self, layout):
        grid = QGridLayout()
        grid.setHorizontalSpacing(9); grid.setVerticalSpacing(8)
        keys = ["intelligence_enabled", "ai_assistant_enabled", "ai_max_results", "alert_progress_gap", "alert_collection_rate", "alert_cost_progress_gap", "alert_document_days"]
        for index, key in enumerate(keys):
            field = self._build_control(key)
            grid.addWidget(field, index // 2, index % 2)
        grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

# شرح الدالة _add_workflow_settings: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _add_workflow_settings(self, layout):
        grid = QGridLayout()
        grid.setHorizontalSpacing(9); grid.setVerticalSpacing(8)
        keys = ["default_tva", "default_retention", "default_advance_recovery", "decimal_places", "default_situation_status"]
        for index, key in enumerate(keys):
            field = self._build_control(key)
            grid.addWidget(field, index // 2, index % 2)
        grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

# شرح الدالة _add_safety_settings: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _add_safety_settings(self, layout):
        grid = QGridLayout()
        grid.setHorizontalSpacing(9); grid.setVerticalSpacing(8)
        for index, key in enumerate(("backup_on_start", "auto_backup_days", "confirm_destructive")):
            grid.addWidget(self._build_control(key), 0, index)
        for col in range(3): grid.setColumnStretch(col, 1)
        layout.addLayout(grid)

# شرح الدالة _build_control: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_control(self, key):
        definition = self.SETTING_DEFINITIONS[key]
        field = QFrame()
        box = QVBoxLayout(field); box.setContentsMargins(0, 0, 0, 0); box.setSpacing(5)
        box.addWidget(self._field_title(definition))
        typ = definition.get("type", "combo")
        if typ == "check":
            control = QCheckBox(translate_text("Enabled"))
            control.setMinimumHeight(32)
        elif typ == "spin":
            control = QSpinBox(); control.setRange(int(definition.get("min", 0)), int(definition.get("max", 1000000)))
            control.setSuffix(translate_text(definition.get("suffix", ""))); control.setMinimumHeight(34)
        elif typ == "double":
            control = QDoubleSpinBox(); control.setRange(float(definition.get("min", 0)), float(definition.get("max", 100)))
            control.setDecimals(2); control.setSuffix(translate_text(definition.get("suffix", ""))); control.setMinimumHeight(34)
        else:
            control = self._make_combo(definition.get("options", []))
        self._controls[key] = control
        box.addWidget(control)
        return field

# شرح الدالة _add_tool_card: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _add_tool_card(self, grid, row, column, title, description, slot):
        card = QFrame()
        card.setObjectName("toolCard")
        card.setMinimumHeight(58)

        box = QVBoxLayout(card)
        box.setContentsMargins(7, 5, 7, 5)
        box.setSpacing(2)

        title_label = QLabel(translate_text(title))
        title_label.setObjectName("toolTitle")
        box.addWidget(title_label)

        desc = QLabel(translate_text(description))
        desc.setObjectName("toolDescription")
        desc.setWordWrap(True)
        box.addWidget(desc, 1)

        button = QPushButton(translate_text("Open"))
        button.setMinimumHeight(27)
        set_button(button, "secondary")
        button.clicked.connect(slot)
        box.addWidget(button)

        grid.addWidget(card, row, column)

# شرح الدالة _field_title: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _field_title(self, definition):
        wrapper = QWidget()
        box = QVBoxLayout(wrapper)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)

        label = QLabel(translate_text(definition["label"]))
        label.setObjectName("settingsFieldLabel")
        box.addWidget(label)

        description = definition.get("description", "")
        if description:
            sub = QLabel(translate_text(description))
            sub.setObjectName("settingsFieldDescription")
            sub.setWordWrap(True)
            box.addWidget(sub)

        return wrapper

# شرح الدالة _make_combo: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _make_combo(self, values):
        combo = LocalizedComboBox()
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        combo.setMinimumHeight(40)
        combo.addItems([str(value) for value in values])
        return combo

    # ============================================================
    # التفاعل
    # ============================================================

# شرح الدالة _language_changed: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _language_changed(self, index):
        combo = self._controls.get("language")
        if combo is None:
            return
        language = str(combo.itemData(index) or "en")
        ctl = controller()
        if ctl:
            ctl.set_language(language)
        self.page_status.setText(translate_text("LOCAL • LANGUAGE PREVIEW"))

# شرح الدالة _theme_changed: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _theme_changed(self, button, checked):
        if not checked:
            return
        theme = str(button.property("theme_value") or "Dark")
        window = cast(Any, self.window())
        apply_theme = getattr(window, "apply_theme", None)
        if callable(apply_theme):
            apply_theme(theme, persist=False)
        self._refresh_theme_cards(theme)
        self._refresh_palette_cards(theme, self._current_palette())
        self.page_status.setText(translate_text(f"LOCAL • {theme.upper()} PREVIEW"))

# شرح الدالة _refresh_theme_card: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _refresh_theme_card(self, key, card):
        if key not in self._theme_cards:
            return

        active = any(
            button.isChecked()
            and str(button.property("theme_value")) == key
            for button in self._theme_group.buttons()
        )

        palette = THEME_PREVIEW_PALETTES[key]
        border = palette["accent"] if active else palette["border"]
        width = 2 if active else 1
        style = """
            QFrame#__selector__ {
                background:__card__; border:__width__px solid __active_border__; border-radius:14px;
            }
            QRadioButton#themeRadio {
                color:__text__; background:transparent; border:none;
                font-size:12px; font-weight:700; spacing:8px;
            }
            QRadioButton#themeRadio::indicator { width:18px; height:18px; }
            QRadioButton#themeRadio::indicator:unchecked {
                border:2px solid __indicator__; border-radius:9px; background:__indicator_bg__;
            }
            QRadioButton#themeRadio::indicator:checked {
                border:2px solid __accent__; border-radius:9px; background:__accent__;
            }
            QLabel#themeChoiceDescription {
                color:__description__; background:transparent; border:none; font-size:11px;
            }
        """
        values = {**palette, "selector": f"themeChoice_{key.lower()}", "width": str(width), "active_border": border}
        for name, value in values.items():
            style = style.replace(f"__{name}__", value)
        card.setStyleSheet(style)

# شرح الدالة _refresh_theme_cards: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _refresh_theme_cards(self, theme):
        for key, card in self._theme_cards.items():
            self._refresh_theme_card(key, card)


# شرح الدالة _open_dev_tool: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _open_dev_tool(self, tool: str) -> None:
        """Open one developer utility through the central developer manager."""
        window = cast(Any, self.window())
        manager = getattr(window, "_dev_manager", None)
        if manager is None:
            self.page_status.setText(translate_text("LOCAL • DEVELOPER MODE OFF"))
            QMessageBox.information(
                self,
                translate_text("Developer tools"),
                translate_text("Enable Developer Mode to use developer diagnostics."),
            )
            return

        try:
            if tool == "inspector":
                manager.toggle_inspector()
            elif tool == "grid":
                manager.toggle_grid()
            elif tool == "hud":
                manager.toggle_hud()
            elif tool == "profiler":
                manager.set_profiler_enabled(True)
                manager.show_kit("diagnostics")
            elif tool == "validation":
                manager.run_validation()
                manager.show_kit("console")
            elif tool == "button_audit":
                manager.run_button_audit()
                manager.show_kit("console")
            elif tool == "translation_audit":
                manager.run_translation_audit()
            elif tool == "theme_audit":
                manager.run_theme_audit()
            elif tool == "database_audit":
                manager.run_database_audit()
            elif tool == "snapshot":
                manager.create_snapshot()
            else:
                manager.show_kit(tool)
            self.page_status.setText(translate_text(f"LOCAL • DEV • {tool.upper()}"))
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            self.page_status.setText(translate_text("LOCAL • DEV TOOL ERROR"))
            QMessageBox.warning(self, translate_text("Developer tools"), str(exc))

# شرح الدالة _open_visual_dev_kit: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _open_visual_dev_kit(self):
        """فتح عدة التطوير المرئي إن كانت متاحة في النسخة الحالية."""
        window = cast(Any, self.window())
        try:
            from dev_tools.visual_dev_kit import install_visual_dev_kit

            kit = install_visual_dev_kit(window, __import__("pathlib").Path(__file__).resolve().parent.parent)
            if hasattr(kit, "show_kit"):
                kit.show_kit("overview")
            elif hasattr(kit, "show"):
                kit.show()
            self.page_status.setText(translate_text("LOCAL • VISUAL DEV KIT"))
        except (ImportError, AttributeError, RuntimeError, TypeError, ValueError) as exc:
            self.page_status.setText(translate_text("LOCAL • DEV KIT ERROR"))
            QMessageBox.warning(
                self,
                translate_text("Developer tools"),
                f"{translate_text('Visual Dev Kit')}\n\n{exc}",
            )

# شرح الدالة _open_color_inspector: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _open_color_inspector(self):
        """فتح مفتش الألوان كأداة مستقلة عن Visual Dev Kit."""
        window = cast(Any, self.window())
        if window is None:
            self.page_status.setText(translate_text("LOCAL • INSPECTOR ERROR"))
            QMessageBox.critical(
                self,
                translate_text("UI Color Inspector"),
                translate_text("Could not open UI Color Inspector."),
            )
            return

        try:
            # لا نستخدم install_color_inspector هنا لأنه يعيد Visual Dev Kit
            # عند وجوده مسبقًا. ننشئ UIColorInspector مستقلًا مباشرة.
            inspector = getattr(window, "_ui_color_inspector", None)
            if inspector is None:
                inspector = UIColorInspector(
                    window,
                    Path(__file__).resolve().parent.parent,
                )
                window._ui_color_inspector = inspector

            self._color_inspector = inspector

            if hasattr(inspector, "show"):
                inspector.show()

            dialog = getattr(inspector, "dialog", None)
            selected_widget = getattr(window, "_selected_widget", None)
            if dialog is not None and selected_widget is not None:
                try:
                    dialog.inspect_widget(selected_widget)
                except (AttributeError, RuntimeError, TypeError):
                    pass

            self.page_status.setText(translate_text("LOCAL • COLOR INSPECTOR"))

        except (ImportError, AttributeError, RuntimeError, TypeError, ValueError) as exc:
            self.page_status.setText(translate_text("LOCAL • INSPECTOR ERROR"))
            QMessageBox.critical(
                self,
                translate_text("UI Color Inspector"),
                f"{translate_text('Could not open UI Color Inspector.')}\n\n{exc}",
            )

    # ============================================================
    # التحميل
    # ============================================================

# شرح الدالة showEvent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def showEvent(self, event):
        super().showEvent(event)
        self.load()

# شرح الدالة load: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def load(self):
        conn = get_connection()
        try:
            rows = conn.execute("SELECT setting_key, setting_value FROM settings").fetchall()
        finally:
            conn.close()

        values = dict(self.DEFAULTS)
        for row in rows:
            key = str(row["setting_key"])
            if key in self.SETTING_DEFINITIONS or key == "theme":
                values[key] = str(row["setting_value"] or "")

        for key, control in self._controls.items():
            if key in {"theme", "color_palette"}:
                continue
            value = values.get(key, self.DEFAULTS.get(key, ""))
            control.blockSignals(True)
            if isinstance(control, QCheckBox):
                control.setChecked(str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"})
            elif isinstance(control, QDoubleSpinBox):
                try:
                    control.setValue(float(value))
                except (TypeError, ValueError):
                    pass
            elif isinstance(control, QSpinBox):
                try:
                    control.setValue(int(float(value)))
                except (TypeError, ValueError):
                    pass
            elif key == "language":
                wanted = "en" if str(value).lower() in {"en", "english"} else "ar"
                index = control.findData(wanted, Qt.ItemDataRole.UserRole)
                if index >= 0: control.setCurrentIndex(index)
            else:
                index = control.findText(value, Qt.MatchFlag.MatchFixedString)
                if index >= 0: control.setCurrentIndex(index)
                else: control.setCurrentText(value)
            control.blockSignals(False)

        self._set_theme_selection(values.get("theme", self.DEFAULTS["theme"]))
        self._set_palette_selection(values.get("color_palette", self.DEFAULTS["color_palette"]))

# شرح الدالة _set_theme_selection: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _set_theme_selection(self, theme):
        wanted = "Light" if str(theme).strip().lower() == "light" else "Dark"
        for button in self._theme_group.buttons():
            button.blockSignals(True)
            button.setChecked(button.property("theme_value") == wanted)
            button.blockSignals(False)
        self._refresh_theme_cards(wanted)

    # ============================================================
    # إعادة الإعدادات الافتراضية
    # ============================================================

# شرح الدالة reset_defaults: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def reset_defaults(self):
        if not self.confirm("Replace the current settings with the recommended defaults?", "Reset settings"):
            return
        for key, control in self._controls.items():
            if key == "theme":
                self._set_theme_selection(self.DEFAULTS["theme"])
                continue
            if key == "color_palette":
                self._set_palette_selection(self.DEFAULTS["color_palette"])
                continue
            value = self.DEFAULTS.get(key, "")
            if isinstance(control, QCheckBox):
                control.setChecked(str(value).lower() in {"1", "true", "yes", "on"})
            elif isinstance(control, QSpinBox):
                control.setValue(int(float(value)))
            elif isinstance(control, QDoubleSpinBox):
                control.setValue(float(value))
            elif key == "language":
                wanted = "en" if value == "English" else "ar"
                index = control.findData(wanted, Qt.ItemDataRole.UserRole)
                if index >= 0: control.setCurrentIndex(index)
            else:
                control.setCurrentText(value)
        self.page_status.setText(translate_text("LOCAL • DEFAULTS READY"))

    # ============================================================
    # الحفظ
    # ============================================================

# شرح الدالة _current_theme: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _current_theme(self):
        for button in self._theme_group.buttons():
            if button.isChecked():
                return str(button.property("theme_value"))
        return self.DEFAULTS["theme"]

# شرح الدالة save: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def save(self):
        data = {}
        for key, control in self._controls.items():
            if key in {"theme", "color_palette"}:
                continue
            if isinstance(control, QCheckBox):
                data[key] = "1" if control.isChecked() else "0"
            elif isinstance(control, (QSpinBox, QDoubleSpinBox)):
                data[key] = str(control.value())
            elif key == "language":
                data[key] = str(control.currentData() or "en")
            else:
                data[key] = control.currentText().strip()
        data["theme"] = self._current_theme()
        data["color_palette"] = self._current_palette()

        conn = get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            for key, value in data.items():
                conn.execute(
                    """INSERT INTO settings(setting_key, setting_value) VALUES(?, ?)
                       ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value""",
                    (key, value),
                )
            conn.commit()
            clear_settings_cache()

            window = self.window()
            apply_language = getattr(window, "apply_language", None)
            if callable(apply_language):
                apply_language(data["language"], persist=False)
            palette = data["color_palette"] if data["color_palette"] in OPTIONS else self.DEFAULTS["color_palette"]
            if window is not None:
                window_any = cast(Any, window)
                window_any.color_palette = palette
                store = getattr(window, "theme_store", None)
                if store is not None:
                    store.set_palette(data["theme"], palette, persist=True)
            apply_theme = getattr(window, "apply_theme", None)
            if callable(apply_theme):
                apply_theme(data["theme"], persist=False)
            self._refresh_palette_cards(data["theme"], palette)

            self.page_status.setText(translate_text("LOCAL • SAVED"))
            QMessageBox.information(self, translate_text("BuildOffice Pro"), translate_text("Settings saved successfully."))
        except (sqlite3.Error, RuntimeError) as exc:
            conn.rollback()
            self.page_status.setText(translate_text("LOCAL • ERROR"))
            self.error(f"{translate_text('Could not save settings.')}\n\n{exc}")
        finally:
            conn.close()


__all__ = ["SettingsPage"]

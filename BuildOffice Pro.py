# ============================================================
# شرح الملف: BuildOffice Pro.py
# هذا الملف جزء من ملف من ملفات المشروع.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
"""BuildOffice Pro application shell.

The shell is deliberately thin: business logic stays in pages/services while
this module owns navigation, global search, theme, company identity and window
state. This makes the application easier to extend without duplicating UI code.
"""

from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path
from typing import cast

from PySide6.QtCore import QDateTime, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.config import APP_NAME, DEFAULT_THEME, ORGANIZATION_NAME
from core.hero_banner import HeroBanner
from core.i18n import controller, get_language, install_localization, translate_text
from core.logging_config import logger
from core.ui_smoothness import install_smooth_ui
from core.ux_features import (
    ActivityLogDialog,
    CommandPaletteDialog,
    NotificationCenterDialog,
    RecentFavoritesDialog,
    UXStore,
    install_shortcuts,
    open_project_quick_view,
)
from database.database import create_database, get_connection
from dev_tools.dev_manager import install_dev_manager
from dev_tools.dev_runtime import is_enabled, record_metric
from dev_tools.ui_color_inspector import install_color_inspector
from pages import (
    AccountingPage,  # Changed to Class
    AdministrationPage,  # Changed to Class
    AIAssistantDialog,
    AttendancePage,
    BackupPage,
    CompanyPage,
    ConstructionControlPage,
    ContactsPage,  # Changed to Class
    DashboardPage,
    DebtsPage,
    DocumentGenerationPage,
    DocumentsPage,
    ExpensesPage,
    IncomePage,
    ManagementPage,
    MediaPage,  # Changed to Class
    MetrePage,
    PayrollPage,
    ProcurementPage,
    ProgressPage,
    ProjectCloseoutPage,
    ProjectControlPage,
    ProjectGovernancePage,
    ProjectProfitabilityPage,
    ProjectsPage,
    ReportsPage,
    SettingsPage,
    SiteOperationsPage,
    StaffPage,
    StatisticsPage,
    SupplementaryPage,
    VehiclesPage,
)
from pages.auth_dialogs import run_security_gate
from services.settings_service import get_setting
from theme import (
    ThemeStore,
    apply_widget_theme,
    build_application_style,
    resolve_style,
)

ROOT = Path(__file__).resolve().parent

MENU = [
    ("Dashboard", DashboardPage, "🏠", "WORKSPACE"),
    ("Projects", ProjectsPage, "🏗️", "WORKSPACE"),
    ("Project Control Center", ProjectControlPage, "🎯", "WORKSPACE"),
    ("Project Profitability", ProjectProfitabilityPage, "📊", "WORKSPACE"),
    ("Project Governance", ProjectGovernancePage, "🛡️", "WORKSPACE"),
    ("Procurement", ProcurementPage, "🛒", "OPERATIONS"),
    ("Métré", MetrePage, "📐", "WORKSPACE"),
    ("Progress / Situations", ProgressPage, "📊", "WORKSPACE"),
    ("Project Closeout", ProjectCloseoutPage, "✅", "WORKSPACE"),
    ("Supplementary Works", SupplementaryPage, "➕", "WORKSPACE"),
    ("Expenses", ExpensesPage, "💸", "FINANCE"),
    ("Accounting & Finance", AccountingPage, "🧾", "FINANCE"),
    ("Income / Payments", IncomePage, "💰", "FINANCE"),
    ("Debts", DebtsPage, "📋", "FINANCE"),
    ("Financial Reports", ReportsPage, "📈", "FINANCE"),
    ("Clients & Suppliers", ContactsPage, "🤝", "SYSTEM"),
    ("Staff", StaffPage, "👥", "PEOPLE"),
    ("Attendance", AttendancePage, "🕒", "PEOPLE"),
    ("Payroll", PayrollPage, "💵", "PEOPLE"),
    ("Vehicles", VehiclesPage, "🚚", "ASSETS"),
    ("Construction Control", ConstructionControlPage, "🦺", "OPERATIONS"),
    ("Site Operations", SiteOperationsPage, "📋", "OPERATIONS"),
    ("Documents", DocumentsPage, "📄", "DOCUMENTS"),
    ("Photos & Attachments", MediaPage, "🖼️", "DOCUMENTS"),
    ("Document Generation", DocumentGenerationPage, "📝", "DOCUMENTS"),
    ("Statistics", StatisticsPage, "📊", "ANALYTICS"),
    ("Management Intelligence", ManagementPage, "🧠", "ANALYTICS"),
    ("Company", CompanyPage, "🏢", "SYSTEM"),
    ("Administration", AdministrationPage, "🔐", "SYSTEM"),
    ("Settings", SettingsPage, "⚙️", "SYSTEM"),
    ("Backup & Restore", BackupPage, "💾", "SYSTEM"),
]

GROUPS = [
    ("WORKSPACE", "Operations & project control"),
    ("OPERATIONS", "Site control & job costing"),
    ("FINANCE", "Money, liabilities & reporting"),
    ("PEOPLE", "Staff, attendance & payroll"),
    ("ASSETS", "Fleet & equipment"),
    ("DOCUMENTS", "Records & administration"),
    ("ANALYTICS", "KPIs & management intelligence"),
    ("SYSTEM", "Company, settings & backups"),
]


# شرح الدالة get_group_label: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def get_group_label(group_code: str, language: str | None = None) -> str:
    """Translate the human-readable section label stored in the catalog."""
    group_map = {code: description for code, description in GROUPS}
    label = group_map.get(group_code, group_code)
    return translate_text(label, language)


# شرح الصنف BuildOffice: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class BuildOffice(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme_store = ThemeStore(ROOT / "data" / "theme_selections.json")
        # Apply the saved coherent palette before the first stylesheet is built.
        self.color_palette = str(get_setting("color_palette", "option_1")).strip()
        if self.color_palette not in ("option_1", "option_2", "option_3", "option_4"):
            self.color_palette = "option_1"
        self.ux_store = UXStore(ROOT / "data" / "ux_preferences.json")
        self._shortcuts = []
        self.sidebar_visible = False
        self._launcher_buttons = []

        app = cast(QApplication, QApplication.instance())
        if app is not None:
            initial_theme = str(get_setting("theme", DEFAULT_THEME)).strip().title()
            if initial_theme not in ("Dark", "Light"):
                initial_theme = DEFAULT_THEME
            self.theme_store.set_palette(initial_theme, self.color_palette, persist=False)
            app.setProperty("buildoffice_theme_store", self.theme_store)
            app.setProperty("buildoffice_theme", initial_theme)

        self.setObjectName("buildOfficeWindow")
        self.setWindowTitle(translate_text("BuildOffice Pro | Construction Management"))
        self.resize(1540, 940)
        self.setMinimumSize(1180, 720)
        self.setup_icon()
        self.setup_ui()
        self._smooth_ui = install_smooth_ui(self)

# شرح الدالة setup_icon: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def setup_icon(self):
        for name in ("logo.png", "logo.jpg"):
            path = ROOT / "resources" / name
            if path.exists():
                self.setWindowIcon(QIcon(str(path)))
                break

# شرح الدالة setup_ui: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def setup_ui(self):
        """Build a launcher-first shell while leaving business pages intact."""
        root = QWidget()
        root.setObjectName("appRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # View 0 is the new icon launcher. View 1 is the existing page workspace.
        self.view_stack = QStackedWidget()
        self.view_stack.setObjectName("appViewStack")
        self.view_stack.addWidget(self.create_launcher())

        page_workspace = QWidget()
        page_workspace.setObjectName("pageWorkspace")
        workspace_layout = QVBoxLayout(page_workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        workspace_layout.addWidget(self.create_topbar())

        self.stack = QStackedWidget()
        self.stack.setObjectName("mainStack")
        self.pages: dict[str, QWidget] = {}
        self._page_classes = {name: cls for name, cls, _, _ in MENU}
        for name, _, _, _ in MENU:
            placeholder = QWidget()
            placeholder.setObjectName(f"pagePlaceholder_{name.replace(' ', '_')}")
            self.stack.addWidget(placeholder)
        workspace_layout.addWidget(self.stack, 1)
        self.view_stack.addWidget(page_workspace)
        root_layout.addWidget(self.view_stack, 1)
        self.setCentralWidget(root)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.update_clock()

        # The launcher is the application's true home screen. Existing page
        # classes are still created lazily exactly as before.
        self.view_stack.setCurrentIndex(0)
        self._shortcuts = install_shortcuts(self)
        self._refresh_notification_badge()

    def create_launcher(self):
        """Create the icon-first home screen: hero banner + workspaces grouped by domain."""
        page = QWidget()
        page.setObjectName("launcherPage")
        # كل أنماط الشاشة الرئيسية مركزية في theme/selectors.py لتتبع الثيم تلقائيًا.
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        banner_host = QWidget()
        banner_host.setObjectName("launcherBannerHost")
        host_lay = QVBoxLayout(banner_host)
        host_lay.setContentsMargins(28, 20, 28, 6)
        banner = HeroBanner(ROOT / "resources" / "dashboard_hero.png")
        banner.setObjectName("launcherBanner")
        banner.setMinimumHeight(168)
        banner.setMaximumHeight(188)
        banner_lay = QHBoxLayout(banner)
        banner_lay.setContentsMargins(34, 22, 24, 20)
        banner_lay.setSpacing(12)

        text_box = QVBoxLayout()
        text_box.setSpacing(6)
        title = QLabel(translate_text("Welcome to BuildOffice Pro"))
        self.launcher_title = title
        title.setObjectName("launcherTitle")
        subtitle = QLabel(translate_text("Manage your construction projects, finances, and operations all in one place."))
        self.launcher_subtitle = subtitle
        subtitle.setObjectName("launcherSubtitle")
        subtitle.setWordWrap(True)
        subtitle.setMaximumWidth(560)
        text_box.addStretch()
        text_box.addWidget(title)
        text_box.addWidget(subtitle)
        text_box.addStretch()
        banner_lay.addLayout(text_box, 1)

        version = QLabel(f"v{str((ROOT / 'VERSION').read_text(encoding='utf-8').strip()) if (ROOT / 'VERSION').exists() else '1.09'}")
        version.setObjectName("launcherVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner_lay.addWidget(version, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        host_lay.addWidget(banner)
        outer.addWidget(banner_host)

        scroll = QScrollArea()
        scroll.setObjectName("launcherScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("launcherScrollContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 12, 28, 18)
        content_layout.setSpacing(14)

        hint = QLabel(translate_text("Choose a workspace"))
        self.launcher_hint = hint
        hint.setObjectName("launcherHint")
        content_layout.addWidget(hint)

        self._launcher_buttons = []
        self._launcher_group_labels = []
        self.buttons = []
        columns = 6
        for group_code, group_description in GROUPS:
            entries = [item for item in MENU if item[3] == group_code]
            if not entries:
                continue
            header = QHBoxLayout()
            header.setSpacing(9)
            dot = QLabel()
            dot.setObjectName("launcherGroupDot")
            dot.setProperty("navGroup", group_code)
            dot.setFixedSize(8, 8)
            header.addWidget(dot)
            group_title = QLabel(translate_text(group_description))
            group_title.setObjectName("launcherGroupTitle")
            self._launcher_group_labels.append((group_title, group_description))
            header.addWidget(group_title)
            line = QFrame()
            line.setObjectName("launcherGroupLine")
            line.setFrameShape(QFrame.Shape.NoFrame)
            line.setFixedHeight(1)
            header.addWidget(line, 1)
            content_layout.addLayout(header)

            grid = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(12)
            for column in range(columns):
                grid.setColumnStretch(column, 1)
            for position, (name, _, icon, _group) in enumerate(entries):
                row, col = divmod(position, columns)
                button = QPushButton()
                button.setObjectName("launcherTile")
                button.setProperty("bo_nav_source", name)
                button.setProperty("bo_nav_icon", icon)
                button.setProperty("navGroup", group_code)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setFixedHeight(124)
                button.setMinimumWidth(120)
                button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                # رمز نصي (بدون متغير الإيموجي) كي يتبع لون المجموعة في الثيم.
                glyph = QLabel(icon.replace("\ufe0f", ""))
                glyph.setObjectName("launcherIcon")
                glyph.setProperty("navGroup", group_code)
                glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
                glyph.setFixedSize(50, 50)
                glyph.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                label = QLabel(translate_text(name))
                label.setObjectName("launcherLabel")
                label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
                label.setWordWrap(True)
                label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                tile_layout = QVBoxLayout(button)
                tile_layout.setContentsMargins(10, 14, 10, 10)
                tile_layout.setSpacing(8)
                tile_layout.addWidget(glyph, 0, Qt.AlignmentFlag.AlignHCenter)
                tile_layout.addWidget(label, 1)
                button.clicked.connect(lambda _, n=name: self.open_page(n))
                grid.addWidget(button, row, col)
                self._launcher_buttons.append((name, button, label, glyph))
                self.buttons.append((name, button))
            content_layout.addLayout(grid)
        content_layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        footer = QFrame()
        footer.setObjectName("launcherFooter")
        footer_lay = QHBoxLayout(footer)
        footer_lay.setContentsMargins(28, 8, 28, 10)
        footer_lay.setSpacing(8)
        brand = QLabel(translate_text("BuildOffice Pro"))
        self.launcher_brand = brand
        brand.setObjectName("launcherFooterBrand")
        tagline = QLabel(translate_text("Build better. Manage smarter."))
        self.launcher_tagline = tagline
        tagline.setObjectName("launcherFooterTagline")
        footer_lay.addWidget(brand)
        footer_lay.addWidget(tagline)
        footer_lay.addStretch()
        self.launcher_clock = QLabel()
        self.launcher_clock.setObjectName("launcherClock")
        footer_lay.addWidget(self.launcher_clock)
        outer.addWidget(footer)
        return page

# شرح الدالة create_topbar: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def create_topbar(self):
        """Build the compact command bar used across the application."""
        bar = QFrame()
        bar.setObjectName("topBar")
        bar.setFixedHeight(66)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 9, 18, 9)
        lay.setSpacing(10)

        self.back_button = QPushButton("←")
        self.back_button.setObjectName("backButton")
        self.back_button.setFixedSize(42, 38)
        self.back_button.setToolTip(translate_text("Back to BuildOffice Pro home"))
        self.back_button.clicked.connect(self.show_launcher)
        lay.addWidget(self.back_button)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        self.top_title = QLabel(translate_text("Dashboard"))
        self.top_title.setObjectName("topTitle")
        title_box.addWidget(self.top_title)
        self.top_meta = QLabel(translate_text("BuildOffice Pro • Operations & project control"))
        self.top_meta.setObjectName("topMeta")
        title_box.addWidget(self.top_meta)
        lay.addLayout(title_box)

        self.global_search = QLineEdit()
        self.global_search.setObjectName("globalTopSearch")
        self.global_search.setPlaceholderText(translate_text("Ask BuildOffice AI about projects, finances, workforce or company…"))
        self.global_search.setClearButtonEnabled(True)
        self.global_search.returnPressed.connect(self.open_ai_assistant)
        lay.addWidget(self.global_search, 1)

        self.ai_button = QPushButton("🤖")
        self.ai_button.setObjectName("aiTopButton")
        self.ai_button.setFixedSize(42, 38)
        self.ai_button.setToolTip(translate_text("BuildOffice AI"))
        self.ai_button.clicked.connect(self.open_ai_assistant)
        lay.addWidget(self.ai_button)

        self.top_clock = QLabel()
        self.top_clock.setObjectName("topMeta")
        lay.addWidget(self.top_clock)

        self.command_button = QPushButton("⌘")
        self.command_button.setObjectName("topIconButton")
        self.command_button.setToolTip(translate_text("Command Palette • Ctrl+K"))
        self.command_button.setFixedSize(42, 38)
        self.command_button.clicked.connect(self.show_command_palette)
        lay.addWidget(self.command_button)

        self.recent_button = QPushButton("★")
        self.recent_button.setObjectName("topIconButton")
        self.recent_button.setToolTip(translate_text("Recent & Favorite Projects • Ctrl+Shift+R"))
        self.recent_button.setFixedSize(42, 38)
        self.recent_button.clicked.connect(self.show_recent_favorites)
        lay.addWidget(self.recent_button)

        self.notification_button = QPushButton("🔔 0")
        self.notification_button.setObjectName("topIconButton")
        self.notification_button.setToolTip(translate_text("Notification Center • Ctrl+Shift+N"))
        self.notification_button.setFixedSize(74, 38)
        self.notification_button.clicked.connect(self.show_notifications)
        lay.addWidget(self.notification_button)

        self.language_selector = QComboBox()
        self.language_selector.setObjectName("languageSelector")
        self.language_selector.addItem("🌐  English", "en")
        self.language_selector.addItem("🌐  العربية", "ar")
        current_lang = get_language() if callable(get_language) else "en"
        self.language_selector.setCurrentIndex(1 if str(current_lang).lower().startswith("ar") else 0)
        self.language_selector.currentIndexChanged.connect(
            lambda index: self.apply_language(str(self.language_selector.itemData(index)))
        )
        lay.addWidget(self.language_selector)

        self.theme_toggle = QPushButton(translate_text("☀  Light"))
        self.theme_toggle.setObjectName("themeToggle")
        self.theme_toggle.setCheckable(True)
        self.theme_toggle.setFixedWidth(108)
        self.theme_toggle.setToolTip(translate_text("Switch between Dark and Light themes"))
        self.theme_toggle.clicked.connect(self._toggle_theme)
        lay.addWidget(self.theme_toggle)

        refresh = QPushButton("↻")
        refresh.setObjectName("topIconButton")
        refresh.setToolTip(translate_text("Refresh current page"))
        refresh.setFixedSize(42, 38)
        refresh.clicked.connect(self.refresh_current)
        lay.addWidget(refresh)

        profile = QFrame()
        profile.setObjectName("profileCard")
        pl = QHBoxLayout(profile)
        pl.setContentsMargins(7, 3, 7, 3)
        pl.setSpacing(6)
        avatar = QLabel("●")
        avatar.setObjectName("profileAvatar")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(32, 32)
        pl.addWidget(avatar)
        profile_text = QVBoxLayout()
        profile_text.setSpacing(0)
        name = QLabel(translate_text("Administrator"))
        name.setObjectName("profileName")
        role = QLabel(translate_text("BuildOffice Pro"))
        role.setObjectName("profileRole")
        profile_text.addWidget(name)
        profile_text.addWidget(role)
        pl.addLayout(profile_text)
        lay.addWidget(profile)
        return bar

# شرح الدالة create_sidebar: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def create_sidebar(self):
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(260)

        outer = QVBoxLayout(side)
        outer.setContentsMargins(9, 9, 9, 9)
        outer.setSpacing(6)

        outer.addWidget(self.create_brand_panel())

        self.nav_scroll = QScrollArea()
        self.nav_scroll.setWidgetResizable(True)
        self.nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.nav_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        host = QWidget()
        host.setObjectName("navHost")
        nav = QVBoxLayout(host)
        nav.setContentsMargins(0, 0, 2, 0)
        nav.setSpacing(2)
        self.buttons = []

        for group, _ in GROUPS:
            for name, _, icon, item_group in MENU:
                if item_group != group:
                    continue

                button = QPushButton()
                button.setObjectName("navButton")
                # Keep the logical menu key separate from the rendered label.
                # This is essential because the label contains an icon and spacing.
                button.setProperty("bo_nav_source", name)
                button.setProperty("bo_nav_icon", icon)
                button.setText(f"  {icon:<3}   {translate_text(name)}")
                button.setCheckable(True)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setFixedHeight(39)
                # button.setMaximumHeight(36)
                button.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
                )
                button.clicked.connect(lambda _, n=name: self.open_page(n))
                nav.addWidget(button)
                self.buttons.append((name, button))

        nav.addStretch()
        self.nav_scroll.setWidget(host)
        outer.addWidget(self.nav_scroll, 1)

        footer = QFrame()
        footer.setObjectName("sidebarFooter")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(8, 5, 8, 5)
        fl.setSpacing(6)

        dot = QLabel("●")
        dot.setObjectName("onlineDot")
        fl.addWidget(dot)

        status = QLabel(translate_text("LOCAL DATABASE  •  SQLITE"))
        status.setObjectName("footer")
        self.sidebar_status = status
        fl.addWidget(status)
        fl.addStretch()
        outer.addWidget(footer)

        return side

# شرح الدالة create_brand_panel: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def create_brand_panel(self):
        panel = QFrame()
        panel.setObjectName("brandPanel")

        lay = QHBoxLayout(panel)
        lay.setContentsMargins(9, 8, 9, 8)
        lay.setSpacing(9)

        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedSize(58, 58)
        self.company_logo_label = logo
        self._refresh_company_logo_widget()

        lay.addWidget(logo)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(1)

        company_name, company_ar = self._company_identity()

        self.company_name_label = QLabel(company_name or "BuildOffice Pro")
        self.company_name_label.setObjectName("brandName")
        self.company_name_label.setWordWrap(True)
        self.company_name_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        info.addWidget(self.company_name_label)

        self.company_app_label = QLabel(translate_text("BuildOffice Pro"))
        self.company_app_label.setObjectName("brandApp")
        info.addWidget(self.company_app_label)

        self.company_ar_label = QLabel(company_ar)
        self.company_ar_label.setObjectName("brandArabic")
        self.company_ar_label.setWordWrap(True)
        self.company_ar_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.company_ar_label.setVisible(bool(company_ar))
        info.addWidget(self.company_ar_label)

        typ = QLabel(translate_text("CONSTRUCTION MANAGEMENT"))
        typ.setObjectName("brandType")
        self.brand_type_label = typ
        info.addWidget(typ)

        self.clock_label = QLabel()
        self.clock_label.setObjectName("sidebarClock")
        info.addWidget(self.clock_label)

        lay.addLayout(info, 1)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.update_clock()

        return panel

# شرح الدالة _company_identity: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _company_identity(self) -> tuple[str, str]:
        try:
            conn = get_connection()
            try:
                row = conn.execute(
                    'SELECT "company name", "company name ar" FROM "company info" ORDER BY id LIMIT 1'
                ).fetchone()
            finally:
                conn.close()
            if row:
                return str(row["company name"] or "").strip(), str(
                    row["company name ar"] or ""
                ).strip()
        except sqlite3.Error:
            logger.exception(
                "Failed to retrieve company identity due to database error"
            )
        except (KeyError, IndexError):
            logger.exception(
                "Failed to retrieve company identity due to unexpected result schema"
            )
        return "BuildOffice Pro", ""

# شرح الدالة refresh_company_brand: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _company_logo_path(self) -> Path | None:
        try:
            conn = get_connection()
            try:
                row = conn.execute(
                    'SELECT "logo path" FROM "company info" ORDER BY id LIMIT 1'
                ).fetchone()
            finally:
                conn.close()
            if row and row["logo path"]:
                path = Path(str(row["logo path"]))
                if path.exists():
                    return path
        except (sqlite3.Error, KeyError, TypeError):
            logger.exception("Failed to retrieve company logo")
        for name in ("company_logo.png", "logo.png", "logo.jpg"):
            path = ROOT / "resources" / name
            if path.exists():
                return path
        return None

    def _refresh_company_logo_widget(self):
        if not hasattr(self, "company_logo_label"):
            return
        self.company_logo_label.clear()
        path = self._company_logo_path()
        if path:
            pix = QPixmap(str(path))
            if not pix.isNull():
                self.company_logo_label.setPixmap(
                    pix.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
                )
                return
        self.company_logo_label.setText("BO")

    def refresh_company_brand(self):
        name, ar = self._company_identity()
        self.company_name_label.setText(name or "BuildOffice Pro")
        self.company_ar_label.setText(ar)
        self.company_ar_label.setVisible(bool(ar))
        self._refresh_company_logo_widget()

# شرح الدالة update_clock: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def update_clock(self):
        now = QDateTime.currentDateTime()
        text = now.toString("HH:mm:ss")
        if hasattr(self, "clock_label"):
            self.clock_label.setText(text)
        if hasattr(self, "top_clock"):
            self.top_clock.setText(
                translate_text(now.toString("ddd, dd MMM yyyy  •  HH:mm"))
            )
        if hasattr(self, "launcher_clock"):
            self.launcher_clock.setText(now.toString("ddd, dd MMM yyyy  •  HH:mm"))

# شرح الدالة refresh_current: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def refresh_current(self):
        page = self.stack.currentWidget()
        if page is None:
            return

        method = getattr(page, "refresh", None) or getattr(page, "load", None)
        if not callable(method):
            return

        started = time.perf_counter()
        try:
            method()
            self.statusBar().showMessage(translate_text("Page refreshed"), 2500)
        except (sqlite3.Error, RuntimeError, AttributeError) as err:
            logger.exception("Failed to refresh current page: %s", err)
            QMessageBox.warning(
                self,
                "BuildOffice Pro",
                translate_text(f"Could not refresh the page.\n\n{err}"),
            )
        finally:
            if is_enabled():
                record_metric("page", (time.perf_counter() - started) * 1000.0)

# شرح الدالة global_search_dialog: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def open_ai_assistant(self):
        """فتح المساعد الذكي المحلي باستخدام السؤال الموجود في شريط العنوان."""
        question = self.global_search.text().strip() if hasattr(self, "global_search") else ""
        if str(get_setting("ai_assistant_enabled", "1")).strip().lower() in {"0", "false", "no", "off"}:
            QMessageBox.information(self, translate_text("BuildOffice AI"), translate_text("The local AI assistant is disabled in Settings."))
            return
        AIAssistantDialog(self, question, self.open_page).exec()
        if hasattr(self, "global_search"):
            self.global_search.clear()

    def global_search_dialog(self):
        """فتح البحث العام المحسن مع فتح بطاقة المشروع السريعة."""
        term = self.global_search.text().strip()
        if not term:
            self.global_search.setFocus()
            return

        like = f"%{term}%"
        rows = []
        queries = [
            (
                "Project",
                "SELECT project_id, project_name, status FROM projects WHERE project_id LIKE ? OR project_name LIKE ? OR COALESCE(contract_code,'') LIKE ? LIMIT 50",
            ),
            (
                "Expense",
                "SELECT expense_id, description, payment_status FROM expenses WHERE expense_id LIKE ? OR description LIKE ? OR COALESCE(category,'') LIKE ? LIMIT 50",
            ),
            (
                "Staff",
                "SELECT staff_id, full_name, status FROM staff WHERE staff_id LIKE ? OR full_name LIKE ? OR COALESCE(position,'') LIKE ? LIMIT 50",
            ),
            (
                "Vehicle",
                "SELECT vehicle_id, licence_plate, status FROM vehicles WHERE CAST(vehicle_id AS TEXT) LIKE ? OR licence_plate LIKE ? OR COALESCE(brand,'') LIKE ? LIMIT 50",
            ),
            (
                "Debt",
                "SELECT debt_id, lender, status FROM debt WHERE CAST(debt_id AS TEXT) LIKE ? OR lender LIKE ? OR COALESCE(notes,'') LIKE ? LIMIT 50",
            ),
            (
                "BOQ",
                "SELECT item_id, description, unit FROM metre_items WHERE item_id LIKE ? OR description LIKE ? OR COALESCE(item_number,'') LIKE ? LIMIT 50",
            ),
        ]
        conn = get_connection()
        try:
            for kind, sql in queries:
                for row in conn.execute(sql, (like, like, like)):
                    rows.append(
                        (kind, str(row[0]), str(row[1] or ""), str(row[2] or "-"))
                    )
        finally:
            conn.close()

        dialog = QDialog(self)
        dialog.setWindowTitle(translate_text(f"Global Search • {term}"))
        dialog.resize(900, 540)
        layout = QVBoxLayout(dialog)
        title = QLabel(translate_text(f"Search results for  “{term}”"))
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        table = QTableWidget(len(rows), 4)
        table.setHorizontalHeaderLabels(["Type", "ID", "Name / Description", "Status"])
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                table.setItem(r, c, QTableWidgetItem(value))
        layout.addWidget(table, 1)
        hint = QLabel(
            translate_text(
                "Double-click a project for Quick View • other records open their page"
            )
        )
        layout.addWidget(hint)
        close = QPushButton(translate_text("Close"))
        close.clicked.connect(dialog.accept)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
        table.cellDoubleClicked.connect(
            lambda r, c: self._open_search_result(
                self._table_item_text(table, r, 0),
                dialog,
                self._table_item_text(table, r, 1),
            )
        )
        dialog.exec()

# شرح الدالة _table_item_text: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _table_item_text(table: QTableWidget, row: int, column: int) -> str:
        item = table.item(row, column)
        return item.text() if item is not None else ""

# شرح الدالة _open_search_result: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _open_search_result(self, kind, dialog, entity_id=""):
        mapping = {
            "Project": "Projects",
            "Expense": "Expenses",
            "Staff": "Staff",
            "Vehicle": "Vehicles",
            "Debt": "Debts",
            "BOQ": "Métré",
        }
        if kind == "Project" and entity_id:
            dialog.accept()
            open_project_quick_view(self, entity_id, self.ux_store, self.open_page)
            self._refresh_notification_badge()
            return
        name = mapping.get(kind)
        if name:
            self.open_page(name)
            dialog.accept()

# شرح الدالة show_command_palette: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def show_command_palette(self):
        CommandPaletteDialog(
            self,
            MENU,
            self.ux_store,
            self.open_page,
            self.show_notifications,
            self.show_activity_log,
            self.show_recent_favorites,
        ).exec()

# شرح الدالة show_notifications: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def show_notifications(self):
        NotificationCenterDialog(self).exec()
        self._refresh_notification_badge()

# شرح الدالة show_activity_log: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def show_activity_log(self):
        ActivityLogDialog(self).exec()

# شرح الدالة show_recent_favorites: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def show_recent_favorites(self):
        RecentFavoritesDialog(self, self.ux_store, self.open_page).exec()

# شرح الدالة toggle_sidebar: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def toggle_sidebar(self):
        # Kept as a compatibility hook for existing shortcuts/plugins. The new
        # shell has no persistent sidebar; Ctrl+B returns to the launcher.
        self.show_launcher()

# شرح الدالة _refresh_notification_badge: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _refresh_notification_badge(self):
        if not hasattr(self, "notification_button"):
            return
        try:
            conn = get_connection()
            try:
                count = int(
                    conn.execute(
                        "SELECT COUNT(*) FROM notifications WHERE is_read=0"
                    ).fetchone()[0]
                )
            finally:
                conn.close()
            self.notification_button.setText(f"🔔 {min(count, 99)}")
        except sqlite3.Error:
            self.notification_button.setText("🔔")

# شرح الدالة _ensure_page: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _ensure_page(self, name: str) -> QWidget | None:
        """Create a page only when first requested and localize it immediately."""
        page = self.pages.get(name)
        if page is not None:
            return page
        cls = self._page_classes.get(name)
        if cls is None:
            return None
        page = cls()
        self.pages[name] = page
        index = next((i for i, item in enumerate(MENU) if item[0] == name), -1)
        if index < 0:
            return None
        old = self.stack.widget(index)
        assert old is not None
        self.stack.removeWidget(old)
        old.deleteLater()
        self.stack.insertWidget(index, page)
        ctl = controller()
        if ctl:
            from core.i18n import localize_widget_tree

            localize_widget_tree(page, ctl.language)
            if hasattr(self, "_smooth_ui"):
                self._smooth_ui.register_widget_tree(page)
        return page

# شرح الدالة _refresh_sidebar_language: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _refresh_sidebar_language(self, language: str):
        """Refresh launcher labels from stable menu keys."""
        lang = "ar" if str(language).lower().startswith("ar") else "en"
        if hasattr(self, "launcher_title"):
            self.launcher_title.setText(translate_text("Welcome to BuildOffice Pro", lang))
        if hasattr(self, "launcher_subtitle"):
            self.launcher_subtitle.setText(translate_text("Manage your construction projects, finances, and operations all in one place.", lang))
        if hasattr(self, "launcher_hint"):
            self.launcher_hint.setText(translate_text("Choose a workspace", lang))
        if hasattr(self, "launcher_brand"):
            self.launcher_brand.setText(translate_text("BuildOffice Pro", lang))
        if hasattr(self, "launcher_tagline"):
            self.launcher_tagline.setText(translate_text("Build better. Manage smarter.", lang))
        for name, button, label, _glyph in getattr(self, "_launcher_buttons", []):
            label.setText(translate_text(name, lang))
        for group_label, group_description in getattr(self, "_launcher_group_labels", []):
            group_label.setText(translate_text(group_description, lang))
        if hasattr(self, "global_search"):
            self.global_search.setPlaceholderText(translate_text("Ask BuildOffice AI about projects, finances, workforce or company…", lang))
        if hasattr(self, "language_selector"):
            self.language_selector.blockSignals(True)
            self.language_selector.setCurrentIndex(1 if lang == "ar" else 0)
            self.language_selector.blockSignals(False)
        if hasattr(self, "back_button"):
            self.back_button.setToolTip(translate_text("Back to BuildOffice Pro home", lang))

# شرح الدالة open_page: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def open_page(self, name):
        started = time.perf_counter()
        for index, (item_name, _, _, group_code) in enumerate(MENU):
            if item_name != name:
                continue
            page = self._ensure_page(name)
            if page is None:
                return
            if hasattr(self, "_smooth_ui"):
                self._smooth_ui.page_will_change(index)
            self.stack.setCurrentIndex(index)
            self.view_stack.setCurrentIndex(1)
            if hasattr(self, "_smooth_ui"):
                self._smooth_ui.page_changed(index)
            self.top_title.setText(translate_text(item_name))
            self.top_meta.setText(translate_text(f"BuildOffice Pro  •  {get_group_label(group_code)}"))
            break
        if is_enabled():
            record_metric("page", (time.perf_counter() - started) * 1000.0)

    def show_launcher(self):
        """Return to the icon launcher without destroying any page state."""
        if hasattr(self, "view_stack"):
            self.view_stack.setCurrentIndex(0)
        if hasattr(self, "top_title"):
            self.top_title.setText(translate_text("BuildOffice Pro"))
        if hasattr(self, "top_meta"):
            self.top_meta.setText(translate_text("Choose a workspace"))

# شرح الدالة open: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def open(self, name):
        self.open_page(name)

# شرح الدالة apply_language: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def apply_language(self, language: str, persist: bool = True):
        language = "en" if str(language).strip().lower() in ("en", "english") else "ar"
        ctl = controller()
        if ctl:
            ctl.set_language(language)
        # The sidebar uses icon + label composites, so it must be refreshed from
        # its stable English menu keys instead of attempting to reverse-translate
        # the rendered string.
        self._refresh_sidebar_language(language)
        # Existing pages stay alive for fast navigation, so re-localize their
        # widget trees when the language changes instead of only translating
        # the launcher. This also updates table headers, tabs, buttons and
        # dialog-owned controls that already exist.
        from core.i18n import localize_widget_tree
        for page in getattr(self, "pages", {}).values():
            try:
                localize_widget_tree(page, language)
            except RuntimeError:
                pass
        if hasattr(self, "ai_button"):
            self.ai_button.setToolTip(translate_text("BuildOffice AI", language))
        if hasattr(self, "command_button"):
            self.command_button.setToolTip(translate_text("Command Palette • Ctrl+K", language))
        if hasattr(self, "recent_button"):
            self.recent_button.setToolTip(translate_text("Recent & Favorite Projects • Ctrl+Shift+R", language))
        if hasattr(self, "notification_button"):
            self.notification_button.setToolTip(translate_text("Notification Center • Ctrl+Shift+N", language))
        if hasattr(self, "theme_toggle"):
            theme = "Light" if self.theme_toggle.isChecked() else "Dark"
            glyph = "☀" if theme == "Light" else "☾"
            self.theme_toggle.setText(f"{glyph}  {translate_text(theme, language)}")
        if hasattr(self, "top_title"):
            stack_index = self.stack.currentIndex() if hasattr(self, "stack") else -1
            current_name = (MENU[stack_index][0] if 0 <= stack_index < len(MENU) and self.view_stack.currentIndex() == 1 else "BuildOffice Pro")
            current_group = (MENU[stack_index][3] if 0 <= stack_index < len(MENU) and self.view_stack.currentIndex() == 1 else "SYSTEM")
            self.top_title.setText(translate_text(current_name, language))
            self.top_meta.setText(
                translate_text(
                    f"BuildOffice Pro  •  {get_group_label(current_group, language)}",
                    language,
                )
            )
        if persist:
            conn = get_connection()
            try:
                conn.execute(
                    "INSERT INTO settings(setting_key,setting_value) VALUES('language',?) "
                    "ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value",
                    (language,),
                )
                conn.commit()
            finally:
                conn.close()
        # Ensure newly created widgets resolve the language selected in Settings.
        from services.settings_service import clear_settings_cache

        clear_settings_cache()

# شرح الدالة current_theme: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def current_theme(self) -> str:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT setting_value FROM settings WHERE setting_key='theme'"
            ).fetchone()
            return (
                str(row[0] if row else DEFAULT_THEME).strip().title() or DEFAULT_THEME
            )
        finally:
            conn.close()

# شرح الدالة _toggle_theme: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _toggle_theme(self, checked: bool):
        self.apply_theme("Light" if checked else "Dark")

# شرح الدالة _sync_theme_toggle: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _sync_theme_toggle(self, theme: str):
        if not hasattr(self, "theme_toggle"):
            return
        is_light = theme == "Light"
        self.theme_toggle.blockSignals(True)
        self.theme_toggle.setChecked(is_light)
        self.theme_toggle.setText(translate_text("☀  Light" if is_light else "☾  Dark"))
        self.theme_toggle.blockSignals(False)

# شرح الدالة apply_theme: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def apply_theme(self, theme: str, persist: bool = True):
        theme = "Light" if str(theme).strip().lower() == "light" else "Dark"
        app = cast(QApplication, QApplication.instance())
        if app is None:
            return
        app.setProperty("buildoffice_theme", theme)
        self.color_palette = str(getattr(self, "color_palette", get_setting("color_palette", "option_1"))).strip()
        if self.color_palette not in ("option_1", "option_2", "option_3", "option_4"):
            self.color_palette = "option_1"
        self.theme_store.set_palette(theme, self.color_palette, persist=False)
        app.setProperty("buildoffice_theme_store", self.theme_store)
        app.setStyleSheet(build_application_style(self.theme_store, theme))
        apply_widget_theme(theme, self.theme_store)
        self._sync_theme_toggle(theme)
        if persist:
            conn = get_connection()
            try:
                conn.execute(
                    "INSERT INTO settings(setting_key,setting_value) VALUES('theme',?) ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value",
                    (theme,),
                )
                conn.commit()
            finally:
                conn.close()
        self.statusBar().showMessage(translate_text(f"Theme: {theme}"), 1800)


# شرح الدالة main: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def main():
    logger.info("Starting BuildOffice Pro")
    try:
        create_database()
    except sqlite3.Error:
        logger.exception("Database initialization failed")
        raise
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    install_localization(app)
    app.setOrganizationName(ORGANIZATION_NAME)

    # Development mode bypasses the commercial security gate for the developer.
    # Customer/release builds should ship with developer_mode disabled.
    developer_mode = False
    dev_config = ROOT / "config" / "developer_mode.json"
    try:
        if dev_config.exists():
            config_data = __import__("json").loads(dev_config.read_text(encoding="utf-8"))
            developer_mode = bool(config_data.get("developer_mode", False))
    except (OSError, UnicodeError, ValueError):
        logger.exception("Could not read developer mode configuration")

    if developer_mode:
        logger.info("Developer mode enabled: security gate bypassed")
        app.setProperty("buildoffice_developer_mode", True)
        app.setProperty(
            "buildoffice_current_user",
            {"username": "Developer", "role": "Developer", "developer_mode": True},
        )
    else:
        # Production flow: activation -> first administrator setup -> login.
        current_user = run_security_gate(app)
        if current_user is None:
            logger.info("Application closed from security gate")
            return 0
        app.setProperty("buildoffice_current_user", current_user)

    window = BuildOffice()
    app.setProperty("buildoffice_theme_store", window.theme_store)
    window.apply_language(get_language(), persist=False)
    window.apply_theme(window.current_theme(), persist=False)
    window.showMaximized()
    install_color_inspector(window, ROOT)
    if developer_mode:
        dev_manager = install_dev_manager(window, ROOT)
        app.setProperty("buildoffice_dev_manager", dev_manager)
        logger.info("Developer Tools & Diagnostics initialized")
    logger.info("BuildOffice Pro UI initialized")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

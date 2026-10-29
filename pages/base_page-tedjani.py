# ============================================================
# شرح الملف: pages/base_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Shared visual and interaction foundation for BuildOffice Pro pages.

The page classes keep their domain logic, while this module provides a consistent
professional workspace: dark navy surfaces, gold accents, colorful KPI cards,
reliable table helpers, safe database context handling and common action controls.
"""

from __future__ import annotations

import logging
import sqlite3
import time
import typing
from collections.abc import Iterable, Sequence
from contextlib import contextmanager

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.i18n import translate_text
from dev_tools.dev_runtime import is_enabled, record_metric
from repositories.db import get_connection
from services.settings_service import money_display
from theme import set_theme_property
from theme.metrics import SPACE_MD, SPACE_SM

from .id_service import next_sequence_id

logger = logging.getLogger(__name__)

# -----------------------------
# Design tokens
# -----------------------------

NAVY = "@surface@"
NAVY_2 = "@components.navigation.navigation_alt@"
NAVY_3 = "@components.navigation.navigation_deep@"
BLUE = "@info@"
GOLD = "@primary@"
GOLD_LIGHT = "@gold@"
TEAL = "@charts.series_2@"
GREEN = "@success@"
RED = "@danger@"
ORANGE = "@warning@"
PURPLE = "@charts.series_3@"
CYAN = "@charts.series_7@"
SURFACE = "@surface@"
SURFACE_2 = "@surface_alt@"
SURFACE_3 = "@surface_alt@"
BORDER = "@border@"
TEXT = "@text_primary@"
MUTED = "@text_muted@"
WHITE = "@selection_text@"


# شرح الدالة money: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def money(value: typing.Any) -> str:
    """Format a number using the application's configured currency."""
    return money_display(value)


# شرح الدالة percent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def percent(value: typing.Any, decimals: int = 1) -> str:
    try:
        return f"{float(value or 0):,.{decimals}f}%"
    except (TypeError, ValueError):
        return f"0.{('0' * decimals)}%"


# شرح الدالة next_id: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def next_id(table: str, column: str, prefix: str, width: int) -> str:
    """Backward-compatible ID helper.

    New code should pass an existing connection to next_sequence_id so the ID
    reservation and record write share one transaction.
    """
    conn = get_connection()
    try:
        return next_sequence_id(conn, prefix, digits=width)
    finally:
        conn.close()


# شرح الدالة db_transaction: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
@contextmanager
def db_transaction():
    """Yield one configured connection and guarantee rollback/close on errors."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except (sqlite3.Error, TypeError, ValueError):
        conn.rollback()
        raise
    finally:
        conn.close()


# شرح الدالة set_button: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def set_button(button: QPushButton, role: str = "secondary") -> QPushButton:
    """Apply a semantic role without coupling page logic to QSS details."""
    roles = {
        "primary": "primaryButton",
        "secondary": "secondaryButton",
        "danger": "dangerButton",
        "gold": "goldButton",
        "success": "successButton",
    }
    button.setObjectName(roles.get(role, "secondaryButton"))
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


# شرح الدالة fill_table: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def fill_table(table, rows: Iterable[Sequence[typing.Any]], *, align_numeric: bool = False):
    """Populate a QTableWidget in one paint pass without transient sorting work."""
    rows = list(rows)
    updates = table.updatesEnabled()
    signals = table.blockSignals(True)
    sorting = table.isSortingEnabled()
    table.setUpdatesEnabled(False)
    table.setSortingEnabled(False)
    try:
        table.clearContents()
        table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                item = QTableWidgetItem("" if value is None else str(value))
                if align_numeric and isinstance(value, (int, float)):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                table.setItem(i, j, item)
    finally:
        table.blockSignals(signals)
        table.setSortingEnabled(sorting)
        table.setUpdatesEnabled(updates)


# شرح الدالة configure_table: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def configure_table(table, *, select_rows: bool = True, stretch_last: bool = True):
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.setSortingEnabled(True)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    if select_rows:
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setHighlightSections(False)
    if stretch_last:
        table.horizontalHeader().setStretchLastSection(True)
    table.setMinimumHeight(220)
    # Let the central table fitter keep the table inside the available page width.
    table.setProperty("bo_auto_fit", True)


# شرح الصنف KpiCard: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class KpiCard(QFrame):
    """Compact, colorful metric card used throughout the application."""

    def __init__(
        self,
        title: str,
        value: str = "0",
        subtitle: str = "",
        accent: str = GOLD,
        icon: str = "•",
    ):
        super().__init__()
        self.setObjectName("kpiCard")
        self.setProperty("unified", True)
        accent_role = str(accent).strip().strip("@").strip()
        self.setProperty("accentRole", accent_role or "primary")
        set_theme_property(self, "accent", accent)
        self.setMinimumHeight(116)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 13)
        root.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(SPACE_SM)
        icon_label = QLabel(icon)
        icon_label.setObjectName("kpiIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(34, 34)
        top.addWidget(icon_label)

        title_label = QLabel(translate_text(title).upper())
        title_label.setObjectName("kpiTitle")
        top.addWidget(title_label, 1)
        root.addLayout(top)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("kpiValue")
        root.addWidget(self.value_label)

        self.subtitle_label = QLabel(translate_text(subtitle))
        self.subtitle_label.setObjectName("kpiSubtitle")
        self.subtitle_label.setWordWrap(False)
        root.addWidget(self.subtitle_label)

# شرح الدالة set_value: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def set_value(self, value: typing.Any, subtitle: str | None = None):
        self.value_label.setText(str(value))
        if subtitle is not None:
            self.subtitle_label.setText(translate_text(subtitle))


# شرح الصنف SectionCard: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class SectionCard(QFrame):
    """Page section with a title, description and content layout."""

    def __init__(self, title: str, subtitle: str = "", accent: str = GOLD):
        super().__init__()

        self.setObjectName("sectionCard")
        self.setProperty("unified", True)
        set_theme_property(self, "accent", accent)

        # التخطيط الرئيسي للبطاقة
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(17, 14, 17, 17)
        self.root_layout.setSpacing(10)

        # عنوان القسم
        head = QHBoxLayout()

        title_label = QLabel(translate_text(title))
        title_label.setObjectName("sectionTitle")

        head.addWidget(title_label)
        head.addStretch()

        self.root_layout.addLayout(head)

        # الوصف الاختياري
        if subtitle:
            sub = QLabel(translate_text(subtitle))
            sub.setObjectName("sectionSubtitle")
            sub.setWordWrap(True)
            self.root_layout.addWidget(sub)

# شرح الدالة add: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add(self, widget: QWidget):
        """إضافة Widget إلى محتوى البطاقة."""
        self.root_layout.addWidget(widget)

# شرح الدالة add_layout: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_layout(self, layout):
        """إضافة Layout إلى محتوى البطاقة."""
        self.root_layout.addLayout(layout)


# شرح الصنف BasePage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class BasePage(QWidget):
    """Common shell shared by every business page."""

    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.page_title = title
        self.page_subtitle = subtitle
        self.setObjectName("businessPage")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 18)
        root.setSpacing(13)
        self._root_layout = root

        # Every page uses the same global header. Dashboard and Projects may keep
        # their specialized content below it, but never bypass the shared shell.
        self.page_status = QLabel(translate_text("LOCAL • READY"))
        self.page_status.setObjectName("pageStatus")
        self.refresh_button = None

        header = QFrame()
        header.setObjectName("pageHeader")
        header.setProperty("unified", True)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 15, 18, 15)
        header_layout.setSpacing(SPACE_MD)

        mark = QLabel(self._page_mark(title))
        mark.setObjectName("pageMark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(48, 48)
        header_layout.addWidget(mark)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_label = QLabel(translate_text(title))
        title_label.setObjectName("pageTitle")
        title_box.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(translate_text(subtitle))
            subtitle_label.setObjectName("pageSubtitle")
            subtitle_label.setWordWrap(True)
            title_box.addWidget(subtitle_label)
        header_layout.addLayout(title_box, 1)

        header_layout.addWidget(self.page_status)

        refresh = QPushButton(translate_text("↻  Refresh"))
        set_button(refresh, "secondary")
        refresh.setToolTip(translate_text("Refresh this page from the database"))
        refresh.clicked.connect(self.refresh_page)
        header_layout.addWidget(refresh)
        self.refresh_button = refresh

        tools = QPushButton(translate_text("⚙ Tools"))
        set_button(tools, "secondary")
        tools.setToolTip(translate_text("Utilities for this page"))
        menu = QMenu(tools)
        insights_action = menu.addAction(translate_text("Smart construction insights"))
        insights_action.triggered.connect(self.show_smart_insights)
        health_action = menu.addAction(translate_text("Database health check"))
        health_action.triggered.connect(self.show_data_health)
        tools.setMenu(menu)
        tools.clicked.connect(lambda: menu.exec(tools.mapToGlobal(tools.rect().bottomLeft())))
        header_layout.addWidget(tools)
        root.addWidget(header)

        self.kpi_layout = QGridLayout()
        self.kpi_layout.setHorizontalSpacing(12)
        self.kpi_layout.setVerticalSpacing(12)
        root.addLayout(self.kpi_layout)
        self._kpi_cards = []
        self._live_kpi_title = title
        if title not in {"Dashboard", "Projects", "Expenses", "Statistics", "Attendance", "Project Control Center"}:
            self._build_live_kpis(title)

        self.body = QVBoxLayout()
        self.body.setSpacing(13)
        root.addLayout(self.body, 1)

# شرح الدالة _page_mark: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _page_mark(title: str) -> str:
        marks = {
            "Dashboard": "⌂",
            "Projects": "🏗️",
            "Métré": "📐",
            "Progress / Situations": "📊",
            "Project Closeout": "✅",
            "Expenses": "💸",
            "Income / Payments": "💰",
            "Debts": "📋",
            "Reports": "📈",
            "Staff": "👥",
            "Attendance": "🕒",
            "Payroll": "💵",
            "Vehicles": "🚚",
            "Documents": "📄",
            "Document Generation": "DG",
            "Statistics": "📊",
            "Company": "🏢",
            "Settings": "⚙️",
            "Backup & Restore": "💾",
        }
        return marks.get(title, "BO")

# شرح الدالة _build_live_kpis: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_live_kpis(self, title: str):
        """Create accurate, read-only KPIs for ordinary CRUD pages.

        Queries are intentionally defensive: a page remains usable even when a
        partially initialized development database lacks an optional table.
        """
        queries = {
            "Projects": [
                (
                    "ACTIVE",
                    "SELECT COUNT(*) FROM projects WHERE status='Active'",
                    "Current projects",
                    "@info@",
                    "P",
                ),
                (
                    "BUDGET HT",
                    "SELECT COALESCE(SUM(budget_ht),0) FROM projects",
                    "Registered project budgets",
                    "@primary@",
                    "₣",
                ),
                (
                    "EXPENSES",
                    "SELECT COALESCE(SUM(amount),0) FROM expenses",
                    "All recorded expenses",
                    "@danger@",
                    "E",
                ),
                (
                    "PROJECTS",
                    "SELECT COUNT(*) FROM projects",
                    "Total records",
                    "@charts.series_2@",
                    "#",
                ),
            ],
            "Métré": [
                (
                    "BOQ ITEMS",
                    "SELECT COUNT(*) FROM metre_items",
                    "Bill of quantities lines",
                    "@info@",
                    "Σ",
                ),
                (
                    "BOQ VALUE",
                    "SELECT COALESCE(SUM(amount),0) FROM metre_items",
                    "Calculated item values",
                    "@primary@",
                    "₣",
                ),
                (
                    "PROJECTS",
                    "SELECT COUNT(DISTINCT project_id) FROM metre_items",
                    "Projects with BOQ",
                    "@charts.series_2@",
                    "P",
                ),
                (
                    "AVG PRICE",
                    "SELECT COALESCE(AVG(unit_price),0) FROM metre_items",
                    "Average unit price",
                    "@charts.series_3@",
                    "∅",
                ),
            ],
            "Progress / Situations": [
                (
                    "SITUATIONS",
                    "SELECT COUNT(*) FROM situations",
                    "All progress records",
                    "@info@",
                    "PG",
                ),
                (
                    "EXECUTED VALUE",
                    "SELECT COALESCE(SUM(amount),0) FROM situation_items",
                    "Executed work value",
                    "@primary@",
                    "₣",
                ),
                (
                    "APPROVED",
                    "SELECT COUNT(*) FROM situations WHERE status='Approved'",
                    "Approved situations",
                    "@success@",
                    "✓",
                ),
                (
                    "DRAFT",
                    "SELECT COUNT(*) FROM situations WHERE status='Draft'",
                    "Still being prepared",
                    "@warning@",
                    "D",
                ),
            ],
            "Income / Payments": [
                (
                    "RECEIVED",
                    "SELECT COALESCE(SUM(amount),0) FROM project_payments",
                    "Recorded project receipts",
                    "@success@",
                    "₣",
                ),
                (
                    "PAYMENTS",
                    "SELECT COUNT(*) FROM project_payments",
                    "Payment transactions",
                    "@info@",
                    "IN",
                ),
                (
                    "PROJECTS",
                    "SELECT COUNT(DISTINCT project_id) FROM project_payments",
                    "Projects with receipts",
                    "@primary@",
                    "P",
                ),
                (
                    "AVERAGE",
                    "SELECT COALESCE(AVG(amount),0) FROM project_payments",
                    "Average receipt",
                    "@charts.series_3@",
                    "Ø",
                ),
            ],
            "Debts": [
                (
                    "DEBT RECORDS",
                    "SELECT COUNT(*) FROM debt",
                    "Registered liabilities",
                    "@danger@",
                    "DB",
                ),
                (
                    "TOTAL DEBT",
                    "SELECT COALESCE(SUM(amount),0) FROM debt",
                    "Original debt amounts",
                    "@primary@",
                    "₣",
                ),
                (
                    "PAID",
                    "SELECT COALESCE(SUM(dp.amount),0) FROM debt_payments dp",
                    "Debt payments",
                    "@success@",
                    "✓",
                ),
                (
                    "OUTSTANDING",
                    "SELECT COALESCE(SUM(d.amount),0)-COALESCE((SELECT SUM(amount) FROM debt_payments),0) FROM debt d",
                    "Approx. outstanding balance",
                    "@warning@",
                    "!",
                ),
            ],
            "Financial Reports": [
                (
                    "PROJECTS",
                    "SELECT COUNT(*) FROM projects",
                    "Reporting scope",
                    "@info@",
                    "P",
                ),
                (
                    "EXPENSES",
                    "SELECT COALESCE(SUM(amount),0) FROM expenses",
                    "Recorded cost",
                    "@danger@",
                    "EX",
                ),
                (
                    "RECEIVED",
                    "SELECT COALESCE(SUM(amount),0) FROM project_payments",
                    "Cash received",
                    "@success@",
                    "IN",
                ),
                (
                    "NET CASH",
                    "SELECT COALESCE((SELECT SUM(amount) FROM project_payments),0)-COALESCE((SELECT SUM(amount) FROM expense_payments),0)",
                    "Receipts less paid expenses",
                    "@primary@",
                    "₣",
                ),
            ],
            "Staff": [
                (
                    "ACTIVE STAFF",
                    "SELECT COUNT(*) FROM staff WHERE status='Active'",
                    "Current workforce",
                    "@success@",
                    "ST",
                ),
                (
                    "ON SITE",
                    "SELECT COUNT(*) FROM staff WHERE attendance_type='On Site' AND status='Active'",
                    "Site workforce",
                    "@info@",
                    "OS",
                ),
                (
                    "ADMIN",
                    "SELECT COUNT(*) FROM staff WHERE attendance_type='Administration' AND status='Active'",
                    "Office workforce",
                    "@charts.series_3@",
                    "AD",
                ),
                (
                    "ASSIGNMENTS",
                    "SELECT COUNT(*) FROM staff_projects WHERE active=1",
                    "Active project assignments",
                    "@primary@",
                    "↔",
                ),
            ],
            "Payroll": [
                (
                    "PAYROLL RECORDS",
                    "SELECT COUNT(*) FROM payroll_records",
                    "Prepared payroll periods",
                    "@info@",
                    "PY",
                ),
                (
                    "NET PAYROLL",
                    "SELECT COALESCE(SUM(net_amount),0) FROM payroll_records",
                    "Net payroll value",
                    "@primary@",
                    "₣",
                ),
                (
                    "DRAFT",
                    "SELECT COUNT(*) FROM payroll_records WHERE status='Draft'",
                    "Draft payroll records",
                    "@warning@",
                    "D",
                ),
                (
                    "PAID",
                    "SELECT COUNT(*) FROM payroll_records WHERE status='Paid'",
                    "Marked paid",
                    "@success@",
                    "✓",
                ),
            ],
            "Vehicles": [
                (
                    "ACTIVE FLEET",
                    "SELECT COUNT(*) FROM vehicles WHERE status='Active'",
                    "Operational vehicles",
                    "@info@",
                    "VH",
                ),
                (
                    "MAINTENANCE",
                    "SELECT COALESCE(SUM(cost),0) FROM maintenance_records",
                    "Recorded maintenance cost",
                    "@danger@",
                    "M",
                ),
                (
                    "FUEL",
                    "SELECT COALESCE(SUM(total_cost),0) FROM fuel_records",
                    "Recorded fuel cost",
                    "@warning@",
                    "F",
                ),
                (
                    "FUEL LITRES",
                    "SELECT COALESCE(SUM(quantity),0) FROM fuel_records",
                    "Recorded fuel quantity",
                    "@charts.series_2@",
                    "L",
                ),
            ],
            "Documents": [
                (
                    "DOCUMENTS",
                    'SELECT (SELECT COUNT(*) FROM "company documents") + (SELECT COUNT(*) FROM "projects documents")',
                    "Central document registry",
                    "@info@",
                    "DC",
                ),
                (
                    "EXPIRED",
                    'SELECT (SELECT COUNT(*) FROM "company documents" WHERE "expiring date" IS NOT NULL AND "expiring date" < date(\'now\')) + (SELECT COUNT(*) FROM "projects documents" WHERE expiring_date IS NOT NULL AND expiring_date < date(\'now\'))',
                    "Past expiry date",
                    "@danger@",
                    "!",
                ),
                (
                    "NEXT 30 DAYS",
                    "SELECT (SELECT COUNT(*) FROM \"company documents\" WHERE \"expiring date\" BETWEEN date('now') AND date('now','+30 day')) + (SELECT COUNT(*) FROM \"projects documents\" WHERE expiring_date BETWEEN date('now') AND date('now','+30 day'))",
                    "Expiring soon",
                    "@warning@",
                    "30",
                ),
                (
                    "PROJECT DOCS",
                    'SELECT COUNT(*) FROM "projects documents"',
                    "Project-linked records",
                    "@primary@",
                    "P",
                ),
            ],
            "Company": [
                (
                    "PROJECTS",
                    "SELECT COUNT(*) FROM projects",
                    "Registered projects",
                    "@info@",
                    "P",
                ),
                (
                    "STAFF",
                    "SELECT COUNT(*) FROM staff",
                    "Personnel records",
                    "@success@",
                    "ST",
                ),
                (
                    "VEHICLES",
                    "SELECT COUNT(*) FROM vehicles",
                    "Fleet records",
                    "@primary@",
                    "VH",
                ),
                (
                    "DOCUMENTS",
                    'SELECT (SELECT COUNT(*) FROM "company documents") + (SELECT COUNT(*) FROM "projects documents")',
                    "Document records",
                    "@charts.series_3@",
                    "DC",
                ),
            ],
            "Settings": [
                (
                    "SETTINGS",
                    "SELECT COUNT(*) FROM settings",
                    "Stored application settings",
                    "@info@",
                    "⚙",
                ),
                (
                    "PROJECTS",
                    "SELECT COUNT(*) FROM projects",
                    "Data records affected by settings",
                    "@primary@",
                    "P",
                ),
                (
                    "AUDIT EVENTS",
                    "SELECT COUNT(*) FROM audit_log",
                    "Audit history",
                    "@charts.series_3@",
                    "LOG",
                ),
                (
                    "NOTIFICATIONS",
                    "SELECT COUNT(*) FROM notifications WHERE is_read=0",
                    "Unread system notices",
                    "@warning@",
                    "!",
                ),
            ],
            "Backup & Restore": [
                (
                    "DATABASE",
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'",
                    "SQLite tables available",
                    "@info@",
                    "DB",
                ),
                (
                    "AUDIT EVENTS",
                    "SELECT COUNT(*) FROM audit_log",
                    "Tracked operations",
                    "@charts.series_3@",
                    "LOG",
                ),
                (
                    "NOTIFICATIONS",
                    "SELECT COUNT(*) FROM notifications",
                    "Stored notifications",
                    "@warning@",
                    "!",
                ),
                (
                    "PROJECTS",
                    "SELECT COUNT(*) FROM projects",
                    "Records protected by backup",
                    "@success@",
                    "P",
                ),
            ],
        }
        spec = queries.get(title)
        if not spec:
            return
        conn = None
        try:
            conn = get_connection()
            for item in spec:
                try:
                    value = conn.execute(item[1]).fetchone()[0]
                except (sqlite3.Error, TypeError, ValueError):
                    value = 0
                is_money = any(
                    k in item[0]
                    for k in (
                        "VALUE",
                        "BUDGET",
                        "EXPENSE",
                        "RECEIVED",
                        "DEBT",
                        "PAID",
                        "AVERAGE",
                        "NET",
                        "PAYROLL",
                        "MAINTENANCE",
                        "FUEL",
                    )
                )
                display = (
                    money(value)
                    if is_money
                    else str(int(value or 0))
                    if float(value or 0).is_integer()
                    else f"{float(value or 0):,.2f}"
                )
                subtitle = item[2]
                self.add_kpi(item[0], display, subtitle, item[3], item[4])
        except (sqlite3.Error, TypeError, ValueError) as exc:
            # KPI creation must never prevent a page from loading.
            logger.warning("Could not build KPI cards for %s: %s", title, exc)
        finally:
            if conn is not None:
                conn.close()

# شرح الدالة add_kpi: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_kpi(
        self,
        title: str,
        value: str = "0",
        subtitle: str = "",
        accent: str = GOLD,
        icon: str = "•",
    ) -> KpiCard:
        card = KpiCard(title, value, subtitle, accent, icon)
        index = len(self._kpi_cards)
        self.kpi_layout.addWidget(card, index // 4, index % 4)
        self._kpi_cards.append(card)
        return card

# شرح الدالة clear_kpis: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def clear_kpis(self):
        for card in self._kpi_cards:
            self.kpi_layout.removeWidget(card)
            card.deleteLater()
        self._kpi_cards.clear()

# شرح الدالة refresh_kpis: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def refresh_kpis(self):
        """Rebuild the compact KPI cards from the current database values."""
        self.clear_kpis()
        self._build_live_kpis(self._live_kpi_title)

# شرح الدالة panel: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def panel(self, title: str | None = None, subtitle: str = "", accent: str = GOLD):
        if title:
            card = SectionCard(title, subtitle, accent)
            return card, card.root_layout

        card = QFrame()
        card.setObjectName("panel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(17, 15, 17, 17)
        layout.setSpacing(11)
        return card, layout

# شرح الدالة toolbar: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def toolbar(self, *widgets: QWidget) -> QFrame:
        frame = QFrame()
        frame.setObjectName("pageToolbar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(SPACE_SM)
        for widget in widgets:
            layout.addWidget(widget)
        layout.addStretch()
        return frame


# شرح الدالة _largest_table: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _largest_table(self):
        """Return the most populated QTableWidget on the current page."""
        from PySide6.QtWidgets import QTableWidget
        tables = self.findChildren(QTableWidget)
        if not tables:
            return None
        return max(tables, key=lambda t: max(t.rowCount(), 1) * max(t.columnCount(), 1))

# شرح الدالة show_smart_insights: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def show_smart_insights(self):
        """Show explainable portfolio insights derived from live operational data."""
        from services.analytics_service import smart_analytics
        try:
            data = smart_analytics()
            portfolio = data.get("portfolio", {})
            quality = data.get("data_quality", {})
            risks = data.get("risks", [])[:5]
            lines = [
                translate_text(data.get("generated_at", "")),
                "",
                f"{translate_text('Active projects')}: {portfolio.get('active_projects', 0)}",
                f"{translate_text('Portfolio budget')}: {money(portfolio.get('portfolio_budget', 0))}",
                f"{translate_text('Portfolio cost')}: {money(portfolio.get('portfolio_cost', 0))}",
                f"{translate_text('Portfolio CPI')}: {portfolio.get('portfolio_cpi', 0):.2f}",
                f"{translate_text('Receivable')}: {money(portfolio.get('receivable', 0))}",
                f"{translate_text('Data confidence')}: {data.get('data_confidence', 0):.0f}%",
                "",
                translate_text(portfolio.get("headline", "")),
            ]
            if risks:
                lines.append("")
                lines.append(translate_text("Priority actions"))
                lines.extend(f"• {r['project_name']}: {r['message']}" for r in risks)
            if any(quality.values()):
                lines.append("")
                lines.append(translate_text("Data quality issues detected. Review the affected records before relying on forecasts."))
            QMessageBox.information(self, translate_text("Smart construction insights"), "\n".join(lines))
        except (sqlite3.Error, TypeError, ValueError, KeyError) as exc:
            self.error(f"Could not build smart insights.\n\n{exc}")

# شرح الدالة show_data_health: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def show_data_health(self):
        """Run read-only database health and consistency checks."""
        from services.data_quality_service import database_health, diagnostics
        try:
            health = database_health()
            issues = diagnostics()
            lines = [
                f"{translate_text('SQLite integrity')}: {health.get('integrity')}",
                f"{translate_text('Foreign key errors')}: {health.get('foreign_key_errors', 0)}",
                f"{translate_text('Tables')}: {health.get('tables', 0)}",
                f"{translate_text('Foreign keys enabled')}: {health.get('foreign_keys', 0)}",
                f"{translate_text('Journal mode')}: {health.get('journal_mode')}",
            ]
            if issues:
                lines += ["", translate_text("Detected issues:")]
                lines += [f"• {item['check']}: {item['count']}" for item in issues]
            else:
                lines += ["", translate_text("No known consistency issues were detected.")]
            QMessageBox.information(self, translate_text("Database health check"), "\n".join(lines))
        except (sqlite3.Error, TypeError, ValueError) as exc:
            self.error(f"Could not check database health.\n\n{exc}")

# شرح الدالة refresh_page: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def refresh_page(self):
        """Invoke the conventional page refresh method without assumptions."""
        started = time.perf_counter()
        try:
            method = getattr(self, "refresh", None) or getattr(self, "load", None)
            if callable(method):
                method()
                self.page_status.setText(translate_text("LOCAL • REFRESHED"))
            else:
                self.page_status.setText(translate_text("LOCAL • READY"))
        except (
            AttributeError,
            RuntimeError,
            TypeError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            self.page_status.setText(translate_text("LOCAL • ERROR"))
            self.error(f"Could not refresh this page.\n\n{exc}")
        finally:
            if is_enabled():
                record_metric("page", (time.perf_counter() - started) * 1000.0)

# شرح الدالة success: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def success(self, message: str):
        self.page_status.setText(translate_text("LOCAL • SAVED"))
        QMessageBox.information(
            self, translate_text("BuildOffice Pro"), translate_text(message)
        )

# شرح الدالة error: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def error(self, message: str):
        self.page_status.setText(translate_text("LOCAL • ERROR"))
        QMessageBox.warning(
            self, translate_text("BuildOffice Pro"), translate_text(message)
        )

# شرح الدالة confirm: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def confirm(self, message: str, title: str = "Confirm") -> bool:
        return (
            QMessageBox.question(
                self,
                translate_text(title),
                translate_text(message),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )

# شرح الدالة set_busy: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def set_busy(self, busy: bool):
        self.setEnabled(not busy)
        self.setCursor(
            Qt.CursorShape.WaitCursor if busy else Qt.CursorShape.ArrowCursor
        )


__all__ = [
    "BLUE",
    "BORDER",
    "CYAN",
    "GOLD",
    "GOLD_LIGHT",
    "GREEN",
    "MUTED",
    "NAVY",
    "NAVY_2",
    "NAVY_3",
    "ORANGE",
    "PURPLE",
    "RED",
    "SURFACE",
    "SURFACE_2",
    "SURFACE_3",
    "TEAL",
    "TEXT",
    "WHITE",
    "BasePage",
    "KpiCard",
    "SectionCard",
    "configure_table",
    "db_transaction",
    "fill_table",
    "money",
    "next_id",
    "percent",
    "set_button",
]

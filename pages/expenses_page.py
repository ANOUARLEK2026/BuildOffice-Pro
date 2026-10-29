# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
# ============================================================
# شرح الملف: expenses_page.py
# يحتوي هذا الملف على جزء من وظائف وتفاصيل تطبيق BuildOffice Pro.
# التعليقات العربية هنا للتوضيح فقط ولا تغيّر منطق البرنامج.
# ============================================================
import sqlite3
from typing import ClassVar

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.analytics_hub import expense_datasets
from services.financial_service import get_expense_paid_amount
from services.settings_service import money_display
from theme import set_theme_style, theme_qcolor
from theme.metrics import (
    CONTROL_HEIGHT,
    SPACE_SM,
)

from .analytics_widgets import AnalyticsCard, AnalyticsChart
from .base_page import BasePage, KpiCard
from .id_service import next_sequence_id


class _ExpenseKpiCard(KpiCard):
    """Backward-compatible wrapper around the shared KPI component."""

    def __init__(self, title="", value="0", subtitle="", accent="@primary@"):
        super().__init__(title, value, subtitle, accent)
        self._title_label = self.findChild(QLabel, "kpiTitle")
        self._value_label = self.findChild(QLabel, "kpiValue")
        self._subtitle_label = self.findChild(QLabel, "kpiSubtitle")
        self._money = True


# هذا الصنف مسؤول عن جزء ExpensesPage من التطبيق.
class ExpensesPage(BasePage):

    # =========================================================
    # Constants
    # =========================================================

    CATEGORIES: ClassVar[list[str]] = [
        "Materials",
        "Equipment",
        "Transport",
        "Fuel",
        "Labor",
        "Maintenance",
        "Office",
        "Utilities",
        "Rent",
        "Services",
        "Taxes",
        "Other",
    ]

    PAYMENT_METHODS: ClassVar[list[str]] = [
        "Cash",
        "Bank Transfer",
        "Cheque",
        "Bank Card",
        "Other",
    ]

    # =========================================================
    # INIT
    # =========================================================

    # تهيئة الكائن وتجهيز الواجهة والبيانات اللازمة.
    def __init__(self):
        super().__init__(
            "Expenses",
            "Manage company expenses, project expenses and credit payments",
        )

        # Keep the page itself compact, but let its content grow vertically.
        # The page body becomes a scrollable canvas so the expense table is
        # never forced into a tiny viewport.
        self._setup_scrollable_content()

        self._loaded_once = False
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(180)
        self._search_timer.timeout.connect(self.load)

        self._build_summary()
        self._build_toolbar()
        self._build_visual_analytics()
        self._build_tables()

        QTimer.singleShot(0, self.load)

    # =========================================================
    # SCROLLABLE CONTENT
    # =========================================================

    # تنفيذ وظيفة _setup_scrollable_content ضمن هذا الجزء من البرنامج.
    def _setup_scrollable_content(self):
        # BasePage provides self.body as the layout attached to the page.
        # Keep that outer layout and place a scroll area inside it.
        outer_body = self.body

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("expensesScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.content = QWidget()
        self.content.setObjectName("expensesContent")
        self.content.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        self.body = QVBoxLayout(self.content)
        self.body.setContentsMargins(2, 2, 12, 20)
        self.body.setSpacing(10)
        self.body.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinAndMaxSize)

        self.scroll_area.setWidget(self.content)
        outer_body.addWidget(self.scroll_area)

        set_theme_style(self.content, 
            """
            QWidget#expensesContent {
                /* خلفية مساحة الصفحة مطابقة للـDashboard. */
                background: @background@;
            }

            QScrollArea#expensesScroll {
                border: none;
                background: transparent;
            }

            QScrollBar:vertical {
                width: 9px;
                margin: 2px 1px 2px 1px;
                background: transparent;
            }

            QScrollBar::handle:vertical {
                min-height: 45px;
                background: @surface_alt@;
                border-radius: 4px;
            }

            QScrollBar::handle:vertical:hover {
                background: @surface@;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
            """
        )

    # =========================================================
    # SUMMARY
    # =========================================================

    # تنفيذ وظيفة _build_summary ضمن هذا الجزء من البرنامج.
    def _build_summary(self):
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 2)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.total_expenses = self._kpi("TOTAL EXPENSES", money_display(0), "All recorded expenses", "gold")
        self.total_paid = self._kpi("TOTAL PAID", money_display(0), "Payments recorded", "green")
        self.total_outstanding = self._kpi("OUTSTANDING", money_display(0), "Amount still due", "red")
        self.expense_count = self._kpi("TOTAL RECORDS", "0", "Expense records", "blue", money=False)
        self.project_expenses = self._kpi("PROJECT EXPENSES", money_display(0), "Assigned to projects", "purple", primary=False)
        self.general_expenses = self._kpi("GENERAL EXPENSES", money_display(0), "Company expenses", "teal", primary=False)
        self.month_expenses = self._kpi("THIS MONTH", money_display(0), "Current month", "cyan", primary=False)
        self.credit_count = self._kpi("CREDIT RECORDS", "0", "Unpaid or partial", "navy", money=False, primary=False)

        cards = [
            self.total_expenses, self.total_paid, self.total_outstanding, self.expense_count,
            self.project_expenses, self.general_expenses, self.month_expenses, self.credit_count,
        ]
        for i, card in enumerate(cards):
            grid.addWidget(card, i // 4, i % 4)

        self.body.addLayout(grid)
        self._apply_kpi_style()

    # تنفيذ وظيفة _kpi ضمن هذا الجزء من البرنامج.
    def _kpi(self, title, value, subtitle="", accent="navy", money=True, primary=True):
        accent_map = {
            "gold": "@gold@", "green": "@success@", "red": "@danger@",
            "blue": "@info@", "purple": "@charts.series_3@",
            "teal": "@charts.series_2@", "cyan": "@charts.series_7@",
            "navy": "@components.navigation.navigation_deep@",
        }
        card = _ExpenseKpiCard(title, value, subtitle, accent_map.get(accent, "@primary@"))
        card._money = money
        card.setProperty("kpiVariant", "primary" if primary else "secondary")
        return card

    # تنفيذ وظيفة _set_kpi ضمن هذا الجزء من البرنامج.
    def _set_kpi(self, card, value, subtitle=None):
        card._value_label.setText(
            money_display(value) if card._money else str(value or 0)
        )
        if subtitle is not None:
            card._subtitle_label.setText(translate_text(subtitle))

    # تنفيذ وظيفة _apply_kpi_style ضمن هذا الجزء من البرنامج.
    def _apply_kpi_style(self):
        """Keep legacy call compatibility; KPI appearance is now centrally themed."""
        for card in (
            self.total_expenses, self.total_paid, self.total_outstanding, self.expense_count,
            self.project_expenses, self.general_expenses, self.month_expenses, self.credit_count,
        ):
            card.setProperty("unified", True)
            card.style().unpolish(card)
            card.style().polish(card)

    def _build_toolbar(self):
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 3, 0, 3)
        bar.setSpacing(SPACE_SM)

        self.search = QLineEdit()
        self.search.setPlaceholderText(translate_text("Search by ID, project, description or category..."))
        self.search.setFixedHeight(CONTROL_HEIGHT)
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._schedule_search_load)

        self.project_filter = LocalizedComboBox()
        self.project_filter.setFixedHeight(CONTROL_HEIGHT)
        self.project_filter.setMinimumWidth(185)
        # Keep the broad "All Projects" option available, but do not use it
        # as the initial view. Loading every expense at startup can be costly
        # on larger databases, so the page opens on one project only.
        self.project_filter.addItem(translate_text("All Projects"), "__ALL__")
        self.project_filter.addItem(translate_text("General Company Expenses"), "__GENERAL__")
        self._load_project_filter()
        self.project_filter.currentIndexChanged.connect(self._filter_changed)

        self.status_filter = LocalizedComboBox()
        self.status_filter.setFixedHeight(CONTROL_HEIGHT)
        self.status_filter.setMinimumWidth(120)
        self.status_filter.addItems([translate_text("All Status"), translate_text("Paid"), translate_text("Partial"), translate_text("Unpaid")])
        self.status_filter.currentIndexChanged.connect(self._filter_changed)

        add_button = QPushButton(translate_text("+  Add Expense"))
        add_button.setObjectName("primaryButton")
        add_button.setFixedHeight(CONTROL_HEIGHT)
        add_button.clicked.connect(self.add_expense)

        self.delete_button = QPushButton(translate_text("Delete"))
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.setFixedHeight(CONTROL_HEIGHT)
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.delete_expense)

        self.edit_button = QPushButton(translate_text("Edit"))
        self.edit_button.setFixedHeight(CONTROL_HEIGHT)
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.edit_expense)

        self.details_button = QPushButton(translate_text("View Details"))
        self.details_button.setFixedHeight(CONTROL_HEIGHT)
        self.details_button.setEnabled(False)
        self.details_button.clicked.connect(self.edit_expense)

        refresh_button = QPushButton(translate_text("Refresh"))
        refresh_button.setFixedHeight(CONTROL_HEIGHT)
        refresh_button.clicked.connect(self.load)

        bar.addWidget(self.search, 1)
        bar.addWidget(self.project_filter)
        bar.addWidget(self.status_filter)
        bar.addWidget(add_button)
        bar.addWidget(self.delete_button)
        bar.addWidget(self.edit_button)
        bar.addWidget(self.details_button)
        bar.addWidget(refresh_button)
        self.body.addLayout(bar)

    # تنفيذ وظيفة _load_project_filter ضمن هذا الجزء من البرنامج.
    def _load_project_filter(self):
        conn = get_connection()
        try:
            projects = conn.execute(
                "SELECT project_id, project_name FROM projects ORDER BY project_name"
            ).fetchall()

            # Default to a single project instead of loading every project's
            # expenses on startup. Prefer the most recently created project,
            # while keeping the existing project list and filter values intact.
            default_project_id = None
            if projects:
                default_row = conn.execute(
                    """
                    SELECT project_id
                    FROM projects
                    ORDER BY datetime(COALESCE(created_at, '1970-01-01')) DESC, project_id DESC
                    LIMIT 1
                    """
                ).fetchone()
                if default_row:
                    default_project_id = default_row["project_id"]
        finally:
            conn.close()

        for row in projects:
            self.project_filter.addItem(row["project_name"], row["project_id"])

        if default_project_id:
            default_index = self.project_filter.findData(default_project_id)
            if default_index >= 0:
                self.project_filter.setCurrentIndex(default_index)

    # تنفيذ وظيفة _filter_changed ضمن هذا الجزء من البرنامج.
    def _filter_changed(self):
        self.load()

    # =========================================================
    # PROJECT SUMMARY + EXPENSE TABLE
    # =========================================================

    # تنفيذ وظيفة _build_tables ضمن هذا الجزء من البرنامج.
    def _build_tables(self):
        """Build the main expense table only.

        Project-level totals are intentionally not duplicated here.
        The project filter is sufficient for this page; project financial
        totals are presented in project/dashboard views.
        """
        # Current selection summary
        self.context_frame = QFrame()
        self.context_frame.setObjectName("expenseContext")
        context = QHBoxLayout(self.context_frame)
        context.setContentsMargins(12, 7, 12, 7)
        context.setSpacing(18)

        self.context_title = QLabel(translate_text("ALL EXPENSES"))
        self.context_title.setObjectName("contextTitle")
        self.context_total = QLabel(translate_text(f"Total: {money_display(0)}"))
        self.context_paid = QLabel(translate_text(f"Paid: {money_display(0)}"))
        self.context_due = QLabel(translate_text(f"Outstanding: {money_display(0)}"))
        self.context_records = QLabel(translate_text("0 records"))
        for label in (self.context_total, self.context_paid, self.context_due, self.context_records):
            label.setObjectName("contextValue")

        context.addWidget(self.context_title)
        context.addStretch()
        context.addWidget(self.context_total)
        context.addWidget(self.context_paid)
        context.addWidget(self.context_due)
        context.addWidget(self.context_records)
        self.body.addWidget(self.context_frame)

        # جدول المصروفات الرئيسي.
        self.expense_table = self._create_table()
        self.expense_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.expense_table.setMinimumHeight(560)
        self.expense_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.body.addWidget(self.expense_table)

        # تطبيق تنسيق الملخص وعناصر التصفية على عناصرها مباشرة للحفاظ على السمة الحالية.
        set_theme_style(self.context_frame, 
            """
            QFrame#expenseContext {
                background: @surface@;
                border: 1px solid @divider@;
                border-radius: 10px;
            }
            QLabel#contextTitle {
                color: @text_primary@;
                font-size: __FONT_SIZE_BODY__px;
                font-weight: 700;
                background: transparent;
            }
            QLabel#contextValue {
                color: @text_secondary@;
                font-size: 11px;
                font-weight: 600;
                background: transparent;
            }
            """
        )
        for control in (self.search, self.project_filter, self.status_filter):
            set_theme_style(control, 
                """
                QLineEdit, LocalizedComboBox {
                    border: 1px solid @components.buttons.button_border@;
                    border-radius: 8px;
                    padding: 0 10px;
                    background: @surface@;
                    color: @text_primary@;
                }
                QLineEdit:focus, LocalizedComboBox:focus {
                    border: 1px solid @primary@;
                }
                """
            )

    def _table_style(self):
        return """
            QTableWidget {
                border: none;
                background: @surface@;
                alternate-background-color: @surface_alt@;
                selection-background-color: @selection_background@;
                selection-color: @selection_text@;
                outline: none;
            }
            QTableWidget::item {
                padding: 7px 8px;
                border-bottom: 1px solid @divider@;
            }
            QTableWidget::item:selected {
                background: @selection_background@;
                color: @selection_text@;
            }
            QHeaderView {
                background: @tables.header_background@;
            }
            QHeaderView::section {
                background: @tables.header_background@;
                color: @selection_text@;
                padding: 9px 8px;
                border: none;
                border-right: 1px solid @tables.border@;
                font-size: 11px;
                font-weight: 700;
            }
        """

    # تنفيذ وظيفة _create_table ضمن هذا الجزء من البرنامج.
    def _create_table(self):
        table = QTableWidget(0, 11)
        table.setHorizontalHeaderLabels([
            translate_text("Expense ID"), translate_text("Project"), translate_text("Date"), translate_text("Description"),
            translate_text("Category"), translate_text("Quantity"), translate_text("Unit"),
            translate_text("Unit Price"), translate_text("Amount"), translate_text("Paid"), translate_text("Outstanding"),
        ])
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setSortingEnabled(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(40)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.ResizeToContents)
        set_theme_style(table, self._table_style())
        table.itemSelectionChanged.connect(self._selection_changed)
        table.cellDoubleClicked.connect(lambda r, c: self.edit_expense())
        return table

    # تنفيذ وظيفة _project_summary_clicked ضمن هذا الجزء من البرنامج.
    def _selected_filter_label(self):
        data = self.project_filter.currentData()
        if data == "__GENERAL__":
            return "GENERAL COMPANY EXPENSES"
        if data == "__ALL__":
            return "ALL EXPENSES"
        return str(self.project_filter.currentText()).upper()

    # تنفيذ وظيفة _selection_changed ضمن هذا الجزء من البرنامج.
    def _selection_changed(self):
        selected = self.expense_table.currentRow() >= 0
        self.edit_button.setEnabled(selected)
        self.details_button.setEnabled(selected)
        self.delete_button.setEnabled(selected)

    # =========================================================
    # VISUAL ANALYTICS
    # =========================================================

    def _build_visual_analytics(self):
        """Create compact live charts for expense composition and trend."""
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 2)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.category_chart_card = AnalyticsCard(
            "Expense composition",
            "Top expense categories"
        )
        self.category_chart = AnalyticsChart("donut", [], interaction_hint="Click a category to filter expenses")
        self.category_chart.clicked.connect(self._on_category_chart_clicked)
        self.category_chart_card.add_chart(self.category_chart)

        self.month_chart_card = AnalyticsCard(
            "Expense trend",
            "Recorded monthly expenses"
        )
        self.month_chart = AnalyticsChart("line", [], interaction_hint="Click a month to filter expenses")
        self.month_chart.clicked.connect(self._on_month_chart_clicked)
        self.month_chart_card.add_chart(self.month_chart)

        grid.addWidget(self.category_chart_card, 0, 0)
        grid.addWidget(self.month_chart_card, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.body.addLayout(grid)

    def _refresh_visual_analytics(self, conn):
        """Refresh chart datasets without changing the transactional table."""
        data = expense_datasets(conn, limit=6)
        self.category_chart.rows = data["categories"]
        self.month_chart.rows = data["monthly"]
        self.category_chart.update()
        self.month_chart.update()

    def _on_category_chart_clicked(self, label, _value):
        """Apply an exact category filter from the analytics chart."""
        self._analytics_category = str(label)
        self._analytics_month = None
        self.load()

    def _on_month_chart_clicked(self, label, _value):
        """Apply an exact month filter from the analytics chart."""
        self._analytics_month = str(label)
        self._analytics_category = None
        self.load()

    # =========================================================
    # SHOW
    # =========================================================

    # تنفيذ وظيفة showEvent ضمن هذا الجزء من البرنامج.
    def showEvent(self, event):
        super().showEvent(event)
        if not self._loaded_once:
            self._schedule_search_load()

    # =========================================================
    # LOAD
    # =========================================================

    def _schedule_search_load(self):
        """Debounce text filtering so rapid typing never queues many DB reads."""
        self._search_timer.start()

    def _analytics_filters(self):
        """Return exact filters selected from analytics interactions."""
        return (
            getattr(self, "_analytics_category", None),
            getattr(self, "_analytics_month", None),
        )

    def clear_analytics_filters(self):
        """Clear chart-driven filters and reload the expense table."""
        self._analytics_category = None
        self._analytics_month = None
        self.load()

    def load(self):
        self._loaded_once = True
        conn = get_connection()
        try:
            query = self.search.text().strip()
            project_filter = self.project_filter.currentData() if hasattr(self, "project_filter") else "__ALL__"
            status_filter = self.status_filter.currentText() if hasattr(self, "status_filter") else "All Status"

            sql = """
                SELECT e.expense_id, e.project_id, e.date, e.description,
                       e.category, e.quantity, e.unit, e.unit_price, e.amount, e.payment_method,
                       COALESCE(p.paid, 0) AS paid
                FROM expenses e
                LEFT JOIN (
                    SELECT expense_id, SUM(amount) AS paid
                    FROM expense_payments
                    GROUP BY expense_id
                ) p ON p.expense_id = e.expense_id
            """
            conditions = []
            args = []

            if query:
                conditions.append("""
                    (CAST(e.expense_id AS TEXT) LIKE ?
                    OR COALESCE(e.project_id, '') LIKE ?
                    OR e.description LIKE ?
                    OR COALESCE(e.category, '') LIKE ?)
                """)
                args.extend([f"%{query}%"] * 4)

            analytics_category, analytics_month = self._analytics_filters()
            if analytics_category:
                conditions.append("COALESCE(e.category, 'Uncategorized') = ?")
                args.append(analytics_category)
            if analytics_month:
                conditions.append("substr(e.date, 1, 7) = ?")
                args.append(analytics_month)

            if project_filter == "__GENERAL__":
                conditions.append("e.project_id IS NULL")
            elif project_filter != "__ALL__" and project_filter:
                conditions.append("e.project_id = ?")
                args.append(project_filter)

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

            sql += " ORDER BY e.date DESC, e.expense_id DESC"
            rows = conn.execute(sql, args).fetchall()

            display_rows = []
            for row in rows:
                total = float(row["amount"] or 0)
                paid = float(row["paid"] or 0)
                outstanding = max(0, total - paid)

                if status_filter == "Paid" and outstanding > 0:
                    continue
                if status_filter == "Unpaid" and paid > 0:
                    continue
                if status_filter == "Partial" and not (paid > 0 and outstanding > 0):
                    continue

                display_rows.append({
                    "expense_id": row["expense_id"],
                    "project_id": row["project_id"],
                    "project": row["project_id"] or "General",
                    "date": row["date"],
                    "description": row["description"],
                    "category": row["category"] or "-",
                    "quantity": float(row["quantity"] or 0),
                    "unit": row["unit"] or "-",
                    "unit_price": float(row["unit_price"] or 0),
                    "amount": total,
                    "paid": paid,
                    "outstanding": outstanding,
                })

            self._fill_table(self.expense_table, display_rows)
            self._update_summary(conn, rows)
            self._update_context(display_rows)
            self._refresh_visual_analytics(conn)

        finally:
            conn.close()

    # تنفيذ وظيفة _fill_table ضمن هذا الجزء من البرنامج.
    def _fill_table(self, table, rows):
        updates = table.updatesEnabled()
        sorting = table.isSortingEnabled()
        table.setUpdatesEnabled(False)
        table.blockSignals(True)
        table.setSortingEnabled(False)
        try:
            table.clearContents()
            table.setRowCount(len(rows))

            # الصفحة قابلة للتمرير عموديًا، لذلك يتمدد الجدول مع البيانات دون شريط تمرير داخلي إضافي.
            if table is self.expense_table:
                row_height = table.verticalHeader().defaultSectionSize()
                header_height = table.horizontalHeader().height()
                frame_height = table.frameWidth() * 2 + 8
                desired_height = header_height + (len(rows) * row_height) + frame_height
                table.setMinimumHeight(560)
                table.setFixedHeight(max(560, desired_height))

            for i, row in enumerate(rows):
                values = [
                    row["expense_id"], row["project"], row["date"], row["description"],
                    row["category"], f'{row["quantity"]:.3f}'.rstrip("0").rstrip("."),
                    row["unit"], money_display(row["unit_price"]), money_display(row["amount"]),
                    money_display(row["paid"]), money_display(row["outstanding"]),
                ]
                for j, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    if j == 0:
                        item.setData(Qt.ItemDataRole.UserRole, row["expense_id"])
                    if j in (0, 2, 5, 6, 7, 8, 9, 10):
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if j == 10 and row["outstanding"] > 0:
                        item.setForeground(theme_qcolor("@danger@"))
                    if j == 9 and row["paid"] > 0:
                        item.setForeground(theme_qcolor("@success@"))
                    table.setItem(i, j, item)
        finally:
            table.blockSignals(False)
            table.setSortingEnabled(sorting)
            table.setUpdatesEnabled(updates)

    # تنفيذ وظيفة _update_context ضمن هذا الجزء من البرنامج.
    def _update_context(self, rows):
        total = sum(r["amount"] for r in rows)
        paid = sum(min(r["paid"], r["amount"]) for r in rows)
        due = sum(r["outstanding"] for r in rows)
        self.context_title.setText(self._selected_filter_label())
        self.context_total.setText(translate_text(f"Total: {money_display(total)}"))
        self.context_paid.setText(translate_text(f"Paid: {money_display(paid)}"))
        self.context_due.setText(translate_text(f"Outstanding: {money_display(due)}"))
        self.context_records.setText(translate_text(f"{len(rows)} records"))

    # تنفيذ وظيفة _update_project_summary ضمن هذا الجزء من البرنامج.
    def _update_summary(self, conn, rows):
        total = 0
        project_total = 0
        general_total = 0
        paid_total = 0
        outstanding_total = 0
        credit_records = 0

        for row in rows:
            amount = float(row["amount"] or 0)
            paid = float(row["paid"] or 0)
            outstanding = max(0, amount - paid)
            total += amount
            paid_total += min(paid, amount)
            outstanding_total += outstanding
            if outstanding > 0:
                credit_records += 1
            if row["project_id"]:
                project_total += amount
            else:
                general_total += amount

        month_row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE substr(date, 1, 7) = ?",
            (QDate.currentDate().toString("yyyy-MM"),),
        ).fetchone()
        month_total = float(month_row["total"] or 0)

        self._set_kpi(self.total_expenses, total)
        self._set_kpi(self.total_paid, paid_total)
        self._set_kpi(self.total_outstanding, outstanding_total)
        self._set_kpi(self.credit_count, credit_records)
        self._set_kpi(self.project_expenses, project_total)
        self._set_kpi(self.general_expenses, general_total)
        self._set_kpi(self.month_expenses, month_total)
        self._set_kpi(self.expense_count, len(rows))

    # =========================================================
    # ADD
    # =========================================================

    # إضافة سجل جديد إلى النظام.
    def add_expense(self):
        self._expense_dialog()

    # =========================================================
    # EDIT / DETAILS
    # =========================================================

    # تنفيذ وظيفة _get_selected_expense_id ضمن هذا الجزء من البرنامج.
    def _get_selected_expense_id(self):
        row = self.expense_table.currentRow()
        if row < 0:
            return None

        item = self.expense_table.item(row, 0)
        if not item:
            return None

        expense_id = item.data(Qt.ItemDataRole.UserRole)
        return str(expense_id) if expense_id else None

    # تعديل السجل المحدد وفتح بياناته للتحرير.
    def edit_expense(self):

        expense_id = (
            self._get_selected_expense_id()
        )

        if not expense_id:
            return

        self._expense_details(
            expense_id
        )

    # حذف السجل المحدد بعد التحقق من الاختيار.
    def delete_expense(self):
        # حذف المصروف وسجل دفعاته المرتبطة.
        expense_id = self._get_selected_expense_id()
        if not expense_id:
            self.error("Select an expense first.")
            return

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT expense_id, description, amount FROM expenses WHERE expense_id = ?",
                (expense_id,),
            ).fetchone()
            if not row:
                self.error("Expense not found.")
                return

            paid = float(get_expense_paid_amount(expense_id) or 0)
            desc = row["description"] or "No description"
            message = (
                f"Delete expense {expense_id}?\n\n"
                f"Description: {desc}\n"
                f"Amount: {money_display(row["amount"])}\n"
                f"Recorded payments: {money_display(paid)}\n\n"
                "This will permanently delete the expense and its payment history."
            )
            if not self.confirm(message, "Delete expense"):
                return

            conn.execute("BEGIN")
            # حذف الدفعات أولًا لتفادي قيود المفتاح الأجنبي.
            try:
                conn.execute(
                    "DELETE FROM expense_payments WHERE expense_id = ?",
                    (expense_id,),
                )
            except sqlite3.OperationalError:
                pass
            conn.execute("DELETE FROM expenses WHERE expense_id = ?", (expense_id,))
            conn.commit()

        except sqlite3.IntegrityError as e:
            conn.rollback()
            self.error(
                "Cannot delete this expense because another record references it.\n\n"
                f"{e}\n\nNo data was deleted."
            )
            return
        except sqlite3.Error as e:
            conn.rollback()
            self.error(f"Could not delete expense.\n\n{e}\n\nNo data was deleted.")
            return
        finally:
            conn.close()

        self.load()

    # =========================================================
    # NEXT EXPENSE ID
    # =========================================================

    # تنفيذ وظيفة _next_expense_id ضمن هذا الجزء من البرنامج.
    def _next_expense_id(
        self,
        conn,
        project_id,
    ):
        scope = project_id or "gen"
        prefix = f"exp-{project_id}" if project_id else "exp-gen"
        return next_sequence_id(conn, prefix, scope=scope, digits=3)

    # =========================================================
    # EXPENSE DIALOG
    # =========================================================

    # تنفيذ وظيفة _expense_dialog ضمن هذا الجزء من البرنامج.
    def _expense_dialog(self, expense_id=None):
        # تفويض نافذة المصروفات إلى وحدة مستقلة مع إبقاء نفس واجهة الصفحة.
        from .expense_dialogs import _expense_dialog
        return _expense_dialog(self, expense_id)

    # =========================================================
    # EXPENSE DETAILS
    # =========================================================

    # تنفيذ وظيفة _expense_details ضمن هذا الجزء من البرنامج.
    def _expense_details(self, expense_id):
        # تفويض نافذة التفاصيل إلى وحدة مستقلة دون تغيير سلوك الصفحة.
        from .expense_dialogs import _expense_details
        return _expense_details(self, expense_id)

    # =========================================================
    # DETAIL CARD
    # =========================================================

    # تنفيذ وظيفة _detail_card ضمن هذا الجزء من البرنامج.
    def _detail_card(
        self,
        title,
        value,
    ):

        card = QFrame()

        set_theme_style(card, 
            """
            QFrame {
                background: @surface@;
                border: 1px solid @border@;
                border-radius: 8px;
            }
            """
        )

        layout = QVBoxLayout(card)

        title_label = QLabel(
            title
        )

        set_theme_style(title_label, 
            """
            font-size: 11px;
            font-weight: 600;
            color: @text_muted@;
            """
        )

        value_label = QLabel(
            value
        )

        set_theme_style(value_label, 
            """
            font-size: 16px;
            font-weight: 700;
            color: @text_primary@;
            """
        )

        layout.addWidget(
            title_label
        )

        layout.addWidget(
            value_label
        )

        return card

    # =========================================================
    # RECORD PAYMENT
    # =========================================================

    # تنفيذ وظيفة _record_payment_dialog ضمن هذا الجزء من البرنامج.
    def _record_payment_dialog(self, expense_id):
        # تفويض نافذة تسجيل الدفعة إلى وحدة مستقلة دون تغيير سلوك الصفحة.
        from .expense_dialogs import _record_payment_dialog
        return _record_payment_dialog(self, expense_id)

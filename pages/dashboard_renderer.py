# ============================================================
# شرح الملف: pages/dashboard_renderer.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""باني واجهة لوحة التحكم من بيانات جاهزة."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout

from core.i18n import translate_text
from theme import set_theme_style
from theme.metrics import (
    FONT_SIZE_BODY,
    FONT_SIZE_HEADING,
    FONT_SIZE_SMALL,
    FONT_SIZE_SUBTITLE,
    FONT_SIZE_TINY,
    FONT_SIZE_TITLE,
    SPACE_XL,
    SPACE_XS,
)

from .base_page import money
from .dashboard_style import (
    AMBER,
    BLUE,
    BORDER,
    EMERALD,
    GOLD,
    GOLD_LIGHT,
    GREEN,
    MUTED,
    NAVY,
    ORANGE,
    PURPLE,
    RED,
    SURFACE,
    TEAL,
    TEXT,
)


# شرح الدالة render_dashboard: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def render_dashboard(page, data, today, month_name):
    page._clear_layout(page.main_layout)

    # =================================================
    # رأس اللوحة التنفيذية
    # =================================================

    header = QFrame()
    header.setObjectName("executiveHeader")
    set_theme_style(header, 
        f"""
        QFrame#executiveHeader {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 15px;
        }}
        """
    )

    header_layout = QHBoxLayout(header)
    header_layout.setContentsMargins(SPACE_XL, 19, SPACE_XL, 19)
    header_layout.setSpacing(20)

    # اسم البرنامج الواضح
    title_box = QVBoxLayout()
    title_box.setSpacing(SPACE_XS)

    brand_row = QHBoxLayout()
    brand_row.setSpacing(10)

    brand_mark = QLabel(translate_text("BO"))
    brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
    brand_mark.setFixedSize(42, 42)
    set_theme_style(brand_mark, 
        f"""
        QLabel {{
            background: {NAVY};
            color: {GOLD_LIGHT};
            border-radius: 10px;
            font-size: {FONT_SIZE_HEADING}px;
            font-weight: 700;
        }}
        """
    )

    brand_row.addWidget(brand_mark)
    brand_row.addWidget(
        page.label(translate_text("BUILD OFFICE PRO"), FONT_SIZE_TITLE, True, TEXT)
    )
    brand_row.addStretch()

    title_box.addLayout(brand_row)
    title_box.addWidget(
        page.label(
            translate_text("Construction Management System  •  Executive Dashboard"),
            FONT_SIZE_BODY,
            False,
            MUTED,
        )
    )

    header_layout.addLayout(title_box, 1)

    # التاريخ وحالة النظام
    date_box = QVBoxLayout()
    date_box.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    date_box.setSpacing(SPACE_XS)

    date_box.addWidget(
        page.label(
            translate_text(today.toString("dddd, dd MMMM yyyy")),
            11,
            True,
            NAVY,
        ),
        alignment=Qt.AlignmentFlag.AlignRight,
    )
    date_box.addWidget(
        page.label(
            translate_text("OFFICE OVERVIEW"),
            8,
            True,
            GOLD,
        ),
        alignment=Qt.AlignmentFlag.AlignRight,
    )

    header_layout.addLayout(date_box)

    page.main_layout.addWidget(header)

    # =================================================
    # شريط المؤشرات الرئيسية
    # =================================================

    kpi_grid = QGridLayout()
    kpi_grid.setHorizontalSpacing(14)
    kpi_grid.setVerticalSpacing(14)

    kpis = [
        (
            "Active Projects",
            str(data["active_projects"]),
            f"{data['projects']} total projects",
            BLUE,
            "P",
        ),
        (
            "Active Staff",
            str(data["active_staff"]),
            f"{data['staff']} registered staff",
            GREEN,
            "S",
        ),
        (
            "Active Vehicles",
            str(data["vehicles"]),
            "Fleet currently active",
            GOLD,
            "V",
        ),
        (
            "Documents",
            str(data["documents"]),
            "Administrative records",
            NAVY,
            "D",
        ),
        (
            "Outstanding Debts",
            str(data["debts_count"]),
            money(data["debts_value"]) if data["debts_count"] else "No debt data",
            RED,
            "$",
        ),
        (
            "Present Today",
            str(data["present_today"]),
            f"{data['attendance_month']} monthly records",
            GREEN,
            "✓",
        ),
    ]

    for index, metric in enumerate(kpis):
        row = index // 3
        col = index % 3
        kpi_grid.addWidget(
            page.metric_card(*metric),
            row,
            col,
        )

    for col in range(3):
        kpi_grid.setColumnStretch(col, 1)

    page.main_layout.addLayout(kpi_grid)

    # =================================================
    # المركز المالي
    # =================================================

    finance_frame, finance_layout = page.section(
        "Financial Command Center",
        "High-level financial position. Project-linked and general expenses are shown separately.",
    )

    finance_grid = QGridLayout()
    finance_grid.setHorizontalSpacing(10)
    finance_grid.setVerticalSpacing(10)

    financial_items = [
        ("Total Budget HT", money(data["budget"]), GOLD, "Approved project budgets"),
        ("Project Profit", money(data["project_profit"]), EMERALD, "Budget HT minus project expenses"),
        ("Total Expenses", money(data["expenses"]), RED, "All recorded expenses"),
        ("Received Income", money(data["received_income"]), TEAL, "Client/project receipts"),
        ("Cash Outflow This Month", money(data["month_cash_outflow"]), ORANGE, "Actual expense payments"),
        ("Remaining Budget", money(data["remaining_budget"]), AMBER, "Budget minus expenses"),
        ("Project Expenses", money(data["project_expenses"]), BLUE, "Linked to a project"),
        ("General Expenses", money(data["general_expenses"]), PURPLE, "Not linked to a project"),
    ]

    for index, (title, value, color, caption) in enumerate(financial_items):
        finance_grid.addWidget(
            page.small_metric(title, value, color, caption),
            index // 3,
            index % 3,
        )

    for col in range(3):
        finance_grid.setColumnStretch(col, 1)

    finance_layout.addLayout(finance_grid)

    progress_row = QHBoxLayout()
    progress_row.setSpacing(10)
    progress_row.addWidget(
        page.label(translate_text("Budget consumption"), FONT_SIZE_BODY, True, TEXT)
    )
    progress_row.addStretch()
    progress_row.addWidget(
        page.label(f"{data['budget_usage']:.1f}%", FONT_SIZE_BODY, True, GOLD)
    )
    finance_layout.addLayout(progress_row)
    finance_layout.addWidget(page.progress(data["budget_usage"], GOLD))

    coverage_row = QHBoxLayout()
    coverage_row.addWidget(
        page.label(translate_text("Revenue / Budget coverage"), FONT_SIZE_SMALL, False, MUTED)
    )
    coverage_row.addStretch()
    coverage_row.addWidget(
        page.label(f"{data['profit_margin']:.1f}%", FONT_SIZE_SMALL, True, GREEN)
    )
    finance_layout.addLayout(coverage_row)

    page.main_layout.addWidget(finance_frame)

    # =================================================
    # العمليات: المشاريع والحضور
    # =================================================

    operations_grid = QGridLayout()
    operations_grid.setHorizontalSpacing(16)
    operations_grid.setVerticalSpacing(16)

    # -------------------------------------------------
    # محفظة المشاريع
    # -------------------------------------------------

    project_frame, project_layout = page.section(
        "Project Portfolio",
        "Projects ranked by budget with current expenditure and remaining capacity.",
    )

    project_table = page.make_table(
        [
            "Project",
            "Status",
            "Budget HT",
            "Expenses",
            "Remaining",
        ],
        minimum_height=190,
    )

    project_rows = data["project_rows"]

    for row in project_rows:
        project_budget = float(row[2] or 0)
        project_spent = float(row[3] or 0)
        project_remaining = project_budget - project_spent

        page.add_table_row(
            project_table,
            [
                row[0],
                row[1],
                money(project_budget),
                money(project_spent),
                money(project_remaining),
            ],
            [
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                Qt.AlignmentFlag.AlignCenter,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            ],
        )

    page.configure_table(
        project_table,
        stretch_columns=[0],
        compact_columns=[1, 2, 3, 4],
    )

    project_layout.addWidget(project_table)
    operations_grid.addWidget(project_frame, 0, 0)

    # -------------------------------------------------
    # ملخص الحضور
    # -------------------------------------------------

    attendance_frame, attendance_layout = page.section(
        "Workforce Attendance",
        f"Attendance and working-time indicators for {month_name}.",
    )

    attendance_grid = QGridLayout()
    attendance_grid.setHorizontalSpacing(9)
    attendance_grid.setVerticalSpacing(9)

    attendance_items = [
        ("Present", str(data["present_month"]), GREEN),
        ("Absent", str(data["absent_month"]), RED),
        ("Leave", str(data["leave_month"]), ORANGE),
        ("Sick", str(data["sick_month"]), RED),
        ("Hours", f"{data['hours_month']:,.1f}", TEXT),
        ("Overtime", f"{data['overtime_month']:,.1f}", GOLD),
    ]

    for index, (title, value, color) in enumerate(attendance_items):
        attendance_grid.addWidget(
            page.small_metric(title, value, color),
            index // 2,
            index % 2,
        )

    attendance_layout.addLayout(attendance_grid)

    rate_row = QHBoxLayout()
    rate_row.addWidget(
        page.label(translate_text("Monthly attendance indicator"), FONT_SIZE_BODY, True, TEXT)
    )
    rate_row.addStretch()
    rate_row.addWidget(
        page.label(f"{data['attendance_rate']:.1f}%", FONT_SIZE_SUBTITLE, True, GREEN)
    )
    attendance_layout.addLayout(rate_row)
    attendance_layout.addWidget(
        page.progress(data["attendance_rate"], GREEN)
    )

    attendance_layout.addWidget(
        page.label(
            translate_text("The indicator uses active staff and the number of days in the current month."),
            8,
            False,
            MUTED,
        )
    )

    operations_grid.addWidget(attendance_frame, 0, 1)

    operations_grid.setColumnStretch(0, 3)
    operations_grid.setColumnStretch(1, 2)

    page.main_layout.addLayout(operations_grid)

    # =================================================
    # ترتيب الموظفين
    # =================================================

    staff_frame, staff_layout = page.section(
        "Staff Attendance Ranking",
        "Active staff ranked by recorded presence and working hours.",
    )

    staff_table = page.make_table(
        [
            "Rank",
            "Worker",
            "Type",
            "Present",
            "Absent",
            "Hours",
            "Attendance",
        ],
        minimum_height=190,
    )

    staff_rows = data["staff_rows"]

    for index, row in enumerate(staff_rows, 1):
        present = int(row[2] or 0)
        absent = int(row[3] or 0)
        hours = float(row[4] or 0)
        recorded = present + absent
        percentage = present / recorded * 100 if recorded else 0

        page.add_table_row(
            staff_table,
            [
                index,
                row[0],
                row[1],
                present,
                absent,
                f"{hours:,.1f}",
                f"{percentage:.1f}%",
            ],
            [
                Qt.AlignmentFlag.AlignCenter,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                Qt.AlignmentFlag.AlignCenter,
                Qt.AlignmentFlag.AlignCenter,
                Qt.AlignmentFlag.AlignCenter,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            ],
        )

    page.configure_table(
        staff_table,
        stretch_columns=[1],
        compact_columns=[0, 2, 3, 4, 5, 6],
    )

    staff_layout.addWidget(staff_table)
    page.main_layout.addWidget(staff_frame)

    # =================================================
    # ملخص إداري
    # =================================================

    snapshot_frame, snapshot_layout = page.section(
        "Management Snapshot",
        "A compact view of the indicators that normally require opening several modules.",
    )

    snapshot_grid = QGridLayout()
    snapshot_grid.setHorizontalSpacing(12)
    snapshot_grid.setVerticalSpacing(12)

    snapshot_items = [
        (
            "Projects",
            f"{data['active_projects']} active",
            f"{data['completed_projects']} completed",
            BLUE,
        ),
        (
            "Workforce",
            f"{data['active_staff']} active",
            f"{data['present_today']} present today",
            GREEN,
        ),
        (
            "Fleet",
            f"{data['vehicles']} active",
            "Vehicle management",
            GOLD,
        ),
        (
            "Documents",
            f"{data['documents']} records",
            "Administrative records",
            NAVY,
        ),
        (
            "Debts",
            f"{data['debts_count']} records",
            money(data["debts_value"]) if data["debts_count"] else "No debt data",
            RED,
        ),
        (
            "Expenses",
            money(data["month_expenses"]),
            "Current month",
            ORANGE,
        ),
    ]

    for index, (title, value, detail, color) in enumerate(snapshot_items):
        box = QFrame()
        box.setMinimumHeight(91)
        box.setObjectName("snapshotMetric")
        set_theme_style(box, 
            f"""
            QFrame#snapshotMetric {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 11px;
            }}
            """
        )

        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(15, 12, 15, 12)
        box_layout.setSpacing(3)

        box_layout.addWidget(
            page.label(title.upper(), FONT_SIZE_TINY, True, MUTED)
        )
        box_layout.addWidget(
            page.label(value, FONT_SIZE_HEADING, True, color)
        )
        box_layout.addWidget(
            page.label(detail, FONT_SIZE_SMALL, False, MUTED)
        )

        snapshot_grid.addWidget(
            box,
            index // 3,
            index % 3,
        )

    for col in range(3):
        snapshot_grid.setColumnStretch(col, 1)

    snapshot_layout.addLayout(snapshot_grid)
    page.main_layout.addWidget(snapshot_frame)

    # =================================================
    # تنبيهات الإدارة
    # =================================================
    alerts_frame, alerts_layout = page.section(
        "Management Alerts",
        "Actionable data-quality and financial-control warnings.",
    )
    alert_counts = data["alert_counts"]
    expired = alert_counts["expired"]
    soon = alert_counts["soon"]
    overdue_expenses = alert_counts["overdue_expenses"]
    over_budget = alert_counts["over_budget"]
    missing_contract = alert_counts["missing_contract"]
    for title, count, severity in [
        ("Expired documents", expired, RED),
        ("Documents expiring within 30 days", soon, ORANGE),
        ("Overdue expenses", overdue_expenses, RED),
        ("Projects over budget", over_budget, RED),
        ("Projects without contract code", missing_contract, ORANGE),
    ]:
        row = QHBoxLayout()
        row.addWidget(page.label(title, FONT_SIZE_BODY, True, TEXT))
        row.addStretch()
        row.addWidget(page.label(str(count), FONT_SIZE_SUBTITLE, True, severity))
        alerts_layout.addLayout(row)
    page.main_layout.addWidget(alerts_frame)

    # =================================================
    # تذييل الصفحة
    # =================================================

    footer = QHBoxLayout()
    footer.setContentsMargins(4, 4, 4, 0)

    footer.addWidget(
        page.label(
            translate_text("BUILD OFFICE PRO"),
            9,
            True,
            NAVY,
        )
    )
    footer.addWidget(
        page.label(
            translate_text("  •  Construction Management System"),
            8,
            False,
            MUTED,
        )
    )
    footer.addStretch()
    footer.addWidget(
        page.label(
            f"Last refresh  •  {today.toString('dd/MM/yyyy')}",
            FONT_SIZE_TINY,
            False,
            MUTED,
        )
    )

    page.main_layout.addLayout(footer)



__all__=["render_dashboard"]

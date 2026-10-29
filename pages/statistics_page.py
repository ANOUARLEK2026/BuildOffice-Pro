# ============================================================
# شرح الملف: pages/statistics_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
from core.i18n import LocalizedComboBox, translate_text
from theme import set_theme_style, theme_qcolor
from theme.metrics import (
    CHART_FONT_POINTS,
    SPACE_MD,
    SPACE_SM,
    UI_FONT_FAMILY,
)

# -*- coding: utf-8 -*-
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
"""Advanced Statistics workspace for BuildOffice Pro.

Only this page is intentionally data-dense. It reads the existing SQLite schema
and does not modify Dashboard, Expenses, or Attendance logic.
"""

# ============================================================
# شرح الملف: statistics_page.py
# يحتوي هذا الملف على جزء من وظائف وتفاصيل تطبيق BuildOffice Pro.
# التعليقات العربية هنا للتوضيح فقط ولا تغيّر منطق البرنامج.
# ============================================================
import sqlite3
from datetime import datetime, timedelta, timezone

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from repositories.db import get_connection
from services.analytics_service import smart_analytics

from .base_page import BasePage, money


# =========================
# أدوات الواجهة
# =========================
# هذا الصنف مسؤول عن جزء HorizontalBars من التطبيق.
class HorizontalBars(QWidget):
    """رسم أفقي بسيط لعرض المقارنات بدون مكتبة خارجية."""
    # تهيئة الكائن وتجهيز الواجهة والبيانات اللازمة.
    def __init__(self, rows, suffix=""):
        super().__init__()
        self.rows = [(str(a), float(b or 0)) for a, b in rows]
        self.suffix = suffix
        self.setMinimumHeight(max(90, 34 * len(self.rows) + 28))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setObjectName("statisticsChart")

    # رسم العنصر المخصص على الواجهة.
    def paintEvent(self, event):
        del event
        if not self.rows:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        left, top, right = 150, 14, self.width() - 22
        max_value = max(v for _, v in self.rows) or 1
        row_h = 32

        for i, (label, value) in enumerate(self.rows):
            y = top + i * row_h
            painter.setPen(QPen(theme_qcolor("@kpi.neutral@")))
            painter.setFont(QFont(UI_FONT_FAMILY, CHART_FONT_POINTS))
            painter.drawText(8, y + 18, left - 18, 20, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label[:22])

            track = max(40, right - left)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(theme_qcolor("@charts.surface@")))
            painter.drawRoundedRect(left, y + 7, track, 12, 6, 6)

            width = int(track * (value / max_value)) if value else 0
            if width:
                painter.setBrush(QBrush(theme_qcolor("@charts.series_2@")))
                painter.drawRoundedRect(left, y + 7, max(5, width), 12, 6, 6)

            painter.setPen(QPen(theme_qcolor("@selection_text@")))
            painter.setFont(QFont(UI_FONT_FAMILY, CHART_FONT_POINTS, QFont.Weight.Bold))
            text = f"{value:,.2f}{self.suffix}" if self.suffix else f"{value:,.2f}"
            painter.drawText(left + 8, y + 18, track - 16, 20, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, text)
        painter.end()


# هذا الصنف مسؤول عن جزء DonutChart من التطبيق.
class DonutChart(QWidget):
    """مخطط دائري خفيف للحالات."""
    # تهيئة الكائن وتجهيز الواجهة والبيانات اللازمة.
    def __init__(self, rows):
        super().__init__()
        self.rows = [(str(a), int(b or 0)) for a, b in rows if int(b or 0) > 0]
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    # رسم العنصر المخصص على الواجهة.
    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        total = sum(v for _, v in self.rows)
        if not total:
            painter.setPen(QPen(theme_qcolor("@charts.axis@")))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, translate_text("No records for this period"))
            painter.end()
            return

        colors = ["@charts.series_2@", "@charts.series_1@", "@warning@", "@charts.series_5@", "@charts.series_3@", "@charts.series_7@"]
        side = min(155, self.height() - 20)
        pie = self.rect().adjusted(12, 10, -(self.width() - side - 12), -10)
        pie.setWidth(side); pie.setHeight(side)
        start = 0
        for i, (_, value) in enumerate(self.rows):
            span = round(value / total * 360 * 16)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(theme_qcolor(colors[i % len(colors)])))
            painter.drawPie(pie, start, span)
            start += span

        inner = pie.adjusted(36, 36, -36, -36)
        painter.setBrush(QBrush(theme_qcolor("@surface@")))
        painter.drawEllipse(inner)

        x = pie.right() + 24
        y = 24
        for i, (label, value) in enumerate(self.rows):
            painter.setBrush(QBrush(theme_qcolor(colors[i % len(colors)])))
            painter.drawRoundedRect(x, y + 3, 10, 10, 3, 3)
            painter.setPen(QPen(theme_qcolor("@charts.axis_light@")))
            painter.setFont(QFont(UI_FONT_FAMILY, CHART_FONT_POINTS))
            painter.drawText(x + 17, y, max(60, self.width() - x - 10), 20, Qt.AlignmentFlag.AlignLeft, f"{label}: {value}")
            y += 25
        painter.end()


# هذا الصنف مسؤول عن جزء Section من التطبيق.
class Section(QFrame):
    """حاوية إحصائية بدون خلفيات مزعجة خلف الجمل."""
    # تهيئة الكائن وتجهيز الواجهة والبيانات اللازمة.
    def __init__(self, title, subtitle=""):
        super().__init__()
        self.setObjectName("statisticsSection")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 18)
        self._layout.setSpacing(9)

        title_label = QLabel(translate_text(title))
        title_label.setObjectName("statisticsSectionTitle")
        set_theme_style(title_label, "background: transparent; padding: 0; border: none;")
        self._layout.addWidget(title_label)

        if subtitle:
            sub = QLabel(translate_text(subtitle))
            sub.setObjectName("statisticsSectionSubtitle")
            sub.setWordWrap(True)
            set_theme_style(sub, "background: transparent; padding: 0; border: none;")
            self._layout.addWidget(sub)

    # إضافة سجل جديد إلى النظام.
    def add(self, widget):
        self._layout.addWidget(widget)

    # إضافة سجل جديد إلى النظام.
    def add_layout(self, layout):
        self._layout.addLayout(layout)


# هذا الصنف مسؤول عن جزء StatisticsPage من التطبيق.
class StatisticsPage(BasePage):
    """صفحة تحليلية كثيفة، تعتمد على تفاصيل البيانات بدل KPI الزائدة."""

    # تهيئة الكائن وتجهيز الواجهة والبيانات اللازمة.
    def __init__(self):
        super().__init__(
            "Statistics",
            "Detailed management intelligence across projects, finance, workforce, documents and assets"
        )
        self._build_page()
        QTimer.singleShot(0, self.refresh)

    # =========================
    # بناء الصفحة
    # =========================
    # تنفيذ وظيفة _build_page ضمن هذا الجزء من البرنامج.
    def _build_page(self):
        self._apply_page_style()

        toolbar = QFrame()
        toolbar.setObjectName("statisticsToolbar")
        bar = QHBoxLayout(toolbar)
        bar.setContentsMargins(16, 10, 16, 10)
        bar.setSpacing(10)

        label = QLabel(translate_text("Analysis period"))
        label.setObjectName("statisticsToolbarText")
        bar.addWidget(label)
        self.period = LocalizedComboBox()
        self.period.addItems([translate_text("All time"), translate_text("Last 30 days"), translate_text("Last 90 days"), translate_text("This year")])
        self.period.currentIndexChanged.connect(self.refresh)
        bar.addWidget(self.period)
        bar.addStretch()

        self.refresh_btn = QPushButton(translate_text("↻  Refresh analytics"))
        self.refresh_btn.setObjectName("secondaryButton")
        self.refresh_btn.clicked.connect(self.refresh)
        bar.addWidget(self.refresh_btn)
        self.body.addWidget(toolbar)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setObjectName("statisticsScroll")

        self.content = QWidget()
        self.content.setObjectName("statisticsContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(2, 4, 10, 24)
        self.content_layout.setSpacing(14)
        self._scroll.setWidget(self.content)
        self.body.addWidget(self._scroll, 1)

    # تنفيذ وظيفة _apply_page_style ضمن هذا الجزء من البرنامج.
    def _apply_page_style(self):
        # النصوص تبقى شفافة حتى لا تظهر كأنها داخل مربعات مظللة.
        set_theme_style(self, """
            #statisticsToolbar, #statisticsSection {
                background: @surface@;
                border: 1px solid @divider@;
                border-radius: 14px;
            }
            #statisticsContent { background: transparent; }
            #statisticsSectionTitle {
                color: @selection_text@;
                font-size: 15px;
                font-weight: 700;
            }
            #statisticsSectionSubtitle, #statisticsToolbarText {
                color: @kpi.neutral@;
                font-size: 12px;
            }
            QLabel#statisticsSectionTitle, QLabel#statisticsSectionSubtitle,
            QLabel#statisticsToolbarText, QLabel.statisticsPlain {
                background: transparent;
                border: none;
            }
            QTableWidget#statisticsTable {
                background: @surface@;
                alternate-background-color: @components.inspector.inspector_surface@;
                border: 1px solid @divider@;
                border-radius: 10px;
                gridline-color: @tables.grid@;
                selection-background-color: @tables.selected_background@;
                selection-color: @selection_text@;
            }
            QTableWidget#statisticsTable::item { padding: 7px; }
            QTableWidget#statisticsTable QHeaderView::section {
                background: @charts.surface_alt@;
                color: @selection_text@;
                padding: 8px;
                border: none;
                font-weight: 700;
            }
            QProgressBar.statisticsProgress {
                border: none;
                background: @background@;
                border-radius: 4px;
                min-height: 8px;
                max-height: 8px;
            }
            QProgressBar.statisticsProgress::chunk {
                background: @primary@;
                border-radius: 4px;
            }
        """)

    # =========================
    # أدوات البيانات
    # =========================
    # تنفيذ وظيفة _clear ضمن هذا الجزء من البرنامج.
    def _clear(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item is None:
                break
            widget = item.widget()
            layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif layout is not None:
                while layout.count():
                    child = layout.takeAt(0)
                    if child is None:
                        break
                    child_widget = child.widget()
                    if child_widget is not None:
                        child_widget.deleteLater()

    # تنفيذ وظيفة _period_start ضمن هذا الجزء من البرنامج.
    def _period_start(self):
        now = datetime.now(timezone.utc).astimezone()
        idx = self.period.currentIndex()
        if idx == 1:
            return (now - timedelta(days=30)).strftime("%Y-%m-%d")
        if idx == 2:
            return (now - timedelta(days=90)).strftime("%Y-%m-%d")
        if idx == 3:
            return f"{now.year}-01-01"
        return None

    # تنفيذ وظيفة _scalar ضمن هذا الجزء من البرنامج.
    @staticmethod
    def _scalar(conn, sql, params=()):
        row = conn.execute(sql, params).fetchone()
        return row[0] if row else 0

    # تنفيذ وظيفة _money ضمن هذا الجزء من البرنامج.
    @staticmethod
    def _money(v):
        return money(v)

    # تنفيذ وظيفة _table ضمن هذا الجزء من البرنامج.
    def _table(self, headers, rows, widths=None, min_height=190):
        table = QTableWidget(len(rows), len(headers))
        table.setObjectName("statisticsTable")
        table.setHorizontalHeaderLabels(
            [translate_text(str(header)) for header in headers]
        )
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.setMinimumHeight(min_height)
        table.setWordWrap(False)
        header = table.horizontalHeader()

        # الجدول نفسه يملك التمرير الأفقي، ولا نسمح بضغط الأعمدة داخل الصفحة.
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setSizeAdjustPolicy(QAbstractItemView.SizeAdjustPolicy.AdjustIgnored)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(70)

        if widths:
            # Interactive يحافظ على عرض الأعمدة ويسمح للمستخدم بتغييرها.
            # -1 يعني عرضًا مرنًا، لكن نضع له عرضًا ثابتًا مناسبًا بدل Stretch.
            fallback_widths = [
                180, 220, 100, 150, 150,
                150, 150, 150, 100, 220,
            ]
            for i in range(len(headers)):
                width = widths[i] if i < len(widths) else 130
                if width == -1:
                    width = fallback_widths[i] if i < len(fallback_widths) else 180
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                table.setColumnWidth(i, width)
        else:
            for i in range(len(headers)):
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                table.setColumnWidth(i, 140)
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                item = QTableWidgetItem("" if value is None else str(value))
                if isinstance(value, (int, float)):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(r, c, item)
        return table

    # تنفيذ وظيفة _empty ضمن هذا الجزء من البرنامج.
    def _empty(self, text):
        label = QLabel(translate_text(text))
        label.setObjectName("statisticsSectionSubtitle")
        label.setProperty("class", "statisticsPlain")
        set_theme_style(label, "background: transparent; border: none; padding: 10px 2px;")
        return label

    # =========================
    # تحديث التحليلات
    # =========================
    # تحميل أو تحديث البيانات المرتبطة بـ refresh.
    def refresh(self):
        conn = get_connection()
        try:
            self._clear()
            start = self._period_start()
            date_filter = "date >= ?" if start else "1=1"
            date_params = (start,) if start else ()

            # قراءة جميع المؤشرات الأساسية من قاعدة البيانات.
            project_count = self._scalar(conn, "SELECT COUNT(*) FROM projects")
            active_projects = self._scalar(conn, "SELECT COUNT(*) FROM projects WHERE status='Active'")
            budget = self._scalar(conn, "SELECT COALESCE(SUM(budget_ht),0) FROM projects")
            ttc = self._scalar(conn, "SELECT COALESCE(SUM(budget_ttc),0) FROM projects")
            revenue = self._scalar(conn, "SELECT COALESCE(SUM(revenue),0) FROM projects")
            expense_total = self._scalar(conn, f"SELECT COALESCE(SUM(amount),0) FROM expenses WHERE {date_filter}", date_params)
            debt_open = self._scalar(conn, "SELECT COALESCE(SUM(amount),0) FROM debt WHERE status='Open'")
            metre_total = self._scalar(conn, "SELECT COALESCE(SUM(amount),0) FROM metre_items")
            staff_total = self._scalar(conn, "SELECT COUNT(*) FROM staff")
            staff_active = self._scalar(conn, "SELECT COUNT(*) FROM staff WHERE status='Active'")
            attendance_hours = self._scalar(conn, f"SELECT COALESCE(SUM(working_hours + overtime_hours),0) FROM attendance WHERE {date_filter}", date_params)
            docs_company = self._scalar(conn, 'SELECT COUNT(*) FROM "company documents"')
            docs_project = self._scalar(conn, 'SELECT COUNT(*) FROM "projects documents"')
            vehicles = self._scalar(conn, "SELECT COUNT(*) FROM vehicles")

            self._overview(conn, project_count, active_projects, budget, ttc, revenue, expense_total, debt_open, metre_total)
            self._projects(conn)
            self._finance(conn)
            self._workforce(conn, staff_total, staff_active, attendance_hours)
            self._metre(conn, metre_total)
            self._documents(conn, docs_company, docs_project)
            self._debts(conn, debt_open)
            self._assets(conn, vehicles)
            self._trends(conn)
            self._smart_control()
            self._data_quality(conn)

        except (sqlite3.Error, TypeError, ValueError) as exc:
            self._clear()
            self.error(translate_text(f"Statistics could not be calculated.\n\n{exc}"))
        finally:
            conn.close()

    # =========================
    # الأقسام التحليلية
    # =========================
    # تنفيذ وظيفة _overview ضمن هذا الجزء من البرنامج.
    def _overview(self, conn, project_count, active_projects, budget, ttc, revenue, expenses, debt, metre):
        section = Section("Executive overview", "A compact financial and operational reading of the current database, not a wall of decorative KPI cards.")
        grid = QGridLayout(); grid.setSpacing(10)

        statuses = conn.execute("SELECT COALESCE(status,'Unknown'), COUNT(*) FROM projects GROUP BY status ORDER BY COUNT(*) DESC").fetchall()
        status_box = QFrame(); status_box.setObjectName("statisticsInnerBox")
        status_layout = QVBoxLayout(status_box); status_layout.setContentsMargins(12,10,12,10)
        title = QLabel(translate_text("Project status distribution")); title.setObjectName("statisticsSectionTitle"); set_theme_style(title, "background: transparent; border: none;")
        status_layout.addWidget(title)
        status_layout.addWidget(DonutChart(statuses))
        for status, count in statuses:
            row = QHBoxLayout();
            a = QLabel(str(status)); set_theme_style(a, "background: transparent; border: none;")
            b = QLabel(f"{count} project(s)"); set_theme_style(b, "background: transparent; border: none; font-weight: 700;")
            row.addWidget(a); row.addStretch(); row.addWidget(b); status_layout.addLayout(row)
        grid.addWidget(status_box, 0, 0, 2, 1)

        financial = QFrame(); financial.setObjectName("statisticsInnerBox")
        fl = QVBoxLayout(financial); fl.setContentsMargins(12,10,12,10); fl.setSpacing(SPACE_SM)
        t = QLabel(translate_text("Financial position")); t.setObjectName("statisticsSectionTitle"); set_theme_style(t, "background: transparent; border: none;"); fl.addWidget(t)
        values = [
            ("Contract budget HT", budget),
            ("Contract value TTC", ttc),
            ("Estimated revenue", revenue),
            ("Recorded expenses", expenses),
            ("Open debt", debt),
            ("Métré value", metre),
        ]
        for name, value in values:
            row = QHBoxLayout(); lab = QLabel(name); set_theme_style(lab, "background: transparent; border: none;")
            val = QLabel(self._money(value)); set_theme_style(val, "background: transparent; border: none; color: @selection_text@; font-weight: 700;")
            row.addWidget(lab); row.addStretch(); row.addWidget(val); fl.addLayout(row)
        margin = revenue - expenses
        note = QLabel(f"Estimated revenue after selected-period expenses: {self._money(margin)}")
        set_theme_style(note, "background: transparent; border: none; color: @charts.series_2@; font-weight: 700; padding-top: 5px;")
        note.setWordWrap(True); fl.addWidget(note)
        grid.addWidget(financial, 0, 1)

        operations = QFrame(); operations.setObjectName("statisticsInnerBox")
        ol = QVBoxLayout(operations); ol.setContentsMargins(12,10,12,10); ol.setSpacing(SPACE_SM)
        t = QLabel(translate_text("Operational reading")); t.setObjectName("statisticsSectionTitle"); set_theme_style(t, "background: transparent; border: none;"); ol.addWidget(t)
        readings = [
            ("Active projects", f"{active_projects} / {project_count}"),
            ("Average contract HT", self._money(budget / project_count) if project_count else money(0)),
            ("Expense ratio vs budget", f"{expenses / budget * 100:.2f}%" if budget else "0.00%"),
            ("Revenue ratio vs budget", f"{revenue / budget * 100:.2f}%" if budget else "0.00%"),
        ]
        for name, value in readings:
            row = QHBoxLayout(); a = QLabel(name); set_theme_style(a, "background: transparent; border: none;")
            b = QLabel(value); set_theme_style(b, "background: transparent; border: none; font-weight: 700;")
            row.addWidget(a); row.addStretch(); row.addWidget(b); ol.addLayout(row)
        grid.addWidget(operations, 1, 1)
        section.add_layout(grid)
        self.content_layout.addWidget(section)

    # تنفيذ وظيفة _projects ضمن هذا الجزء من البرنامج.
    def _projects(self, conn):
        section = Section("Project intelligence", "Contract, schedule, profitability and cost exposure for every project.")
        rows = conn.execute("""
            SELECT p.project_name, p.contracting_authority, p.status,
                   COALESCE(p.budget_ht,0), COALESCE(p.budget_ttc,0),
                   COALESCE(p.expenses,0), COALESCE(p.revenue,0),
                   COALESCE(p."revenue %",0), p.start_date, p.end_date
            FROM projects p
            ORDER BY COALESCE(p.budget_ht,0) DESC, p.project_name
        """).fetchall()
        data=[]
        for r in rows:
            margin = float(r[6] or 0) - float(r[5] or 0)
            data.append((r[0], r[1] or "-", r[2], self._money(r[3]), self._money(r[4]), self._money(r[5]), self._money(r[6]), self._money(margin), f"{float(r[7] or 0):.2f}%", f"{r[8] or '-'} → {r[9] or '-'}"))
        table = self._table(["Project","Authority","Status","Budget HT","Budget TTC","Project expenses","Revenue","Margin","Margin %","Schedule"], data, [180,220,100,150,150,160,160,160,100,220], 245)
        # تمرير أفقي للجدول فقط، دون تحريك بقية صفحة Statistics.
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        section.add(table)

        status_rows = conn.execute("SELECT COALESCE(status,'Unknown'), COALESCE(SUM(budget_ht),0) FROM projects GROUP BY status ORDER BY SUM(budget_ht) DESC").fetchall()
        if status_rows:
            section.add(QLabel(translate_text("Contract value concentration by status")))
            section.add(HorizontalBars(status_rows, ""))
        self.content_layout.addWidget(section)

    # تنفيذ وظيفة _finance ضمن هذا الجزء من البرنامج.
    def _finance(self, conn):
        section = Section("Financial intelligence", "Understand where money is going, how it is paid, and which projects carry the largest exposure.")
        grid = QGridLayout(); grid.setSpacing(SPACE_MD)

        by_project = conn.execute("""
            SELECT COALESCE(p.project_name,'Unassigned'), COALESCE(SUM(e.amount),0)
            FROM expenses e LEFT JOIN projects p ON p.project_id=e.project_id
            GROUP BY e.project_id ORDER BY SUM(e.amount) DESC LIMIT 10
        """).fetchall()
        box = Section("Expenses by project", "Top 10 project cost exposure")
        box.add(HorizontalBars(by_project, "") if by_project else self._empty("No expense records."))
        grid.addWidget(box, 0, 0)

        by_category = conn.execute("""
            SELECT COALESCE(category,'Uncategorized'), COALESCE(SUM(amount),0)
            FROM expenses GROUP BY category ORDER BY SUM(amount) DESC LIMIT 10
        """).fetchall()
        box2 = Section("Expenses by category", "Highest spending categories across the database")
        box2.add(HorizontalBars(by_category, "") if by_category else self._empty("No categories available."))
        grid.addWidget(box2, 0, 1)

        payments = conn.execute("""
            SELECT COALESCE(payment_status,'Unknown'), COUNT(*), COALESCE(SUM(amount),0)
            FROM expenses GROUP BY payment_status ORDER BY SUM(amount) DESC
        """).fetchall()
        pay_data=[(r[0], r[1], self._money(r[2])) for r in payments]
        box3 = Section("Payment status", "Expense obligations grouped by payment state")
        box3.add(self._table(["Status","Entries","Amount"], pay_data, [-1,100,150], 155) if pay_data else self._empty("No payment records."))
        grid.addWidget(box3, 1, 0)

        monthly = conn.execute("""
            SELECT substr(date,1,7) month, COALESCE(SUM(amount),0)
            FROM expenses WHERE date IS NOT NULL AND date <> ''
            GROUP BY substr(date,1,7) ORDER BY month DESC LIMIT 12
        """).fetchall()
        monthly=list(reversed(monthly))
        box4 = Section("Monthly expense movement", "Last 12 recorded months")
        box4.add(HorizontalBars(monthly, "") if monthly else self._empty("No dated expenses."))
        grid.addWidget(box4, 1, 1)
        section.add_layout(grid)
        self.content_layout.addWidget(section)

    # تنفيذ وظيفة _workforce ضمن هذا الجزء من البرنامج.
    def _workforce(self, conn, staff_total, staff_active, attendance_hours):
        section = Section("Workforce & attendance intelligence", "Staff distribution, project assignments and recorded working time. Attendance records are read-only here.")
        assignments = conn.execute("""
            SELECT s.full_name, COALESCE(s.position,'-'), COALESCE(s.status,'-'),
                   COUNT(sp.project_id), COALESCE(GROUP_CONCAT(p.project_name, ', '),'Unassigned')
            FROM staff s
            LEFT JOIN staff_projects sp ON sp.staff_id=s.staff_id AND sp.active=1
            LEFT JOIN projects p ON p.project_id=sp.project_id
            GROUP BY s.staff_id ORDER BY s.full_name
        """).fetchall()
        data=[(r[0],r[1],r[2],r[3],r[4]) for r in assignments]
        grid=QGridLayout(); grid.setSpacing(SPACE_MD)
        left=Section("Staff allocation", f"{staff_active} active of {staff_total} registered")
        left.add(self._table(["Employee","Position","Status","Projects","Assigned projects"], data, [180,140,90,80,-1], 190) if data else self._empty("No staff records."))
        grid.addWidget(left,0,0)

        att=conn.execute("""
            SELECT COALESCE(status,'Unknown'), COUNT(*),
                   COALESCE(SUM(working_hours),0), COALESCE(SUM(overtime_hours),0)
            FROM attendance GROUP BY status ORDER BY COUNT(*) DESC
        """).fetchall()
        adata=[(r[0],r[1],f"{float(r[2]):,.2f}",f"{float(r[3]):,.2f}") for r in att]
        right=Section("Attendance reading", f"Total recorded hours: {float(attendance_hours):,.2f}")
        right.add(self._table(["Status","Records","Regular h","Overtime h"], adata, [-1,100,110,110], 190) if adata else self._empty("No attendance records for the current database."))
        grid.addWidget(right,0,1)
        section.add_layout(grid)
        self.content_layout.addWidget(section)

    # تنفيذ وظيفة _metre ضمن هذا الجزء من البرنامج.
    def _metre(self, conn, metre_total):
        section = Section("Métré intelligence", "Measure the value and structure of project items without duplicating the Métré workflow.")
        by_project = conn.execute("""
            SELECT COALESCE(p.project_name,'Unknown'), COUNT(m.item_id), COALESCE(SUM(m.amount),0)
            FROM metre_items m LEFT JOIN projects p ON p.project_id=m.project_id
            GROUP BY m.project_id ORDER BY SUM(m.amount) DESC
        """).fetchall()
        data=[(r[0],r[1],self._money(r[2])) for r in by_project]
        grid=QGridLayout(); grid.setSpacing(SPACE_MD)
        left=Section("Métré by project", f"Total item value: {self._money(metre_total)}")
        left.add(self._table(["Project","Items","Value"],data,[-1,90,160],190) if data else self._empty("No Métré items recorded."))
        grid.addWidget(left,0,0)

        top_items=conn.execute("""
            SELECT COALESCE(p.project_name,'Unknown'), COALESCE(m.item_number,'-'), m.description,
                   COALESCE(m.quantity,0), COALESCE(m.unit,''), COALESCE(m.amount,0)
            FROM metre_items m LEFT JOIN projects p ON p.project_id=m.project_id
            ORDER BY m.amount DESC LIMIT 10
        """).fetchall()
        tdata=[(r[0],r[1],r[2],f"{float(r[3]):,.3f}",r[4],self._money(r[5])) for r in top_items]
        right=Section("Highest-value items", "Top 10 Métré lines")
        right.add(self._table(["Project","No.","Description","Qty","Unit","Amount"],tdata,[120,70,-1,90,70,130],190) if tdata else self._empty("No item records."))
        grid.addWidget(right,0,1)
        section.add_layout(grid)
        self.content_layout.addWidget(section)

    # تنفيذ وظيفة _documents ضمن هذا الجزء من البرنامج.
    def _documents(self, conn, docs_company, docs_project):
        section = Section("Document control", "Expiry monitoring for company and project documents. Expired and soon-to-expire records are surfaced explicitly.")
        now = datetime.now(timezone.utc).astimezone()
        today=now.strftime("%Y-%m-%d")
        soon=(now + timedelta(days=30)).strftime("%Y-%m-%d")
        company=conn.execute('''SELECT "document name", "expiring date", status FROM "company documents" ORDER BY "expiring date"''').fetchall()
        project=conn.execute('''SELECT p.project_name, d.document_name, d.expiring_date, d.status FROM "projects documents" d LEFT JOIN projects p ON p.project_id=d.project_id ORDER BY d.expiring_date''').fetchall()

        # تنفيذ وظيفة doc_state ضمن هذا الجزء من البرنامج.
        def doc_state(expiry, status):
            if str(status).lower() not in ("active", "valid", ""):
                return "Inactive"
            if not expiry: return "No expiry"
            if str(expiry) < today: return "OVERDUE"
            if str(expiry) <= soon: return "Due ≤30d"
            return "Valid"

        cdata=[(r[0],r[1] or "-",doc_state(r[1],r[2]),r[2] or "-") for r in company]
        pdata=[(r[0] or "Unknown",r[1],r[2] or "-",doc_state(r[2],r[3]),r[3] or "-") for r in project]
        grid=QGridLayout(); grid.setSpacing(SPACE_MD)
        a=Section("Company documents", f"{docs_company} records")
        a.add(self._table(["Document","Expiry","Control","Status"],cdata,[-1,120,110,90],185) if cdata else self._empty("No company documents."))
        grid.addWidget(a,0,0)
        b=Section("Project documents", f"{docs_project} records")
        b.add(self._table(["Project","Document","Expiry","Control","Status"],pdata,[130,-1,110,100,90],185) if pdata else self._empty("No project documents."))
        grid.addWidget(b,0,1)
        section.add_layout(grid)
        self.content_layout.addWidget(section)

    # تنفيذ وظيفة _debts ضمن هذا الجزء من البرنامج.
    def _debts(self, conn, debt_open):
        section=Section("Debt exposure", "Open obligations, lenders and project attribution.")
        rows=conn.execute("""
            SELECT COALESCE(d.lender,'Unknown'), COALESCE(p.project_name,'Unassigned'), d.date,
                   COALESCE(d.amount,0), COALESCE(d.status,'Unknown')
            FROM debt d LEFT JOIN projects p ON p.project_id=d.project_id
            ORDER BY CASE WHEN d.status='Open' THEN 0 ELSE 1 END, d.date DESC
        """).fetchall()
        data=[(r[0],r[1],r[2],self._money(r[3]),r[4]) for r in rows]
        section.add(self._table(["Lender","Project","Date","Amount","Status"],data,[180,-1,110,150,100],205) if data else self._empty(f"No debt records. Current open exposure: {self._money(debt_open)}"))
        self.content_layout.addWidget(section)

    # تنفيذ وظيفة _assets ضمن هذا الجزء من البرنامج.
    def _assets(self, conn, vehicles):
        section=Section("Fleet & assets", "Vehicle inventory and current operational status.")
        rows=conn.execute("""
            SELECT brand, model, licence_plate, COALESCE(serial_number,'-'),
                   COALESCE(buy_date,'-'), COALESCE(status,'Unknown')
            FROM vehicles ORDER BY status, brand, model
        """).fetchall()
        data=[tuple(r) for r in rows]
        section.add(self._table(["Brand","Model","Licence plate","Serial","Purchase date","Status"],data,[130,130,120,150,120,100],190) if data else self._empty(f"No vehicle records. Registered vehicles: {vehicles}"))
        self.content_layout.addWidget(section)

    # تنفيذ وظيفة _trends ضمن هذا الجزء من البرنامج.
    def _trends(self, conn):
        section=Section("Time-based trends", "Monthly workload and spending movement, useful for spotting concentration and operational changes.")
        grid=QGridLayout(); grid.setSpacing(SPACE_MD)
        exp=conn.execute("""
            SELECT substr(date,1,7), COALESCE(SUM(amount),0)
            FROM expenses WHERE date IS NOT NULL AND date<>''
            GROUP BY substr(date,1,7) ORDER BY substr(date,1,7) DESC LIMIT 12
        """).fetchall()
        att=conn.execute("""
            SELECT substr(date,1,7), COALESCE(SUM(working_hours + overtime_hours),0)
            FROM attendance WHERE date IS NOT NULL AND date<>''
            GROUP BY substr(date,1,7) ORDER BY substr(date,1,7) DESC LIMIT 12
        """).fetchall()
        a=Section("Expense trend", "Monthly total")
        a.add(HorizontalBars(list(reversed(exp)), "") if exp else self._empty("No monthly expense data."))
        grid.addWidget(a,0,0)
        b=Section("Working-hours trend", "Regular + overtime hours")
        b.add(HorizontalBars(list(reversed(att)), " h") if att else self._empty("No attendance trend data."))
        grid.addWidget(b,0,1)
        section.add_layout(grid)
        self.content_layout.addWidget(section)

# شرح الدالة _smart_control: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _smart_control(self):
        """Show an explainable control cockpit for project decisions."""
        data = smart_analytics()
        portfolio = data.get("portfolio", {})

        section = Section(
            "Smart project control",
            "Simple reading first: health, progress, cost, forecast, cash exposure and the next management action."
        )

        summary = QFrame(); summary.setObjectName("statisticsInnerBox")
        sl = QGridLayout(summary); sl.setContentsMargins(12, 10, 12, 10); sl.setSpacing(8)
        summary_values = [
            ("Portfolio health", portfolio.get("headline", "-")),
            ("Active projects", str(portfolio.get("active_projects", 0))),
            ("Healthy", str(portfolio.get("healthy_count", 0))),
            ("Watch", str(portfolio.get("watch_count", 0))),
            ("Critical", str(portfolio.get("critical_count", 0))),
            ("Data confidence", f"{data.get('data_confidence', 0):.0f}%"),
        ]
        for i, (label, value) in enumerate(summary_values):
            box = QVBoxLayout()
            a = QLabel(translate_text(label)); set_theme_style(a, "background: transparent; border: none; color: @kpi.neutral@; font-size: 11px;")
            b = QLabel(str(value)); set_theme_style(b, "background: transparent; border: none; color: @selection_text@; font-weight: 700; font-size: 13px;")
            b.setWordWrap(True)
            box.addWidget(a); box.addWidget(b)
            sl.addLayout(box, i // 3, i % 3)
        section.add(summary)

        grid = QGridLayout(); grid.setSpacing(SPACE_MD)
        rows = []
        for m in data.get("projects", []):
            rows.append((
                m["project_name"], m["health"], f"{m['health_score']:.0f}/100",
                f"{m['progress']:.1f}%", f"{m['cost_pct']:.1f}%",
                f"{m['cpi']:.2f}", f"{m['spi']:.2f}", self._money(m["eac"]),
            ))
        left = Section("Project health matrix", "One row gives the complete control picture for a project.")
        left.add(self._table(
            ["Project", "Health", "Score", "Progress", "Cost %", "CPI", "SPI", "EAC"],
            rows, [180, 85, 75, 85, 80, 65, 65, 145], 250
        ) if rows else self._empty("No projects available for smart analysis."))
        grid.addWidget(left, 0, 0)

        risk_rows = []
        for risk in data.get("risks", [])[:15]:
            risk_rows.append((
                risk["severity"], risk["project_name"], risk["message"],
                f"CPI {risk['cpi']:.2f} / SPI {risk['spi']:.2f}"
            ))
        right = Section("Actionable risks", "The system converts weak indicators into a concrete next check.")
        right.add(self._table(
            ["Level", "Project", "Recommended action", "Evidence"],
            risk_rows, [75, 150, 300, 145], 250
        ) if risk_rows else self._empty("No material project risks detected from the current data."))
        grid.addWidget(right, 0, 1)
        section.add_layout(grid)

        detail_rows = []
        for m in sorted(data.get("projects", []), key=lambda x: x["actual_cost"], reverse=True)[:12]:
            detail_rows.append((
                m["project_name"], m["top_cost_type"], self._money(m["top_cost_value"]),
                self._money(m["receivable"]), self._money(m["payable"]),
                self._money(m["cost_variance"]), m["explanation"],
            ))
        detail = Section("Cost and cash exposure", "The largest cost driver and outstanding cash position for each project.")
        detail.add(self._table(
            ["Project", "Largest cost", "Amount", "Receivable", "Payable", "Budget headroom", "Reading"],
            detail_rows, [170, 120, 135, 135, 135, 150, 300], 270
        ) if detail_rows else self._empty("No project exposure data."))
        section.add(detail)

        forecast = Section("Portfolio forecast", "Management-level totals generated from active projects.")
        forecast.add(self._table(["Indicator", "Value"], [
            ("Portfolio budget", self._money(portfolio.get("portfolio_budget"))),
            ("Controlled cost", self._money(portfolio.get("portfolio_cost"))),
            ("Earned value", self._money(portfolio.get("portfolio_earned"))),
            ("Portfolio CPI", f"{portfolio.get('portfolio_cpi', 1):.2f}"),
            ("Forecast cost at current efficiency (EAC)", self._money(portfolio.get("portfolio_eac"))),
            ("Forecast margin", self._money(portfolio.get("portfolio_margin"))),
            ("Receivable from earned work", self._money(portfolio.get("receivable"))),
            ("Payable from recorded project expenses", self._money(portfolio.get("payable"))),
            ("Overdue expenses", self._money(portfolio.get("overdue_expenses"))),
            ("Open debt", self._money(portfolio.get("open_debt"))),
        ], [300, 230], 270))
        self.content_layout.addWidget(section)
        self.content_layout.addWidget(forecast)

    # تنفيذ وظيفة _data_quality ضمن هذا الجزء من البرنامج.
    def _data_quality(self, conn):
        section=Section("Data quality & management alerts", "Checks that help detect incomplete records before they contaminate reports.")
        checks=[]
        checks.append(("Projects without contract code", self._scalar(conn,"SELECT COUNT(*) FROM projects WHERE contract_code IS NULL OR TRIM(contract_code)=''")))
        checks.append(("Projects without start date", self._scalar(conn,"SELECT COUNT(*) FROM projects WHERE start_date IS NULL OR TRIM(start_date)=''")))
        checks.append(("Staff without position", self._scalar(conn,"SELECT COUNT(*) FROM staff WHERE position IS NULL OR TRIM(position)=''")))
        checks.append(("Expenses without project", self._scalar(conn,"SELECT COUNT(*) FROM expenses WHERE project_id IS NULL OR TRIM(project_id)=''")))
        checks.append(("Open debts without project", self._scalar(conn,"SELECT COUNT(*) FROM debt WHERE status='Open' AND (project_id IS NULL OR TRIM(project_id)='')")))
        checks.append(("Documents without expiry date", self._scalar(conn, "SELECT COUNT(*) FROM \"company documents\" WHERE \"expiring date\" IS NULL OR TRIM(\"expiring date\") = ''") + self._scalar(conn, "SELECT COUNT(*) FROM \"projects documents\" WHERE expiring_date IS NULL OR TRIM(expiring_date) = ''")))

        rows=[]
        for label,count in checks:
            state="OK" if int(count)==0 else "Review"
            rows.append((label,int(count),state))
        section.add(self._table(["Check","Records","State"],rows,[-1,100,100],230))
        self.content_layout.addWidget(section)

    # تنفيذ وظيفة showEvent ضمن هذا الجزء من البرنامج.
    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

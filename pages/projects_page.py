# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
# ============================================================
# شرح الملف: projects_page.py
# يحتوي هذا الملف على واجهة إدارة المشاريع ووظائف CRUD الخاصة بها.
# التعليقات العربية للتوضيح فقط ولا تغيّر منطق البرنامج.
# ============================================================

from __future__ import annotations

import itertools
import sqlite3
from datetime import datetime, timezone

from PySide6.QtCore import QDate, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPolygon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.project_service import archive_project as archive_project_service
from services.project_service import delete_project as delete_project_service
from services.settings_service import default_tva, qt_date_format
from theme import set_theme_style

from .base_page import BasePage, KpiCard, money, next_id

# ============================================================
# Typed UI helper classes
# ============================================================

class MetricCard(KpiCard):
    """Backward-compatible project KPI using the application's unified KPI design."""

    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str,
        accent_role: str,
        icon: str,
        parent: QWidget | None = None,
    ):
        accent_map = {
            "info": "@info@",
            "success": "@success@",
            "warning": "@warning@",
            "danger": "@danger@",
            "charts.series_2": "@charts.series_2@",
            "charts.series_3": "@charts.series_3@",
            "charts.series_7": "@charts.series_7@",
            "primary": "@primary@",
        }
        super().__init__(
            title, value, subtitle, accent_map.get(accent_role, "@primary@"), icon
        )
        if parent is not None:
            self.setParent(parent)


class SummaryPanel(QFrame):
    """Typed summary panel containing its value, detail and chart widgets."""

    def __init__(
        self,
        title: str,
        value: str = "0",
        detail: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.value_label = QLabel(str(value))
        self.detail_label = QLabel()
        self.extra_label = QLabel()
        self.chart: QWidget

        self.setObjectName("projectsSummaryCard")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(15, 13, 15, 13)
        lay.setSpacing(6)

        title_label = QLabel(translate_text(title))
        title_label.setObjectName("projectsSummaryTitle")
        lay.addWidget(title_label)

        self.value_label.setObjectName("projectsSummaryValue")
        lay.addWidget(self.value_label)

        chart_row = QHBoxLayout()
        chart_row.setSpacing(12)

        self.extra_label.setObjectName("projectsSummaryDetail")
        self.extra_label.setWordWrap(True)

        if title == "Budget Overview":
            self.chart = BudgetDonutWidget()
            self.chart.setFixedSize(118, 118)
            chart_row.addWidget(self.chart, 0, Qt.AlignmentFlag.AlignCenter)
            chart_row.addWidget(self.extra_label, 1)

        elif title == "Expenses Trend":
            self.chart = MiniLineChart()
            self.chart.setMinimumHeight(118)
            chart_row.addWidget(self.chart, 1)

        else:
            self.chart = ActivityDonutWidget()
            self.chart.setFixedSize(118, 118)
            chart_row.addWidget(self.chart, 0, Qt.AlignmentFlag.AlignCenter)
            chart_row.addWidget(self.extra_label, 1)

        lay.addLayout(chart_row, 1)

        self.detail_label.setObjectName("projectsSummaryDetail")
        self.detail_label.setWordWrap(True)
        self.detail_label.setText(translate_text(detail))
        lay.addWidget(self.detail_label)


class StatsPanel(QFrame):
    """Typed statistics panel."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.donut = DonutWidget()
        self.legend = QLabel()

        self.setObjectName("projectsSideCard")
        self.setMinimumHeight(210)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(15, 14, 15, 14)
        lay.setSpacing(8)

        title = QLabel(translate_text("Project Statistics"))
        title.setObjectName("projectsSideTitle")
        lay.addWidget(title)

        body = QHBoxLayout()

        self.donut.setFixedSize(108, 108)
        body.addWidget(self.donut, 0, Qt.AlignmentFlag.AlignCenter)

        self.legend.setObjectName("projectsSideText")
        self.legend.setWordWrap(True)
        body.addWidget(self.legend, 1)

        lay.addLayout(body)


class ActivityPanel(QFrame):
    """Typed recent activity panel."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.activity_layout = QVBoxLayout()

        self.setObjectName("projectsSideCard")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(15, 14, 15, 14)
        lay.setSpacing(8)

        head = QHBoxLayout()

        title = QLabel(translate_text("Recent Activity"))
        title.setObjectName("projectsSideTitle")
        head.addWidget(title, 1)

        all_label = QLabel(translate_text("View all"))
        all_label.setObjectName("projectsLink")
        head.addWidget(all_label)

        lay.addLayout(head)

        self.activity_layout.setSpacing(7)
        lay.addLayout(self.activity_layout, 1)


class QuickPanel(QFrame):
    """Typed quick-actions panel."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.body_label = QLabel()

        self.setObjectName("projectsSideCard")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(15, 14, 15, 14)
        lay.setSpacing(7)

        title = QLabel(translate_text("Quick Actions"))
        title.setObjectName("projectsSideTitle")
        lay.addWidget(title)

        self.body_label.setObjectName("projectsSideText")
        self.body_label.setWordWrap(True)
        lay.addWidget(self.body_label)


# ============================================================
# Charts
# ============================================================

class DonutWidget(QWidget):
    """Theme-aware ring chart used by the Projects dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.active = 0
        self.completed = 0
        self.suspended = 0
        self.archived = 0

        self.center_text = "0"
        self.center_subtitle = "Total"

        self.setMinimumSize(96, 96)

    def set_values(
        self,
        active,
        completed,
        suspended,
        archived,
        *,
        center_text=None,
        subtitle="Total",
    ):
        self.active = int(active or 0)
        self.completed = int(completed or 0)
        self.suspended = int(suspended or 0)
        self.archived = int(archived or 0)

        if center_text is None:
            center_text = sum(
                (
                    self.active,
                    self.completed,
                    self.suspended,
                    self.archived,
                )
            )

        self.center_text = str(center_text)
        self.center_subtitle = str(subtitle)

        self.update()

    def _display_total(self):
        return self.center_text

    def paintEvent(self, event):
        from theme import theme_color

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(10, 10, -10, -10)

        background = QColor(theme_color("divider"))
        painter.setPen(QPen(background, 11))
        painter.drawArc(rect, 0, 360 * 16)

        colors = [
            theme_color("success"),
            theme_color("info"),
            theme_color("warning"),
            theme_color("danger"),
        ]

        values = [
            self.active,
            self.completed,
            self.suspended,
            self.archived,
        ]

        total = max(1, sum(values))
        start = 90 * 16

        for value, color in zip(values, colors):
            if value <= 0:
                continue

            span = max(
                1,
                int(360 * 16 * value / total),
            )

            painter.setPen(QPen(QColor(color), 11))
            painter.drawArc(rect, start, -span)
            start -= span

        painter.setPen(QColor(theme_color("text_primary")))

        font = painter.font()
        font.setBold(True)
        font.setPointSize(
            max(
                10,
                min(
                    18,
                    int(self.width() / 8),
                ),
            )
        )
        painter.setFont(font)

        painter.drawText(
            rect.adjusted(0, -6, 0, -1),
            Qt.AlignmentFlag.AlignCenter,
            self._display_total(),
        )

        font.setBold(False)
        font.setPointSize(
            max(
                7,
                min(
                    10,
                    int(self.width() / 14),
                ),
            )
        )

        painter.setFont(font)
        painter.setPen(QColor(theme_color("text_muted")))

        painter.drawText(
            rect.adjusted(0, 20, 0, 0),
            Qt.AlignmentFlag.AlignCenter,
            translate_text(self.center_subtitle),
        )

        painter.end()


class ProjectsHero(QFrame):
    """Dedicated Projects welcome hero with a construction silhouette."""

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        base_x = int(width * 0.60)

        painter.setPen(Qt.PenStyle.NoPen)

        for i, (xoff, block_width, block_height) in enumerate(
            (
                (0, 110, 64),
                (88, 145, 88),
                (206, 120, 72),
            )
        ):
            x = base_x + xoff
            y = height - block_height

            painter.setBrush(
                QBrush(
                    QColor(
                        255,
                        255,
                        255,
                        24 if i != 1 else 32,
                    )
                )
            )

            painter.drawRect(
                x,
                y,
                block_width,
                block_height,
            )

            painter.setBrush(QBrush(QColor(255, 255, 255, 65)))

            for yy in range(y + 13, height - 8, 16):
                for xx in range(x + 12, x + block_width - 10, 20):
                    painter.drawRoundedRect(
                        xx,
                        yy,
                        8,
                        6,
                        2,
                        2,
                    )

        crane_x = int(width * 0.78)

        painter.setPen(
            QPen(
                QColor(255, 255, 255, 95),
                3,
            )
        )

        painter.drawLine(
            crane_x,
            height - 10,
            crane_x,
            17,
        )

        painter.drawLine(
            crane_x - 8,
            22,
            min(width - 24, crane_x + 220),
            22,
        )

        painter.drawLine(
            crane_x + 42,
            22,
            crane_x + 10,
            6,
        )

        painter.drawLine(
            crane_x + 42,
            22,
            crane_x + 74,
            6,
        )

        painter.drawLine(
            crane_x + 126,
            22,
            crane_x + 126,
            66,
        )

        painter.setPen(Qt.PenStyle.NoPen)

        painter.setBrush(
            QBrush(
                QColor(
                    255,
                    255,
                    255,
                    14,
                )
            )
        )

        painter.drawPolygon(
            QPolygon(
                [
                    QPoint(crane_x - 18, height - 10),
                    QPoint(crane_x + 18, height - 10),
                    QPoint(crane_x, 22),
                ]
            )
        )

        painter.end()


class MiniLineChart(QWidget):
    """Six-period expense trend with real labels and values."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.values = [0.0] * 6
        self.labels = ["1", "2", "3", "4", "5", "6"]

        self.setMinimumHeight(105)

    def set_series(self, values, labels):
        self.values = [
            float(value or 0)
            for value in values
        ][-6:]

        self.labels = [
            str(value)
            for value in labels
        ][-6:]

        while len(self.values) < 6:
            self.values.insert(0, 0.0)

        while len(self.labels) < 6:
            self.labels.insert(0, "")

        self.update()

    def paintEvent(self, event):
        from theme import theme_color

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(
            28,
            8,
            8,
            21,
        )

        grid = QColor(theme_color("divider"))
        line = QColor(theme_color("info"))
        axis = QColor(theme_color("text_muted"))

        fill = QColor(line)
        fill.setAlpha(32)

        painter.setPen(QPen(grid, 1))

        for i in range(4):
            y = rect.top() + int(
                rect.height() * i / 3
            )

            painter.drawLine(
                rect.left(),
                y,
                rect.right(),
                y,
            )

        vmax = max(
            max(self.values),
            1.0,
        )

        points = []

        for i, value in enumerate(self.values):
            x = rect.left() + int(
                rect.width() * i / 5
            )

            y = rect.bottom() - int(
                (value / vmax) * rect.height()
            )

            points.append(QPoint(x, y))

        polygon = QPolygon(
            [
                QPoint(
                    rect.left(),
                    rect.bottom(),
                ),
                *points,
                QPoint(
                    rect.right(),
                    rect.bottom(),
                ),
            ]
        )

        painter.setBrush(QBrush(fill))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(polygon)

        painter.setPen(QPen(line, 2.5))

        for first, second in itertools.pairwise(points):
            painter.drawLine(first, second)

        painter.setBrush(QBrush(line))
        painter.setPen(Qt.PenStyle.NoPen)

        for point in points:
            painter.drawEllipse(
                point,
                3,
                3,
            )

        font = painter.font()
        font.setPointSize(7)
        painter.setFont(font)

        painter.setPen(axis)

        for i, text in enumerate(self.labels):
            x = rect.left() + int(
                rect.width() * i / 5
            )

            painter.drawText(
                x - 16,
                self.height() - 4,
                32,
                12,
                Qt.AlignmentFlag.AlignCenter,
                text,
            )

        last_value = (
            f"{money(self.values[-1])}"
            if self.values and self.values[-1]
            else "0"
        )

        painter.drawText(
            0,
            rect.top() - 1,
            26,
            14,
            Qt.AlignmentFlag.AlignRight,
            last_value,
        )

        painter.end()


class BudgetDonutWidget(DonutWidget):
    """Used/remaining budget ring."""

    def set_budget(self, budget, expenses):
        used = max(
            0.0,
            float(expenses or 0),
        )

        budget_float = max(
            0.0,
            float(budget or 0),
        )

        remaining = max(
            0.0,
            budget_float - used,
        )

        if budget_float >= 1_000_000:
            center = f"{budget_float / 1_000_000:.2f}M"
        elif budget_float >= 1_000:
            center = f"{budget_float / 1_000:.1f}K"
        else:
            center = money(budget_float)

        self.active = round(used)
        self.completed = round(remaining)
        self.suspended = 0
        self.archived = 0

        self.center_text = center
        self.center_subtitle = "Budget"

        self.update()


class ActivityDonutWidget(DonutWidget):
    """Project status distribution ring."""

    def set_activity(
        self,
        active,
        completed,
        suspended,
        archived,
    ):
        total = (
            int(active or 0)
            + int(completed or 0)
            + int(suspended or 0)
            + int(archived or 0)
        )

        self.set_values(
            active,
            completed,
            suspended,
            archived,
            center_text=str(total),
            subtitle="Projects",
        )


# ============================================================
# Project card
# ============================================================

class ProjectCard(QFrame):
    """Clickable project summary card used by the Cards view."""

    clicked = Signal(str)

    def __init__(self, project, parent=None):
        super().__init__(parent)

        self.project_id = str(project[0])

        self.setObjectName("projectListCard")
        self.setProperty("selected", False)
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.setMinimumHeight(190)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(8)

        ident = QLabel(self.project_id)
        ident.setObjectName("projectListCardId")

        top.addWidget(ident)
        top.addStretch(1)

        status = QLabel(
            str(project[9] or "")
        )

        status.setObjectName(
            "projectListCardStatus"
        )

        status.setProperty(
            "statusRole",
            str(project[9] or ""),
        )

        top.addWidget(status)
        layout.addLayout(top)

        title = QLabel(
            str(
                project[1]
                or "Untitled project"
            )
        )

        title.setObjectName(
            "projectListCardTitle"
        )

        title.setWordWrap(True)
        layout.addWidget(title)

        authority = QLabel(
            str(project[2] or "")
        )

        authority.setObjectName(
            "projectListCardMeta"
        )

        authority.setWordWrap(True)
        layout.addWidget(authority)

        grid = QHBoxLayout()
        grid.setSpacing(14)

        details = [
            ("Type", project[3]),
            ("Contract code", project[4]),
            (
                "Schedule",
                f"{project[5] or '-'} → {project[6] or '-'}",
            ),
        ]

        for label_text, value in details:
            box = QVBoxLayout()
            box.setSpacing(2)

            caption = QLabel(
                translate_text(label_text)
            )

            caption.setObjectName(
                "projectListCardCaption"
            )

            value_label = QLabel(
                str(value or "-")
            )

            value_label.setObjectName(
                "projectListCardValue"
            )

            value_label.setWordWrap(True)

            box.addWidget(caption)
            box.addWidget(value_label)

            grid.addLayout(box, 1)

        layout.addLayout(grid)

        footer = QHBoxLayout()

        budget_label = QLabel(
            translate_text("Budget HT")
        )

        budget_label.setObjectName(
            "projectListCardCaption"
        )

        budget_value = QLabel(
            money(project[7] or 0)
        )

        budget_value.setObjectName(
            "projectListCardBudget"
        )

        footer.addWidget(budget_label)
        footer.addWidget(budget_value)
        footer.addStretch(1)

        ttc = QLabel(
            money(project[8] or 0)
        )

        ttc.setObjectName(
            "projectListCardTTC"
        )

        footer.addWidget(ttc)

        layout.addLayout(footer)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(
                self.project_id
            )

        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        self.setProperty(
            "selected",
            bool(selected),
        )

        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


# ============================================================
# Projects page
# ============================================================

class ProjectsPage(BasePage):
    """Projects management page."""

    def __init__(self):
        super().__init__(
            "Projects",
            "Contracts, budgets, schedules and project status",
        )

        self._selected_project_id: str | None = None
        self._project_rows: list[tuple] = []

        self.build_ui()
        QTimer.singleShot(0, self.load)

    # ========================================================
    # UI construction
    # ========================================================

    def build_ui(self):
        """Build the Projects page as a self-contained dashboard."""

        self.body.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName(
            "projectsDashboardScroll"
        )
        scroll.setProperty("themeSurface", "background")

        scroll.setWidgetResizable(True)
        scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        content = QWidget()
        content.setObjectName(
            "projectsDashboardContent"
        )
        content.setProperty("themeSurface", "background")

        root = QVBoxLayout(content)
        root.setContentsMargins(
            2,
            2,
            14,
            18,
        )
        root.setSpacing(12)

        # ----------------------------------------------------
        # HERO
        # ----------------------------------------------------

        hero = ProjectsHero()

        hero.setObjectName(
            "projectsWelcomeHero"
        )

        hero.setMinimumHeight(118)

        hero.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        hero_layout = QHBoxLayout(hero)

        hero_layout.setContentsMargins(
            22,
            18,
            24,
            18,
        )

        hero_layout.setSpacing(15)

        mark = QLabel("🏗")
        mark.setObjectName(
            "projectsWelcomeIcon"
        )

        mark.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        mark.setFixedSize(54, 54)

        hero_layout.addWidget(mark)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title = QLabel(
            translate_text(
                "Good morning, Administrator"
            )
        )

        title.setObjectName(
            "projectsWelcomeTitle"
        )

        subtitle = QLabel(
            translate_text(
                "Here's what's happening with your construction projects today."
            )
        )

        subtitle.setObjectName(
            "projectsWelcomeSubtitle"
        )

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        hero_layout.addLayout(
            title_box,
            1,
        )

        slogan = QLabel(
            translate_text(
                "Build today\nfor a better tomorrow"
            )
        )

        slogan.setObjectName(
            "projectsWelcomeSlogan"
        )

        slogan.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        hero_layout.addWidget(slogan)

        root.addWidget(hero)

        # ----------------------------------------------------
        # KPI ROW
        # ----------------------------------------------------

        metrics = QHBoxLayout()
        metrics.setSpacing(12)

        self.metric_active = MetricCard(
            "TOTAL PROJECTS",
            "0",
            "Active projects",
            "info",
            "▣",
        )

        self.metric_budget = MetricCard(
            "TOTAL BUDGET (HT)",
            money(0),
            "Registered project budgets",
            "success",
            "₣",
        )

        self.metric_expenses = MetricCard(
            "TOTAL EXPENSES",
            money(0),
            "All recorded expenses",
            "charts.series_3",
            "◉",
        )

        self.metric_total = MetricCard(
            "TOTAL RECORDS",
            "0",
            "Projects and activity records",
            "warning",
            "▤",
        )

        for card in (
            self.metric_active,
            self.metric_budget,
            self.metric_expenses,
            self.metric_total,
        ):
            metrics.addWidget(card, 1)

        root.addLayout(metrics)

        # ----------------------------------------------------
        # FILTER / ACTION BAR
        # ----------------------------------------------------

        toolbar = QFrame()
        toolbar.setObjectName(
            "projectsToolbar"
        )

        toolbar_layout = QHBoxLayout(
            toolbar
        )

        toolbar_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        toolbar_layout.setSpacing(8)

        self.search = QLineEdit()

        self.search.setObjectName(
            "projectsSearch"
        )

        self.search.setPlaceholderText(
            translate_text(
                "Search by project name, authority, contract code…"
            )
        )

        self.search.textChanged.connect(
            self.load
        )

        self.search.setMinimumHeight(40)

        toolbar_layout.addWidget(
            self.search,
            1,
        )

        self.status_filter = LocalizedComboBox()

        self.status_filter.setObjectName(
            "projectsFilter"
        )

        for status_value in (
            "All statuses",
            "Active",
            "Completed",
            "Suspended",
            "Archived",
        ):
            self.status_filter.addItem(
                translate_text(status_value),
                status_value,
            )

        self.status_filter.currentIndexChanged.connect(
            self.load
        )

        self.status_filter.setMinimumHeight(40)

        toolbar_layout.addWidget(
            self.status_filter
        )

        buttons = [
            (
                "↻ Refresh",
                self.load,
                "secondaryButton",
            ),
            (
                "+ New Project",
                self.add_project,
                "primaryButton",
            ),
            (
                "Edit",
                self.edit_project,
                "secondaryButton",
            ),
            (
                "Archive",
                self.archive_project,
                "secondaryButton",
            ),
            (
                "Restore",
                self.restore_project,
                "secondaryButton",
            ),
            (
                "Delete",
                self.delete_project,
                "dangerButton",
            ),
        ]

        for text, slot, object_name in buttons:
            button = QPushButton(
                translate_text(text)
            )

            button.setObjectName(
                object_name
            )

            button.setMinimumHeight(40)

            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            button.clicked.connect(slot)

            toolbar_layout.addWidget(button)

        root.addWidget(toolbar)

        # ----------------------------------------------------
        # MAIN WORKSPACE
        # ----------------------------------------------------

        workspace = QHBoxLayout()
        workspace.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(12)

        right = QVBoxLayout()
        right.setSpacing(12)

        # ----------------------------------------------------
        # TABLE CARD
        # ----------------------------------------------------

        table_card = QFrame()
        table_card.setObjectName(
            "projectsTableCard"
        )

        table_layout = QVBoxLayout(
            table_card
        )

        table_layout.setContentsMargins(
            14,
            13,
            14,
            14,
        )

        table_layout.setSpacing(9)

        table_head = QHBoxLayout()

        heading_box = QVBoxLayout()
        heading_box.setSpacing(2)

        heading = QLabel(
            translate_text(
                "Projects List"
            )
        )

        heading.setObjectName(
            "projectsSectionTitle"
        )

        self.kpi = QLabel()
        self.kpi.setObjectName(
            "projectsSectionSubtitle"
        )

        heading_box.addWidget(heading)
        heading_box.addWidget(self.kpi)

        table_head.addLayout(
            heading_box,
            1,
        )

        self.view_btn = QPushButton(
            translate_text("▦  Table")
        )

        self.view_btn.setObjectName(
            "viewModeButton"
        )

        self.view_btn.setCheckable(True)
        self.view_btn.setChecked(True)

        self.view_btn.clicked.connect(
            lambda: self._set_view_mode("table")
        )

        self.cards_btn = QPushButton(
            translate_text("▦  Cards")
        )

        self.cards_btn.setObjectName(
            "viewModeSecondary"
        )

        self.cards_btn.setCheckable(True)
        self.cards_btn.setChecked(False)

        self.cards_btn.clicked.connect(
            lambda: self._set_view_mode("cards")
        )

        table_head.addWidget(
            self.view_btn
        )

        table_head.addWidget(
            self.cards_btn
        )

        table_layout.addLayout(
            table_head
        )

        self.view_stack = QStackedWidget()
        self.view_stack.setObjectName(
            "projectsViewStack"
        )

        # ----------------------------------------------------
        # PROJECT TABLE
        # ----------------------------------------------------

        self.table = QTableWidget(
            0,
            10,
        )

        self.table.setObjectName(
            "projectsTable"
        )

        self.table.setHorizontalHeaderLabels(
            [
                translate_text("ID"),
                translate_text("Project name"),
                translate_text("Authority"),
                translate_text("Type"),
                translate_text("Contract code"),
                translate_text("Start date"),
                translate_text("End date"),
                translate_text("Budget HT"),
                translate_text("Budget TTC"),
                translate_text("Status"),
            ]
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self.table.doubleClicked.connect(
            self.edit_project
        )

        self.table.itemSelectionChanged.connect(
            self._sync_table_selection
        )

        self.table.verticalHeader().setVisible(
            False
        )

        self.table.setAlternatingRowColors(
            True
        )

        self.table.setShowGrid(False)

        self.table.setSortingEnabled(
            True
        )

        self.table.setWordWrap(False)

        self.table.setMinimumHeight(345)

        self.table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.table.setFocusPolicy(
            Qt.FocusPolicy.StrongFocus
        )

        header = self.table.horizontalHeader()

        header.setHighlightSections(False)
        header.setStretchLastSection(False)

        widths = {
            0: 105,
            1: 185,
            2: 170,
            3: 110,
            4: 165,
            5: 98,
            6: 98,
            7: 140,
            8: 140,
            9: 92,
        }

        for column, width in widths.items():
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.Interactive,
            )

            header.resizeSection(
                column,
                width,
            )

        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )

        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch,
        )

        self.view_stack.addWidget(
            self.table
        )

        # ----------------------------------------------------
        # CARDS VIEW
        # ----------------------------------------------------

        self.cards_scroll = QScrollArea()

        self.cards_scroll.setObjectName(
            "projectCardsScroll"
        )

        self.cards_scroll.setWidgetResizable(
            True
        )

        self.cards_scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.cards_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.cards_container = QWidget()

        self.cards_layout = QVBoxLayout(
            self.cards_container
        )

        self.cards_layout.setContentsMargins(
            2,
            2,
            8,
            8,
        )

        self.cards_layout.setSpacing(10)

        self.cards_scroll.setWidget(
            self.cards_container
        )

        self.view_stack.addWidget(
            self.cards_scroll
        )

        table_layout.addWidget(
            self.view_stack,
            1,
        )

        left.addWidget(
            table_card,
            1,
        )

        # ----------------------------------------------------
        # ANALYTICS
        # ----------------------------------------------------

        analytics = QHBoxLayout()
        analytics.setSpacing(12)

        self.budget_panel = SummaryPanel(
            "Budget Overview",
            money(0),
            "",
        )

        self.expense_panel = SummaryPanel(
            "Expenses Trend",
            money(0),
            "",
        )

        self.status_panel = SummaryPanel(
            "Activity Summary",
            "0",
            "",
        )

        for panel in (
            self.budget_panel,
            self.expense_panel,
            self.status_panel,
        ):
            panel.setMinimumHeight(215)

            panel.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

            analytics.addWidget(
                panel,
                1,
            )

        left.addLayout(
            analytics
        )

        # ----------------------------------------------------
        # RIGHT RAIL
        # ----------------------------------------------------

        self.stats_panel = StatsPanel()
        self.activity_panel = ActivityPanel()
        self.quick_panel = QuickPanel()

        right.addWidget(
            self.stats_panel
        )

        right.addWidget(
            self.activity_panel,
            1,
        )

        right.addWidget(
            self.quick_panel
        )

        workspace.addLayout(
            left,
            4,
        )

        workspace.addLayout(
            right,
            1,
        )

        root.addLayout(
            workspace,
            1,
        )

        scroll.setWidget(
            content
        )

        self.body.addWidget(
            scroll
        )

    # ========================================================
    # View mode
    # ========================================================

    def _set_view_mode(self, mode):
        """Switch between table and cards."""

        cards = mode == "cards"

        self.view_stack.setCurrentIndex(
            1 if cards else 0
        )

        self.cards_btn.setChecked(
            cards
        )

        self.view_btn.setChecked(
            not cards
        )

        if cards:
            self._populate_cards_from_table()

    # ========================================================
    # Selection
    # ========================================================

    def _select_project_id(self, project_id):
        """Synchronize card selection with the table."""

        selected_id = str(project_id)

        self._selected_project_id = selected_id

        for row in range(
            self.table.rowCount()
        ):
            item = self.table.item(
                row,
                0,
            )

            if (
                item is not None
                and item.text() == selected_id
            ):
                self.table.setCurrentCell(
                    row,
                    0,
                )

                self.table.selectRow(
                    row
                )

                break

        self._update_card_selection()

    def _update_card_selection(self):
        """Update selected state of visible project cards."""

        selected_id = (
            self._selected_project_id
        )

        for index in range(
            self.cards_layout.count()
        ):
            item = self.cards_layout.itemAt(index)

            if item is None:
                continue

            widget = item.widget()

            if isinstance(
                widget,
                ProjectCard,
            ):
                widget.set_selected(
                    widget.project_id
                    == selected_id
                )

    def _populate_cards_from_table(self):
        """Build cards from the same records shown in the table."""

        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)

            if item is None:
                continue

            if item is not None:
                widget = item.widget()

                if widget is not None:
                    widget.deleteLater()

        selected_id = (
            self._selected_project_id
        )

        for project in self._project_rows:
            card = ProjectCard(
                project
            )

            card.clicked.connect(
                self._select_project_id
            )

            card.set_selected(
                card.project_id
                == selected_id
            )

            self.cards_layout.addWidget(
                card
            )

        self.cards_layout.addStretch(
            1
        )

    def _sync_table_selection(self):
        """Keep selected project ID synchronized with the table."""

        row = self.table.currentRow()

        project_id = None

        if row >= 0:
            item = self.table.item(
                row,
                0,
            )

            if item is not None:
                project_id = item.text()

        self._selected_project_id = (
            str(project_id)
            if project_id
            else None
        )

        self._update_card_selection()

    def selected_id(self):
        """Return the currently selected project ID."""

        current = (
            self._selected_project_id
        )

        if current:
            for row in range(
                self.table.rowCount()
            ):
                item = self.table.item(
                    row,
                    0,
                )

                if (
                    item is not None
                    and item.text() == str(current)
                ):
                    return str(current)

            self._selected_project_id = None

        row = self.table.currentRow()

        if row >= 0:
            item = self.table.item(
                row,
                0,
            )

            if item is not None:
                self._selected_project_id = (
                    item.text()
                )

                return item.text()

        return None

    # ========================================================
    # Analytics navigation
    # ========================================================

    def apply_analytics_project_filter(self, project_id):
        """Apply an exact project filter requested by an analytics chart."""
        target = str(project_id).strip()
        if not target:
            return
        self._analytics_project_id = target
        self.load()

    def clear_analytics_project_filter(self):
        """Clear the exact analytics project filter."""
        self._analytics_project_id = None
        self.load()

    # ========================================================
    # Data loading
    # ========================================================

    def load(self):
        """Load projects, filters, KPIs and analytics."""

        previous_id = (
            self._selected_project_id
        )

        conn = get_connection()

        try:
            query = """
                SELECT
                    project_id,
                    project_name,
                    contracting_authority,
                    project_type,
                    contract_code,
                    start_date,
                    end_date,
                    budget_ht,
                    budget_ttc,
                    status
                FROM projects
                WHERE 1=1
            """

            params = []

            analytics_project_id = getattr(self, "_analytics_project_id", None)
            if analytics_project_id:
                query += " AND project_id = ?"
                params.append(analytics_project_id)

            term = (
                self.search.text().strip()
                if hasattr(self, "search")
                else ""
            )

            if term:
                query += """
                    AND (
                        project_name LIKE ?
                        OR contracting_authority LIKE ?
                        OR contract_code LIKE ?
                    )
                """

                params.extend(
                    [
                        f"%{term}%",
                        f"%{term}%",
                        f"%{term}%",
                    ]
                )

            status = (
                self.status_filter.currentData()
                if hasattr(
                    self,
                    "status_filter",
                )
                else "All statuses"
            )

            status = (
                status
                or "All statuses"
            )

            if status != "All statuses":
                query += " AND status=?"
                params.append(status)

            query += """
                ORDER BY
                    updated_at DESC,
                    project_name
            """

            rows = conn.execute(
                query,
                params,
            ).fetchall()

            self._project_rows = [
                tuple(row)
                for row in rows
            ]

            # ------------------------------------------------
            # Preserve selection if the selected project
            # still exists after filtering.
            # ------------------------------------------------

            visible_ids = {
                str(row[0])
                for row in self._project_rows
            }

            if (
                previous_id
                and str(previous_id)
                in visible_ids
            ):
                self._selected_project_id = (
                    str(previous_id)
                )
            else:
                self._selected_project_id = None

            # ------------------------------------------------
            # Populate table.
            # Sorting is disabled while inserting rows.
            # ------------------------------------------------

            self.table.setSortingEnabled(
                False
            )

            self.table.clearContents()
            self.table.setRowCount(
                len(rows)
            )

            self.table.setAlternatingRowColors(
                True
            )

            from theme import theme_color

            status_colors = {
                "Active": theme_color(
                    "success"
                ),
                "Completed": theme_color(
                    "info"
                ),
                "Suspended": theme_color(
                    "warning"
                ),
                "Archived": theme_color(
                    "danger"
                ),
            }

            for row_index, row in enumerate(
                rows
            ):
                for column, value in enumerate(
                    row
                ):
                    if column in (7, 8):
                        text = money(
                            value or 0
                        )
                    else:
                        text = (
                            ""
                            if value is None
                            else str(value)
                        )

                    item = QTableWidgetItem(
                        text
                    )

                    if column in (
                        0,
                        1,
                        2,
                        3,
                        4,
                    ):
                        alignment = (
                            Qt.AlignmentFlag.AlignLeft
                        )
                    else:
                        alignment = (
                            Qt.AlignmentFlag.AlignCenter
                        )

                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignVCenter
                        | alignment
                    )

                    if column == 3 and text:
                        item.setText(
                            "◆ " + text
                        )

                        item.setForeground(
                            QColor(
                                theme_color(
                                    "info"
                                )
                            )
                        )

                    elif (
                        column == 9
                        and text
                    ):
                        color = status_colors.get(
                            text,
                            theme_color(
                                "text_primary"
                            ),
                        )

                        item.setText(
                            "● " + text
                        )

                        item.setForeground(
                            QColor(color)
                        )

                        background = QColor(
                            color
                        )

                        background.setAlpha(
                            24
                        )

                        item.setBackground(
                            background
                        )

                    self.table.setItem(
                        row_index,
                        column,
                        item,
                    )

                self.table.setRowHeight(
                    row_index,
                    42,
                )

            self.table.setSortingEnabled(
                True
            )

            # ------------------------------------------------
            # Restore table selection.
            # ------------------------------------------------

            if self._selected_project_id:
                self._select_project_in_table(
                    self._selected_project_id
                )

            # ------------------------------------------------
            # Cards.
            # ------------------------------------------------

            if (
                self.view_stack.currentIndex()
                == 1
            ):
                self._populate_cards_from_table()

            # ------------------------------------------------
            # Global project statistics.
            # ------------------------------------------------

            total = int(
                conn.execute(
                    "SELECT COUNT(*) FROM projects"
                ).fetchone()[0]
                or 0
            )

            active = int(
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM projects
                    WHERE status='Active'
                    """
                ).fetchone()[0]
                or 0
            )

            completed = int(
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM projects
                    WHERE status='Completed'
                    """
                ).fetchone()[0]
                or 0
            )

            archived = int(
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM projects
                    WHERE status='Archived'
                    """
                ).fetchone()[0]
                or 0
            )

            suspended = int(
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM projects
                    WHERE status='Suspended'
                    """
                ).fetchone()[0]
                or 0
            )

            budget = (
                conn.execute(
                    """
                    SELECT
                        COALESCE(
                            SUM(budget_ht),
                            0
                        )
                    FROM projects
                    """
                ).fetchone()[0]
                or 0
            )

            expenses = (
                conn.execute(
                    """
                    SELECT
                        COALESCE(
                            SUM(amount),
                            0
                        )
                    FROM expenses
                    """
                ).fetchone()[0]
                or 0
            )

            # ------------------------------------------------
            # KPI cards.
            # ------------------------------------------------

            self.kpi.setText(
                translate_text(
                    f"{total} projects • "
                    f"{active} active • "
                    f"Total budget HT: "
                    f"{money(budget)}"
                )
            )

            self.metric_active.value_label.setText(
                str(total)
            )

            self.metric_budget.value_label.setText(
                money(budget)
            )

            self.metric_expenses.value_label.setText(
                money(expenses)
            )

            self.metric_total.value_label.setText(
                str(total)
            )

            # ------------------------------------------------
            # Budget panel.
            # ------------------------------------------------

            self.budget_panel.value_label.setText(
                money(budget)
            )

            budget_float = float(
                budget or 0
            )

            expense_float = float(
                expenses or 0
            )

            used_pct = (
                expense_float
                / budget_float
                * 100
                if budget_float > 0
                else 0.0
            )

            remaining = max(
                0.0,
                budget_float
                - expense_float,
            )

            self.budget_panel.detail_label.setText(
                translate_text(
                    f"Used {money(expenses)} • "
                    f"{used_pct:.2f}% of budget"
                )
            )

            self.budget_panel.extra_label.setText(
                translate_text(
                    f"Remaining\n"
                    f"{money(remaining)}\n\n"
                    f"Used\n"
                    f"{money(expenses)}"
                )
            )

            budget_chart = (
                self.budget_panel.chart
            )

            if isinstance(
                budget_chart,
                BudgetDonutWidget,
            ):
                budget_chart.set_budget(
                    budget,
                    expenses,
                )

            # ------------------------------------------------
            # Expense trend.
            # ------------------------------------------------

            self.expense_panel.value_label.setText(
                money(expenses)
            )

            self.expense_panel.detail_label.setText(
                translate_text(
                    f"Recorded expenses across "
                    f"{total} project(s)"
                )
            )

            month_keys = []

            now = datetime.now(timezone.utc)

            for back in range(
                5,
                -1,
                -1,
            ):
                year = now.year
                month = (
                    now.month - back
                )

                while month <= 0:
                    year -= 1
                    month += 12

                month_keys.append(
                    f"{year:04d}-{month:02d}"
                )

            expense_by_month = {
                row[0]: float(
                    row[1] or 0
                )
                for row in conn.execute(
                    """
                    SELECT
                        strftime('%Y-%m', date),
                        COALESCE(
                            SUM(amount),
                            0
                        )
                    FROM expenses
                    WHERE date IS NOT NULL
                    GROUP BY
                        strftime('%Y-%m', date)
                    """
                ).fetchall()
            }

            monthly = [
                expense_by_month.get(
                    key,
                    0.0,
                )
                for key in month_keys
            ]

            labels = []

            for key in month_keys:
                try:
                    month_name = datetime.strptime(
                        key,
                        "%Y-%m",
                    ).replace(tzinfo=timezone.utc).strftime("%B")

                    labels.append(
                        translate_text(
                            month_name
                        )
                    )

                except ValueError:
                    labels.append(
                        key[5:]
                    )

            expense_chart = (
                self.expense_panel.chart
            )

            if isinstance(
                expense_chart,
                MiniLineChart,
            ):
                expense_chart.set_series(
                    monthly,
                    labels,
                )

            # ------------------------------------------------
            # Status summary.
            # ------------------------------------------------

            self.status_panel.value_label.setText(
                str(total)
            )

            self.status_panel.detail_label.setText(
                translate_text(
                    f"Active {active} • "
                    f"Completed {completed} • "
                    f"Suspended {suspended} • "
                    f"Archived {archived}"
                )
            )

            self.status_panel.extra_label.setText(
                translate_text(
                    f"Active\n{active}\n\n"
                    f"Completed\n{completed}\n\n"
                    f"Suspended\n{suspended}\n\n"
                    f"Archived\n{archived}"
                )
            )

            status_chart = (
                self.status_panel.chart
            )

            if isinstance(
                status_chart,
                ActivityDonutWidget,
            ):
                status_chart.set_activity(
                    active,
                    completed,
                    suspended,
                    archived,
                )

            # ------------------------------------------------
            # Right-side statistics.
            # ------------------------------------------------

            self.stats_panel.donut.set_values(
                active,
                completed,
                suspended,
                archived,
                center_text=str(total),
                subtitle="Projects",
            )

            self.stats_panel.legend.setText(
                translate_text(
                    f"● Active        {active}\n"
                    f"● On Hold       {suspended}\n"
                    f"● Completed     {completed}\n"
                    f"● Cancelled     {archived}"
                )
            )

            # ------------------------------------------------
            # Recent activity.
            # ------------------------------------------------

            recent = []

            project_activity = conn.execute(
                """
                SELECT
                    'project',
                    project_name,
                    COALESCE(
                        updated_at,
                        created_at,
                        ''
                    )
                FROM projects
                ORDER BY
                    COALESCE(
                        updated_at,
                        created_at
                    ) DESC
                LIMIT 3
                """
            ).fetchall()

            for row in project_activity:
                recent.append(
                    (
                        row[0],
                        "New project created",
                        str(
                            row[1]
                            or "Project"
                        ),
                        str(
                            row[2]
                            or ""
                        ),
                    )
                )

            expense_activity = conn.execute(
                """
                SELECT
                    'expense',
                    COALESCE(
                        description,
                        'Expense'
                    ),
                    amount,
                    COALESCE(
                        updated_at,
                        created_at,
                        date,
                        ''
                    )
                FROM expenses
                ORDER BY
                    COALESCE(
                        updated_at,
                        created_at,
                        date
                    ) DESC
                LIMIT 3
                """
            ).fetchall()

            for row in expense_activity:
                recent.append(
                    (
                        row[0],
                        "Expense recorded",
                        (
                            f"{money(row[2])} • "
                            f"{row[1]}"
                        ),
                        str(
                            row[3]
                            or ""
                        ),
                    )
                )

            recent.sort(
                key=lambda value: value[3],
                reverse=True,
            )

            self._set_activity(
                total,
                budget,
                expenses,
                recent,
            )

            self.quick_panel.body_label.setText(
                translate_text(
                    "Use New Project to register a contract.\n"
                    "Double-click a row to edit.\n"
                    "Archive preserves project history."
                )
            )

        except sqlite3.Error as exc:
            self.error(
                translate_text(
                    f"Could not load projects.\n\n{exc}"
                )
            )

        finally:
            conn.close()

    def _select_project_in_table(
        self,
        project_id: str,
    ):
        """Select a project in the table without relying on row order."""

        for row in range(
            self.table.rowCount()
        ):
            item = self.table.item(
                row,
                0,
            )

            if (
                item is not None
                and item.text()
                == str(project_id)
            ):
                self.table.setCurrentCell(
                    row,
                    0,
                )

                self.table.selectRow(
                    row
                )

                return

    # ========================================================
    # Activity
    # ========================================================

    def _set_activity(
        self,
        total,
        budget,
        expenses,
        recent_rows=None,
    ):
        """Refresh recent activity widgets."""

        layout = (
            self.activity_panel.activity_layout
        )

        while layout.count():
            item = layout.takeAt(0)

            widget = (
                item.widget()
                if item is not None
                else None
            )

            if widget is not None:
                widget.deleteLater()

        entries = []

        for row in (
            recent_rows
            or []
        ):
            kind, title, detail, *stamp = row

            icon = {
                "project": "+",
                "expense": "◉",
                "payment": "↗",
            }.get(
                kind,
                "•",
            )

            timestamp = (
                stamp[0]
                if stamp
                else ""
            )

            suffix = (
                self._relative_time(
                    timestamp
                )
                if timestamp
                else ""
            )

            display_detail = (
                f"{detail}\n{suffix}"
                if suffix
                else str(detail)
            )

            entries.append(
                (
                    icon,
                    title,
                    display_detail,
                )
            )

        if not entries:
            entries = [
                (
                    "+",
                    "New project created",
                    f"{total} project(s) in portfolio",
                ),
                (
                    "◉",
                    "Expense recorded",
                    money(expenses)
                    + " • Expenses",
                ),
                (
                    "↗",
                    "Project budget tracked",
                    money(budget)
                    + " • Budget HT",
                ),
            ]

        for icon, title, detail in entries[:5]:
            row_widget = QWidget()

            row_widget.setLayout(
                self._activity_item(
                    icon,
                    title,
                    detail,
                )
            )

            bubble = row_widget.findChild(
                QLabel,
                "activityBubble",
            )

            if bubble is not None:
                role = (
                    "expense"
                    if icon == "◉"
                    else (
                        "payment"
                        if icon == "↗"
                        else "project"
                    )
                )

                bubble.setProperty(
                    "activityRole",
                    role,
                )

                bubble.style().unpolish(
                    bubble
                )

                bubble.style().polish(
                    bubble
                )

            layout.addWidget(
                row_widget
            )

        layout.addStretch(1)

    @staticmethod
    def _activity_item(
        icon,
        title,
        detail,
    ):
        """Create one activity row."""

        row = QHBoxLayout()
        row.setSpacing(8)

        bubble = QLabel(icon)

        bubble.setObjectName(
            "activityBubble"
        )

        bubble.setProperty(
            "activityRole",
            "project",
        )

        bubble.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        bubble.setFixedSize(
            30,
            30,
        )

        row.addWidget(
            bubble
        )

        text = QVBoxLayout()
        text.setSpacing(0)

        title_label = QLabel(
            translate_text(title)
        )

        title_label.setObjectName(
            "activityTitle"
        )

        detail_label = QLabel(
            translate_text(detail)
        )

        detail_label.setObjectName(
            "activityDetail"
        )

        text.addWidget(
            title_label
        )

        text.addWidget(
            detail_label
        )

        row.addLayout(
            text,
            1,
        )

        return row

    @staticmethod
    def _relative_time(raw_timestamp):
        """Convert an ISO timestamp into a compact relative label."""

        value = str(
            raw_timestamp or ""
        ).strip()

        if not value:
            return translate_text(
                "Recently"
            )

        try:
            parsed = datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )

            now = (
                datetime.now(
                    parsed.tzinfo
                )
                if parsed.tzinfo
                else datetime.now(timezone.utc)
            )

            seconds = max(
                0,
                int(
                    (
                        now - parsed
                    ).total_seconds()
                ),
            )

            if seconds < 60:
                return translate_text(
                    "Just now"
                )

            minutes = seconds // 60

            if minutes < 60:
                return translate_text(
                    f"{minutes} min ago"
                )

            hours = minutes // 60

            if hours < 24:
                return translate_text(
                    f"{hours} h ago"
                )

            days = hours // 24

            return translate_text(
                f"{days} d ago"
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            return translate_text(
                "Recently"
            )

    # ========================================================
    # Page lifecycle
    # ========================================================

    def showEvent(self, event):
        super().showEvent(event)
        self.load()

    # ========================================================
    # CRUD
    # ========================================================

    def add_project(self):
        self.project_dialog()

    def edit_project(self):
        project_id = self.selected_id()

        if project_id:
            self.project_dialog(
                project_id
            )
        else:
            self.error(
                "Select a project first."
            )

    def delete_project(self):
        project_id = self.selected_id()

        if not project_id:
            self.error(
                "Select a project first."
            )
            return

        conn = get_connection()

        try:
            dependencies = []

            dependency_queries = [
                (
                    "expenses",
                    """
                    SELECT COUNT(*)
                    FROM expenses
                    WHERE project_id=?
                    """,
                ),
                (
                    "Métré",
                    """
                    SELECT COUNT(*)
                    FROM metre_items
                    WHERE project_id=?
                    """,
                ),
                (
                    "Situations",
                    """
                    SELECT COUNT(*)
                    FROM situations
                    WHERE project_id=?
                    """,
                ),
                (
                    "attendance",
                    """
                    SELECT COUNT(*)
                    FROM attendance
                    WHERE project_id=?
                    """,
                ),
                (
                    "payments",
                    """
                    SELECT COUNT(*)
                    FROM project_payments
                    WHERE project_id=?
                    """,
                ),
            ]

            for name, query in dependency_queries:
                try:
                    count = int(
                        conn.execute(
                            query,
                            (project_id,),
                        ).fetchone()[0]
                        or 0
                    )

                    dependencies.append(
                        (
                            name,
                            count,
                        )
                    )

                except sqlite3.Error:
                    # Preserve existing behavior while allowing
                    # installations without an optional table.
                    continue

            blocked = [
                f"{name}={count}"
                for name, count
                in dependencies
                if count
            ]

        finally:
            conn.close()

        if blocked:
            self.error(
                translate_text(
                    "This project has historical records and cannot be deleted.\n\n"
                    "Archive the project instead so its financial and operational history remains intact."
                )
                + "\n\n"
                + ", ".join(blocked)
            )

            return

        confirmed = self.confirm(
            translate_text(
                f"Delete project {project_id}? "
                "This is allowed only because it has no dependent history."
            ),
            translate_text(
                "Delete project"
            ),
        )

        if not confirmed:
            return

        try:
            delete_project_service(
                project_id
            )

            self._selected_project_id = None
            self.load()

        except (
            sqlite3.Error,
            TypeError,
            ValueError,
        ) as exc:
            self.error(
                str(exc)
            )

    def archive_project(self):
        project_id = self.selected_id()

        if not project_id:
            self.error(
                "Select a project first."
            )
            return

        confirmed = self.confirm(
            translate_text(
                f"Archive project {project_id}? "
                "Historical data will be preserved."
            ),
            translate_text(
                "Archive project"
            ),
        )

        if not confirmed:
            return

        try:
            archive_project_service(
                project_id
            )

            self.load()

        except (
            sqlite3.Error,
            TypeError,
            ValueError,
        ) as exc:
            self.error(
                str(exc)
            )

    def restore_project(self):
        project_id = self.selected_id()

        if not project_id:
            self.error(
                "Select a project first."
            )
            return

        conn = get_connection()

        try:
            row = conn.execute(
                """
                SELECT status
                FROM projects
                WHERE project_id=?
                """,
                (project_id,),
            ).fetchone()

            if not row:
                self.error(
                    "Project not found."
                )
                return

            if row["status"] != "Archived":
                self.error(
                    "Only archived projects can be restored."
                )
                return

            conn.execute(
                """
                UPDATE projects
                SET
                    status='Active',
                    updated_at=CURRENT_TIMESTAMP
                WHERE project_id=?
                """,
                (project_id,),
            )

            conn.commit()

        except (
            sqlite3.Error,
            TypeError,
            ValueError,
        ) as exc:
            conn.rollback()

            self.error(
                str(exc)
            )

            return

        finally:
            conn.close()

        self.load()

    # ========================================================
    # Project dialog
    # ========================================================

    def project_dialog(
        self,
        project_id=None,
    ):
        """Open the project create/edit dialog."""

        conn = get_connection()

        try:
            existing = (
                conn.execute(
                    """
                    SELECT *
                    FROM projects
                    WHERE project_id=?
                    """,
                    (project_id,),
                ).fetchone()
                if project_id
                else None
            )

        finally:
            conn.close()

        dialog = QDialog(self)

        dialog.setWindowTitle(
            translate_text(
                "Edit Project"
                if existing
                else "New Project"
            )
        )

        dialog.resize(
            980,
            760,
        )

        dialog.setMinimumSize(
            900,
            680,
        )

        # ----------------------------------------------------
        # Theme detection
        # ----------------------------------------------------

        app_window = self.window()


        try:
            theme_method = getattr(
                app_window,
                "current_theme",
                None,
            )

            if callable(theme_method):
                str(
                    theme_method()
                ).strip().title()

        except (
            AttributeError,
            RuntimeError,
            TypeError,
        ):
            pass

        # Use the central theme resolver so this dialog follows both the selected
        # Light/Dark mode AND the currently selected professional palette.
        set_theme_style(
            dialog,
            """
            QDialog { background: @surface@; color: @text_primary@; }
            QFrame#projectDialogHeader {
                background: @surface_alt@; color: @text_primary@;
                border: 1px solid @border@; border-radius: 10px;
            }
            QLabel#projectDialogIcon, QLabel#projectSectionIcon {
                color: @primary@; background: @hover@;
                border: 1px solid @border@; border-radius: 8px; font-weight: 700;
            }
            QLabel#projectDialogTitle, QLabel#projectSectionTitle {
                color: @text_primary@; background: transparent; font-weight: 700;
            }
            QLabel#projectDialogSubtitle, QLabel#projectFieldLabel, QLabel#projectCalculatedDate {
                color: @text_secondary@; background: transparent;
            }
            QFrame#projectSection {
                background: @surface@; color: @text_primary@;
                border: 1px solid @border@; border-radius: 8px;
            }
            QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
                background: @components.forms.search@; color: @components.forms.input_text@;
                border: 1px solid @components.forms.input_border@; border-radius: 7px;
                padding: 6px 10px;
                selection-background-color: @primary@; selection-color: @components.theme.on_primary@;
            }
            QLineEdit:hover, QComboBox:hover, QDateEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QPlainTextEdit:hover {
                background: @hover@; border-color: @primary@;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus {
                border: 2px solid @primary@;
            }
            QComboBox QAbstractItemView {
                background: @components.forms.combo_popup@; color: @components.forms.input_text@;
                border: 1px solid @border@;
                selection-background-color: @primary@; selection-color: @components.theme.on_primary@;
            }
            QScrollArea { background: transparent; border: none; }
            QDialogButtonBox QPushButton {
                min-height: 34px; padding: 6px 18px;
                border: 1px solid @border@; border-radius: 7px;
                background: @components.buttons.button_secondary@;
                color: @components.buttons.button_secondary_text@;
            }
            QDialogButtonBox QPushButton:hover {
                border-color: @primary@; background: @hover@; color: @text_primary@;
            }
            """
        )

        # ----------------------------------------------------
        # Helpers
        # ----------------------------------------------------

        def make_label(
            text,
            object_name="projectFieldLabel",
        ):
            widget = QLabel(
                translate_text(text)
            )

            widget.setObjectName(
                object_name
            )

            return widget

        def make_section(
            title,
            icon_text,
        ):
            frame = QFrame()

            frame.setObjectName(
                "projectSection"
            )

            frame.setFrameShape(
                QFrame.Shape.StyledPanel
            )

            frame.setFrameShadow(
                QFrame.Shadow.Plain
            )

            layout = QVBoxLayout(frame)

            layout.setContentsMargins(
                14,
                12,
                14,
                14,
            )

            layout.setSpacing(10)

            heading = QHBoxLayout()
            heading.setSpacing(8)

            icon = QLabel(
                icon_text
            )

            icon.setObjectName(
                "projectSectionIcon"
            )

            icon.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            icon.setFixedSize(
                30,
                30,
            )

            heading.addWidget(
                icon
            )

            title_label = QLabel(
                translate_text(title)
            )

            title_label.setObjectName(
                "projectSectionTitle"
            )

            heading.addWidget(
                title_label,
                1,
            )

            layout.addLayout(
                heading
            )

            form = QFormLayout()

            form.setFieldGrowthPolicy(
                QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
            )

            form.setLabelAlignment(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter
            )

            form.setHorizontalSpacing(
                18
            )

            form.setVerticalSpacing(
                8
            )

            layout.addLayout(
                form
            )

            return frame, form

        def prepare_field(widget):
            widget.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

            widget.setMinimumHeight(
                34
            )

            return widget

        # ----------------------------------------------------
        # Main dialog layout
        # ----------------------------------------------------

        root = QVBoxLayout(
            dialog
        )

        root.setContentsMargins(
            18,
            16,
            18,
            14,
        )

        root.setSpacing(12)

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        header = QFrame()

        header.setObjectName(
            "projectDialogHeader"
        )

        header.setFrameShape(
            QFrame.Shape.StyledPanel
        )

        header.setFrameShadow(
            QFrame.Shadow.Plain
        )

        header_layout = QHBoxLayout(
            header
        )

        header_layout.setContentsMargins(
            14,
            12,
            14,
            12,
        )

        header_layout.setSpacing(12)

        header_icon = QLabel("PR")

        header_icon.setObjectName(
            "projectDialogIcon"
        )

        header_icon.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        header_icon.setFixedSize(
            44,
            44,
        )

        header_layout.addWidget(
            header_icon
        )

        header_text = QVBoxLayout()
        header_text.setSpacing(2)

        header_title = QLabel(
            translate_text(
                "Edit Project"
                if existing
                else "New Project"
            )
        )

        header_title.setObjectName(
            "projectDialogTitle"
        )

        header_subtitle = QLabel(
            translate_text(
                "Update project information and financial details"
                if existing
                else "Create a new project and organize its contract information"
            )
        )

        header_subtitle.setObjectName(
            "projectDialogSubtitle"
        )

        header_subtitle.setWordWrap(
            True
        )

        header_text.addWidget(
            header_title
        )

        header_text.addWidget(
            header_subtitle
        )

        header_layout.addLayout(
            header_text,
            1,
        )

        root.addWidget(
            header
        )

        # ----------------------------------------------------
        # Scrollable content
        # ----------------------------------------------------

        content = QWidget()

        content_layout = QVBoxLayout(
            content
        )

        content_layout.setContentsMargins(
            1,
            1,
            8,
            4,
        )

        content_layout.setSpacing(12)

        content_scroll = QScrollArea()

        content_scroll.setWidgetResizable(
            True
        )

        content_scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        content_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        content_scroll.setWidget(
            content
        )

        root.addWidget(
            content_scroll,
            1,
        )

        # ----------------------------------------------------
        # Basic information
        # ----------------------------------------------------

        basic_card, basic_form = make_section(
            "Project Information",
            "01",
        )

        name = prepare_field(
            QLineEdit()
        )

        name.setPlaceholderText(
            translate_text(
                "Project name"
            )
        )

        summary = prepare_field(
            QLineEdit()
        )

        summary.setPlaceholderText(
            translate_text(
                "Short name"
            )
        )

        authority = prepare_field(
            LocalizedComboBox()
        )

        authority.setEditable(
            True
        )

        authority.setInsertPolicy(
            QComboBox.InsertPolicy.NoInsert
        )

        authority.setPlaceholderText(
            translate_text(
                "Select or type contracting authority"
            )
        )

        authorities = [
            "DTP — مديرية الأشغال العمومية",
            "DTPB — مديرية الأشغال العمومية والمنشآت القاعدية",
            "DLEP — مديرية السكن والتجهيزات العمومية",
            "DUAC — مديرية التعمير والهندسة المعمارية والبناء",
            "DEP — مديرية التجهيزات العمومية",
            "DR — مديرية الري",
            "DHW — مديرية الموارد المائية",
            "DJS — مديرية الشباب والرياضة",
            "DE — مديرية التربية",
            "DSP — مديرية الصحة والسكان",
            "DSA — مديرية المصالح الفلاحية",
            "DGF — مديرية الغابات",
            "DPE — مديرية الطاقة",
            "DWC — مديرية التجارة",
            "DAS — مديرية النشاط الاجتماعي والتضامن",
            "DPSB — مديرية البرمجة ومتابعة الميزانية",
            "DRAG — مديرية التنظيم والشؤون العامة",
            "DPS — مديرية الحماية المدنية",
            "DTT — مديرية النقل",
            "DPRH — مديرية الموارد البشرية والتكوين",
            "APC — المجلس الشعبي البلدي",
            "APW — المجلس الشعبي الولائي",
            "Wilaya — ولاية",
            "EPIC — مؤسسة عمومية ذات طابع صناعي وتجاري",
            "EPH — المؤسسة العمومية الاستشفائية",
            "EPE — مؤسسة عمومية اقتصادية",
        ]

        authority.addItems(
            authorities
        )

        project_type = prepare_field(
            LocalizedComboBox()
        )

        project_type.setEditable(
            True
        )

        project_type.setInsertPolicy(
            QComboBox.InsertPolicy.NoInsert
        )

        project_type.setPlaceholderText(
            translate_text(
                "Select project type"
            )
        )

        project_types = [
            "بناء",
            "إعادة اعتبار",
            "تأهيل",
            "تموين",
            "تجديد طرقات",
            "إنجاز طرقات",
            "تهيئة حضرية",
            "تهيئة عمرانية",
            "شبكات الصرف الصحي",
            "شبكات المياه",
            "منشآت مائية",
            "منشآت فنية",
            "بناء وتجهيز",
            "ترميم",
            "توسعة",
            "إعادة تهيئة",
            "أشغال عمومية",
            "أشغال مختلفة",
            "أخرى",
        ]

        project_type.addItems(
            project_types
        )

        code = prepare_field(
            QLineEdit()
        )

        code.setPlaceholderText(
            translate_text(
                "Contract code"
            )
        )

        location = prepare_field(
            QLineEdit()
        )

        location.setPlaceholderText(
            translate_text(
                "Project location"
            )
        )

        basic_form.addRow(
            make_label("Project name"),
            name,
        )

        basic_form.addRow(
            make_label("Short name"),
            summary,
        )

        basic_form.addRow(
            make_label(
                "Contracting authority"
            ),
            authority,
        )

        basic_form.addRow(
            make_label("Project type"),
            project_type,
        )

        basic_form.addRow(
            make_label("Contract code"),
            code,
        )

        basic_form.addRow(
            make_label("Location"),
            location,
        )

        content_layout.addWidget(
            basic_card
        )

        # ----------------------------------------------------
        # Contract and schedule
        # ----------------------------------------------------

        dates_card, dates_form = make_section(
            "Contract & Schedule",
            "02",
        )

        today = QDate.currentDate()

        contract_date = prepare_field(
            QDateEdit(today)
        )

        contract_date.setCalendarPopup(
            True
        )

        contract_date.setDisplayFormat(
            qt_date_format()
        )

        start = prepare_field(
            QDateEdit(today)
        )

        start.setCalendarPopup(
            True
        )

        start.setDisplayFormat(
            qt_date_format()
        )

        period = prepare_field(
            QSpinBox()
        )

        period.setRange(
            0,
            10000,
        )

        period.setSuffix(
            " days"
        )

        period.setValue(
            0
        )

        calculated_end = start.date().addDays(
            period.value()
        )

        def calculate_end_date():
            nonlocal calculated_end

            calculated_end = (
                start.date().addDays(
                    period.value()
                )
            )

        start.dateChanged.connect(
            calculate_end_date
        )

        period.valueChanged.connect(
            calculate_end_date
        )

        actual = prepare_field(
            QDateEdit()
        )

        actual.setCalendarPopup(
            True
        )

        actual.setDisplayFormat(
            qt_date_format()
        )

        actual.setSpecialValueText(
            translate_text(
                "Not completed"
            )
        )

        actual.setMinimumDate(
            QDate(
                2000,
                1,
                1,
            )
        )

        actual.setDate(
            QDate(
                2000,
                1,
                1,
            )
        )

        dates_form.addRow(
            make_label("Contract date"),
            contract_date,
        )

        dates_form.addRow(
            make_label("Start date"),
            start,
        )

        dates_form.addRow(
            make_label("Duration"),
            period,
        )

        dates_form.addRow(
            make_label(
                "Actual completion"
            ),
            actual,
        )

        end_info = QLabel()

        end_info.setObjectName(
            "projectCalculatedDate"
        )

        def refresh_end_info():
            calculate_end_date()

            end_info.setText(
                f"{translate_text('Calculated end date')}: "
                f"{calculated_end.toString(qt_date_format())}"
            )

        refresh_end_info()

        start.dateChanged.connect(
            refresh_end_info
        )

        period.valueChanged.connect(
            refresh_end_info
        )

        dates_form.addRow(
            "",
            end_info,
        )

        content_layout.addWidget(
            dates_card
        )

        # ----------------------------------------------------
        # Financial information
        # ----------------------------------------------------

        financial_card, financial_form = make_section(
            "Financial Information",
            "03",
        )

        budget = prepare_field(
            QDoubleSpinBox()
        )

        budget.setRange(
            0,
            1e15,
        )

        budget.setDecimals(
            2
        )

        budget.setSingleStep(
            1000
        )

        tva = prepare_field(
            LocalizedComboBox()
        )

        tva.addItems(
            [
                "19",
                "9",
                translate_text("0"),
            ]
        )

        current_tva = default_tva()

        if current_tva.is_integer():
            tva_value = str(
                int(current_tva)
            )
        else:
            tva_value = str(
                current_tva
            )

        tva.setCurrentText(
            tva_value
        )

        financial_form.addRow(
            make_label("Contract HT"),
            budget,
        )

        financial_form.addRow(
            make_label("TVA %"),
            tva,
        )

        content_layout.addWidget(
            financial_card
        )

        # ----------------------------------------------------
        # Status and description
        # ----------------------------------------------------

        details_card, details_form = make_section(
            "Status & Description",
            "04",
        )

        status = prepare_field(
            LocalizedComboBox()
        )

        status.addItems(
            [
                translate_text("Active"),
                translate_text("Completed"),
                translate_text("Suspended"),
                translate_text("Archived"),
            ]
        )

        status.setCurrentText(
            translate_text("Active")
        )

        description = QPlainTextEdit()

        description.setPlaceholderText(
            translate_text(
                "Project description"
            )
        )

        description.setMinimumHeight(
            105
        )

        description.setMaximumHeight(
            140
        )

        description.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        details_form.addRow(
            make_label("Status"),
            status,
        )

        details_form.addRow(
            make_label("Description"),
            description,
        )

        content_layout.addWidget(
            details_card
        )

        content_layout.addStretch(
            1
        )

        # ----------------------------------------------------
        # Theme-aware widgets
        # ----------------------------------------------------

        for widget in (
            name,
            summary,
            authority,
            project_type,
            code,
            location,
            contract_date,
            start,
            period,
            actual,
            budget,
            tva,
            status,
            description,
        ):
            widget.setProperty(
                "themeAware",
                True,
            )

        header.setProperty(
            "accentRole",
            "primary",
        )

        header_icon.setProperty(
            "accentRole",
            "primary",
        )

        # ----------------------------------------------------
        # Load existing project
        # ----------------------------------------------------

        if existing:

            def get_value(
                column,
                default=None,
            ):
                try:
                    return existing[column]
                except (
                    KeyError,
                    IndexError,
                ):
                    return default

            name.setText(
                get_value(
                    "project_name",
                    "",
                )
                or ""
            )

            summary.setText(
                get_value(
                    "summarised_name",
                    "",
                )
                or ""
            )

            existing_authority = (
                get_value(
                    "contracting_authority",
                    "",
                )
                or ""
            )

            if existing_authority:
                authority.setEditText(
                    existing_authority
                )

            existing_type = (
                get_value(
                    "project_type",
                    "",
                )
                or ""
            )

            if existing_type:
                index = project_type.findText(
                    existing_type
                )

                if index >= 0:
                    project_type.setCurrentIndex(
                        index
                    )
                else:
                    project_type.setEditText(
                        existing_type
                    )

            else:
                project_type.setCurrentIndex(
                    -1
                )

            code.setText(
                get_value(
                    "contract_code",
                    "",
                )
                or ""
            )

            location.setText(
                get_value(
                    "location",
                    "",
                )
                or ""
            )

            description.setPlainText(
                get_value(
                    "description",
                    "",
                )
                or ""
            )

            contract_value = get_value(
                "contract_date"
            )

            if contract_value:
                parsed = QDate.fromString(
                    str(contract_value),
                    "yyyy-MM-dd",
                )

                if parsed.isValid():
                    contract_date.setDate(
                        parsed
                    )

            start_value = get_value(
                "start_date"
            )

            if start_value:
                parsed = QDate.fromString(
                    str(start_value),
                    "yyyy-MM-dd",
                )

                if parsed.isValid():
                    start.setDate(
                        parsed
                    )

            try:
                period_value = int(
                    get_value(
                        "period",
                        0,
                    )
                    or 0
                )
            except (
                TypeError,
                ValueError,
            ):
                period_value = 0

            period.setValue(
                max(
                    0,
                    period_value,
                )
            )

            actual_value = get_value(
                "actual_completion_date"
            )

            if actual_value:
                parsed = QDate.fromString(
                    str(actual_value),
                    "yyyy-MM-dd",
                )

                if parsed.isValid():
                    actual.setDate(
                        parsed
                    )

            try:
                budget_value = float(
                    get_value(
                        "budget_ht",
                        0,
                    )
                    or 0
                )
            except (
                TypeError,
                ValueError,
            ):
                budget_value = 0.0

            budget.setValue(
                max(
                    0.0,
                    budget_value,
                )
            )

            stored_tva = get_value(
                "tva_percent"
            )

            if stored_tva is not None:
                tva.setCurrentText(
                    str(stored_tva)
                )

            status_value = (
                get_value(
                    "status",
                    "Active",
                )
                or "Active"
            )

            status_index = status.findText(
                str(status_value)
            )

            if status_index >= 0:
                status.setCurrentIndex(
                    status_index
                )
            else:
                status.setCurrentText(
                    translate_text(
                        "Active"
                    )
                )

            calculate_end_date()
            refresh_end_info()

        # ----------------------------------------------------
        # Buttons
        # ----------------------------------------------------

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.setObjectName(
            "projectDialogButtons"
        )

        buttons.accepted.connect(
            dialog.accept
        )

        buttons.rejected.connect(
            dialog.reject
        )

        root.addWidget(
            buttons
        )

        # ----------------------------------------------------
        # Show
        # ----------------------------------------------------

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        # ----------------------------------------------------
        # Validation
        # ----------------------------------------------------

        project_name = (
            name.text().strip()
        )

        if not project_name:
            self.error(
                "Project name is required."
            )
            return

        # ----------------------------------------------------
        # End date
        # ----------------------------------------------------

        end_date = start.date().addDays(
            period.value()
        )

        end_string = end_date.toString(
            "yyyy-MM-dd"
        )

        # ----------------------------------------------------
        # Financial calculations
        # ----------------------------------------------------

        ht = float(
            budget.value()
        )

        try:
            tv = float(
                tva.currentText().strip()
                or 0
            )
        except ValueError:
            self.error(
                "Invalid TVA percentage."
            )
            return

        if tv < 0:
            self.error(
                "TVA percentage cannot be negative."
            )
            return

        tax = (
            ht * tv / 100
        )

        ttc = (
            ht + tax
        )

        # ----------------------------------------------------
        # Actual completion date
        # ----------------------------------------------------

        actual_date = None

        if actual.date() != QDate(
            2000,
            1,
            1,
        ):
            actual_date = actual.date().toString(
                "yyyy-MM-dd"
            )

        # ----------------------------------------------------
        # Values
        # ----------------------------------------------------

        values = (
            project_name,
            summary.text().strip()
            or None,
            authority.currentText().strip()
            or None,
            project_type.currentText().strip()
            or None,
            code.text().strip()
            or None,
            contract_date.date().toString(
                "yyyy-MM-dd"
            ),
            start.date().toString(
                "yyyy-MM-dd"
            ),
            int(period.value()),
            end_string,
            ht,
            tv,
            tax,
            ttc,
            status.currentData()
            or status.currentText(),
            location.text().strip()
            or None,
            description.toPlainText().strip()
            or None,
            actual_date,
        )

        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        conn = get_connection()

        try:
            if existing:

                conn.execute(
                    """
                    UPDATE projects SET
                        project_name=?,
                        summarised_name=?,
                        contracting_authority=?,
                        project_type=?,
                        contract_code=?,
                        contract_date=?,
                        start_date=?,
                        period=?,
                        end_date=?,
                        budget_ht=?,
                        tva_percent=?,
                        tva=?,
                        budget_ttc=?,
                        status=?,
                        location=?,
                        description=?,
                        actual_completion_date=?,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE project_id=?
                    """,
                    values
                    + (
                        project_id,
                    ),
                )

                saved_id = str(
                    project_id
                )

            else:
                saved_id = next_id(
                    "projects",
                    "project_id",
                    "prj",
                    3,
                )

                conn.execute(
                    """
                    INSERT INTO projects(
                        project_id,
                        project_name,
                        summarised_name,
                        contracting_authority,
                        project_type,
                        contract_code,
                        contract_date,
                        start_date,
                        period,
                        end_date,
                        budget_ht,
                        tva_percent,
                        tva,
                        budget_ttc,
                        status,
                        location,
                        description,
                        actual_completion_date
                    )
                    VALUES(
                        ?,?,?,?,?,?,?,?,?,?,
                        ?,?,?,?,?,?,?,?
                    )
                    """,
                    (
                        saved_id,
                    )
                    + values,
                )

            conn.commit()

            self._selected_project_id = (
                saved_id
            )

            self.load()

        except sqlite3.IntegrityError as exc:
            conn.rollback()

            self.error(
                translate_text(
                    "Could not save project.\n\n"
                    "The contract code may already be used by "
                    "another project.\n\n"
                    f"{exc}"
                )
            )

        except (
            sqlite3.Error,
            TypeError,
            ValueError,
        ) as exc:
            conn.rollback()

            self.error(
                translate_text(
                    f"Could not save project.\n\n{exc}"
                )
            )

        finally:
            conn.close()
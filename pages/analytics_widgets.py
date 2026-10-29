# ============================================================
# شرح الملف: pages/analytics_widgets.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Compact, theme-aware visual analytics widgets for BuildOffice Pro."""
from __future__ import annotations

import itertools
import time
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QFont, QPainter, QPen
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout

from core.i18n import translate_text
from dev_tools.dev_runtime import is_enabled, record_metric
from theme import set_theme_style, theme_qcolor


# شرح الصنف AnalyticsChart: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class AnalyticsChart(QFrame):
    """Small chart canvas supporting bar, line and donut visualizations."""

    clicked = Signal(str, object)

    def __init__(self, chart_type: str, rows, value_suffix: str = "", interaction_hint: str = ""):
        super().__init__()
        self.chart_type = chart_type
        self.rows = self._normalize_rows(rows)
        self.value_suffix = value_suffix
        self.interaction_hint = interaction_hint
        if interaction_hint:
            self.setToolTip(interaction_hint)
        self.setCursor(Qt.CursorShape.PointingHandCursor if interaction_hint else Qt.CursorShape.ArrowCursor)
        self.setObjectName("analyticsChart")
        self.setMinimumHeight(178)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        set_theme_style(self, "QFrame#analyticsChart { background: transparent; border: none; }")

# شرح الدالة _normalize_rows: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _normalize_rows(rows):
        """Normalize chart values without discarding signed line-chart data."""
        normalized = []
        for label, value in rows or []:
            try:
                numeric = Decimal(str(value))
            except (InvalidOperation, TypeError, ValueError):
                continue
            if numeric.is_finite():
                normalized.append((str(label), numeric))
        return normalized

# شرح الدالة mousePressEvent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self.rows:
            return super().mousePressEvent(event)
        index = self._hit_test(event.position())
        if index is not None:
            label, value = self.rows[index]
            self.clicked.emit(label, value)
            event.accept()
            return
        super().mousePressEvent(event)

# شرح الدالة _hit_test: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _hit_test(self, position):
        x = float(position.x())
        y = float(position.y())
        rect = self.rect().adjusted(8, 8, -8, -8)
        if self.chart_type == "bar":
            values = [float(value) for _, value in self.rows]
            left = rect.left() + 4
            bottom = rect.bottom() - 22
            width = max(12.0, (rect.width() - 12) / max(1, len(values)) - 8)
            for index in range(len(values)):
                bar_x = left + index * (width + 8)
                height = (values[index] / (max(values) or 1.0)) * max(20.0, rect.height() - 46)
                bar_y = bottom - height
                if bar_x <= x <= bar_x + width and bar_y <= y <= bottom:
                    return index
        elif self.chart_type == "line":
            values = [float(value) for _, value in self.rows]
            if not values:
                return None
            points = []
            maximum = max(values) or 1.0
            minimum = min(values) if values else 0.0
            span = max(1.0, maximum - minimum)
            for index, numeric in enumerate(values):
                px = rect.left() + 6 + ((rect.width() - 12) * index / max(1, len(values) - 1))
                py = rect.bottom() - 30 - ((numeric - minimum) / span) * max(30.0, rect.height() - 50)
                points.append((px, py))
            nearest = min(range(len(points)), key=lambda i: (points[i][0] - x) ** 2 + (points[i][1] - y) ** 2)
            if (points[nearest][0] - x) ** 2 + (points[nearest][1] - y) ** 2 <= 18 ** 2:
                return nearest
        elif self.chart_type == "donut":
            center_x = rect.left() + min(130, int(rect.height()) - 8) / 2
            center_y = rect.top() + 8 + min(130, int(rect.height()) - 8) / 2
            dx, dy = x - center_x, y - center_y
            radius = (dx * dx + dy * dy) ** 0.5
            if radius < 45 or radius > 78:
                return None
            import math
            angle = (math.degrees(math.atan2(-dy, dx)) - 90) % 360
            total = float(sum((value for _, value in self.rows), Decimal(0))) or 1.0
            cursor = 0.0
            for index, (_, value) in enumerate(self.rows):
                span = float(value) / total * 360.0
                if cursor <= angle < cursor + span:
                    return index
                cursor += span
        return None

# شرح الدالة _colors: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _colors(self):
        return [
            "@charts.series_1@", "@charts.series_2@", "@charts.series_3@",
            "@charts.series_4@", "@charts.series_5@", "@charts.series_6@",
        ]

# شرح الدالة paintEvent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def paintEvent(self, event):
        del event
        started = time.perf_counter()
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rectangle = QRectF(self.rect().adjusted(8, 8, -8, -8))
            if not self.rows:
                painter.setPen(QPen(theme_qcolor("@text_muted@")))
                painter.drawText(
                    rectangle,
                    Qt.AlignmentFlag.AlignCenter,
                    translate_text("No visual data available"),
                )
                return
            if self.chart_type == "donut":
                self._draw_donut(painter, rectangle)
            elif self.chart_type == "line":
                self._draw_line(painter, rectangle)
            else:
                self._draw_bars(painter, rectangle)
        finally:
            painter.end()
            if is_enabled():
                record_metric("chart", (time.perf_counter() - started) * 1000.0)

# شرح الدالة _draw_donut: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _draw_donut(self, painter: QPainter, rect: QRectF):
        total = sum((value for _, value in self.rows), Decimal(0)) or Decimal(1)
        side = min(130, int(rect.height()) - 8)
        box = QRectF(rect.left(), rect.top() + 8, side, side)
        start = 90 * 16
        colors = self._colors()
        for index, (_, value) in enumerate(self.rows):
            span = int((value / total) * Decimal(360) * Decimal(16))
            painter.setPen(QPen(theme_qcolor(colors[index % len(colors)]), 17))
            painter.drawArc(box, start, -span)
            start -= span
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(theme_qcolor("@surface@")))
        painter.drawEllipse(box.adjusted(30, 30, -30, -30))
        painter.setPen(QPen(theme_qcolor("@text_primary@")))
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, f"{int(total):,}")
        self._draw_legend(painter, rect, box.right() + 18, self.rows, colors)

# شرح الدالة _draw_bars: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _draw_bars(self, painter: QPainter, rect: QRectF):
        values = [float(value) for _, value in self.rows]
        maximum = max(values) or 1.0
        left = rect.left() + 4
        bottom = rect.bottom() - 22
        width = max(12.0, (rect.width() - 12) / max(1, len(values)) - 8)
        colors = self._colors()
        painter.setPen(QPen(theme_qcolor("@divider@"), 1))
        painter.drawLine(QPointF(left, bottom), QPointF(rect.right(), bottom))
        for index, ((label, value), numeric) in enumerate(zip(self.rows, values)):
            height = (numeric / maximum) * max(20.0, rect.height() - 46)
            x = left + index * (width + 8)
            y = bottom - height
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(theme_qcolor(colors[index % len(colors)])))
            painter.drawRoundedRect(QRectF(x, y, width, height), 5, 5)
            painter.setPen(QPen(theme_qcolor("@text_muted@")))
            painter.setFont(QFont("Segoe UI", 7))
            painter.drawText(QRectF(x - 4, bottom + 4, width + 8, 16), Qt.AlignmentFlag.AlignCenter, label[-9:])

# شرح الدالة _draw_line: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _draw_line(self, painter: QPainter, rect: QRectF):
        values = [float(value) for _, value in self.rows]
        maximum = max(values) or 1.0
        minimum = min(values) if values else 0.0
        span = max(1.0, maximum - minimum)
        points = []
        for index, numeric in enumerate(values):
            x = rect.left() + 6 + ((rect.width() - 12) * index / max(1, len(values) - 1))
            y = rect.bottom() - 30 - ((numeric - minimum) / span) * max(30.0, rect.height() - 50)
            points.append(QPointF(x, y))
        painter.setPen(QPen(theme_qcolor("@divider@"), 1))
        painter.drawLine(QPointF(rect.left(), rect.bottom() - 30), QPointF(rect.right(), rect.bottom() - 30))
        painter.setPen(QPen(theme_qcolor("@charts.series_2@"), 3))
        for first, second in itertools.pairwise(points):
            painter.drawLine(first, second)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(theme_qcolor("@charts.series_2@")))
        for point in points:
            painter.drawEllipse(point, 3.5, 3.5)
        painter.setPen(QPen(theme_qcolor("@text_muted@")))
        painter.setFont(QFont("Segoe UI", 7))
        for index, (label, _) in enumerate(self.rows):
            if index % max(1, len(self.rows) // 6) == 0 or index == len(self.rows) - 1:
                x = rect.left() + 6 + ((rect.width() - 12) * index / max(1, len(self.rows) - 1))
                painter.drawText(QRectF(x - 24, rect.bottom() - 24, 48, 16), Qt.AlignmentFlag.AlignCenter, label[-9:])

# شرح الدالة _draw_legend: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _draw_legend(self, painter, rect, start_x, rows, colors):
        y = rect.top() + 10
        for index, (label, value) in enumerate(rows[:6]):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(theme_qcolor(colors[index % len(colors)])))
            painter.drawRoundedRect(QRectF(start_x, y + 3, 9, 9), 3, 3)
            painter.setPen(QPen(theme_qcolor("@text_secondary@")))
            painter.setFont(QFont("Segoe UI", 8))
            text = f"{label}: {float(value):,.2f}{self.value_suffix}"
            painter.drawText(QRectF(start_x + 14, y, max(80, rect.right() - start_x), 16), Qt.AlignmentFlag.AlignLeft, text)
            y += 24


# شرح الصنف AnalyticsCard: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class AnalyticsCard(QFrame):
    """Compact titled container for one analytical visualization."""

    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.setObjectName("analyticsCard")
        set_theme_style(self, """
            QFrame#analyticsCard {
                background: @surface@;
                border: 1px solid @border@;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        heading = QLabel(translate_text(title))
        heading.setObjectName("analyticsCardTitle")
        set_theme_style(heading, "QLabel { background: transparent; border: none; color: @text_primary@; font-size: 12px; font-weight: 700; }")
        layout.addWidget(heading)
        if subtitle:
            caption = QLabel(translate_text(subtitle))
            caption.setObjectName("analyticsCardSubtitle")
            set_theme_style(caption, "QLabel { background: transparent; border: none; color: @text_muted@; font-size: 10px; }")
            layout.addWidget(caption)
        self.content_layout = layout

# شرح الدالة add_chart: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_chart(self, chart: AnalyticsChart):
        self.content_layout.addWidget(chart)


__all__ = ["AnalyticsCard", "AnalyticsChart"]

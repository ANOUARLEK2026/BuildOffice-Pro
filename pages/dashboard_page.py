# ============================================================
# شرح الملف: pages/dashboard_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""BuildOffice Pro executive dashboard matching the new visual direction."""
from __future__ import annotations

import itertools
import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QDate, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.i18n import translate_text
from repositories.db import get_connection
from services.dashboard_service import load_dashboard_data
from services.settings_service import money_display
from theme import apply_card_shadow, set_theme_style, theme_color

from .analytics_widgets import AnalyticsCard, AnalyticsChart
from .base_page import BasePage

# Central semantic theme roles. The actual colors come from the active Light/Dark theme.
BLUE = "@info@"
BLUE_DARK = "@text_primary@"
GREEN = "@success@"
PURPLE = "@charts.series_3@"
GOLD = "@primary@"
RED = "@danger@"
TEAL = "@charts.series_2@"
MUTED = "@text_muted@"


# شرح الدالة money: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def money(value) -> str:
    return money_display(value)


# شرح الصنف ChartWidget: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class ChartWidget(QFrame):
    """Small theme-neutral chart canvas. Background is inherited from the card."""
    def __init__(self, kind="donut", values=None, labels=None, colors=None):
        super().__init__()
        self.kind, self.values, self.labels, self.colors = kind, values or [], labels or [], colors or []
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background: transparent; border: none;")

# شرح الدالة paintEvent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def paintEvent(self, event):
        # الرسم المحسّن أولًا؛ عند أي خطأ غير متوقع يُستخدم الرسم القديم كشبكة أمان.
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(8, 8, -8, -8)
        try:
            if self.kind == "donut": self._donut(p, r)
            elif self.kind == "line": self._line(p, r)
            elif self.kind == "bars": self._bars(p, r)
        except (RuntimeError, ValueError, TypeError, IndexError, ZeroDivisionError):
            p.end()
            self._paint_legacy(event)

    def _series_color(self, i):
        return QColorSafe(self.colors[i % len(self.colors)]) if self.colors else QColorSafe(BLUE)

    def _donut(self, p, r):
        from PySide6.QtGui import QColor
        total = sum(max(0, float(v)) for v in self.values) or 1
        side = min(r.width(), r.height()) - 16
        thickness = max(14, side * 0.16)
        box = QRectF(r.center().x() - side / 2, r.center().y() - side / 2, side, side).adjusted(thickness / 2, thickness / 2, -thickness / 2, -thickness / 2)
        track = QColorSafe("@divider@")
        p.setPen(QPen(track, thickness)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawEllipse(box)
        start = 90 * 16
        gap = 24 if len([v for v in self.values if float(v) > 0]) > 1 else 0
        for i, v in enumerate(self.values):
            value = max(0, float(v))
            if value <= 0: continue
            span = -360 * 16 * value / total
            pen = QPen(self._series_color(i), thickness); pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawArc(box, int(start), int(span + (gap if span < -gap else 0))); start += span
        p.setPen(QPen(QColorSafe("@text_primary@")))
        p.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        p.drawText(box, Qt.AlignmentFlag.AlignCenter, str(int(sum(self.values))))

    def _line(self, p, r):
        from PySide6.QtGui import QColor, QLinearGradient, QPainterPath
        vals = [float(v) for v in self.values] or [0]
        vmax = max(vals) or 1
        plot = r.adjusted(4, 8, -4, -4)
        grid = QColorSafe("@divider@")
        p.setPen(QPen(grid, 1, Qt.PenStyle.DashLine))
        for i in range(4):
            y = plot.top() + i * plot.height() / 3
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
        pts = []
        for i, v in enumerate(vals):
            x = plot.left() + (plot.width() * i / max(1, len(vals) - 1))
            y = plot.bottom() - (v / vmax) * (plot.height() - 10)
            pts.append(QPointF(x, y))
        color = QColorSafe(BLUE)
        path = QPainterPath(pts[0])
        for a, b in itertools.pairwise(pts):
            mid = (a.x() + b.x()) / 2
            path.cubicTo(QPointF(mid, a.y()), QPointF(mid, b.y()), b)
        area = QPainterPath(path)
        area.lineTo(QPointF(pts[-1].x(), plot.bottom())); area.lineTo(QPointF(pts[0].x(), plot.bottom())); area.closeSubpath()
        fill = QLinearGradient(0, plot.top(), 0, plot.bottom())
        top = QColor(color); top.setAlpha(90); bottom = QColor(color); bottom.setAlpha(4)
        fill.setColorAt(0, top); fill.setColorAt(1, bottom)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(fill)); p.drawPath(area)
        pen = QPen(color, 3); pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush); p.drawPath(path)
        ring = QColorSafe("@surface@")
        for pt in pts:
            p.setPen(QPen(ring, 2)); p.setBrush(QBrush(color)); p.drawEllipse(pt, 4.5, 4.5)

    def _bars(self, p, r):
        from PySide6.QtGui import QColor, QLinearGradient
        vals = [max(0, float(v)) for v in self.values] or [0]
        vmax = max(vals) or 1
        gap = 14; w = max(8, (r.width() - gap * (len(vals) - 1)) / max(1, len(vals)))
        w = min(w, 64)
        used = w * len(vals) + gap * (len(vals) - 1)
        left = r.left() + max(0, (r.width() - used) / 2)
        grid = QColorSafe("@divider@")
        p.setPen(QPen(grid, 1, Qt.PenStyle.DashLine))
        for i in range(4):
            y = r.bottom() - i * (r.height() - 24) / 3
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
        for i, v in enumerate(vals):
            h = max(4.0, (v / vmax) * (r.height() - 24)) if v > 0 else 3.0
            x = left + i * (w + gap)
            y = r.bottom() - h
            base = self._series_color(i)
            lighter = QColor(base).lighter(125)
            g = QLinearGradient(0, y, 0, r.bottom()); g.setColorAt(0, lighter); g.setColorAt(1, base)
            p.setBrush(QBrush(g)); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(x, y, w, h), 7, 7)


    def _paint_legacy(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(8, 8, -8, -8)
        if self.kind == "donut": self._donut_legacy(p, r)
        elif self.kind == "line": self._line_legacy(p, r)
        elif self.kind == "bars": self._bars_legacy(p, r)

# شرح الدالة _donut: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _donut_legacy(self, p, r):
        total = sum(max(0, float(v)) for v in self.values) or 1
        side = min(r.width(), r.height()) - 16
        box = QRectF(r.left(), r.top() + 3, side, side)
        start = 90 * 16
        for i, v in enumerate(self.values):
            span = -360 * 16 * max(0, float(v)) / total
            p.setPen(QPen(QColorSafe(self.colors[i % len(self.colors)]), 18))
            p.drawArc(box, int(start), int(span)); start += span
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(self.palette().window()))
        inner = box.adjusted(22, 22, -22, -22); p.drawEllipse(inner)
        p.setPen(QPen(QColorSafe(BLUE_DARK))); p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold));
        p.drawText(inner, Qt.AlignmentFlag.AlignCenter, str(int(sum(self.values))))

# شرح الدالة _line: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _line_legacy(self, p, r):
        vals = [float(v) for v in self.values] or [0]
        vmax = max(vals) or 1
        # grid
        pen = QPen(QColorSafe("lightsteelblue"), 1)
        p.setPen(pen)
        for i in range(4):
            y = r.top() + i * r.height() / 3
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
        pts = []
        for i, v in enumerate(vals):
            x = r.left() + (r.width() * i / max(1, len(vals)-1))
            y = r.bottom() - (v / vmax) * (r.height() - 16)
            pts.append(QPointF(x, y))
        p.setPen(QPen(QColorSafe(BLUE), 3));
        for a, b in itertools.pairwise(pts): p.drawLine(a, b)
        p.setBrush(QBrush(QColorSafe(BLUE))); p.setPen(Qt.PenStyle.NoPen)
        for pt in pts: p.drawEllipse(pt, 4, 4)

# شرح الدالة _bars: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _bars_legacy(self, p, r):
        vals = [max(0, float(v)) for v in self.values] or [0]
        vmax = max(vals) or 1
        gap = 12; w = max(8, (r.width() - gap*(len(vals)-1)) / max(1, len(vals)))
        for i, v in enumerate(vals):
            h = (v / vmax) * (r.height() - 24)
            x = r.left() + i * (w + gap)
            y = r.bottom() - h
            p.setBrush(QBrush(QColorSafe(self.colors[i % len(self.colors)]))); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(x, y, w, h), 6, 6)


# شرح الدالة QColorSafe: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def QColorSafe(value):
    from PySide6.QtGui import QColor
    text = str(value).strip()
    if text.startswith("@") and text.endswith("@"):
        return QColor(theme_color(text[1:-1]))
    return QColor(text)


# شرح الصنف DashboardCard: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class DashboardCard(QFrame):
    def __init__(self, accent=BLUE, colored=False):
        super().__init__(); self.setObjectName("dashCard")
        bg = accent if colored else "@surface@"
        border = accent if colored else "@border@"
        set_theme_style(self, f"QFrame#dashCard {{ background: {bg}; border: 1px solid {border}; border-radius: 14px; }}")
        self.card_layout = QVBoxLayout(self); self.card_layout.setContentsMargins(16, 14, 16, 14); self.card_layout.setSpacing(7)
        apply_card_shadow(self, blur=22, offset_y=5, alpha=38)


# شرح الصنف DashboardPage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class DashboardPage(BasePage):
    """Executive command center. Data is read-only and sourced from existing tables."""
    def __init__(self):
        super().__init__("Dashboard", "Company-wide operational and financial overview")
        self._build_shell(); QTimer.singleShot(0, self.refresh)

# شرح الدالة _build_shell: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_shell(self):
        self.scroll_area = QScrollArea(); self.scroll_area.setWidgetResizable(True); self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content = QWidget(); self.content.setObjectName("dashboardContent")
        set_theme_style(self.content, "QWidget#dashboardContent { background: @background@; }")
        self.main = QVBoxLayout(self.content); self.main.setContentsMargins(2, 2, 14, 18); self.main.setSpacing(12)
        self.scroll_area.setWidget(self.content); self.body.addWidget(self.scroll_area)

# شرح الدالة _label: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _label(self, text, size=11, bold=False, color="@text_primary@"):
        source = str(text)
        w = QLabel(translate_text(source))
        w.setProperty("bo_i18n_text", source)
        w.setWordWrap(False)
        set_theme_style(w, f"QLabel {{ color: {color}; font-size: {size + 2 if size <= 11 else size}px; font-weight: {700 if bold else 400}; background: transparent; border: none; }}")
        return w

# شرح الدالة _title: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _title(self, text, subtitle=None):
        box = QVBoxLayout(); box.setSpacing(2); box.addWidget(self._label(text, 15, True))
        if subtitle: box.addWidget(self._label(subtitle, 9, False, "@text_secondary@"))
        return box

# شرح الدالة _card_header: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _card_header(self, card, title, subtitle=None, right=None):
        row = QHBoxLayout(); row.addLayout(self._title(title, subtitle)); row.addStretch()
        if right: row.addWidget(self._label(right, 9, False, "@info@"))
        card.card_layout.addLayout(row)

# شرح الدالة _on_project_chart_clicked: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _on_project_chart_clicked(self, label, _value):
        """Open Projects and apply an exact analytics project filter."""
        window = self.window()
        if window is None or not hasattr(window, "open_page"):
            return

        main_window = cast(Any, window)
        main_window.open_page("Projects")

        page = getattr(main_window, "pages", {}).get("Projects")
        if page is None:
            return

        project_id = None

        for row in getattr(page, "_project_rows", []):
            if isinstance(row, (tuple, list)) and len(row) >= 2 and str(row[1]) == str(label):
                project_id = row[0]
                break

            if isinstance(row, dict) and str(row.get("project_name", "")) == str(label):
                project_id = row.get("project_id")
                break

        apply_filter = getattr(page, "apply_analytics_project_filter", None)
        if callable(apply_filter) and project_id:
            apply_filter(project_id)
            return

        search = getattr(page, "search", None)
        if search is not None:
            search.setText(str(label))
            search.setFocus()

# شرح الدالة _build_kpis: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_kpis(self, data):
        """Build the executive KPI row from live dashboard data."""
        grid = QGridLayout()
        grid.setHorizontalSpacing(10); grid.setVerticalSpacing(10)
        cards = [
            (translate_text("Total Projects"), str(data["projects"]), translate_text(f"{data['active_projects']} active"), BLUE, "▣"),
            (translate_text("Total Contract Value"), money(data["budget"]), translate_text("Registered project budgets"), GREEN, "◉"),
            (translate_text("Total Expenses"), money(data["expenses"]), translate_text(money(data["month_expenses"]) + " this month"), PURPLE, "▤"),
            (translate_text("Total Receivables"), money(data["received_income"]), translate_text(money(data["month_payments"]) + " received this month"), GOLD, "↔"),
        ]
        for i, args in enumerate(cards):
            grid.addWidget(self._kpi(*args), 0, i); grid.setColumnStretch(i, 1)
        return grid

# شرح الدالة _kpi: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _kpi(self, title, value, subtitle, accent, icon):
        c = DashboardCard(accent, True); c.setMinimumHeight(112)
        top = QHBoxLayout(); badge = QLabel(icon); badge.setAlignment(Qt.AlignmentFlag.AlignCenter); badge.setFixedSize(38,38)
        set_theme_style(badge, "background: @components.theme.on_colored_surface_muted@; color: @components.theme.on_colored_surface@; border: 1px solid @components.theme.on_colored_surface_border@; border-radius: 10px; font-size: 18px; font-weight: 700;")
        top.addWidget(badge); top.addSpacing(8); top.addWidget(self._label(title, 10, True, "@components.theme.on_colored_surface@")); top.addStretch(); c.card_layout.addLayout(top)
        c.card_layout.addWidget(self._label(value, 22, True, "@components.theme.on_colored_surface@")); c.card_layout.addWidget(self._label(subtitle, 9, False, "@components.theme.on_colored_surface_muted@")); return c

# شرح الدالة _hero: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _hero(self, company):
        c = QFrame(); c.setMinimumHeight(112); c.setObjectName("dashHero")
        set_theme_style(c, "QFrame#dashHero { background: @components.navigation.navigation@; border: 1px solid @border@; border-radius: 15px; }")
        hero_path = (Path(__file__).resolve().parent.parent / "resources" / "dashboard_hero.png").resolve()
        hero_url = hero_path.as_posix()
        c.setStyleSheet(c.styleSheet() + f" QFrame#dashHero {{ background-image: url(\"{hero_url}\"); background-position: right center; background-repeat: no-repeat; }}")
        lay = QHBoxLayout(c); lay.setContentsMargins(22, 18, 22, 18)
        icon = QLabel("☀"); icon.setAlignment(Qt.AlignmentFlag.AlignCenter); icon.setFixedSize(52,52); set_theme_style(icon, "QLabel { background: @gold@; color: @text_primary@; border-radius: 14px; font-size: 26px; font-weight: 700; }")
        lay.addWidget(icon); lay.addSpacing(14)
        text = QVBoxLayout(); text.setSpacing(3); text.addWidget(self._label("Good morning, Administrator", 20, True, "@components.theme.on_colored_surface@")); text.addWidget(self._label("Here's an overview of your company's activity today.", 10, False, "@components.theme.on_colored_surface_muted@")); text.addWidget(self._label(company, 9, True, "@components.theme.on_colored_surface_muted@")); lay.addLayout(text,1)
        right = QVBoxLayout(); right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter); right.addWidget(self._label(QDate.currentDate().toString("ddd, dd MMM yyyy"), 9, True, "@components.theme.on_colored_surface@"), alignment=Qt.AlignmentFlag.AlignRight); right.addWidget(self._label("Build today\nfor a better tomorrow", 9, False, "@components.theme.on_colored_surface_muted@"), alignment=Qt.AlignmentFlag.AlignRight); lay.addLayout(right)
        return c

# شرح الدالة _legend: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _legend(self, title, value, color):
        row = QHBoxLayout(); dot = QLabel("●"); set_theme_style(dot, f"QLabel {{ color:{color}; font-size:12px; background:transparent; border:none; }}"); row.addWidget(dot); row.addWidget(self._label(title, 9, False)); row.addStretch(); row.addWidget(self._label(str(value), 9, True)); return row

# شرح الدالة _module_snapshot: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _module_snapshot(self, data):
        c = DashboardCard(); self._card_header(c, "All Modules Snapshot", "Quick overview of every module in your system")
        grid = QGridLayout(); grid.setHorizontalSpacing(8); grid.setVerticalSpacing(8)
        items = [
            ("Projects", f"{data['projects']} projects", f"{data['active_projects']} active", BLUE, "▣"),
            ("Métré / BOQ", f"{data['metre_items']} items", f"{data['situations']} situations", GREEN, "△"),
            ("Progress / Situations", f"{data['boq_progress']:.0f}% avg.", f"{data['situations']} situations", PURPLE, "↗"),
            ("Expenses", money(data['expenses']), money(data['month_expenses']) + " this month", RED, "▣"),
            ("Payments", money(data['received_income']), money(data['month_payments']) + " this month", TEAL, "↔"),
            ("Debts", money(data['debts_value']), f"{data['debts_count']} open records", GOLD, "◉"),
            ("Financial Reports", f"{data['report_count']} records", "Latest operational data", BLUE, "▤"),
            ("Staff", f"{data['staff']} employees", f"{data['active_staff']} active", PURPLE, "♟"),
            ("Attendance", f"{data['present_today']} present", f"{data['attendance_rate']:.0f}% month rate", TEAL, "▣"),
            ("Payroll", money(data['payroll']), "Current payroll records", PURPLE, "$"),
            ("Vehicles", f"{data['vehicles']} active", f"{data['maintenance_due']} maintenance due", GOLD, "▰"),
            ("Construction Control", money(data['construction_controlled_cost']), f"{data['construction_risks']} cost centers", TEAL, "CC"),
            ("Documents", f"{data['documents']} total", f"{data['expiring_docs']} expiring soon", GREEN, "▤"),
            ("Statistics", f"{data['audit_count']} activity logs", "Live database summary", PURPLE, "▥"),
            ("Company", data['company_name'], "Company information", BLUE, "▦"),
            ("Settings", "System ready", "Language • Theme • Local DB", MUTED, "⚙"),
        ]
        for i, (title, value, detail, accent, icon) in enumerate(items):
            box = QFrame(); box.setObjectName("moduleTile"); set_theme_style(box, "QFrame#moduleTile { background:@surface@; border:1px solid @border@; border-radius:10px; }")
            l=QHBoxLayout(box); l.setContentsMargins(9,8,9,8); l.setSpacing(8)
            ic=QLabel(icon); ic.setAlignment(Qt.AlignmentFlag.AlignCenter); ic.setFixedSize(32,32); set_theme_style(ic, f"QLabel {{ background: {accent}; color: @components.buttons.button_text@; border-radius: 8px; font-weight: 700; }}")
            l.addWidget(ic); t=QVBoxLayout(); t.setSpacing(1); t.addWidget(self._label(title,8,True)); t.addWidget(self._label(value,10,True,"@text_primary@")); t.addWidget(self._label(detail,8,False,"@text_muted@")); l.addLayout(t,1)
            grid.addWidget(box, i//5, i%5)
        c.card_layout.addLayout(grid); return c

# شرح الدالة _build_projects: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_projects(self, data):
        """Build the active-project portfolio section."""
        card = DashboardCard(); self._card_header(card, "Active Projects", "Budget and status overview")
        for row in data["project_rows"]:
            line = QHBoxLayout(); line.addWidget(self._label(row[0], 9, True)); line.addStretch()
            line.addWidget(self._label(money(row[2]), 9, True, "@text_primary@"))
            line.addWidget(self._label(row[1], 8, False, "@success@" if row[1] == "Active" else "@warning@"))
            card.card_layout.addLayout(line)
        return card

# شرح الدالة _recent_activity: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _recent_activity(self, data):
        c=DashboardCard(); self._card_header(c,"Recent Activity","Latest system events","View all")
        if not data['recent']:
            c.card_layout.addWidget(self._label("No activity recorded yet.",10,False,"@text_muted@")); return c
        for action, entity, description, occurred in data['recent']:
            row=QHBoxLayout(); badge=QLabel("+"); badge.setAlignment(Qt.AlignmentFlag.AlignCenter); badge.setFixedSize(30,30); set_theme_style(badge, "background:@info@;color:@components.theme.on_colored_surface@;border-radius:15px;font-size:16px;font-weight:700;")
            row.addWidget(badge); text=QVBoxLayout(); text.setSpacing(1); text.addWidget(self._label(f"{action} • {entity}",9,True)); text.addWidget(self._label(description or "System activity",8,False,"@text_secondary@")); row.addLayout(text,1); row.addWidget(self._label(str(occurred or "")[:16],8,False,"@text_muted@")); c.card_layout.addLayout(row)
        return c

# شرح الدالة refresh: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def refresh(self):
        conn=get_connection()
        error = "Unknown database error"
        try:
            today=QDate.currentDate(); y,m=today.year(),today.month(); start=f"{y:04d}-{m:02d}-01"; end=f"{y:04d}-{m:02d}-{today.daysInMonth():02d}"
            data=load_dashboard_data(conn,start_date=start,end_date=end,today_string=today.toString("yyyy-MM-dd"),days_in_month=today.daysInMonth(),month_name=today.toString("yyyy-MM-dd"))
        except (sqlite3.Error,OSError,TypeError,ValueError) as exc:
            data=None; error=str(exc)
        finally: conn.close()
        while self.main.count():
            item=self.main.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                child = item.layout()
                if child is not None:
                    self._clear_layout(child)
        if data is None:
            c=DashboardCard(RED); c.card_layout.addWidget(self._label("Dashboard data could not be loaded.",14,True,"@danger@")); c.card_layout.addWidget(self._label(error,9,False,"@text_muted@")); self.main.addWidget(c); return

        self.main.addWidget(self._hero(data['company_name']))
        self.main.addLayout(self._build_kpis(data))

        top=QGridLayout(); top.setHorizontalSpacing(10); top.setVerticalSpacing(10)
        project=DashboardCard(); self._card_header(project,"Project Performance","Projects by status")
        chart=ChartWidget("donut",[x[1] for x in data['status_rows']],[x[0] for x in data['status_rows']],[GREEN,BLUE,GOLD,RED]); project.card_layout.addWidget(chart)
        for (name,val),color in zip(data['status_rows'],[GREEN,BLUE,GOLD,RED]): project.card_layout.addLayout(self._legend(name,val,color))
        finance=DashboardCard(); self._card_header(finance,translate_text("Financial Overview"),translate_text("Budget, expenses and payments (DZD)"))
        finance.card_layout.addWidget(ChartWidget("bars",[data['budget'],data['expenses'],data['received_income'],data['debts_value']],["Budget","Expenses","Payments","Debts"],[BLUE,RED,GREEN,GOLD]))
        for title,val,color in [("Budget",data['budget'],BLUE),("Expenses",data['expenses'],RED),("Payments",data['received_income'],GREEN),("Debts",data['debts_value'],GOLD)]: finance.card_layout.addLayout(self._legend(title,money(val),color))
        trend=DashboardCard(); self._card_header(trend,translate_text("Expenses Trend"),translate_text("Last 6 months (DZD)"))
        trend.card_layout.addWidget(ChartWidget("line",[x[1] for x in data['month_points']],[x[0] for x in data['month_points']],[BLUE])); trend.card_layout.addWidget(self._label(" • ".join(f"{x[0]}: {money(x[1])}" for x in data['month_points']),8,False,"@text_muted@"))
        deadlines=DashboardCard(); self._card_header(deadlines,translate_text("Upcoming Deadlines"),translate_text("Items requiring attention"),translate_text("View all"))
        for title,val,color in [("Documents expiring soon",data['expiring_docs'],GOLD),("Maintenance due",data['maintenance_due'],RED),("Unread notifications",data['notifications'],BLUE),("Open debts",data['debts_count'],PURPLE)]: deadlines.card_layout.addLayout(self._legend(title,val,color))
        top.addWidget(project,0,0); top.addWidget(finance,0,1); top.addWidget(trend,0,2); top.addWidget(deadlines,0,3)
        for i in range(4): top.setColumnStretch(i,1)
        self.main.addLayout(top)

        mid=QGridLayout(); mid.setHorizontalSpacing(10); mid.setVerticalSpacing(10)
        mid.addWidget(self._recent_activity(data),0,0,1,2)
        progress=DashboardCard(); self._card_header(progress,"Progress / Situations","Live execution summary")
        progress.card_layout.addWidget(self._label(f"{data['boq_progress']:.0f}%",28,True,"@success@")); progress.card_layout.addWidget(self._label("Average BOQ execution",9,False,"@text_secondary@")); bar=QProgressBar(); bar.setRange(0,100); bar.setValue(round(data['boq_progress'])); bar.setTextVisible(False); bar.setFixedHeight(8); set_theme_style(bar,"QProgressBar{background:@surface_alt@;border:none;border-radius:4px;} QProgressBar::chunk{background:@success@;border-radius:4px;}"); progress.card_layout.addWidget(bar); progress.card_layout.addWidget(self._label(f"{data['situations']} situations • {data['metre_items']} BOQ items",9,False,"@text_muted@")); mid.addWidget(progress,0,2)
        boq=DashboardCard(); self._card_header(boq,"Métré / BOQ","Recent activity")
        boq.card_layout.addWidget(self._label(str(data['metre_items']),28,True,"@primary@")); boq.card_layout.addWidget(self._label("Total BOQ items",9,False,"@text_secondary@")); boq.card_layout.addWidget(self._label(f"{data['situations']} situations recorded",9,False,"@text_muted@")); boq.card_layout.addStretch(); boq.card_layout.addWidget(self._label("View details ›",9,True,"@info@")); mid.addWidget(boq,0,3)
        self.main.addLayout(mid)

        # Compact analytical layer: charts answer operational questions without
        # turning the dashboard into a dense reporting page.
        visual_grid = QGridLayout()
        visual_grid.setHorizontalSpacing(10)
        visual_grid.setVerticalSpacing(10)

        cash_card = AnalyticsCard(
            "Cash flow pulse",
            "Payments received minus recorded expenses"
        )
        cash_rows = []
        for month, expenses_value, payments_value in data.get("month_points", []):
            cash_rows.append((month, Decimal(str(payments_value or 0)) - Decimal(str(expenses_value or 0))))
        cash_card.add_chart(AnalyticsChart("line", cash_rows, " DZD"))

        project_card = AnalyticsCard(
            "Project cost exposure",
            "Recorded project expenses for the largest projects"
        )
        project_rows = [
            (row[0], row[3])
            for row in data.get("project_rows", [])
            if len(row) >= 4
        ]
        project_chart = AnalyticsChart("bar", project_rows, " DZD", interaction_hint="Click a project to open its records")
        project_chart.clicked.connect(self._on_project_chart_clicked)
        project_card.add_chart(project_chart)

        visual_grid.addWidget(cash_card, 0, 0)
        visual_grid.addWidget(project_card, 0, 1)
        visual_grid.setColumnStretch(0, 1)
        visual_grid.setColumnStretch(1, 1)
        self.main.addLayout(visual_grid)

        smart = data.get("smart", {})
        portfolio = data.get("smart_portfolio", {})
        signal = DashboardCard()
        self._card_header(signal, "Smart Management Signal", "Automatic reading of cost, progress and cash exposure")
        signal_grid = QGridLayout(); signal_grid.setHorizontalSpacing(18); signal_grid.setVerticalSpacing(8)
        headline = portfolio.get("headline", "No active project forecast available.")
        signal_grid.addWidget(self._label(headline, 12, True, "@text_primary@"), 0, 0, 1, 4)
        signal_grid.addWidget(self._label(f"CPI {portfolio.get('portfolio_cpi', 1):.2f}", 10, True, "@success@"), 1, 0)
        signal_grid.addWidget(self._label(f"EAC {money(portfolio.get('portfolio_eac', 0))}", 10, True, "@info@"), 1, 1)
        signal_grid.addWidget(self._label(f"Receivable {money(portfolio.get('receivable', 0))}", 10, True, "@warning@"), 1, 2)
        signal_grid.addWidget(self._label(f"Data confidence {smart.get('data_confidence', 0):.0f}%", 10, True, "@text_secondary@"), 1, 3)
        top_risk = data.get("top_smart_risk")
        if top_risk:
            signal_grid.addWidget(self._label(f"Priority: {top_risk['project_name']} • {top_risk['message']}", 9, False, "@warning@"), 2, 0, 1, 4)
        else:
            signal_grid.addWidget(self._label("No priority risk detected from the current operational data.", 9, False, "@text_muted@"), 2, 0, 1, 4)
        signal.card_layout.addLayout(signal_grid)
        self.main.addWidget(signal)

        self.main.addWidget(self._build_projects(data))
        self.main.addWidget(self._module_snapshot(data))
        footer=QHBoxLayout(); footer.addWidget(self._label("Local Database • SQLite",8,False,"@text_muted@")); footer.addStretch(); footer.addWidget(self._label("BuildOffice Pro • Executive Dashboard",8,False,"@text_muted@")); self.main.addLayout(footer)

# شرح الدالة _clear_layout: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item=layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                child = item.layout()
                if child is not None:
                    DashboardPage._clear_layout(child)


__all__=["DashboardPage"]

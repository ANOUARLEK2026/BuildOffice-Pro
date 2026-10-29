# ============================================================
# شرح الملف: core/hero_banner.py
# بانر الشاشة الرئيسية: تدرّج لوني من ثيم التطبيق مع صورة موقع بناء تذوب تدريجيًا فيه.
# المكوّن عرض فقط ولا يلمس أي منطق أعمال أو قاعدة بيانات.
# ============================================================
"""Hero banner widget used by the launcher home screen."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QFrame

from theme import theme_qcolor

# ألوان احتياطية تُستعمل فقط إذا لم يكن مخزن الثيم جاهزًا بعد.
_FALLBACK = {
    "sidebar": "#07101D",
    "navigation": "#10233B",
    "navigation_accent": "#2B66D9",
}


def _themed(name: str) -> QColor:
    try:
        return theme_qcolor(f"@components.navigation.{name}@")
    except (RuntimeError, KeyError, ValueError):
        return QColor(_FALLBACK[name])


class HeroBanner(QFrame):
    """Rounded gradient banner with an optional photo fading in from the right."""

    RADIUS = 22.0

    def __init__(self, image_path: Path | str | None = None, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap(str(image_path)) if image_path and Path(image_path).exists() else QPixmap()
        self.setFrameShape(QFrame.Shape.NoFrame)

    def paintEvent(self, event):  # noqa: N802 - Qt API name
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QPainterPath()
        clip.addRoundedRect(rect, self.RADIUS, self.RADIUS)
        painter.setClipPath(clip)

        base = QLinearGradient(rect.left(), 0, rect.right(), 0)
        base.setColorAt(0.0, _themed("sidebar"))
        base.setColorAt(0.55, _themed("navigation"))
        base.setColorAt(1.0, _themed("navigation_accent"))
        painter.fillRect(rect, base)

        if not self._pixmap.isNull() and rect.width() > 40:
            photo_width = int(rect.width() * 0.62)
            target = QRect(int(rect.right()) - photo_width, int(rect.top()), photo_width, int(rect.height()))
            scaled = self._pixmap.scaled(
                target.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
            )
            source = QRect(
                (scaled.width() - target.width()) // 2, (scaled.height() - target.height()) // 2,
                target.width(), target.height(),
            )
            painter.drawPixmap(target, scaled, source)
            # الذوبان: لون الثيم معتم عند يسار الصورة ويشفّ تدريجيًا نحو يمينها.
            fade = QLinearGradient(target.left(), 0, target.right(), 0)
            deep = _themed("sidebar")
            mid = _themed("navigation")
            solid = QColor(mid)
            solid.setAlpha(255)
            soft = QColor(deep)
            soft.setAlpha(110)
            clear = QColor(deep)
            clear.setAlpha(40)
            fade.setColorAt(0.0, solid)
            fade.setColorAt(0.45, soft)
            fade.setColorAt(1.0, clear)
            painter.fillRect(target, fade)

        painter.setClipping(False)
        painter.setPen(QPen(QColor(255, 255, 255, 38), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, self.RADIUS, self.RADIUS)
        painter.end()


__all__ = ["HeroBanner"]

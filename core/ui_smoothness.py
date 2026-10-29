"""Lightweight visual motion layer for BuildOffice Pro.

The module intentionally uses only small, short-lived animations and avoids
full-window blur, repeated page rendering, geometry fights with layouts, and
global wheel interception. It is presentation-only and does not touch business
logic or database state.
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QRect, QPropertyAnimation, Qt, QParallelAnimationGroup
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QMainWindow,
    QMenu,
    QStackedWidget,
    QWidget,
)


class SmoothUIController(QObject):
    """Centralized low-cost UI motion for the existing application."""

    # Deliberately visible, but short enough to keep navigation responsive.
    PAGE_MS = 420
    PAGE_FADE_MS = 360
    PAGE_SLIDE_PX = 28
    DIALOG_IN_MS = 430
    DIALOG_OUT_MS = 320
    POPUP_MS = 220
    SCROLL_MS = 260
    GLASS_FADE_MS = 220

    def __init__(self, window: QMainWindow):
        super().__init__(window)
        self.window = window
        self._animations: list[QPropertyAnimation] = []
        self._active_animations: dict[tuple[int, bytes], QPropertyAnimation] = {}
        self._dialog_states: dict[int, dict[str, Any]] = {}
        self._closing_dialog_ids: set[int] = set()
        self._glass: QFrame | None = None
        self._page_overlay: QLabel | None = None
        self._page_group: QParallelAnimationGroup | None = None
        self._page_token = 0
        self._last_page_index = -1
        self._pending_page_pixmap: QPixmap | None = None
        self._pending_page_index = -1
        self._pending_page_direction = 1
        self._scroll_targets: dict[int, int] = {}

    def install(self) -> None:
        app = QApplication.instance()
        if app is not None:
            # Kept only for dialog/menu discovery. Wheel and button handling are
            # registered locally, so ordinary application events stay untouched.
            app.installEventFilter(self)
        self.window.setProperty("bo_smooth_ui", True)
        stack = self.window.findChild(QStackedWidget, "mainStack")
        if stack is not None:
            stack.setProperty("bo_smooth_stack", True)

    def register_widget_tree(self, root: QWidget) -> None:
        """Register only scroll viewports below a newly-created page/dialog."""
        if root is None:
            return
        for area in root.findChildren(QAbstractScrollArea):
            viewport = area.viewport()
            if viewport is not None and viewport.property("bo_smooth_scroll") is not True:
                viewport.setProperty("bo_smooth_scroll", True)
                viewport.installEventFilter(self)
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if isinstance(watched, QMenu) and event.type() == QEvent.Type.Show:
            self._popup_show(watched)
            return False

        if isinstance(watched, QDialog):
            if event.type() == QEvent.Type.Show:
                self._dialog_show(watched)
            elif event.type() == QEvent.Type.Close:
                if id(watched) in self._closing_dialog_ids:
                    return False
                return self._dialog_close(watched)

        if event.type() == QEvent.Type.Wheel and watched.property("bo_smooth_scroll") is True:
            area = self._scroll_area_for_viewport(watched)
            if area is not None:
                return self._smooth_scroll(area, event)

        return False

    def _scroll_area_for_viewport(self, watched: QObject) -> QAbstractScrollArea | None:
        parent = watched.parentWidget() if isinstance(watched, QWidget) else None
        while parent is not None:
            if isinstance(parent, QAbstractScrollArea):
                return parent
            parent = parent.parentWidget()
        return watched if isinstance(watched, QAbstractScrollArea) else None

    def page_will_change(self, index: int) -> None:
        """Capture the outgoing page once, before QStackedWidget switches pages."""
        stack = self.window.findChild(QStackedWidget, "mainStack")
        if stack is None or index < 0 or index >= stack.count():
            return
        old = stack.currentWidget()
        if old is None or index == stack.currentIndex() or not old.isVisible():
            self._pending_page_pixmap = None
            return
        pixmap = old.grab()
        self._pending_page_pixmap = None if pixmap.isNull() else pixmap
        self._pending_page_index = index
        self._pending_page_direction = 1 if index > stack.currentIndex() else -1

    def page_changed(self, index: int) -> None:
        """Slide the outgoing snapshot away while the new page is already live."""
        stack = self.window.findChild(QStackedWidget, "mainStack")
        if stack is None or index < 0 or index >= stack.count():
            return
        page = stack.widget(index)
        if page is None:
            return

        old_index = self._last_page_index
        self._last_page_index = index
        if old_index == index and self._pending_page_pixmap is None:
            return

        self._page_token += 1
        token = self._page_token
        self._cancel_page_transition()

        pixmap = self._pending_page_pixmap
        direction = self._pending_page_direction
        self._pending_page_pixmap = None
        self._pending_page_index = -1
        if pixmap is None:
            self._fade_page(page, token)
            return

        rect = stack.rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return

        overlay = QLabel(stack)
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        overlay.setPixmap(pixmap)
        overlay.setGeometry(rect)
        overlay.show()
        overlay.raise_()
        self._page_overlay = overlay

        start = QRect(rect)
        end = QRect(rect)
        end.translate(-direction * self.PAGE_SLIDE_PX, 0)

        effect = QGraphicsOpacityEffect(overlay)
        overlay.setGraphicsEffect(effect)
        slide = self._make_animation(
            overlay,
            b"geometry",
            start,
            end,
            self.PAGE_MS,
            QEasingCurve.Type.OutCubic,
        )
        fade = self._make_animation(
            effect,
            b"opacity",
            1.0,
            0.0,
            self.PAGE_FADE_MS,
            QEasingCurve.Type.OutCubic,
        )
        group = QParallelAnimationGroup(self)
        group.addAnimation(slide)
        group.addAnimation(fade)

        def finish() -> None:
            if token != self._page_token:
                return
            if self._page_overlay is overlay:
                overlay.deleteLater()
                self._page_overlay = None
            self._page_group = None

        group.finished.connect(finish)
        self._page_group = group
        group.start()

    def _fade_page(self, page: QWidget, token: int) -> None:
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        animation = self._make_animation(
            effect,
            b"opacity",
            0.0,
            1.0,
            self.PAGE_FADE_MS,
            QEasingCurve.Type.OutCubic,
        )

        def finish() -> None:
            if token != self._page_token:
                return
            if page.graphicsEffect() is effect:
                page.setGraphicsEffect(None)

        animation.finished.connect(finish)
        animation.start()

    def _cancel_page_transition(self) -> None:
        if self._page_group is not None:
            self._page_group.stop()
            self._page_group.deleteLater()
            self._page_group = None
        if self._page_overlay is not None:
            self._page_overlay.deleteLater()
            self._page_overlay = None

    def _popup_show(self, popup: QMenu) -> None:
        if popup.property("bo_smooth_popup") is True:
            return
        popup.setProperty("bo_smooth_popup", True)
        popup.setWindowOpacity(0.0)
        self._make_animation(
            popup,
            b"windowOpacity",
            0.0,
            1.0,
            self.POPUP_MS,
            QEasingCurve.Type.OutCubic,
        ).start()

    def _dialog_show(self, dialog: QDialog) -> None:
        key = id(dialog)
        if key in self._dialog_states or dialog.property("bo_smooth_dialog") is True:
            return
        dialog.setProperty("bo_smooth_dialog", True)
        dialog.adjustSize()
        final_rect = dialog.geometry()
        if final_rect.width() <= 0 or final_rect.height() <= 0:
            return

        scale = 0.90
        start_w = max(140, int(final_rect.width() * scale))
        start_h = max(100, int(final_rect.height() * scale))
        start_rect = QRect(
            final_rect.center().x() - start_w // 2,
            final_rect.center().y() - start_h // 2,
            start_w,
            start_h,
        )
        dialog.setGeometry(start_rect)
        dialog.setWindowOpacity(0.0)
        self.register_widget_tree(dialog)
        self._dialog_states[key] = {"closing": False}

        geometry = self._make_animation(
            dialog,
            b"geometry",
            start_rect,
            final_rect,
            self.DIALOG_IN_MS,
            QEasingCurve.Type.OutCubic,
        )
        opacity = self._make_animation(
            dialog,
            b"windowOpacity",
            0.0,
            1.0,
            self.DIALOG_IN_MS,
            QEasingCurve.Type.OutCubic,
        )
        geometry.start()
        opacity.start()

    def _dialog_close(self, dialog: QDialog) -> bool:
        state = self._dialog_states.get(id(dialog))
        if not state:
            return False
        if state.get("closing"):
            return True
        state["closing"] = True

        final_rect = dialog.geometry()
        scale = 0.90
        small_w = max(120, int(final_rect.width() * scale))
        small_h = max(90, int(final_rect.height() * scale))
        small_rect = QRect(
            final_rect.center().x() - small_w // 2,
            final_rect.center().y() - small_h // 2,
            small_w,
            small_h,
        )

        geometry = self._make_animation(
            dialog,
            b"geometry",
            final_rect,
            small_rect,
            self.DIALOG_OUT_MS,
            QEasingCurve.Type.InCubic,
        )
        opacity = self._make_animation(
            dialog,
            b"windowOpacity",
            float(dialog.windowOpacity()),
            0.0,
            self.DIALOG_OUT_MS,
            QEasingCurve.Type.InCubic,
        )

        def finish() -> None:
            self._hide_glass()
            self._dialog_states.pop(id(dialog), None)
            self._closing_dialog_ids.add(id(dialog))
            dialog.close()
            self._closing_dialog_ids.discard(id(dialog))
            dialog.setProperty("bo_smooth_dialog", False)

        opacity.finished.connect(finish)
        geometry.start()
        opacity.start()
        return True

    def _show_glass(self, dialog: QDialog) -> None:
        """Compatibility hook: dialogs no longer add a persistent parent overlay."""
        self._hide_glass()

    def _hide_glass(self) -> None:
        overlay = self._glass
        self._glass = None
        if overlay is not None:
            try:
                overlay.hide()
                overlay.deleteLater()
            except RuntimeError:
                pass

    def _smooth_scroll(self, area: QAbstractScrollArea, event: QEvent) -> bool:
        delta = event.angleDelta().y()  # type: ignore[attr-defined]
        bar = area.verticalScrollBar()
        if delta == 0 or bar is None or bar.maximum() <= bar.minimum():
            return False

        current = self._scroll_targets.get(id(bar), bar.value())
        step = max(45, int(abs(delta) * 1.05))
        target = current - step if delta > 0 else current + step
        target = max(bar.minimum(), min(bar.maximum(), target))
        if target == current:
            return False
        self._scroll_targets[id(bar)] = target

        key = (id(bar), b"value")
        old = self._active_animations.get(key)
        if old is not None:
            old.stop()

        animation = self._make_animation(
            bar,
            b"value",
            bar.value(),
            target,
            self.SCROLL_MS,
            QEasingCurve.Type.OutCubic,
        )

        def clear_target() -> None:
            if bar.value() == target:
                self._scroll_targets.pop(id(bar), None)

        animation.finished.connect(clear_target)
        animation.start()
        event.accept()  # type: ignore[attr-defined]
        return True

    def _make_animation(
        self,
        target: QObject,
        prop: bytes,
        start: Any,
        end: Any,
        duration: int,
        easing: QEasingCurve.Type,
    ) -> QPropertyAnimation:
        key = (id(target), prop)
        old = self._active_animations.get(key)
        if old is not None:
            old.stop()

        animation = QPropertyAnimation(target, prop, self)
        animation.setDuration(duration)
        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.setEasingCurve(easing)
        self._animations.append(animation)
        self._active_animations[key] = animation

        def cleanup() -> None:
            if animation in self._animations:
                self._animations.remove(animation)
            if self._active_animations.get(key) is animation:
                self._active_animations.pop(key, None)
            animation.deleteLater()

        animation.finished.connect(cleanup)
        animation.destroyed.connect(lambda: self._active_animations.pop(key, None) if self._active_animations.get(key) is animation else None)
        return animation


def install_smooth_ui(window: QMainWindow) -> SmoothUIController:
    """Install the visual layer once and return its controller."""
    existing = window.property("bo_smooth_controller")
    if isinstance(existing, SmoothUIController):
        return existing
    ctl = SmoothUIController(window)
    window.setProperty("bo_smooth_controller", ctl)
    ctl.install()
    return ctl

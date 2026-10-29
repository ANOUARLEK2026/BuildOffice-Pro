# ============================================================
# شرح الملف: dev_tools/dev_manager.py
# هذا الملف جزء من أدوات التطوير والتشخيص ومراقبة الأداء.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Central Developer Tools orchestrator for BuildOffice Pro.

This module owns developer-only UI hooks. Production pages do not need to
import it, and disabling developer mode removes the installed event filters,
timers, shortcuts, profilers and exception hook.
"""
from __future__ import annotations

import ast
import inspect
import io
import os
import sys
import time
import traceback
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from types import TracebackType
from typing import Any

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.decimal_utils import amount, q2
from core.i18n import get_language, set_language_value
from core.transaction import transaction
from dev_tools.dev_runtime import (
    record_metric,
    record_stall,
    set_delay_ms,
    set_enabled,
    snapshot_metrics,
)
from dev_tools.diagnostics_suite import (
    DatabaseAudit,
    DiagnosticSnapshot,
    ThemeAudit,
    TranslationAudit,
)
from tools.button_audit import audit as audit_file
from tools.validate_project import main as validate_project

ROOT = Path(__file__).resolve().parent.parent


# شرح الصنف MockTransaction: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
@dataclass
class MockTransaction:
    """Small transaction object exposed to the calculation sandbox."""

    name: str = "developer"
    project_id: str = "DEV-001"
    amount_ht: Any = field(default_factory=lambda: amount("0"))
    vat_rate: Any = field(default_factory=lambda: amount("19"))


# شرح الصنف DevConsole: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class DevConsole(QObject):
    """Thread-safe bridge from runtime hooks to the developer console."""

    message = Signal(str)

# شرح الدالة write: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def write(self, text: str) -> None:
        """Emit non-empty console output."""
        if text:
            self.message.emit(str(text))

# شرح الدالة flush: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def flush(self) -> None:
        """Support file-like stdout semantics."""
        return


# شرح الصنف _ServiceProfiler: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class _ServiceProfiler:
    """Profile only discovered public service functions while developer mode is active."""

    def __init__(self, console: DevConsole) -> None:
        self.console = console
        self.active = False
        self._previous: Callable[..., Any] | None = None
        self._lock = Lock()
        self._threshold_ms = 20.0
        self._targets: dict[Any, str] = {}
        self._started: dict[int, float] = {}

# شرح الدالة set_threshold: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def set_threshold(self, value: float) -> None:
        """Set the duration threshold used for visible warnings."""
        self._threshold_ms = max(0.0, float(value))

# شرح الدالة _discover_targets: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _discover_targets(self) -> dict[Any, str]:
        """Build a small code-object map for public module-level service functions."""
        targets: dict[Any, str] = {}
        for module_name, module in list(sys.modules.items()):
            if not module_name.startswith("services.") or module is None:
                continue
            try:
                members = inspect.getmembers(module, inspect.isfunction)
            except (TypeError, ValueError):
                continue
            for name, function in members:
                if name.startswith("_"):
                    continue
                code = getattr(function, "__code__", None)
                if code is not None:
                    targets[code] = f"{module_name}.{name}"
        return targets

# شرح الدالة enable: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def enable(self) -> None:
        """Install a filtered profiler that observes service functions only."""
        with self._lock:
            if self.active:
                return
            self._targets = self._discover_targets()
            self._started.clear()
            self._previous = sys.getprofile()
            sys.setprofile(self._trace)
            self.active = True

# شرح الدالة disable: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def disable(self) -> None:
        """Restore the previous Python profiler and clear profiling state."""
        with self._lock:
            if not self.active:
                return
            sys.setprofile(self._previous)
            self._previous = None
            self._started.clear()
            self._targets.clear()
            self.active = False

# شرح الدالة _trace: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _trace(self, frame, event, arg):
        code = frame.f_code
        if event == "call":
            if code in self._targets:
                self._started[id(frame)] = time.perf_counter()
            return self._trace
        if event == "return":
            started = self._started.pop(id(frame), None)
            if started is None:
                return self._trace
            elapsed = (time.perf_counter() - started) * 1000.0
            record_metric("service", elapsed)
            if elapsed >= self._threshold_ms:
                name = self._targets.get(code, code.co_name)
                self.console.write(f"[SERVICE] {name} -> {elapsed:.2f} ms")
        return self._trace


# شرح الصنف DevOverlay: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class DevOverlay(QFrame):
    """Compact performance HUD rendered above the main window."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("developerHud")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.label = QLabel(self)
        self.label.setStyleSheet(
            "QLabel { background: rgba(10, 18, 32, 225); color: white; "
            "padding: 7px 10px; border-radius: 7px; font-weight: 700; }"
        )
        self._last_frame = time.perf_counter()
        self._frames = 0
        self._fps = 0.0

# شرح الدالة tick: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def tick(self, metrics: dict[str, float | int]) -> None:
        """Update the HUD from the main Qt timer using real recorded timings."""
        now = time.perf_counter()
        self._frames += 1
        elapsed = now - self._last_frame
        if elapsed >= 1.0:
            self._fps = self._frames / elapsed
            self._frames = 0
            self._last_frame = now
        cpu = self._cpu_percent()
        ram = self._ram_mb()
        page = float(metrics.get("last_page_ms", 0.0))
        chart = float(metrics.get("last_chart_ms", 0.0))
        query = float(metrics.get("last_query_ms", 0.0))
        service = float(metrics.get("last_service_ms", 0.0))
        stall = float(metrics.get("last_stall_ms", 0.0))
        self.label.setText(
            f"DEV  FPS {self._fps:5.1f} | PAGE {page:6.1f} ms | "
            f"CHART {chart:5.1f} | DB {query:5.1f} | SVC {service:5.1f} | "
            f"STALL {stall:5.1f} | CPU {cpu:5.1f}% | RAM {ram:,.0f} MB"
        )
        self.adjustSize()
        self.move(12, 74)

# شرح الدالة _cpu_percent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _cpu_percent() -> float:
        try:
            import importlib
            psutil = importlib.import_module("psutil")
        except ImportError:
            return 0.0
        return float(psutil.cpu_percent(interval=None))

# شرح الدالة _ram_mb: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _ram_mb() -> float:
        try:
            import importlib
            psutil = importlib.import_module("psutil")
        except ImportError:
            return 0.0
        return float(psutil.Process(os.getpid()).memory_info().rss / 1048576.0)


# شرح الصنف DevManager: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class DevManager(QMainWindow):
    """Central developer console, inspector host and diagnostics controller."""

    def __init__(self, main_window: QMainWindow, project_root: Path | None = None):
        super().__init__(main_window)
        self.main_window = main_window
        self.project_root = Path(project_root or ROOT).resolve()
        self.console = DevConsole()
        self.console.message.connect(self._append_console)
        self.profiler = _ServiceProfiler(self.console)
        self._shortcuts: list[QShortcut] = []
        self._filters_installed = False
        self._inspector_enabled = False
        self._hud_enabled = False
        self._event_count = 0
        self._last_event_ms = 0.0
        self._block_threshold_ms = 180.0
        self._block_last = time.perf_counter()
        self._original_excepthook = sys.excepthook
        self._hook_installed = False
        self._previous_language = get_language()
        self._build_ui()
        self._install_shortcuts()
        self._install_exception_hook()
        self._set_runtime(True)
        self._start_block_detector()

# شرح الدالة _build_ui: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_ui(self) -> None:
        """Build the developer tools window."""
        self.setWindowTitle("BuildOffice Pro | Developer Tools")
        self.resize(820, 540)
        self.setMinimumSize(680, 440)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(7, 7, 7, 7)

        header = QHBoxLayout()
        title = QLabel("🛠 Developer Tools")
        title.setStyleSheet("font-size: 14px; font-weight: 800;")
        header.addWidget(title)
        header.addStretch(1)

        self.mode_check = QCheckBox("Hooks")
        self.mode_check.setChecked(True)
        self.mode_check.toggled.connect(self._set_runtime)
        header.addWidget(self.mode_check)

        self.hud_check = QCheckBox("HUD")
        self.hud_check.toggled.connect(self.set_hud_enabled)
        header.addWidget(self.hud_check)

        self.profiler_check = QCheckBox("Profiler")
        self.profiler_check.toggled.connect(self.set_profiler_enabled)
        header.addWidget(self.profiler_check)

        layout.addLayout(header)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setUsesScrollButtons(True)
        tabs.addTab(self._sandbox_page(), "Sandbox")
        tabs.addTab(self._console_page(), "Console")
        tabs.addTab(self._diagnostics_page(), "Diagnostics")
        tabs.addTab(self._health_page(), "Health")
        tabs.addTab(self._state_page(), "Runtime")
        layout.addWidget(tabs, 1)

        self.setCentralWidget(root)

# شرح الدالة _sandbox_page: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _sandbox_page(self) -> QWidget:
        """Create the calculation and logic sandbox."""
        page = QWidget()
        layout = QVBoxLayout(page)
        hint = QLabel(
            "Decimal-first expressions. Use D('123.45'), amount(value), q2(value), "
            "and tx for a mock transaction. The sandbox is developer-only."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.editor = QPlainTextEdit()
        self.editor.setMaximumBlockCount(300)
        self.editor.setPlaceholderText(
            "Examples:\n"
            "D('100000') * D('19') / D('100')\n"
            "amount(tx.amount_ht) + D('2500')\n"
            "tx.project_id\n"
        )
        layout.addWidget(self.editor, 1)

        row = QHBoxLayout()
        run = QPushButton("▶ Evaluate")
        run.clicked.connect(self.evaluate)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.editor.clear)
        row.addWidget(run)
        row.addWidget(clear)
        row.addStretch(1)
        layout.addLayout(row)

        self.result = QPlainTextEdit()
        self.result.setReadOnly(True)
        self.result.setMaximumHeight(100)
        layout.addWidget(self.result)
        return page

# شرح الدالة _console_page: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _console_page(self) -> QWidget:
        """Create the live runtime console."""
        page = QWidget()
        layout = QVBoxLayout(page)
        self.console_output = QPlainTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setMaximumBlockCount(500)
        layout.addWidget(self.console_output, 1)
        clear = QPushButton("Clear console")
        clear.clicked.connect(self.console_output.clear)
        layout.addWidget(clear)
        return page

# شرح الدالة _diagnostics_page: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _diagnostics_page(self) -> QWidget:
        """Create project audit and UI inspection controls."""
        page = QWidget()
        layout = QVBoxLayout(page)
        actions = QHBoxLayout()

        inspect = QPushButton("UI Inspector")
        inspect.clicked.connect(self.toggle_inspector)
        actions.addWidget(inspect)

        grid = QPushButton("Grid / Boundaries")
        grid.clicked.connect(self.toggle_grid)
        actions.addWidget(grid)

        colors = QPushButton("Color Inspector")
        colors.clicked.connect(self.open_color_inspector)
        actions.addWidget(colors)

        audit = QPushButton("Run project validation")
        audit.clicked.connect(self.run_validation)
        actions.addWidget(audit)

        buttons = QPushButton("Run button audit")
        buttons.clicked.connect(self.run_button_audit)
        actions.addWidget(buttons)
        layout.addLayout(actions)

        self.widget_info = QPlainTextEdit()
        self.widget_info.setReadOnly(True)
        self.widget_info.setPlaceholderText(
            "Select a widget in the main application to inspect it."
        )
        layout.addWidget(self.widget_info, 1)
        return page

# شرح الدالة _health_page: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _health_page(self) -> QWidget:
        """Create compact localization, theme, database, and snapshot diagnostics."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(6)

        actions = QHBoxLayout()
        self.translation_button = QPushButton("Translation Audit")
        self.translation_button.clicked.connect(self.run_translation_audit)
        actions.addWidget(self.translation_button)
        self.theme_button = QPushButton("Theme Audit")
        self.theme_button.clicked.connect(self.run_theme_audit)
        actions.addWidget(self.theme_button)
        self.database_button = QPushButton("Database Health")
        self.database_button.clicked.connect(self.run_database_audit)
        actions.addWidget(self.database_button)
        self.snapshot_button = QPushButton("Diagnostic Snapshot")
        self.snapshot_button.clicked.connect(self.create_snapshot)
        actions.addWidget(self.snapshot_button)
        layout.addLayout(actions)

        self.health_output = QPlainTextEdit()
        self.health_output.setReadOnly(True)
        self.health_output.setMaximumBlockCount(800)
        layout.addWidget(self.health_output, 1)
        return page

# شرح الدالة _state_page: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _state_page(self) -> QWidget:
        """Create runtime state and latency controls."""
        page = QWidget()
        form = QFormLayout(page)

        self.locale_box = QComboBox()
        self.locale_box.addItem("English", "en")
        self.locale_box.addItem("Arabic", "ar")
        self.locale_box.setCurrentIndex(1 if get_language() == "ar" else 0)
        self.locale_box.currentIndexChanged.connect(self.set_locale)
        form.addRow("Locale", self.locale_box)

        self.delay_slider = QSlider(Qt.Orientation.Horizontal)
        self.delay_slider.setRange(0, 2000)
        self.delay_slider.setValue(0)
        self.delay_slider.valueChanged.connect(self._delay_changed)
        self.delay_label = QLabel("0 ms")
        delay_row = QHBoxLayout()
        delay_row.addWidget(self.delay_slider, 1)
        delay_row.addWidget(self.delay_label)
        form.addRow("Service / database delay", delay_row)

        self.permission_box = QComboBox()
        self.permission_box.addItem("Developer", "Developer")
        self.permission_box.addItem("Administrator", "Administrator")
        self.permission_box.addItem("Manager", "Manager")
        self.permission_box.currentIndexChanged.connect(self.set_permission)
        form.addRow("Mock permission", self.permission_box)

        inject = QPushButton("Inject mock project state")
        inject.clicked.connect(self.inject_mock_state)
        form.addRow("Test data", inject)

        reset = QPushButton("Reset developer runtime")
        reset.clicked.connect(self.reset_runtime)
        form.addRow("Reset", reset)
        return page

# شرح الدالة _start_block_detector: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _start_block_detector(self) -> None:
        """Start a lightweight event-loop stall detector."""
        self._block_timer = QTimer(self)
        self._block_timer.setInterval(100)
        self._block_timer.timeout.connect(self._check_main_thread_block)
        self._block_last = time.perf_counter()
        self._block_timer.start()

# شرح الدالة _check_main_thread_block: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _check_main_thread_block(self) -> None:
        """Report event-loop stalls above the configured threshold."""
        now = time.perf_counter()
        elapsed_ms = (now - self._block_last) * 1000.0
        self._block_last = now
        if not self._filters_installed:
            return
        if elapsed_ms >= self._block_threshold_ms:
            record_stall(elapsed_ms)
            self.console.write(f"[PERFORMANCE] MAIN THREAD BLOCKED: {elapsed_ms:.0f} ms")

# شرح الدالة set_block_threshold: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def set_block_threshold(self, value: float) -> None:
        """Set the main-thread stall warning threshold."""
        self._block_threshold_ms = max(50.0, float(value))

# شرح الدالة _install_shortcuts: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _install_shortcuts(self) -> None:
        """Install the requested developer keybindings on the main window."""
        bindings = [
            ("Ctrl+Shift+D", self.toggle_inspector),
            ("Ctrl+Shift+P", self.toggle_hud),
            ("Ctrl+Shift+L", self.toggle_console),
        ]
        for sequence, callback in bindings:
            shortcut = QShortcut(QKeySequence(sequence), self.main_window)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

# شرح الدالة _install_exception_hook: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _install_exception_hook(self) -> None:
        """Install an exception hook that renders developer diagnostics."""
        if self._hook_installed:
            return
        sys.excepthook = self._handle_exception
        self._hook_installed = True

# شرح الدالة _remove_exception_hook: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _remove_exception_hook(self) -> None:
        """Restore the previous Python exception hook."""
        if self._hook_installed:
            sys.excepthook = self._original_excepthook
            self._hook_installed = False

# شرح الدالة _handle_exception: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _handle_exception(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        """Show the uncaught exception and selected local variables."""
        trace_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        context_lines: list[str] = []
        current = exc_tb
        while current is not None:
            frame = current.tb_frame
            context_lines.append(f"\n[{Path(frame.f_code.co_filename).name}:{current.tb_lineno}]")
            for key, value in frame.f_locals.items():
                if key.startswith("_"):
                    continue
                try:
                    rendered = repr(value)
                except (RuntimeError, ValueError, TypeError):
                    rendered = "<unavailable>"
                context_lines.append(f"{key} = {rendered[:400]}")
            current = current.tb_next
        text = trace_text + "\n\nVARIABLE CONTEXT\n" + "\n".join(context_lines)
        self.console.write(text)
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("BuildOffice Pro | Unhandled Exception")
        dialog.resize(900, 620)
        layout = QVBoxLayout(dialog)
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(text)
        layout.addWidget(editor, 1)
        close = QPushButton("Close")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

# شرح الدالة eventFilter: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Capture lightweight UI interaction diagnostics."""
        if not self._filters_installed:
            return super().eventFilter(watched, event)
        if isinstance(watched, QWidget):
            event_type = event.type()
            if event_type in (
                QEvent.Type.MouseButtonPress,
                QEvent.Type.KeyPress,
                QEvent.Type.FocusIn,
            ):
                self._event_count += 1
                self._last_event_ms = time.perf_counter() * 1000.0
                if event_type == QEvent.Type.MouseButtonPress:
                    widget = watched
                    self.console.write(
                        f"[UI] click {widget.metaObject().className()} "
                        f"#{widget.objectName() or '<unnamed>'}"
                    )
                elif event_type == QEvent.Type.FocusIn:
                    widget = watched
                    self.console.write(
                        f"[UI] focus {widget.metaObject().className()} "
                        f"#{widget.objectName() or '<unnamed>'}"
                    )
        return super().eventFilter(watched, event)

# شرح الدالة _set_runtime: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _set_runtime(self, enabled: bool) -> None:
        """Install or remove developer runtime hooks."""
        enabled = bool(enabled)
        set_enabled(enabled)
        app = QApplication.instance()
        if app is not None:
            if enabled and not self._filters_installed:
                app.installEventFilter(self)
                self._filters_installed = True
            elif not enabled and self._filters_installed:
                app.removeEventFilter(self)
                self._filters_installed = False
        block_timer = getattr(self, "_block_timer", None)
        if enabled and block_timer is not None:
            self._block_last = time.perf_counter()
            block_timer.start()
        if not enabled:
            if block_timer is not None:
                block_timer.stop()
            self.set_hud_enabled(False)
            self.set_profiler_enabled(False)

# شرح الدالة set_hud_enabled: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def set_hud_enabled(self, enabled: bool) -> None:
        """Enable or disable the performance HUD."""
        self._hud_enabled = bool(enabled)
        if self._hud_enabled:
            if not hasattr(self, "_hud"):
                self._hud = DevOverlay(self.main_window)
            self._hud.setParent(self.main_window)
            self._hud.show()
            if not hasattr(self, "_hud_timer"):
                self._hud_timer = QTimer(self)
                self._hud_timer.setInterval(250)
                self._hud_timer.timeout.connect(self._update_hud)
            self._hud_timer.start()
        else:
            timer = getattr(self, "_hud_timer", None)
            if timer is not None:
                timer.stop()
            hud = getattr(self, "_hud", None)
            if hud is not None:
                hud.hide()

# شرح الدالة _update_hud: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _update_hud(self) -> None:
        """Refresh the HUD from real page, chart, query, service and stall timings."""
        hud = getattr(self, "_hud", None)
        if hud is not None:
            hud.tick(snapshot_metrics())

# شرح الدالة set_profiler_enabled: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def set_profiler_enabled(self, enabled: bool) -> None:
        """Enable or disable targeted service call profiling."""
        if bool(enabled):
            self.profiler.enable()
        else:
            self.profiler.disable()

# شرح الدالة set_profiler_threshold: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def set_profiler_threshold(self, value: float) -> None:
        """Set the service profiler warning threshold."""
        self.profiler.set_threshold(value)

# شرح الدالة toggle_inspector: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def toggle_inspector(self) -> None:
        """Toggle the existing Visual Dev Kit inspector."""
        kit = getattr(self.main_window, "_visual_dev_kit", None)
        if kit is None:
            try:
                from dev_tools.visual_dev_kit import install_visual_dev_kit
                kit = install_visual_dev_kit(self.main_window, self.project_root)
            except (ImportError, RuntimeError, AttributeError) as exc:
                self.console.write(f"[ERROR] Inspector unavailable: {exc}")
                return
        kit.show_kit("inspector")
        self._refresh_widget_info(getattr(kit, "selected_widget", None))

# شرح الدالة toggle_grid: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def toggle_grid(self) -> None:
        """Toggle the existing Visual Dev Kit grid overlay."""
        kit = getattr(self.main_window, "_visual_dev_kit", None)
        if kit is None:
            self.toggle_inspector()
            kit = getattr(self.main_window, "_visual_dev_kit", None)
        if kit is None:
            return
        try:
            check = getattr(kit, "grid_check", None)
            if check is not None:
                check.setChecked(not check.isChecked())
        except (RuntimeError, AttributeError):
            return

# شرح الدالة open_color_inspector: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def open_color_inspector(self) -> None:
        """Open the existing color inspector or Visual Dev Kit color page."""
        kit = getattr(self.main_window, "_visual_dev_kit", None)
        if kit is not None:
            kit.show_kit("colors")
            return
        try:
            from dev_tools.ui_color_inspector import install_color_inspector
            install_color_inspector(self.main_window, self.project_root)
        except (ImportError, RuntimeError, AttributeError) as exc:
            self.console.write(f"[ERROR] Color inspector unavailable: {exc}")

# Function explanation: executes a logical step related to the functionality of this file.
    def _refresh_widget_info(self, widget: QWidget | None) -> None:
        """Render class, geometry, layout and style details for a widget."""
        if widget is None:
            self.widget_info.setPlainText("No widget selected.")
            return
        lines = [
            f"Class: {widget.metaObject().className()}",
            f"Object name: {widget.objectName() or '<unnamed>'}",
            f"Geometry: {widget.geometry().getRect()}",
            f"Visible: {widget.isVisible()}",
            f"Enabled: {widget.isEnabled()}",
            f"Window: {widget.window().metaObject().className()}",
            f"Style sheet length: {len(widget.styleSheet())}",
            f"Style sheet:\n{widget.styleSheet() or '<inherited/global>'}",
        ]
        layout = widget.layout()
        if layout is not None:
            m = layout.contentsMargins()
            lines.append(
                f"Layout: {layout.metaObject().className()} "
                f"margins={(m.left(), m.top(), m.right(), m.bottom())} "
                f"spacing={layout.spacing()}"
            )
        lines.append("Signals/slots: inspectable Qt meta-object methods:")
        meta = widget.metaObject()
        for index in range(meta.methodOffset(), meta.methodCount()):
            method = meta.method(index)
            # Wrap in bytes() to safely handle bytes, bytearray, or memoryview 
            signature = bytes(method.methodSignature().data()).decode("utf-8", errors="replace")
            if signature:
                lines.append(f"  {signature}")
        self.widget_info.setPlainText("\n".join(lines))

# Function explanation: executes a logical step related to the functionality of this file.
    def evaluate(self) -> None:
        """Evaluate a restricted Decimal-first expression in the sandbox."""
        source = self.editor.toPlainText().strip()
        if not source:
            self.result.setPlainText("Enter an expression first.")
            return
        try:
            tree = ast.parse(source, mode="eval")
        except SyntaxError as exc:
            self.result.setPlainText(f"Syntax error: {exc}")
            return
        allowed_nodes = (
            ast.Expression, ast.Constant, ast.Name, ast.BinOp, ast.UnaryOp,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
            ast.USub, ast.UAdd, ast.Call, ast.Attribute, ast.Load,
        )
        if any(not isinstance(node, allowed_nodes) for node in ast.walk(tree)):
            self.result.setPlainText("Blocked syntax. Use a Decimal-first expression.")
            return
        globals_map = {
            "__builtins__": {},
            "D": amount,
            "amount": amount,
            "q2": q2,
            "tx": MockTransaction(),
            "transaction": transaction,
            "state": self._active_state(),
        }
        try:
            result = eval(compile(tree, "<developer-sandbox>", "eval"), globals_map, {})
            self.result.setPlainText(repr(result))
        except (ValueError, TypeError, ZeroDivisionError, AttributeError, KeyError) as exc:
            self.result.setPlainText(f"{type(exc).__name__}: {exc}")

# شرح الدالة set_locale: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def set_locale(self, index: int) -> None:
        """Switch the active application locale through the existing controller."""
        value = str(self.locale_box.itemData(index))
        language = set_language_value(value)
        apply_language = getattr(self.main_window, "apply_language", None)
        if callable(apply_language):
            apply_language(language)
        else:
            self.console.write(f"[STATE] Requested locale: {language}")

# شرح الدالة set_permission: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def set_permission(self, index: int) -> None:
        """Temporarily replace the current user object with a mock role."""
        app = QApplication.instance()
        if app is None:
            return
        role = str(self.permission_box.itemData(index))
        current = app.property("buildoffice_current_user")
        user = dict(current) if isinstance(current, dict) else {}
        user["role"] = role
        user["developer_mode"] = True
        app.setProperty("buildoffice_current_user", user)
        self.console.write(f"[STATE] Mock permission -> {role}")

# شرح الدالة _active_state: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _active_state(self) -> dict[str, Any]:
        """Return non-sensitive runtime state exposed to the sandbox."""
        app = QApplication.instance()
        if app is None:
            return {}
        state = app.property("buildoffice_mock_state")
        return dict(state) if isinstance(state, dict) else {}

# شرح الدالة inject_mock_state: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def inject_mock_state(self) -> None:
        """Inject a small non-persistent project state for UI testing."""
        app = QApplication.instance()
        if app is None:
            return
        app.setProperty(
            "buildoffice_mock_state",
            {
                "project_id": "DEV-001",
                "project_name": "Developer Test Project",
                "contract_ht": amount("1000000"),
                "executed_ht": amount("425000"),
                "attendance_hours": amount("168"),
            },
        )
        refresh = getattr(self.main_window, "refresh_current", None)
        if callable(refresh):
            refresh()
        self.console.write("[STATE] Mock project state injected into QApplication.")

# شرح الدالة _delay_changed: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _delay_changed(self, value: int) -> None:
        """Update artificial runtime latency."""
        normalized = set_delay_ms(value)
        self.delay_label.setText(f"{normalized} ms")
        self.console.write(f"[STATE] Artificial delay -> {normalized} ms")

# شرح الدالة run_validation: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def run_validation(self) -> None:
        """Run the project's existing static validation utility."""
        stdout = io.StringIO()
        stderr = io.StringIO()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = validate_project()
        except (OSError, SyntaxError, ImportError, ValueError) as exc:
            self.console.write(f"[VALIDATE] {type(exc).__name__}: {exc}")
            return
        output = stdout.getvalue() + stderr.getvalue()
        self.console.write(f"[VALIDATE] exit={code}\n{output}")

# شرح الدالة run_button_audit: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def run_button_audit(self) -> None:
        """Run the existing static button audit across application pages."""
        chunks: list[str] = []
        pages = sorted((self.project_root / "pages").glob("*_page.py"))
        for page in pages:
            try:
                buttons, connects, handlers = audit_file(page)
            except (OSError, SyntaxError, ValueError) as exc:
                chunks.append(f"{page.name}: {type(exc).__name__}: {exc}")
                continue
            chunks.append(
                f"{page.name}: buttons={len(buttons)} connects={connects} "
                f"methods={len(handlers)}"
            )
        self.console.write("[BUTTON AUDIT]\n" + "\n".join(chunks))

# شرح الدالة _show_health: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _show_health(self, title: str, data: dict[str, Any]) -> None:
        """Render diagnostic results as compact readable text."""
        lines = [title, "=" * len(title)]
        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"{key}: {len(value)}")
                for item in value[:20]:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {value}")
        self.health_output.setPlainText("\n".join(lines))
        self.show_kit("health")

# شرح الدالة run_translation_audit: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def run_translation_audit(self) -> None:
        """Run the read-only translation audit."""
        result = TranslationAudit(self.project_root).run()
        self._show_health("Translation Audit", result)
        self.console.write(f"[TRANSLATION] missing_ar={len(result['missing_ar'])} missing_en={len(result['missing_en'])} hardcoded={len(result['hardcoded'])}")

# شرح الدالة run_theme_audit: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def run_theme_audit(self) -> None:
        """Run the read-only theme contrast audit."""
        result = ThemeAudit(self.project_root).run()
        self._show_health("Theme / Contrast Audit", result)
        self.console.write(f"[THEME] colors={len(result['colors'])} warning_pairs={result['warning_count']}")

# شرح الدالة run_database_audit: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def run_database_audit(self) -> None:
        """Run the read-only database health audit."""
        result = DatabaseAudit(self.project_root).run()
        self._show_health("Database Health", result)
        self.console.write(f"[DATABASE] status={result.get('status', 'UNKNOWN')}")

# شرح الدالة create_snapshot: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def create_snapshot(self) -> None:
        """Create a JSON diagnostic snapshot in the project's diagnostics folder."""
        runtime = {
            "developer_hooks": self.mode_check.isChecked(),
            "performance_hud": self._hud_enabled,
            "service_profiler": self.profiler.active,
            "locale": get_language(),
            "artificial_delay_ms": self.delay_slider.value(),
            "events_seen": self._event_count,
        }
        data = DiagnosticSnapshot(self.project_root).build(runtime)
        destination = self.project_root / "diagnostics" / f"snapshot_{time.strftime('%Y%m%d_%H%M%S')}.json"
        try:
            path = DiagnosticSnapshot(self.project_root).save(data, destination)
        except OSError as exc:
            self.console.write(f"[SNAPSHOT] OSError: {exc}")
            return
        self._show_health("Diagnostic Snapshot", {"saved": str(path.relative_to(self.project_root)), "status": "PASS"})
        self.console.write(f"[SNAPSHOT] {path}")

# شرح الدالة toggle_hud: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def toggle_hud(self) -> None:
        """Toggle the performance HUD."""
        self.set_hud_enabled(not self._hud_enabled)
        self.hud_check.setChecked(self._hud_enabled)

# شرح الدالة toggle_console: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def toggle_console(self) -> None:
        """Show the developer console window."""
        self.show()
        central_widget = self.centralWidget()
        tabs = central_widget.findChild(QTabWidget) if central_widget is not None else None
        if tabs is not None:
            tabs.setCurrentIndex(1)
        self.raise_()
        self.activateWindow()

# شرح الدالة reset_runtime: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def reset_runtime(self) -> None:
        """Restore developer runtime state without touching business data."""
        self.delay_slider.setValue(0)
        self.permission_box.setCurrentIndex(0)
        self.inject_mock_state()
        self.console.write("[STATE] Developer runtime reset.")

# شرح الدالة _append_console: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _append_console(self, text: str) -> None:
        """Append a timestamped line to the console."""
        if not hasattr(self, "console_output"):
            return
        timestamp = time.strftime("%H:%M:%S")
        self.console_output.appendPlainText(f"[{timestamp}] {text}")

# شرح الدالة show_kit: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def show_kit(self, tool: str = "overview") -> None:
        """Show the compact developer window and select a tool tab."""
        self.showNormal()
        self.show()
        central_widget = self.centralWidget()
        tabs = central_widget.findChild(QTabWidget) if central_widget is not None else None
        if tabs is not None:
            index_map = {"sandbox": 0, "console": 1, "diagnostics": 2, "health": 3, "runtime": 4, "state": 4}
            if tool in index_map:
                tabs.setCurrentIndex(index_map[tool])
        self.raise_()
        self.activateWindow()

# شرح الدالة closeEvent: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def closeEvent(self, event) -> None:
        """Disable all runtime hooks when the developer window closes."""
        self._set_runtime(False)
        self.profiler.disable()
        self._remove_exception_hook()
        for shortcut in self._shortcuts:
            shortcut.setEnabled(False)
        self._shortcuts.clear()
        set_delay_ms(0)
        super().closeEvent(event)


# شرح الدالة install_dev_manager: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def install_dev_manager(main_window: QMainWindow, project_root: Path | None = None) -> DevManager:
    """Install one developer manager on the main window."""
    existing = getattr(main_window, "_dev_manager", None)
    if existing is not None:
        return existing
    manager = DevManager(main_window, project_root)
    main_window_any: Any = main_window
    main_window_any._dev_manager = manager
    return manager


__all__ = ["DevManager", "MockTransaction", "install_dev_manager"]

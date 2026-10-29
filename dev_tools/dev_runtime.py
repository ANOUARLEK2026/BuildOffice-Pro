# ============================================================
# شرح الملف: dev_tools/dev_runtime.py
# هذا الملف جزء من أدوات التطوير والتشخيص ومراقبة الأداء.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Runtime state shared by BuildOffice Pro developer tools."""
from __future__ import annotations

import time
from contextlib import contextmanager
from threading import RLock

_lock = RLock()
_enabled = False
_delay_ms = 0
_metrics = {
    "last_page_ms": 0.0,
    "last_chart_ms": 0.0,
    "last_query_ms": 0.0,
    "last_service_ms": 0.0,
    "last_stall_ms": 0.0,
    "page_count": 0,
    "chart_count": 0,
    "query_count": 0,
    "service_count": 0,
}


# شرح الدالة is_enabled: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def is_enabled() -> bool:
    """Return whether developer runtime hooks are enabled."""
    with _lock:
        return _enabled


# شرح الدالة set_enabled: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def set_enabled(value: bool) -> None:
    """Enable or disable developer runtime hooks."""
    global _enabled
    with _lock:
        _enabled = bool(value)
        if not _enabled:
            for key in _metrics:
                if key.endswith("_ms"):
                    _metrics[key] = 0.0


# شرح الدالة get_delay_ms: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def get_delay_ms() -> int:
    """Return the configured artificial service delay."""
    with _lock:
        return _delay_ms


# شرح الدالة set_delay_ms: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def set_delay_ms(value: int) -> int:
    """Set the artificial service delay and return the normalized value."""
    global _delay_ms
    normalized = max(0, min(int(value), 5000))
    with _lock:
        _delay_ms = normalized
    return normalized


# شرح الدالة maybe_delay: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def maybe_delay() -> None:
    """Inject the configured delay only while developer mode is active."""
    with _lock:
        enabled = _enabled
        delay = _delay_ms
    if enabled and delay:
        time.sleep(delay / 1000.0)


# شرح الدالة record_metric: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def record_metric(kind: str, elapsed_ms: float) -> None:
    """Record one developer timing metric without affecting production behavior."""
    if not is_enabled():
        return
    value = max(0.0, float(elapsed_ms))
    key = f"last_{kind}_ms"
    count_key = f"{kind}_count"
    with _lock:
        if key in _metrics:
            _metrics[key] = value
        if count_key in _metrics:
            _metrics[count_key] += 1


# شرح الدالة record_stall: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def record_stall(elapsed_ms: float) -> None:
    """Record the latest event-loop stall."""
    if not is_enabled():
        return
    with _lock:
        _metrics["last_stall_ms"] = max(0.0, float(elapsed_ms))


# شرح الدالة snapshot_metrics: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def snapshot_metrics() -> dict[str, float | int]:
    """Return a copy of current developer timing metrics."""
    with _lock:
        return dict(_metrics)


# شرح الدالة timed: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
@contextmanager
def timed(kind: str, label: str = ""):
    """Measure an operation and optionally return its elapsed duration to callers."""
    started = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        record_metric(kind, elapsed_ms)


# شرح الدالة disabled_hooks: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
@contextmanager
def disabled_hooks():
    """Temporarily disable developer runtime hooks."""
    global _enabled
    with _lock:
        previous = _enabled
        _enabled = False
    try:
        yield
    finally:
        with _lock:
            _enabled = previous

# ============================================================
# شرح الملف: services/settings_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""وصول مركزي إلى إعدادات التطبيق التي يحددها المستخدم."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from repositories.db import get_connection

_CACHE: dict[str, Any] = {}

DEFAULTS = {
    "currency": "DZD",
    "default_tva": "19",
    "date_format": "yyyy-MM-dd",
    "startup_page": "Dashboard",
    "theme": "Dark",
    "color_palette": "option_1",
    "language": "en",
    "backup_on_start": "1",
    "auto_backup_days": "7",
    "alert_document_days": "30",
    "alert_progress_gap": "15",
    "alert_collection_rate": "50",
    "alert_cost_progress_gap": "15",
    "intelligence_enabled": "1",
    "ai_assistant_enabled": "1",
    "ai_max_results": "20",
    "decimal_places": "2",
    "default_retention": "0",
    "default_advance_recovery": "0",
    "default_situation_status": "Draft",
    "confirm_destructive": "1",
    "media_retention_days": "0",
    "auto_backup_enabled": "1",
}

CURRENCY_SYMBOLS = {
    "DZD": "DZD",
    "EUR": "EUR",
    "USD": "USD",
    "GBP": "GBP",
}

QT_DATE_FORMATS = {
    "yyyy-MM-dd": "yyyy-MM-dd",
    "dd/MM/yyyy": "dd/MM/yyyy",
    "dd-MM-yyyy": "dd-MM-yyyy",
    "MM/dd/yyyy": "MM/dd/yyyy",
}

PY_DATE_FORMATS = {
    "yyyy-MM-dd": "%Y-%m-%d",
    "dd/MM/yyyy": "%d/%m/%Y",
    "dd-MM-yyyy": "%d-%m-%Y",
    "MM/dd/yyyy": "%m/%d/%Y",
}


# شرح الدالة clear_settings_cache: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def clear_settings_cache() -> None:
    """إبطال ذاكرة الإعدادات المؤقتة بعد حفظ التغييرات."""
    _CACHE.clear()


# شرح الدالة get_setting: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def get_setting(key: str, default: Any = None) -> Any:
    """قراءة إعداد واحد من SQLite مع استخدام القيمة الاحتياطية عند الحاجة."""
    if key in _CACHE:
        return _CACHE[key]

    fallback = DEFAULTS.get(key, default)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT setting_value FROM settings WHERE setting_key=?",
            (key,),
        ).fetchone()
        value = fallback if row is None or row[0] is None or str(row[0]).strip() == "" else str(row[0]).strip()
        _CACHE[key] = value
        return value
    except sqlite3.Error:
        # أخطاء قاعدة البيانات لا ينبغي أن تخفي أخطاء برمجية غير متوقعة.
        return fallback
    finally:
        conn.close()


# شرح الدالة currency_code: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def currency_code() -> str:
    value = str(get_setting("currency", "DZD")).upper()
    return value if value in CURRENCY_SYMBOLS else "DZD"


# شرح الدالة currency_suffix: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def currency_suffix() -> str:
    return CURRENCY_SYMBOLS[currency_code()]


# شرح الدالة money_display: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def money_display(value: Any) -> str:
    """تنسيق مبلغ باستخدام العملة المحددة في الإعدادات."""
    try:
        return f"{float(value or 0):,.2f} {currency_suffix()}"
    except (TypeError, ValueError):
        return f"0.00 {currency_suffix()}"


# شرح الدالة default_tva: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def default_tva() -> float:
    try:
        value = float(get_setting("default_tva", "19"))
        return value if value in (0, 9, 19) else 19.0
    except (TypeError, ValueError):
        return 19.0


# شرح الدالة tva_amount: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def tva_amount(ht: Any, rate: Any = None) -> float:
    try:
        base = float(ht or 0)
        tv = default_tva() if rate is None else float(rate or 0)
        return base * tv / 100.0
    except (TypeError, ValueError):
        return 0.0


# شرح الدالة apply_tva: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def apply_tva(ht: Any, rate: Any = None) -> float:
    try:
        base = float(ht or 0)
        return base + tva_amount(base, rate)
    except (TypeError, ValueError):
        return 0.0


# شرح الدالة qt_date_format: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def qt_date_format() -> str:
    value = str(get_setting("date_format", "yyyy-MM-dd"))
    return QT_DATE_FORMATS.get(value, "yyyy-MM-dd")


# شرح الدالة format_date: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def format_date(value: Any) -> str:
    """تنسيق تاريخ أو وقت بصيغة ISO وفق تنسيق العرض المحدد في الإعدادات."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    for parser in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], parser).replace(tzinfo=timezone.utc).strftime(
                PY_DATE_FORMATS.get(get_setting("date_format", "yyyy-MM-dd"), "%Y-%m-%d")
            )
        except ValueError:
            pass
    return text


# شرح الدالة setting_bool: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def setting_bool(key: str, default: bool = False) -> bool:
    """قراءة إعداد منطقي مخزن كـ 0/1 أو true/false."""
    value = str(get_setting(key, "1" if default else "0")).strip().lower()
    return value in {"1", "true", "yes", "on", "enabled"}


# شرح الدالة setting_int: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def setting_int(key: str, default: int = 0, minimum: int | None = None, maximum: int | None = None) -> int:
    """قراءة رقم صحيح مع حماية من القيم غير الصالحة."""
    try:
        value = int(float(get_setting(key, str(default))))
    except (TypeError, ValueError):
        value = int(default)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


# شرح الدالة setting_float: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def setting_float(key: str, default: float = 0.0, minimum: float | None = None, maximum: float | None = None) -> float:
    """قراءة رقم عشري مع حماية من القيم غير الصالحة."""
    try:
        value = float(get_setting(key, str(default)))
    except (TypeError, ValueError):
        value = float(default)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


# شرح الدالة decimal_places: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def decimal_places() -> int:
    return setting_int("decimal_places", 2, 0, 4)


# شرح الدالة alert_document_days: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def alert_document_days() -> int:
    return setting_int("alert_document_days", 30, 1, 365)


# شرح الدالة alert_progress_gap: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def alert_progress_gap() -> float:
    return setting_float("alert_progress_gap", 15, 0, 100)


# شرح الدالة alert_collection_rate: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def alert_collection_rate() -> float:
    return setting_float("alert_collection_rate", 50, 0, 100)


# شرح الدالة alert_cost_progress_gap: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def alert_cost_progress_gap() -> float:
    return setting_float("alert_cost_progress_gap", 15, 0, 100)


__all__ = [
    "alert_collection_rate",
    "alert_cost_progress_gap",
    "alert_document_days",
    "alert_progress_gap",
    "apply_tva",
    "clear_settings_cache",
    "currency_code",
    "currency_suffix",
    "decimal_places",
    "default_tva",
    "format_date",
    "get_setting",
    "money_display",
    "qt_date_format",
    "setting_bool",
    "setting_float",
    "setting_int",
    "tva_amount",
]

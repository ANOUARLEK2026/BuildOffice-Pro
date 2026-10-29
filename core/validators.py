# ============================================================
# شرح الملف: core/validators.py
# هذا الملف جزء من المكوّنات الأساسية المشتركة في التطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
from __future__ import annotations

import math
import re
from datetime import date

ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,120}$")


# شرح الدالة required: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def required(value: object, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is required.")
    return text


# شرح الدالة non_negative: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def non_negative(value: float, field: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number.")
    if number < 0:
        raise ValueError(f"{field} cannot be negative.")
    return number


# شرح الدالة positive: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def positive(value: float, field: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number.")
    if number <= 0:
        raise ValueError(f"{field} must be greater than zero.")
    return number


# شرح الدالة identifier: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def identifier(value: str, field: str = "ID") -> str:
    text = required(value, field)
    if not ID_RE.fullmatch(text):
        raise ValueError(f"Invalid {field}.")
    return text


# شرح الدالة iso_date: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def iso_date(value: str, field: str = "Date") -> str:
    text = required(value, field)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"Invalid {field}. Use YYYY-MM-DD.") from exc
    return text

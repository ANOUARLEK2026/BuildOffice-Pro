# ============================================================
# شرح الملف: services/i18n.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: مصدر اللغة الوحيد في التطبيق هو core.i18n.
"""Compatibility wrapper around the centralized localization service."""
from __future__ import annotations

from core.i18n import LANGUAGE_AR, LANGUAGE_EN, get_language, translate_text


# شرح الدالة translate: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def translate(key: str, language: str | None = None, default: str | None = None) -> str:
    """ترجمة نص من المصدر المركزي باستخدام لغة الإعدادات عند عدم تحديدها."""
    result = translate_text(key, language or get_language())
    return default if result == key and default is not None else result


__all__ = ["LANGUAGE_AR", "LANGUAGE_EN", "translate"]

# ============================================================
# شرح الملف: core/logging_config.py
# هذا الملف جزء من المكوّنات الأساسية المشتركة في التطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. استخدم الإعدادات المركزية وتجنب تعديل منطق الأعمال من الواجهة.
"""إعداد السجل المركزي للتطبيق، مع الحفاظ على واجهة logger الحالية."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from core.config import (
    LOG_BACKUP_COUNT,
    LOG_FILENAME,
    LOG_LEVEL,
    LOG_MAX_BYTES,
    log_dir,
)


# شرح الدالة configure_logging: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def configure_logging() -> logging.Logger:
    """إنشاء logger واحد للتطبيق وعدم إضافة handlers مكررة."""
    logger = logging.getLogger("buildoffice")
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    handler = RotatingFileHandler(
        log_dir() / LOG_FILENAME,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    logger.addHandler(handler)
    return logger


# نقطة الاستخدام الموحدة لبقية المشروع.
logger = configure_logging()

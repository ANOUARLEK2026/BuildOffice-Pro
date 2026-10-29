# ============================================================
# شرح الملف: core/transaction.py
# هذا الملف جزء من المكوّنات الأساسية المشتركة في التطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from database.database import get_connection


# شرح الدالة transaction: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
@contextmanager
def transaction(conn: sqlite3.Connection | None = None) -> Iterator[sqlite3.Connection]:
    """Own exactly one transaction and close only connections created here."""
    owns = conn is None
    active = conn or get_connection()
    try:
        if active.in_transaction:
            yield active
        else:
            active.execute("BEGIN IMMEDIATE")
            try:
                yield active
                active.commit()
            except (sqlite3.Error, ValueError, TypeError, OSError):
                active.rollback()
                raise
    finally:
        if owns:
            active.close()

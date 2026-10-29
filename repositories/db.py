# ============================================================
# شرح الملف: repositories/db.py
# هذا الملف جزء من طبقة الوصول إلى البيانات والمستودعات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Single repository-facing database gateway.

Pages and services use this module instead of importing the database connection
directly. SQL can then be migrated into domain repositories incrementally without
changing connection semantics.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from database.database import get_connection as _get_connection


# شرح الدالة get_connection: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def get_connection():
    """Return a configured SQLite connection through the repository boundary."""
    return _get_connection()


# شرح الدالة fetchone: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def fetchone(conn, sql, params=()):
    """Fetch one row through the repository query boundary."""
    return conn.execute(sql, params).fetchone()


# شرح الدالة fetchall: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def fetchall(conn, sql, params=()):
    """Fetch all rows through the repository query boundary."""
    return conn.execute(sql, params).fetchall()


# شرح الدالة execute: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def execute(conn, sql, params=()):
    """Execute one statement through the repository query boundary."""
    return conn.execute(sql, params)


# شرح الدالة session: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
@contextmanager
def session():
    """Open a repository session with commit/rollback semantics."""
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except (sqlite3.Error, ValueError, TypeError, OSError):
        conn.rollback()
        raise
    finally:
        conn.close()

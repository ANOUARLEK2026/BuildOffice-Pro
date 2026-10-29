# ============================================================
# شرح الملف: core/id_service.py
# هذا الملف جزء من المكوّنات الأساسية المشتركة في التطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
"""Atomic, non-reusing business ID allocation."""
from __future__ import annotations

import secrets
import sqlite3

from database.database import get_connection


# شرح الدالة _ensure_registry: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _ensure_registry(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS id_sequences (
        sequence_key TEXT PRIMARY KEY,
        next_value INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS id_registry (
        entity_id TEXT PRIMARY KEY,
        entity_type TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")


# شرح الدالة _reserve: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _reserve(conn: sqlite3.Connection, entity_id: str, entity_type: str, key: str, next_value: int) -> str:
    _ensure_registry(conn)
    conn.execute("INSERT INTO id_registry(entity_id,entity_type) VALUES(?,?)", (entity_id, entity_type))
    conn.execute("""INSERT INTO id_sequences(sequence_key,next_value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(sequence_key) DO UPDATE SET next_value=excluded.next_value, updated_at=CURRENT_TIMESTAMP""", (key, next_value))
    return entity_id


# شرح الدالة _next: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _next(conn: sqlite3.Connection, key: str) -> int:
    row = conn.execute("SELECT next_value FROM id_sequences WHERE sequence_key=?", (key,)).fetchone()
    return int(row[0]) if row else 1


# شرح الدالة next_sequence_id: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def next_sequence_id(conn: sqlite3.Connection | None, prefix: str, *, scope: str | None = None, digits: int = 3) -> str:
    key = f"{prefix}:{scope}" if scope else prefix
    own = conn is None
    target = conn or get_connection()
    try:
        if own and not target.in_transaction:
            target.execute("BEGIN IMMEDIATE")
        _ensure_registry(target)
        value = _next(target, key)
        while target.execute("SELECT 1 FROM id_registry WHERE entity_id=?", (f"{prefix}-{value:0{digits}d}",)).fetchone():
            value += 1
        entity_id = f"{prefix}-{value:0{digits}d}"
        _reserve(target, entity_id, prefix, key, value + 1)
        if own:
            target.commit()
        return entity_id
    except (sqlite3.Error, ValueError, TypeError, OSError):
        if own:
            target.rollback()
        raise
    finally:
        if own:
            target.close()


# شرح الدالة next_child_id: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def next_child_id(conn: sqlite3.Connection | None, prefix: str, *parent_ids: str, digits: int = 3) -> str:
    if not parent_ids or any(not str(x).strip() for x in parent_ids):
        raise ValueError("parent_ids are required")
    parent_part = "-".join(str(x) for x in parent_ids)
    out_prefix = f"{prefix}-{parent_part}"
    return next_sequence_id(conn, out_prefix, scope=out_prefix, digits=digits).replace(f"{out_prefix}-", f"{out_prefix}-", 1)


# شرح الدالة next_random_id: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def next_random_id(conn: sqlite3.Connection | None, prefix: str, *, digits: int = 10) -> str:
    own = conn is None
    target = conn or get_connection()
    try:
        if own and not target.in_transaction:
            target.execute("BEGIN IMMEDIATE")
        _ensure_registry(target)
        while True:
            entity_id = f"{prefix}-{secrets.randbelow(10**digits):0{digits}d}"
            if not target.execute("SELECT 1 FROM id_registry WHERE entity_id=?", (entity_id,)).fetchone():
                _reserve(target, entity_id, prefix, f"random:{prefix}", _next(target, f"random:{prefix}"))
                break
        if own:
            target.commit()
        return entity_id
    except (sqlite3.Error, ValueError, TypeError, OSError):
        if own:
            target.rollback()
        raise
    finally:
        if own:
            target.close()

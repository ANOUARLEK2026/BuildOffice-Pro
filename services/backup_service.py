# ============================================================
# شرح الملف: services/backup_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
"""SQLite-safe backup and restore helpers."""
from __future__ import annotations

import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from core.config import (
    BACKUP_FILENAME_PREFIX,
    DATABASE_TIMEOUT_SECONDS,
    RESTORE_TEMP_SUFFIX,
    SAFETY_BACKUP_PREFIX,
)
from database import database as db


# شرح الدالة _backup_file: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _backup_file(source: Path, destination: Path) -> None:
    """Copy a SQLite database using the SQLite backup API."""
    src = sqlite3.connect(source)
    dst = sqlite3.connect(destination)
    try:
        src.backup(dst)
        dst.commit()
    finally:
        dst.close()
        src.close()


# شرح الدالة validate_backup: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def validate_backup(path: str | Path) -> bool:
    """Return True only when the SQLite database passes integrity checks."""
    db_path = Path(path)
    if not db_path.exists() or not db_path.is_file():
        return False
    try:
        c = sqlite3.connect(db_path, timeout=DATABASE_TIMEOUT_SECONDS)
        try:
            integrity = c.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_keys = c.execute("PRAGMA foreign_key_check").fetchone()
            return integrity == "ok" and foreign_keys is None
        finally:
            c.close()
    except sqlite3.DatabaseError:
        return False


# شرح الدالة validate_database: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def validate_database(path: str | Path) -> bool:
    """Backward-compatible public name used by the Backup page."""
    return validate_backup(path)


# شرح الدالة create_backup: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def create_backup(target_dir: str | Path) -> Path:
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    out = target / f"{BACKUP_FILENAME_PREFIX}{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}.db"
    tmp = out.with_name(out.name + ".tmp")
    try:
        _backup_file(Path(db.DATABASE_FILE), tmp)
        if not validate_backup(tmp):
            raise RuntimeError("Backup integrity validation failed.")
        os.replace(tmp, out)
        return out
    finally:
        tmp.unlink(missing_ok=True)


# شرح الدالة restore_backup: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def restore_backup(source: str | Path, target: str | Path | None = None) -> Path:
    """Safely restore a validated SQLite backup without risking the live DB.

    The source is validated first, copied to a temporary database, validated
    again, then atomically replaced. When replacing an existing target, a
    safety backup is kept and used for rollback if the final validation fails.
    """
    source = Path(source)
    target = Path(target) if target is not None else Path(db.DATABASE_FILE)
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(source)
    if source.resolve() == target.resolve():
        if not validate_backup(source):
            raise RuntimeError("Cannot restore an invalid database over itself.")
        return target
    if not validate_backup(source):
        raise RuntimeError("Backup failed integrity validation; current database was not changed.")

    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=RESTORE_TEMP_SUFFIX, dir=target.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    safety = target.with_name(target.name + f"{SAFETY_BACKUP_PREFIX}{target.name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}.db")
    try:
        _backup_file(source, tmp)
        if not validate_backup(tmp):
            raise RuntimeError("Prepared restore failed integrity validation; current database was not changed.")

        had_target = target.exists()
        if had_target:
            _backup_file(target, safety)
            if not validate_backup(safety):
                raise RuntimeError("Safety backup failed integrity validation; current database was not changed.")

        os.replace(tmp, target)
        if not validate_backup(target):
            raise RuntimeError("Final restored database failed integrity validation.")
        return target
    except (OSError, sqlite3.Error, RuntimeError, ValueError):
        if target.exists() and safety.exists():
            rollback_tmp = safety.with_suffix(safety.suffix + ".rollback.tmp")
            try:
                _backup_file(safety, rollback_tmp)
                os.replace(rollback_tmp, target)
            finally:
                rollback_tmp.unlink(missing_ok=True)
        raise
    finally:
        tmp.unlink(missing_ok=True)
        safety.unlink(missing_ok=True)

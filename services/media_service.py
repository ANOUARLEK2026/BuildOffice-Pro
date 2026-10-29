# ============================================================
# شرح الملف: services/media_service.py
# خدمة مركزية لحفظ واسترجاع الصور والمرفقات المرتبطة بسجلات البرنامج.
# ============================================================
from __future__ import annotations

import mimetypes
import shutil
import sqlite3
import uuid
from pathlib import Path

from core.config import ROOT_DIR
from repositories.db import get_connection

MEDIA_ROOT = ROOT_DIR / "media"


def ensure_media_root() -> Path:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    return MEDIA_ROOT


def add_media(owner_type: str, owner_id: str | None, source_path: str,
              media_type: str = "Document", description: str = "") -> str:
    """Copy a file into the managed media store and register its metadata."""
    source = Path(source_path)
    if not source.is_file():
        raise FileNotFoundError(source_path)

    ensure_media_root()
    media_id = f"MED-{uuid.uuid4().hex[:12].upper()}"
    safe_name = source.name
    destination_dir = MEDIA_ROOT / owner_type / (owner_id or "unassigned")
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{media_id}_{safe_name}"
    shutil.copy2(source, destination)

    mime = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
    size = destination.stat().st_size

    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO media_items(
                media_id, owner_type, owner_id, media_type, file_name,
                file_path, mime_type, file_size, description
            ) VALUES(?,?,?,?,?,?,?,?,?)
        """, (
            media_id, owner_type, owner_id, media_type, safe_name,
            str(destination), mime, size, description or None,
        ))
        conn.commit()
    except (OSError, sqlite3.Error, ValueError, TypeError):
        conn.rollback()
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    finally:
        conn.close()
    return media_id


def delete_media(media_id: str) -> None:
    """Delete a managed attachment and its database metadata."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT file_path FROM media_items WHERE media_id=?", (media_id,)
        ).fetchone()
        if not row:
            return
        conn.execute("DELETE FROM media_items WHERE media_id=?", (media_id,))
        conn.commit()
    finally:
        conn.close()

    try:
        Path(row["file_path"]).unlink(missing_ok=True)
    except OSError:
        pass

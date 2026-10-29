# ============================================================
# شرح الملف: services/audit_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
from __future__ import annotations

import sqlite3

from repositories.db import get_connection


# شرح الدالة audit: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def audit(action: str, entity: str, entity_id=None, description: str = '', user_name: str='Local User', conn: sqlite3.Connection|None=None) -> None:
    owns=conn is None; c=conn or get_connection()
    try:
        c.execute("INSERT INTO audit_log(user_name,action,entity,entity_id,description) VALUES(?,?,?,?,?)",(user_name,action,entity,None if entity_id is None else str(entity_id),description))
        if owns: c.commit()
    except (sqlite3.Error, ValueError, TypeError, OSError):
        if owns: c.rollback()
        raise
    finally:
        if owns: c.close()

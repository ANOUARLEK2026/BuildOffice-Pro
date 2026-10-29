# ============================================================
# شرح الملف: repositories/base.py
# هذا الملف جزء من طبقة الوصول إلى البيانات والمستودعات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
from __future__ import annotations

import sqlite3


# شرح الصنف Repository: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class Repository:
    table: str
    id_column: str

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

# شرح الدالة get: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def get(self, entity_id: str):
        return self.conn.execute(f'SELECT * FROM "{self.table}" WHERE "{self.id_column}"=?', (entity_id,)).fetchone()

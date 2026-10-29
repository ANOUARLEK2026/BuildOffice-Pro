# ============================================================
# شرح الملف: services/attendance_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
"""Attendance operations with duplicate protection and transaction reuse."""
from __future__ import annotations

import sqlite3

from repositories.db import get_connection

STATUSES = {"Present", "Absent", "Leave", "Sick", "Holiday"}


# شرح الدالة save_attendance: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def save_attendance(record_id, staff_id, project_id, date, status, working_hours=0, overtime_hours=0, notes=None, conn=None):
    if status not in STATUSES: raise ValueError("Invalid attendance status.")
    if float(working_hours) < 0 or float(overtime_hours) < 0: raise ValueError("Hours cannot be negative.")
    owns = conn is None; target = conn or get_connection()
    try:
        duplicate = target.execute("SELECT record_id FROM attendance WHERE staff_id=? AND project_id IS ? AND date=? AND record_id<>?", (staff_id, project_id, date, record_id)).fetchone()
        if duplicate: raise ValueError("Attendance already exists for this staff member, project and date.")
        target.execute("""INSERT INTO attendance(record_id,staff_id,project_id,date,status,working_hours,overtime_hours,notes)
                         VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(record_id) DO UPDATE SET staff_id=excluded.staff_id,
                         project_id=excluded.project_id,date=excluded.date,status=excluded.status,
                         working_hours=excluded.working_hours,overtime_hours=excluded.overtime_hours,notes=excluded.notes""",
                       (record_id,staff_id,project_id,date,status,float(working_hours),float(overtime_hours),notes))
        if owns: target.commit()
    except (sqlite3.Error, ValueError, TypeError, OSError):
        if owns: target.rollback()
        raise
    finally:
        if owns: target.close()

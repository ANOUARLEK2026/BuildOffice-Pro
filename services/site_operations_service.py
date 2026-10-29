# ============================================================
# شرح الملف: services/site_operations_service.py
# طبقة خدمات تقارير الموقع اليومية ومراقبة تنفيذ الأعمال.
# التعليقات العربية للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# ============================================================
from __future__ import annotations

import sqlite3
from typing import Any

from core.id_service import next_random_id
from repositories.db import get_connection


def _conn(conn=None):
    return conn or get_connection()


def _owned(conn):
    return conn is None


def list_reports(project_id: str | None = None, date_from: str | None = None, date_to: str | None = None, conn=None):
    c = _conn(conn)
    try:
        sql = """
            SELECT r.report_id, r.report_number, r.report_date, r.weather,
                   r.manpower_count, r.progress_percent, r.work_performed,
                   r.delays, r.safety_notes, r.status, p.project_name
            FROM site_daily_reports r
            JOIN projects p ON p.project_id=r.project_id
            WHERE 1=1
        """
        args: list[Any] = []
        if project_id:
            sql += " AND r.project_id=?"; args.append(project_id)
        if date_from:
            sql += " AND r.report_date>=?"; args.append(date_from)
        if date_to:
            sql += " AND r.report_date<=?"; args.append(date_to)
        sql += " ORDER BY r.report_date DESC, r.report_number DESC"
        return c.execute(sql, args).fetchall()
    finally:
        if _owned(conn): c.close()


def get_report(report_id: str, conn=None):
    c = _conn(conn)
    try:
        return c.execute("SELECT * FROM site_daily_reports WHERE report_id=?", (report_id,)).fetchone()
    finally:
        if _owned(conn): c.close()


def save_report(project_id: str, report_date: str, weather: str = "", manpower_count: int = 0,
                progress_percent: float = 0, work_performed: str = "", materials_used: str = "",
                equipment_used: str = "", delays: str = "", safety_notes: str = "",
                notes: str = "", status: str = "Draft", report_id: str | None = None):
    if not project_id or not report_date:
        raise ValueError("Project and report date are required.")
    progress_percent = max(0.0, min(100.0, float(progress_percent or 0)))
    manpower_count = max(0, int(manpower_count or 0))
    allowed = {"Draft", "Submitted", "Approved"}
    status = status if status in allowed else "Draft"
    c = get_connection()
    try:
        c.execute("BEGIN IMMEDIATE")
        if report_id:
            c.execute("""
                UPDATE site_daily_reports SET project_id=?, report_date=?, weather=?, manpower_count=?,
                    progress_percent=?, work_performed=?, materials_used=?, equipment_used=?, delays=?,
                    safety_notes=?, notes=?, status=?, updated_at=CURRENT_TIMESTAMP WHERE report_id=?
            """, (project_id, report_date, weather or None, manpower_count, progress_percent,
                  work_performed or None, materials_used or None, equipment_used or None,
                  delays or None, safety_notes or None, notes or None, status, report_id))
            rid = report_id
        else:
            rid = next_random_id(c, "sdr", digits=10)
            count = c.execute("SELECT COUNT(*) FROM site_daily_reports WHERE project_id=?", (project_id,)).fetchone()[0]
            number = f"SDR-{project_id}-{count + 1:04d}"
            while c.execute("SELECT 1 FROM site_daily_reports WHERE report_number=?", (number,)).fetchone():
                count += 1; number = f"SDR-{project_id}-{count + 1:04d}"
            c.execute("""
                INSERT INTO site_daily_reports(
                    report_id, project_id, report_number, report_date, weather, manpower_count,
                    progress_percent, work_performed, materials_used, equipment_used, delays,
                    safety_notes, notes, status
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (rid, project_id, number, report_date, weather or None, manpower_count,
                  progress_percent, work_performed or None, materials_used or None,
                  equipment_used or None, delays or None, safety_notes or None, notes or None, status))
        c.commit()
        return rid
    except (sqlite3.Error, ValueError, TypeError, OSError):
        c.rollback(); raise
    finally:
        c.close()


def delete_report(report_id: str) -> None:
    c = get_connection()
    try:
        c.execute("DELETE FROM site_daily_reports WHERE report_id=?", (report_id,))
        c.commit()
    except sqlite3.Error:
        c.rollback(); raise
    finally:
        c.close()


def report_summary(project_id: str | None = None, conn=None) -> dict[str, float | int]:
    c = _conn(conn)
    try:
        where = "WHERE project_id=?" if project_id else ""
        args = (project_id,) if project_id else ()
        r = c.execute(f"""
            SELECT COUNT(*), COALESCE(AVG(progress_percent),0), COALESCE(MAX(progress_percent),0),
                   COALESCE(SUM(CASE WHEN status='Approved' THEN 1 ELSE 0 END),0),
                   COALESCE(SUM(CASE WHEN delays IS NOT NULL AND TRIM(delays)<>'' THEN 1 ELSE 0 END),0)
            FROM site_daily_reports {where}
        """, args).fetchone()
        return {"reports": int(r[0] or 0), "avg_progress": float(r[1] or 0),
                "max_progress": float(r[2] or 0), "approved": int(r[3] or 0), "delayed_reports": int(r[4] or 0)}
    finally:
        if _owned(conn): c.close()


__all__ = ["delete_report", "get_report", "list_reports", "report_summary", "save_report"]

# ============================================================
# Structured field-control extensions for Phase 4 completion.
# ============================================================
def list_progress(report_id: str, conn=None):
    c = _conn(conn)
    try:
        return c.execute("""
            SELECT sp.progress_id, sp.item_id, m.item_number, m.description, m.unit,
                   m.quantity AS planned_quantity, sp.executed_quantity, m.unit_price,
                   sp.executed_quantity * m.unit_price AS amount, sp.notes
            FROM site_report_progress sp
            JOIN metre_items m ON m.item_id=sp.item_id
            WHERE sp.report_id=? ORDER BY m.item_number
        """, (report_id,)).fetchall()
    finally:
        if _owned(conn): c.close()


def save_progress(report_id: str, item_id: str, executed_quantity: float, notes: str = "", progress_id: str | None = None):
    qty = max(0.0, float(executed_quantity or 0))
    c = get_connection()
    try:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT quantity FROM metre_items WHERE item_id=?", (item_id,)).fetchone()
        if not row:
            raise ValueError("BOQ item not found.")
        if qty > float(row[0] or 0):
            raise ValueError("Executed quantity cannot exceed the BOQ planned quantity.")
        if progress_id:
            c.execute("UPDATE site_report_progress SET item_id=?, executed_quantity=?, notes=? WHERE progress_id=?",
                      (item_id, qty, notes or None, progress_id))
        else:
            existing = c.execute("SELECT progress_id FROM site_report_progress WHERE report_id=? AND item_id=?",
                                 (report_id, item_id)).fetchone()
            if existing:
                c.execute("UPDATE site_report_progress SET executed_quantity=?, notes=? WHERE progress_id=?",
                          (qty, notes or None, existing[0]))
            else:
                c.execute("INSERT INTO site_report_progress(progress_id,report_id,item_id,executed_quantity,notes) VALUES(?,?,?,?,?)",
                          (next_random_id(c, "spr", digits=10), report_id, item_id, qty, notes or None))
        c.commit()
    except (sqlite3.Error, ValueError, TypeError, OSError):
        c.rollback(); raise
    finally:
        c.close()


def delete_progress(progress_id: str):
    c = get_connection()
    try:
        c.execute("DELETE FROM site_report_progress WHERE progress_id=?", (progress_id,)); c.commit()
    finally:
        c.close()


def list_report_resources(report_id: str, conn=None):
    c = _conn(conn)
    try:
        rows = []
        # Attendance is the field labor source; no duplicate attendance rows are created.
        r = c.execute("""
            SELECT a.record_id AS source_id, 'Labor' AS resource_type, a.working_hours+a.overtime_hours AS quantity,
                   0 AS unit_cost, 0 AS total_cost, s.name AS description
            FROM site_daily_reports d JOIN attendance a ON a.project_id=d.project_id AND a.date=d.report_date
            LEFT JOIN staff s ON s.staff_id=a.staff_id WHERE d.report_id=?
        """, (report_id,)).fetchall()
        rows.extend(r)
        r = c.execute("""
            SELECT mm.movement_id AS source_id, 'Material' AS resource_type, mm.quantity,
                   mm.unit_cost, mm.quantity*mm.unit_cost AS total_cost, m.name AS description
            FROM site_daily_reports d JOIN material_movements mm ON mm.project_id=d.project_id AND mm.movement_date=d.report_date
            JOIN materials m ON m.material_id=mm.material_id
            WHERE d.report_id=? AND mm.movement_type='Consumption'
        """, (report_id,)).fetchall()
        rows.extend(r)
        r = c.execute("""
            SELECT eu.usage_id AS source_id, 'Equipment' AS resource_type, eu.operating_hours AS quantity,
                   eu.hourly_cost AS unit_cost, eu.operating_hours*eu.hourly_cost+eu.fuel_cost AS total_cost,
                   COALESCE(v.licence_plate, v.brand || ' ' || v.model, 'Equipment') AS description
            FROM site_daily_reports d JOIN equipment_usage eu ON eu.project_id=d.project_id AND eu.usage_date=d.report_date
            LEFT JOIN vehicles v ON v.vehicle_id=eu.vehicle_id WHERE d.report_id=?
        """, (report_id,)).fetchall()
        rows.extend(r)
        return rows
    finally:
        if _owned(conn): c.close()


def report_execution_snapshot(report_id: str, conn=None):
    c = _conn(conn)
    try:
        d = c.execute("SELECT project_id,report_date,progress_percent FROM site_daily_reports WHERE report_id=?", (report_id,)).fetchone()
        if not d: return {}
        progress = c.execute("SELECT COALESCE(SUM(executed_quantity*unit_price),0), COUNT(*) FROM site_report_progress WHERE report_id=?", (report_id,)).fetchone()
        resources = list_report_resources(report_id, c)
        material = sum(float(r['total_cost'] or 0) for r in resources if r['resource_type']=='Material')
        equipment = sum(float(r['total_cost'] or 0) for r in resources if r['resource_type']=='Equipment')
        labor_hours = sum(float(r['quantity'] or 0) for r in resources if r['resource_type']=='Labor')
        return {'progress_value': float(progress[0] or 0), 'progress_items': int(progress[1] or 0),
                'material_cost': material, 'equipment_cost': equipment, 'labor_hours': labor_hours}
    finally:
        if _owned(conn): c.close()

__all__ += ["delete_progress", "list_progress", "list_report_resources", "report_execution_snapshot", "save_progress"]

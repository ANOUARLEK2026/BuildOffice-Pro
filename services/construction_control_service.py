# ============================================================
# شرح الملف: services/construction_control_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Construction-specific operational services.

This module adds the missing field-control layer without replacing the existing
Projects, Métré, Situations, Expenses, Staff or Vehicles modules.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from core.id_service import next_random_id
from repositories.db import get_connection


# شرح الدالة _conn: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _conn(conn=None):
    return conn or get_connection()


# شرح الدالة _own: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _own(conn):
    return conn is None


# شرح الدالة list_projects: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def list_projects(conn=None):
    c = _conn(conn)
    try:
        return c.execute("SELECT project_id, project_name, budget_ht FROM projects ORDER BY project_name").fetchall()
    finally:
        if _own(conn): c.close()


# شرح الدالة list_cost_centers: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def list_cost_centers(project_id: str | None = None, conn=None):
    c = _conn(conn)
    try:
        if project_id:
            return c.execute("SELECT * FROM project_cost_centers WHERE project_id=? ORDER BY code, name", (project_id,)).fetchall()
        return c.execute("SELECT cc.*, p.project_name FROM project_cost_centers cc JOIN projects p ON p.project_id=cc.project_id ORDER BY p.project_name, cc.code").fetchall()
    finally:
        if _own(conn): c.close()


# شرح الدالة save_cost_center: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def save_cost_center(project_id, code, name, budget_amount: float = 0, boq_item_id=None, parent_id=None, cost_center_id=None):
    if not project_id or not name.strip():
        raise ValueError("Project and cost center name are required.")
    c = get_connection()
    try:
        c.execute("BEGIN IMMEDIATE")
        if cost_center_id:
            c.execute("""UPDATE project_cost_centers SET code=?, name=?, budget_amount=?, boq_item_id=?, parent_id=?, updated_at=CURRENT_TIMESTAMP WHERE cost_center_id=? AND project_id=?""", (code or None, name.strip(), max(0, float(budget_amount or 0)), boq_item_id, parent_id, cost_center_id, project_id))
        else:
            cid = next_random_id(c, "cc", digits=10)
            c.execute("""INSERT INTO project_cost_centers(cost_center_id,project_id,code,name,budget_amount,boq_item_id,parent_id) VALUES(?,?,?,?,?,?,?)""", (cid, project_id, code or None, name.strip(), max(0, float(budget_amount or 0)), boq_item_id, parent_id))
            cost_center_id = cid
        c.commit()
        return cost_center_id
    except (sqlite3.Error, ValueError, TypeError, OSError):
        c.rollback(); raise
    finally:
        c.close()


# شرح الدالة save_labor_allocation: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def save_labor_allocation(staff_id, project_id, work_date, hours, hourly_cost: float = 0, cost_center_id=None, activity=None, overtime_hours: float = 0, notes=None, attendance_id=None):
    if not staff_id or not project_id or not work_date:
        raise ValueError("Staff, project and date are required.")
    hours = float(hours or 0); overtime_hours = float(overtime_hours or 0); hourly_cost = float(hourly_cost or 0)
    if hours < 0 or overtime_hours < 0 or hourly_cost < 0: raise ValueError("Hours and cost cannot be negative.")
    c = get_connection()
    try:
        c.execute("BEGIN IMMEDIATE")
        source_type = 'Legacy'
        if attendance_id:
            att = c.execute("SELECT staff_id,project_id,date,working_hours,overtime_hours,status FROM attendance WHERE record_id=?", (attendance_id,)).fetchone()
            if not att: raise ValueError("Attendance record not found.")
            if att['staff_id'] != staff_id: raise ValueError("Attendance belongs to another employee.")
            if att['date'] != work_date: raise ValueError("Labor date must match attendance date.")
            if att['status'] != 'Present': raise ValueError("Only Present attendance can be allocated to site labor.")
            if att['project_id'] and att['project_id'] != project_id: raise ValueError("Project does not match the attendance record.")
            used = c.execute("SELECT COALESCE(SUM(hours),0) h,COALESCE(SUM(overtime_hours),0) ot FROM labor_allocations WHERE attendance_id=?", (attendance_id,)).fetchone()
            if hours > float(att['working_hours'] or 0) - float(used['h'] or 0) + 1e-9: raise ValueError("Regular labor hours exceed the remaining attendance hours.")
            if overtime_hours > float(att['overtime_hours'] or 0) - float(used['ot'] or 0) + 1e-9: raise ValueError("Overtime allocation exceeds the remaining attendance overtime.")
            source_type = 'Attendance'
        aid = next_random_id(c, "la", digits=10)
        c.execute("""INSERT INTO labor_allocations(allocation_id,staff_id,project_id,cost_center_id,work_date,attendance_id,source_type,hours,overtime_hours,hourly_cost,activity,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (aid,staff_id,project_id,cost_center_id,work_date,attendance_id,source_type,hours,overtime_hours,hourly_cost,activity,notes))
        c.commit(); return aid
    except (sqlite3.Error, ValueError, TypeError, OSError):
        c.rollback(); raise
    finally: c.close()

# شرح الدالة attendance_for_labor: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def attendance_for_labor(staff_id=None, work_date=None, project_id=None, conn=None):
    c = conn or get_connection()
    try:
        q = """SELECT a.record_id,a.staff_id,s.full_name,a.project_id,a.date,a.working_hours,a.overtime_hours,
                       a.working_hours-COALESCE(SUM(l.hours),0) available_hours,
                       a.overtime_hours-COALESCE(SUM(l.overtime_hours),0) available_overtime
                FROM attendance a JOIN staff s ON s.staff_id=a.staff_id
                LEFT JOIN labor_allocations l ON l.attendance_id=a.record_id
                WHERE a.status='Present'"""
        params=[]
        if staff_id: q += " AND a.staff_id=?"; params.append(staff_id)
        if work_date: q += " AND a.date=?"; params.append(work_date)
        if project_id: q += " AND (a.project_id IS NULL OR a.project_id=?)"; params.append(project_id)
        q += " GROUP BY a.record_id ORDER BY a.date DESC,s.full_name"
        return c.execute(q, params).fetchall()
    finally:
        if conn is None: c.close()


# شرح الدالة save_equipment_usage: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def save_equipment_usage(vehicle_id, project_id, usage_date, operating_hours, hourly_cost: float = 0, fuel_cost: float = 0, cost_center_id=None, operator_staff_id=None, meter_start=None, meter_end=None, notes=None):
    operating_hours = float(operating_hours or 0); hourly_cost = float(hourly_cost or 0); fuel_cost = float(fuel_cost or 0)
    if operating_hours < 0 or hourly_cost < 0 or fuel_cost < 0: raise ValueError("Equipment hours and costs cannot be negative.")
    c = get_connection()
    try:
        c.execute("BEGIN IMMEDIATE")
        uid = next_random_id(c, "eu", digits=10)
        c.execute("""INSERT INTO equipment_usage(usage_id,vehicle_id,project_id,cost_center_id,usage_date,operating_hours,hourly_cost,fuel_cost,operator_staff_id,meter_start,meter_end,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (uid,vehicle_id,project_id,cost_center_id,usage_date,operating_hours,hourly_cost,fuel_cost,operator_staff_id,meter_start,meter_end,notes))
        c.commit(); return uid
    except (sqlite3.Error, ValueError, TypeError, OSError):
        c.rollback(); raise
    finally: c.close()


# شرح الدالة save_material_movement: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def save_material_movement(material_id, project_id, movement_date, quantity, movement_type, warehouse=None, unit_cost: float = 0, reference=None, notes=None):
    movement_type = movement_type.strip().title()
    if movement_type not in {"Receipt", "Transfer In", "Transfer Out", "Consumption", "Adjustment"}:
        raise ValueError("Unsupported material movement type.")
    quantity = float(quantity or 0); unit_cost = float(unit_cost or 0)
    if quantity <= 0 or unit_cost < 0: raise ValueError("Quantity must be positive and cost cannot be negative.")
    c = get_connection()
    try:
        c.execute("BEGIN IMMEDIATE")
        mid = next_random_id(c, "mm", digits=10)
        c.execute("""INSERT INTO material_movements(movement_id,material_id,project_id,movement_date,movement_type,warehouse,quantity,unit_cost,reference,notes) VALUES(?,?,?,?,?,?,?,?,?,?)""", (mid,material_id,project_id,movement_date,movement_type,warehouse,quantity,unit_cost,reference,notes))
        c.commit(); return mid
    except (sqlite3.Error, ValueError, TypeError, OSError):
        c.rollback(); raise
    finally: c.close()


# شرح الدالة save_material: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def save_material(material_code, name, unit, standard_cost: float = 0, minimum_stock: float = 0, material_id=None):
    if not name.strip(): raise ValueError("Material name is required.")
    c = get_connection()
    try:
        c.execute("BEGIN IMMEDIATE")
        if material_id:
            c.execute("UPDATE materials SET code=?,name=?,unit=?,standard_cost=?,minimum_stock=?,updated_at=CURRENT_TIMESTAMP WHERE material_id=?", (material_code or None,name.strip(),unit or None,max(0,float(standard_cost or 0)),max(0,float(minimum_stock or 0)),material_id))
        else:
            material_id = next_random_id(c, "mat", digits=10)
            c.execute("INSERT INTO materials(material_id,code,name,unit,standard_cost,minimum_stock) VALUES(?,?,?,?,?,?)", (material_id,material_code or None,name.strip(),unit or None,max(0,float(standard_cost or 0)),max(0,float(minimum_stock or 0))))
        c.commit(); return material_id
    except (sqlite3.Error, ValueError, TypeError, OSError):
        c.rollback(); raise
    finally: c.close()


# شرح الدالة save_subcontractor: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def save_subcontractor(name, contact=None, phone=None, tax_id=None, notes=None, subcontractor_id=None):
    if not name.strip(): raise ValueError("Subcontractor name is required.")
    c = get_connection()
    try:
        c.execute("BEGIN IMMEDIATE")
        if subcontractor_id:
            c.execute("UPDATE subcontractors SET name=?,contact=?,phone=?,tax_id=?,notes=?,updated_at=CURRENT_TIMESTAMP WHERE subcontractor_id=?", (name.strip(),contact,phone,tax_id,notes,subcontractor_id))
        else:
            subcontractor_id = next_random_id(c, "sub", digits=10)
            c.execute("INSERT INTO subcontractors(subcontractor_id,name,contact,phone,tax_id,notes) VALUES(?,?,?,?,?,?)", (subcontractor_id,name.strip(),contact,phone,tax_id,notes))
        c.commit(); return subcontractor_id
    except (sqlite3.Error, ValueError, TypeError, OSError):
        c.rollback(); raise
    finally: c.close()


# شرح الدالة save_subcontract: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def save_subcontract(contractor_id, project_id, contract_no, contract_date, contract_amount, notes=None, contract_id=None):
    amount = float(contract_amount or 0)
    if amount < 0: raise ValueError("Contract amount cannot be negative.")
    c = get_connection()
    try:
        c.execute("BEGIN IMMEDIATE")
        if contract_id:
            c.execute("UPDATE subcontractor_contracts SET subcontractor_id=?,project_id=?,contract_no=?,contract_date=?,contract_amount=?,notes=?,updated_at=CURRENT_TIMESTAMP WHERE contract_id=?", (contractor_id,project_id,contract_no,contract_date,amount,notes,contract_id))
        else:
            contract_id = next_random_id(c, "sct", digits=10)
            c.execute("INSERT INTO subcontractor_contracts(contract_id,subcontractor_id,project_id,contract_no,contract_date,contract_amount,notes) VALUES(?,?,?,?,?,?,?)", (contract_id,contractor_id,project_id,contract_no,contract_date,amount,notes))
        c.commit(); return contract_id
    except (sqlite3.Error, ValueError, TypeError, OSError):
        c.rollback(); raise
    finally: c.close()


# شرح الدالة save_subcontract_situation: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def save_subcontract_situation(contract_id, situation_date, gross_amount, retention: float = 0, advance_recovery: float = 0, other_deductions: float = 0, progress_percent: float | None = None, notes=None, situation_id=None):
    gross = float(gross_amount or 0); retention=float(retention or 0); advance=float(advance_recovery or 0); other=float(other_deductions or 0)
    if gross < 0 or min(retention,advance,other) < 0: raise ValueError("Amounts cannot be negative.")
    net = max(0, gross-retention-advance-other)
    c=get_connection()
    try:
        c.execute("BEGIN IMMEDIATE")
        if situation_id:
            c.execute("UPDATE subcontractor_situations SET situation_date=?,gross_amount=?,retention_amount=?,advance_recovery=?,other_deductions=?,net_amount=?,progress_percent=?,notes=?,updated_at=CURRENT_TIMESTAMP WHERE situation_id=?", (situation_date,gross,retention,advance,other,net,progress_percent,notes,situation_id))
        else:
            situation_id=next_random_id(c,"scs",digits=10)
            c.execute("INSERT INTO subcontractor_situations(situation_id,contract_id,situation_date,gross_amount,retention_amount,advance_recovery,other_deductions,net_amount,progress_percent,notes) VALUES(?,?,?,?,?,?,?,?,?,?)", (situation_id,contract_id,situation_date,gross,retention,advance,other,net,progress_percent,notes))
        c.commit(); return situation_id
    except (sqlite3.Error, ValueError, TypeError, OSError):
        c.rollback(); raise
    finally: c.close()


# شرح الدالة project_control_snapshot: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def project_control_snapshot(project_id: str, conn=None) -> dict[str, Any]:
    c=_conn(conn)
    try:
        project=c.execute("SELECT * FROM projects WHERE project_id=?",(project_id,)).fetchone()
        if not project: return {}
        expense=float(c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project_id=?",(project_id,)).fetchone()[0] or 0)
        labor=float(c.execute("SELECT COALESCE(SUM(hours*hourly_cost + overtime_hours*hourly_cost*1.5),0) FROM labor_allocations WHERE project_id=?",(project_id,)).fetchone()[0] or 0)
        equipment=float(c.execute("SELECT COALESCE(SUM(operating_hours*hourly_cost + fuel_cost),0) FROM equipment_usage WHERE project_id=?",(project_id,)).fetchone()[0] or 0)
        materials=float(c.execute("SELECT COALESCE(SUM(CASE WHEN movement_type IN ('Consumption','Transfer Out') THEN quantity*unit_cost ELSE 0 END),0) FROM material_movements WHERE project_id=?",(project_id,)).fetchone()[0] or 0)
        subcontract=float(c.execute("SELECT COALESCE(SUM(net_amount),0) FROM subcontractor_situations ss JOIN subcontractor_contracts sc ON sc.contract_id=ss.contract_id WHERE sc.project_id=?",(project_id,)).fetchone()[0] or 0)
        total=expense+labor+equipment+materials+subcontract
        return {"project_id":project_id,"project_name":project["project_name"],"budget":float(project["budget_ht"] or 0),"expenses":expense,"labor_cost":labor,"equipment_cost":equipment,"material_cost":materials,"subcontract_cost":subcontract,"controlled_cost":total}
    finally:
        if _own(conn): c.close()


__all__=["attendance_for_labor", "list_cost_centers", "list_projects", "project_control_snapshot", "save_cost_center", "save_equipment_usage", "save_labor_allocation", "save_material", "save_material_movement", "save_subcontract", "save_subcontract_situation", "save_subcontractor"]

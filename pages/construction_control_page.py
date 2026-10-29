 # ============================================================
# شرح الملف: pages/construction_control_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Field operations control: cost centers, labor, equipment, materials and subcontractors."""
from __future__ import annotations

import sqlite3
from typing import Any, cast

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.construction_control_service import (
    attendance_for_labor,
    list_cost_centers,
    list_projects,
    save_cost_center,
    save_equipment_usage,
    save_labor_allocation,
    save_material,
    save_material_movement,
    save_subcontract,
    save_subcontract_situation,
    save_subcontractor,
)

from .base_page import BasePage, money


# شرح الصنف ConstructionControlPage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class ConstructionControlPage(BasePage):
    """Central site-control workspace for construction-specific allocations."""
    def __init__(self):
        super().__init__("Construction Control", "Job costing, site materials, labor, equipment and subcontractor control")
        self.tabs=QTabWidget(); self.body.addWidget(self.tabs,1)
        self._build_cost_centers(); self._build_labor(); self._build_equipment(); self._build_materials(); self._build_subcontractors()
        self.refresh()

# شرح الدالة _project_combo: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _project_combo(self):
        c=LocalizedComboBox()
        for p in list_projects(): c.addItem(p["project_name"],p["project_id"])
        return c
# شرح الدالة _table: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _table(self, headers):
        t=QTableWidget(0,len(headers)); t.setHorizontalHeaderLabels([translate_text(x) for x in headers]); t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); t.horizontalHeader().setStretchLastSection(True); return t
# شرح الدالة _button: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _button(self,text,slot): b=QPushButton(translate_text(text)); b.clicked.connect(slot); return b

# شرح الدالة _build_cost_centers: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_cost_centers(self):
        w=QWidget(); l=QVBoxLayout(w); bar=QHBoxLayout(); self.cc_project=self._project_combo(); bar.addWidget(self.cc_project,1); bar.addWidget(self._button("+ Add cost center",self.add_cost_center)); l.addLayout(bar); self.cc_table=self._table(["Project","Code","Cost center","Budget","BOQ item"]); l.addWidget(self.cc_table,1); self.tabs.addTab(w,translate_text("Cost Centers"))
# شرح الدالة _build_labor: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_labor(self):
        w=QWidget(); l=QVBoxLayout(w); bar=QHBoxLayout(); bar.addWidget(self._button("+ Add labor allocation",self.add_labor)); l.addLayout(bar); self.labor_table=self._table(["Date","Project","Employee","Attendance","Hours","Overtime","Cost","Activity"]); l.addWidget(self.labor_table,1); self.tabs.addTab(w,translate_text("Site Labor"))
# شرح الدالة _build_equipment: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_equipment(self):
        w=QWidget(); l=QVBoxLayout(w); bar=QHBoxLayout(); bar.addWidget(self._button("+ Add equipment usage",self.add_equipment)); l.addLayout(bar); self.equipment_table=self._table(["Date","Project","Vehicle","Hours","Hourly cost","Fuel","Total"]); l.addWidget(self.equipment_table,1); self.tabs.addTab(w,translate_text("Equipment Usage"))
# شرح الدالة _build_materials: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_materials(self):
        w=QWidget(); l=QVBoxLayout(w); bar=QHBoxLayout(); bar.addWidget(self._button("+ Add material",self.add_material)); bar.addWidget(self._button("+ Record movement",self.add_material_movement)); l.addLayout(bar); self.material_table=self._table(["Code","Material","Unit","Standard cost","Minimum stock","Current stock"]); l.addWidget(self.material_table,1); self.tabs.addTab(w,translate_text("Materials & Site Stock"))
# شرح الدالة _build_subcontractors: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_subcontractors(self):
        w=QWidget(); l=QVBoxLayout(w); bar=QHBoxLayout(); bar.addWidget(self._button("+ Add subcontractor",self.add_subcontractor)); bar.addWidget(self._button("+ Add contract",self.add_subcontract)); bar.addWidget(self._button("+ Add situation",self.add_subcontract_situation)); l.addLayout(bar); self.sub_table=self._table(["Subcontractor","Project","Contract","Contract value","Situations","Net certified"]); l.addWidget(self.sub_table,1); self.tabs.addTab(w,translate_text("Subcontractors"))

# شرح الدالة refresh: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def refresh(self):
        try:
            self._refresh_cost_centers(); self._refresh_labor(); self._refresh_equipment(); self._refresh_materials(); self._refresh_subcontractors()
        except (sqlite3.Error, ValueError, TypeError, OSError, RuntimeError):
            return
# شرح الدالة _fill: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _fill(self,t,rows):
        t.setRowCount(len(rows))
        for r,row in enumerate(rows):
            for c,v in enumerate(row): t.setItem(r,c,QTableWidgetItem("" if v is None else str(v)))

# شرح الدالة _refresh_cost_centers: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _refresh_cost_centers(self):
        rows=list_cost_centers(); self._fill(self.cc_table,[(r["project_name"],r["code"] or "",r["name"],money(r["budget_amount"]),r["boq_item_id"] or "") for r in rows])
# شرح الدالة _refresh_labor: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _refresh_labor(self):
        c=get_connection();
        try: rows=c.execute("SELECT l.work_date,p.project_name,s.full_name,CASE WHEN l.attendance_id IS NULL THEN 'Legacy' ELSE 'Linked' END,l.hours,l.overtime_hours,l.hours*l.hourly_cost+l.overtime_hours*l.hourly_cost*1.5,l.activity FROM labor_allocations l JOIN projects p ON p.project_id=l.project_id JOIN staff s ON s.staff_id=l.staff_id ORDER BY l.work_date DESC LIMIT 300").fetchall()
        finally:c.close()
        self._fill(self.labor_table,rows)
# شرح الدالة _refresh_equipment: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _refresh_equipment(self):
        c=get_connection();
        try: rows=c.execute("SELECT e.usage_date,p.project_name,v.licence_plate,e.operating_hours,e.hourly_cost,e.fuel_cost,e.operating_hours*e.hourly_cost+e.fuel_cost FROM equipment_usage e JOIN projects p ON p.project_id=e.project_id JOIN vehicles v ON v.vehicle_id=e.vehicle_id ORDER BY e.usage_date DESC LIMIT 300").fetchall()
        finally:c.close()
        self._fill(self.equipment_table,rows)
# شرح الدالة _refresh_materials: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _refresh_materials(self):
        c=get_connection();
        try: rows=c.execute("SELECT m.code,m.name,m.unit,m.standard_cost,m.minimum_stock,COALESCE((SELECT SUM(CASE WHEN movement_type IN ('Receipt','Transfer In','Adjustment') THEN quantity ELSE -quantity END) FROM material_movements mm WHERE mm.material_id=m.material_id),0) FROM materials m ORDER BY m.name").fetchall()
        finally:c.close()
        self._fill(self.material_table,rows)
# شرح الدالة _refresh_subcontractors: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _refresh_subcontractors(self):
        c=get_connection();
        try: rows=c.execute("SELECT s.name,p.project_name,sc.contract_no,sc.contract_amount,COUNT(ss.situation_id),COALESCE(SUM(ss.net_amount),0) FROM subcontractors s JOIN subcontractor_contracts sc ON sc.subcontractor_id=s.subcontractor_id JOIN projects p ON p.project_id=sc.project_id LEFT JOIN subcontractor_situations ss ON ss.contract_id=sc.contract_id GROUP BY sc.contract_id ORDER BY s.name").fetchall()
        finally:c.close()
        self._fill(self.sub_table,rows)

# شرح الدالة _dialog: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _dialog(self,title,fields):
        d=QDialog(self); d.setWindowTitle(translate_text(title)); form=QFormLayout(d); widgets={}
        for key,label,kind in fields:
            if kind=="project": x=self._project_combo()
            elif kind=="date": x=QDateEdit(QDate.currentDate()); x.setCalendarPopup(True)
            elif kind=="number": x=QDoubleSpinBox(); x.setRange(0,1e12); x.setDecimals(3)
            else: x=QLineEdit()
            form.addRow(translate_text(label),x); widgets[key]=x
        box=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel); box.accepted.connect(d.accept); box.rejected.connect(d.reject); form.addRow(box); return d,widgets
# شرح الدالة _val: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _val(self,w,kind=None):
        if isinstance(w,QDoubleSpinBox): return w.value()
        if isinstance(w,QDateEdit): return w.date().toString("yyyy-MM-dd")
        if isinstance(w,QComboBox): return w.currentData()
        return w.text().strip()
# شرح الدالة _number: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _number(self,w):
        return float(self._val(w) or 0)
# شرح الدالة _insert_dialog_row: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _insert_dialog_row(self,d,label,widget,row):
        layout=d.layout()
        if isinstance(layout,QFormLayout):
            layout.insertRow(row,translate_text(label),widget)

# شرح الدالة add_cost_center: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_cost_center(self):
        d,w=self._dialog("Add cost center",[("project","Project","project"),("code","Code","text"),("name","Cost center","text"),("budget","Budget","number")]);
        if d.exec(): save_cost_center(self._val(w["project"]),self._val(w["code"]),self._val(w["name"]),self._number(w["budget"])); self.refresh()
# شرح الدالة add_labor: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_labor(self):
        c=get_connection()
        try: staff=c.execute("SELECT staff_id,full_name,COALESCE(rate,0) rate FROM staff WHERE status='Active' ORDER BY full_name").fetchall()
        finally:c.close()
        if not staff: self.error("No active employees found."); return
        d,w=self._dialog("Allocate attendance to site labor",[("project","Project","project"),("date","Work date","date"),("hours","Regular hours","number"),("overtime","Overtime hours","number"),("cost","Hourly labor cost","number"),("activity","Activity","text")])
        staffbox=LocalizedComboBox(); [staffbox.addItem(x["full_name"],(x["staff_id"],x["rate"])) for x in staff]; w["staff"]=staffbox; self._insert_dialog_row(d,"Employee",staffbox,1)
        attendance_box=LocalizedComboBox(); w["attendance"]=attendance_box; self._insert_dialog_row(d,"Attendance source",attendance_box,2)
# شرح الدالة load_attendance: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
        def load_attendance():
            attendance_box.clear()
            sid=staffbox.currentData()[0] if staffbox.currentData() else None
            pid=self._val(w["project"])
            dt=self._val(w["date"])
            if not sid or not dt: return
            for a in attendance_for_labor(sid,dt,pid):
                attendance_box.addItem(f'{a["date"]} | {a["available_hours"]:.2f}h + {a["available_overtime"]:.2f} OT',a["record_id"])
            if attendance_box.count()==0: attendance_box.addItem(translate_text("No available Present attendance"),None)
        staffbox.currentIndexChanged.connect(load_attendance); w["project"].currentIndexChanged.connect(load_attendance); w["date"].dateChanged.connect(load_attendance)
# شرح الدالة fill_available: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
        def fill_available():
            aid=attendance_box.currentData()
            if not aid: return
            c=get_connection()
            try:
                a=c.execute("SELECT working_hours,overtime_hours FROM attendance WHERE record_id=?",(aid,)).fetchone(); used=c.execute("SELECT COALESCE(SUM(hours),0),COALESCE(SUM(overtime_hours),0) FROM labor_allocations WHERE attendance_id=?",(aid,)).fetchone()
            finally:c.close()
            w["hours"].setValue(max(0,float(a["working_hours"] or 0)-float(used[0] or 0))); w["overtime"].setValue(max(0,float(a["overtime_hours"] or 0)-float(used[1] or 0)))
        attendance_box.currentIndexChanged.connect(fill_available); load_attendance()
        if d.exec():
            staff_data = cast(tuple[Any, Any], staffbox.currentData())
            sid, rate = staff_data
            aid=self._val(attendance_box); cost=self._val(w["cost"]) or float(rate or 0)
            if not aid: self.error("Select a Present attendance record before allocating site labor."); return
            try: save_labor_allocation(sid,self._val(w["project"]),self._val(w["date"]),self._number(w["hours"]),float(cost or 0),None,self._val(w["activity"]),self._number(w["overtime"]),attendance_id=aid)
            except ValueError as exc: self.error(str(exc)); return
            self.refresh()
# شرح الدالة add_equipment: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_equipment(self):
        c=get_connection();
        try: vehicles=c.execute("SELECT vehicle_id,licence_plate FROM vehicles WHERE status='Active' ORDER BY licence_plate").fetchall()
        finally:c.close()
        d,w=self._dialog("Add equipment usage",[("project","Project","project"),("date","Date","date"),("hours","Operating hours","number"),("hourly","Hourly cost","number"),("fuel","Fuel cost","number"),("notes","Notes","text")]); v=LocalizedComboBox(); [v.addItem(x["licence_plate"],x["vehicle_id"]) for x in vehicles]; w["vehicle"]=v; self._insert_dialog_row(d,"Vehicle",v,1)
        if d.exec(): save_equipment_usage(self._val(v),self._val(w["project"]),self._val(w["date"]),self._number(w["hours"]),self._number(w["hourly"]),self._number(w["fuel"]),notes=self._val(w["notes"])); self.refresh()
# شرح الدالة add_material: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_material(self):
        d,w=self._dialog("Add material",[("code","Code","text"),("name","Material","text"),("unit","Unit","text"),("cost","Standard cost","number"),("minimum","Minimum stock","number")]);
        if d.exec(): save_material(self._val(w["code"]),self._val(w["name"]),self._val(w["unit"]),self._number(w["cost"]),self._number(w["minimum"])); self.refresh()
# شرح الدالة add_material_movement: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_material_movement(self):
        c=get_connection();
        try: mats=c.execute("SELECT material_id,name FROM materials ORDER BY name").fetchall()
        finally:c.close()
        d,w=self._dialog("Record material movement",[("project","Project","project"),("date","Date","date"),("quantity","Quantity","number"),("unit_cost","Unit cost","number"),("warehouse","Warehouse / Site","text"),("reference","Reference","text")]); m=LocalizedComboBox(); [m.addItem(x["name"],x["material_id"]) for x in mats]; typ=QComboBox(); typ.addItems(["Receipt","Transfer In","Transfer Out","Consumption","Adjustment"]); w["material"]=m; w["type"]=typ; self._insert_dialog_row(d,"Material",m,1); self._insert_dialog_row(d,"Movement type",typ,2)
        if d.exec(): save_material_movement(self._val(m),self._val(w["project"]),self._val(w["date"]),self._number(w["quantity"]),typ.currentText(),self._val(w["warehouse"]),self._number(w["unit_cost"]),self._val(w["reference"])); self.refresh()
# شرح الدالة add_subcontractor: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_subcontractor(self):
        d,w=self._dialog("Add subcontractor",[("name","Name","text"),("contact","Contact","text"),("phone","Phone","text"),("tax","Tax ID","text")]);
        if d.exec(): save_subcontractor(self._val(w["name"]),self._val(w["contact"]),self._val(w["phone"]),self._val(w["tax"])); self.refresh()
# شرح الدالة add_subcontract: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_subcontract(self):
        c=get_connection();
        try: subs=c.execute("SELECT subcontractor_id,name FROM subcontractors ORDER BY name").fetchall()
        finally:c.close()
        d,w=self._dialog("Add subcontractor contract",[("project","Project","project"),("no","Contract no.","text"),("date","Contract date","date"),("amount","Contract amount","number"),("notes","Notes","text")]); s=LocalizedComboBox(); [s.addItem(x["name"],x["subcontractor_id"]) for x in subs]; w["sub"]=s; self._insert_dialog_row(d,"Subcontractor",s,1)
        if d.exec(): save_subcontract(self._val(s),self._val(w["project"]),self._val(w["no"]),self._val(w["date"]),self._val(w["amount"]),self._val(w["notes"])); self.refresh()
# شرح الدالة add_subcontract_situation: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_subcontract_situation(self):
        c=get_connection();
        try: rows=c.execute("SELECT sc.contract_id,s.name,p.project_name,sc.contract_no FROM subcontractor_contracts sc JOIN subcontractors s ON s.subcontractor_id=sc.subcontractor_id JOIN projects p ON p.project_id=sc.project_id ORDER BY p.project_name,s.name").fetchall()
        finally:c.close()
        d,w=self._dialog("Add subcontractor situation",[("date","Date","date"),("gross","Gross amount","number"),("retention","Retention","number"),("advance","Advance recovery","number"),("other","Other deductions","number"),("progress","Progress %","number"),("notes","Notes","text")]); s=LocalizedComboBox(); [s.addItem(f'{x["project_name"]} / {x["name"]} / {x["contract_no"] or "-"}',x["contract_id"]) for x in rows]; w["contract"]=s; self._insert_dialog_row(d,"Contract",s,1)
        if d.exec(): save_subcontract_situation(self._val(s),self._val(w["date"]),self._number(w["gross"]),self._number(w["retention"]),self._number(w["advance"]),self._number(w["other"]),self._number(w["progress"]),self._val(w["notes"])); self.refresh()

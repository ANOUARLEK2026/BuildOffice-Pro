# ============================================================
# شرح الملف: pages/vehicles_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
from __future__ import annotations

import sqlite3

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.settings_service import qt_date_format

from .base_page import BasePage, money
from .id_service import next_child_id, next_sequence_id


# شرح الصنف VehiclesPage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class VehiclesPage(BasePage):
    """Fleet, maintenance and fuel costs, including project allocation."""
    METHODS = ("Cash", "Bank Transfer", "Cheque", "Bank Card", "Other")

    def __init__(self):
        super().__init__("Vehicles", "Fleet registry, project allocation, maintenance and fuel costs")
        tabs = QTabWidget()
        tabs.addTab(self._fleet_tab(), translate_text("Fleet"))
        tabs.addTab(self._maintenance_tab(), translate_text("Maintenance"))
        tabs.addTab(self._fuel_tab(), translate_text("Fuel"))
        self.body.addWidget(tabs)
        self.load(); self.load_maintenance(); self.load_fuel()

# شرح الدالة _fleet_tab: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _fleet_tab(self):
        w=QWidget(); l=QVBoxLayout(w); bar=QHBoxLayout()
        self.search=QLineEdit(); self.search.setPlaceholderText(translate_text("Search brand, model, plate or VIN…")); self.search.textChanged.connect(self.load)
        self.status=LocalizedComboBox(); self.status.addItems([translate_text("All statuses"),translate_text("Active"),translate_text("Maintenance"),translate_text("Inactive")]); self.status.currentIndexChanged.connect(self.load)
        bar.addWidget(self.search,1); bar.addWidget(self.status)
        for text,slot,obj in [("Refresh",self.load,None),("+ Add vehicle",self.add,"primaryButton"),("Edit",self.edit,None),("Delete",self.delete,"dangerButton")]:
            b=QPushButton(translate_text(text)); b.clicked.connect(slot); b.setObjectName(obj or ""); bar.addWidget(b)
        l.addLayout(bar); self.summary=QLabel(); self.summary.setObjectName("pageSubtitle"); l.addWidget(self.summary)
        self.table=QTableWidget(0,9); self.table.setHorizontalHeaderLabels([translate_text("ID"),translate_text("Brand"),translate_text("Model"),translate_text("VIN"),translate_text("Licence plate"),translate_text("Buy date"),translate_text("Project"),translate_text("Status"),translate_text("Notes")])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.doubleClicked.connect(self.edit)
        self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch); self.table.horizontalHeader().setSectionResizeMode(8,QHeaderView.ResizeMode.Stretch); l.addWidget(self.table,1)
        return w

# شرح الدالة _maintenance_tab: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _maintenance_tab(self):
        w=QWidget(); l=QVBoxLayout(w); bar=QHBoxLayout()
        self.maint_vehicle=LocalizedComboBox(); self.maint_vehicle.addItem(translate_text("All vehicles"),None); self.maint_vehicle.currentIndexChanged.connect(self.load_maintenance)
        for text,slot,obj in [("Refresh",self.load_maintenance,None),("+ Add maintenance",self.add_maintenance,"primaryButton"),("Delete",self.delete_maintenance,"dangerButton")]:
            b=QPushButton(translate_text(text)); b.clicked.connect(slot); b.setObjectName(obj or ""); bar.addWidget(b)
        bar.insertWidget(0,self.maint_vehicle,1); l.addLayout(bar)
        self.maint_table=QTableWidget(0,8); self.maint_table.setHorizontalHeaderLabels([translate_text("ID"),translate_text("Vehicle"),translate_text("Date"),translate_text("Type"),translate_text("Description"),translate_text("Cost"),translate_text("Mileage"),translate_text("Next maintenance")]); self.maint_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.maint_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.maint_table.horizontalHeader().setSectionResizeMode(4,QHeaderView.ResizeMode.Stretch); l.addWidget(self.maint_table,1)
        self._load_vehicle_combo(self.maint_vehicle); return w

# شرح الدالة _fuel_tab: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _fuel_tab(self):
        w=QWidget(); l=QVBoxLayout(w); bar=QHBoxLayout()
        self.fuel_vehicle=LocalizedComboBox(); self.fuel_vehicle.addItem(translate_text("All vehicles"),None); self.fuel_vehicle.currentIndexChanged.connect(self.load_fuel)
        for text,slot,obj in [("Refresh",self.load_fuel,None),("+ Add fuel",self.add_fuel,"primaryButton"),("Delete",self.delete_fuel,"dangerButton")]:
            b=QPushButton(translate_text(text)); b.clicked.connect(slot); b.setObjectName(obj or ""); bar.addWidget(b)
        bar.insertWidget(0,self.fuel_vehicle,1); l.addLayout(bar)
        self.fuel_table=QTableWidget(0,8); self.fuel_table.setHorizontalHeaderLabels([translate_text("ID"),translate_text("Vehicle"),translate_text("Date"),translate_text("Qty"),translate_text("Unit price"),translate_text("Total cost"),translate_text("Mileage"),translate_text("Project")]); self.fuel_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.fuel_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.fuel_table.horizontalHeader().setSectionResizeMode(7,QHeaderView.ResizeMode.Stretch); l.addWidget(self.fuel_table,1)
        self._load_vehicle_combo(self.fuel_vehicle); return w

# شرح الدالة _load_vehicle_combo: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _load_vehicle_combo(self, combo):
        conn=get_connection()
        try:
            for r in conn.execute("SELECT vehicle_id,brand,model,licence_plate FROM vehicles ORDER BY brand,model"):
                combo.addItem(f"{r['brand']} {r['model']} • {r['licence_plate']}",r['vehicle_id'])
        finally: conn.close()

# شرح الدالة _projects: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _projects(self):
        conn=get_connection()
        try:return conn.execute("SELECT project_id,project_name FROM projects ORDER BY project_name").fetchall()
        finally:conn.close()

# شرح الدالة selected_id: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def selected_id(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return str(item.text()).strip() if item is not None else None

# شرح الدالة load: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def load(self):
        if not hasattr(self,'table'): return
        conn=get_connection()
        try:
            q="""SELECT v.vehicle_id,v.brand,v.model,v.vin,v.licence_plate,v.buy_date,
                         COALESCE(p.project_name,'Unassigned') project_name,v.status,v.notes
                  FROM vehicles v LEFT JOIN projects p ON p.project_id=v.current_project_id WHERE 1=1"""; args=[]
            term=self.search.text().strip()
            if term:
                q+=" AND (v.brand LIKE ? OR v.model LIKE ? OR v.licence_plate LIKE ? OR COALESCE(v.vin,'') LIKE ?)"; args += [f"%{term}%"]*4
            st=self.status.currentText()
            if st!="All statuses": q+=" AND v.status=?"; args.append(st)
            q += " ORDER BY v.brand,v.model"
            rows=conn.execute(q,args).fetchall(); self.table.setRowCount(len(rows))
            for i,r in enumerate(rows):
                vals=[r[x] for x in ['vehicle_id','brand','model','vin','licence_plate','buy_date','project_name','status','notes']]
                for j,v in enumerate(vals): self.table.setItem(i,j,QTableWidgetItem('' if v is None else str(v)))
            total=conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]; active=conn.execute("SELECT COUNT(*) FROM vehicles WHERE status='Active'").fetchone()[0]; maint=conn.execute("SELECT COUNT(*) FROM vehicles WHERE status='Maintenance'").fetchone()[0]
            self.summary.setText(translate_text(f"{total} vehicles • {active} active • {maint} in maintenance"))
        finally: conn.close()

# شرح الدالة add: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add(self): self.dialog()
# شرح الدالة edit: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def edit(self):
        vid=self.selected_id()
        if vid is None:self.error("Select a vehicle first.");return
        self.dialog(vid)

# شرح الدالة dialog: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def dialog(self,vid=None):
        conn=get_connection()
        try:e=conn.execute("SELECT * FROM vehicles WHERE vehicle_id=?",(vid,)).fetchone() if vid else None
        finally:conn.close()
        d=QDialog(self); d.setWindowTitle(translate_text("Edit vehicle" if e else "Add vehicle")); f=QFormLayout(d)
        brand=QLineEdit(); model=QLineEdit(); vin=QLineEdit(); plate=QLineEdit(); buy=QDateEdit(QDate.currentDate()); buy.setCalendarPopup(True); buy.setDisplayFormat(qt_date_format())
        project=LocalizedComboBox(); project.addItem(translate_text("Unassigned"),None); [project.addItem(p['project_name'],p['project_id']) for p in self._projects()]
        status=LocalizedComboBox(); status.addItems([translate_text("Active"),translate_text("Maintenance"),translate_text("Inactive")]); notes=QPlainTextEdit()
        for lab,w in [("Brand",brand),("Model",model),("VIN / serial number",vin),("Licence plate",plate),("Purchase date",buy),("Current project",project),("Status",status),("Notes",notes)]:f.addRow(translate_text(lab),w)
        if e:
            brand.setText(e['brand'] or '');model.setText(e['model'] or '');vin.setText(e['vin'] or e['serial_number'] or '');plate.setText(e['licence_plate'] or '')
            if e['buy_date']:buy.setDate(QDate.fromString(e['buy_date'],'yyyy-MM-dd'))
            project.setCurrentIndex(max(0,project.findData(e['current_project_id'])));status.setCurrentText(e['status'] or 'Active');notes.setPlainText(e['notes'] or '')
        bb=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);bb.accepted.connect(d.accept);bb.rejected.connect(d.reject);f.addRow(bb)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        if not brand.text().strip() or not model.text().strip() or not plate.text().strip():self.error("Brand, model and licence plate are required.");return
        vals=(brand.text().strip(),model.text().strip(),vin.text().strip() or None,plate.text().strip().upper(),buy.date().toString('yyyy-MM-dd'),project.currentData(),status.currentText(),notes.toPlainText().strip() or None)
        conn=get_connection()
        try:
            if e:conn.execute("UPDATE vehicles SET brand=?,model=?,vin=?,serial_number=?,licence_plate=?,buy_date=?,current_project_id=?,status=?,notes=? WHERE vehicle_id=?",(vals[0],vals[1],vals[2],vals[2],vals[3],vals[4],vals[5],vals[6],vals[7],vid))
            else:
                 vehicle_id = next_sequence_id(conn, "vhc", digits=3)
                 conn.execute("INSERT INTO vehicles(vehicle_id,brand,model,vin,serial_number,licence_plate,buy_date,current_project_id,status,notes) VALUES(?,?,?,?,?,?,?,?,?,?)",(vehicle_id,vals[0],vals[1],vals[2],vals[2],vals[3],vals[4],vals[5],vals[6],vals[7]))
            conn.commit()
        except sqlite3.IntegrityError:conn.rollback();self.error("The licence plate or vehicle data conflicts with an existing record.")
        finally:conn.close()
        self.load(); self.load_maintenance(); self.load_fuel()

# شرح الدالة delete: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def delete(self):
        vid=self.selected_id()
        if vid is None:self.error("Select a vehicle first.");return
        if not self.confirm("Delete this vehicle and its maintenance/fuel history? This changes asset cost history.","Delete vehicle"):return
        conn=get_connection()
        try:conn.execute("DELETE FROM vehicles WHERE vehicle_id=?",(vid,));conn.commit()
        except sqlite3.IntegrityError:conn.rollback();self.error("The vehicle could not be deleted because another record depends on it.")
        finally:conn.close()
        self.load();self.load_maintenance();self.load_fuel()

# شرح الدالة load_maintenance: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def load_maintenance(self):
        if not hasattr(self,'maint_table'):return
        conn=get_connection()
        try:
            q="""SELECT m.maintenance_id, v.brand||' '||v.model||' • '||v.licence_plate vehicle,
                         m.maintenance_date,m.maintenance_type,m.description,m.cost,m.mileage,m.next_maintenance_date
                  FROM maintenance_records m JOIN vehicles v ON v.vehicle_id=m.vehicle_id WHERE 1=1""";args=[]
            vid=self.maint_vehicle.currentData()
            if vid is not None:q+=" AND m.vehicle_id=?";args.append(vid)
            q += " ORDER BY m.maintenance_date DESC"
            rows=conn.execute(q,args).fetchall();self.maint_table.setRowCount(len(rows))
            for i,r in enumerate(rows):
                vals=[r[x] for x in ['maintenance_id','vehicle','maintenance_date','maintenance_type','description','cost','mileage','next_maintenance_date']]
                for j,v in enumerate(vals):self.maint_table.setItem(i,j,QTableWidgetItem(money(v) if j==5 else ('' if v is None else str(v))))
        finally:conn.close()

# شرح الدالة add_maintenance: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_maintenance(self):
        vehicles=self._vehicle_rows()
        if not vehicles:self.error("Add a vehicle first.");return
        d=QDialog(self);d.setWindowTitle(translate_text("Add maintenance"));f=QFormLayout(d);v=LocalizedComboBox();[v.addItem(f"{x['brand']} {x['model']} • {x['licence_plate']}",x['vehicle_id']) for x in vehicles]
        date=QDateEdit(QDate.currentDate());date.setCalendarPopup(True);date.setDisplayFormat(qt_date_format());typ=QLineEdit();desc=QLineEdit();cost=QDoubleSpinBox();cost.setRange(0,1e15);cost.setDecimals(2);mileage=QDoubleSpinBox();mileage.setRange(0,1e9);mileage.setDecimals(1);nxt=QDateEdit(QDate.currentDate());nxt.setCalendarPopup(True);nxt.setDisplayFormat(qt_date_format());project=LocalizedComboBox();project.addItem(translate_text('No project'),None);[project.addItem(p['project_name'],p['project_id']) for p in self._projects()]
        for lab,w in [('Vehicle',v),('Date',date),('Type',typ),('Description',desc),('Cost',cost),('Mileage',mileage),('Next maintenance',nxt),('Project',project)]:f.addRow(translate_text(lab),w)
        bb=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);bb.accepted.connect(d.accept);bb.rejected.connect(d.reject);f.addRow(bb)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        conn=get_connection()
        try:
            maintenance_id = next_child_id(conn, "mtn", str(v.currentData()), digits=6)
            conn.execute("INSERT INTO maintenance_records(maintenance_id,vehicle_id,maintenance_date,maintenance_type,description,cost,mileage,next_maintenance_date,project_id) VALUES(?,?,?,?,?,?,?,?,?)",(maintenance_id,v.currentData(),date.date().toString('yyyy-MM-dd'),typ.text().strip() or None,desc.text().strip() or None,cost.value(),mileage.value() or None,nxt.date().toString('yyyy-MM-dd'),project.currentData()));conn.commit()
        finally:conn.close()
        self.load_maintenance()

# شرح الدالة delete_maintenance: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def delete_maintenance(self):
        row=self.maint_table.currentRow()
        if row<0:self.error('Select a maintenance record first.');return
        item=self.maint_table.item(row,0)
        if item is None: self.error('Select a maintenance record first.'); return
        mid=str(item.text()).strip()
        if not self.confirm('Delete this maintenance record?','Delete maintenance'):return
        conn=get_connection()
        try:
            conn.execute('DELETE FROM maintenance_records WHERE maintenance_id=?',(mid,)); conn.commit()
        except sqlite3.IntegrityError as e:
            conn.rollback(); self.error(f'Could not delete maintenance record.\n\n{e}')
        finally:
            conn.close()
        self.load_maintenance()

# شرح الدالة load_fuel: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def load_fuel(self):
        if not hasattr(self,'fuel_table'):return
        conn=get_connection()
        try:
            q="""SELECT f.fuel_id,v.brand||' '||v.model||' • '||v.licence_plate vehicle,f.date,f.quantity,f.unit_price,f.total_cost,f.mileage,COALESCE(p.project_name,'No project') project
                 FROM fuel_records f JOIN vehicles v ON v.vehicle_id=f.vehicle_id LEFT JOIN projects p ON p.project_id=f.project_id WHERE 1=1""";args=[];vid=self.fuel_vehicle.currentData()
            if vid is not None:q+=' AND f.vehicle_id=?';args.append(vid)
            rows=conn.execute(q+' ORDER BY f.date DESC',args).fetchall();self.fuel_table.setRowCount(len(rows))
            for i,r in enumerate(rows):
                vals=[r[x] for x in ['fuel_id','vehicle','date','quantity','unit_price','total_cost','mileage','project']]
                for j,v in enumerate(vals):self.fuel_table.setItem(i,j,QTableWidgetItem(money(v) if j in (4,5) else ('' if v is None else str(v))))
        finally:conn.close()

# شرح الدالة add_fuel: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def add_fuel(self):
        vehicles=self._vehicle_rows()
        if not vehicles:self.error('Add a vehicle first.');return
        d=QDialog(self);d.setWindowTitle(translate_text('Add fuel record'));f=QFormLayout(d);v=LocalizedComboBox();[v.addItem(f"{x['brand']} {x['model']} • {x['licence_plate']}",x['vehicle_id']) for x in vehicles]
        date=QDateEdit(QDate.currentDate());date.setCalendarPopup(True);date.setDisplayFormat(qt_date_format());qty=QDoubleSpinBox();qty.setRange(.001,1e6);qty.setDecimals(3);unit=QDoubleSpinBox();unit.setRange(0,1e6);unit.setDecimals(2);mileage=QDoubleSpinBox();mileage.setRange(0,1e9);mileage.setDecimals(1);project=LocalizedComboBox();project.addItem(translate_text('No project'),None);[project.addItem(p['project_name'],p['project_id']) for p in self._projects()]
        total=QLabel('0.00');qty.valueChanged.connect(lambda x:total.setText(money(x*unit.value())));unit.valueChanged.connect(lambda x:total.setText(money(x*qty.value())))
        for lab,w in [('Vehicle',v),('Date',date),('Quantity',qty),('Unit price',unit),('Total cost',total),('Mileage',mileage),('Project',project)]:f.addRow(translate_text(lab),w)
        bb=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);bb.accepted.connect(d.accept);bb.rejected.connect(d.reject);f.addRow(bb)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        conn=get_connection()
        try:
            fuel_id = next_child_id(conn, "fuel", str(v.currentData()), digits=6)
            conn.execute("INSERT INTO fuel_records(fuel_id,vehicle_id,date,quantity,unit_price,total_cost,mileage,project_id) VALUES(?,?,?,?,?,?,?,?)",(fuel_id,v.currentData(),date.date().toString('yyyy-MM-dd'),qty.value(),unit.value(),qty.value()*unit.value(),mileage.value() or None,project.currentData()));conn.commit()
        finally:conn.close()
        self.load_fuel()

# شرح الدالة delete_fuel: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def delete_fuel(self):
        row=self.fuel_table.currentRow()
        if row<0:self.error('Select a fuel record first.');return
        item=self.fuel_table.item(row,0)
        if item is None: self.error('Select a fuel record first.'); return
        fid=str(item.text()).strip()
        if not self.confirm('Delete this fuel record?','Delete fuel record'):return
        conn=get_connection()
        try:
            conn.execute('DELETE FROM fuel_records WHERE fuel_id=?',(fid,)); conn.commit()
        except sqlite3.IntegrityError as e:
            conn.rollback(); self.error(f'Could not delete fuel record.\n\n{e}')
        finally:
            conn.close()
        self.load_fuel()

# شرح الدالة _vehicle_rows: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _vehicle_rows(self):
        conn=get_connection()
        try:return conn.execute('SELECT vehicle_id,brand,model,licence_plate FROM vehicles ORDER BY brand,model').fetchall()
        finally:conn.close()

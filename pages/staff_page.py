# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
# ============================================================
# شرح الملف: staff_page.py
# يحتوي هذا الملف على جزء من وظائف وتفاصيل تطبيق BuildOffice Pro.
# التعليقات العربية هنا للتوضيح فقط ولا تغيّر منطق البرنامج.
# ============================================================
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection

from .base_page import BasePage, money, next_id


# هذا الصنف مسؤول عن جزء StaffPage من التطبيق.
class StaffPage(BasePage):
    # تهيئة الكائن وتجهيز الواجهة والبيانات اللازمة.
    def __init__(self):
        super().__init__("Staff", "Personnel registry, employment details and project assignments")
        self.build_ui(); self.load()

    # بناء عناصر واجهة المستخدم وترتيبها.
    def build_ui(self):
        bar=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText(translate_text("Search name, position or phone…")); self.search.textChanged.connect(self.load); self.status=LocalizedComboBox(); self.status.addItems([translate_text("All statuses"),translate_text("Active"),translate_text("Inactive")]); self.status.currentIndexChanged.connect(self.load); bar.addWidget(self.search,1); bar.addWidget(self.status)
        for t,s,o in [("Refresh",self.load,None),("+ Add staff",self.add_staff,"primaryButton"),("Edit",self.edit_staff,None),("Delete",self.delete_staff,"dangerButton")]: b=QPushButton(translate_text(t));b.clicked.connect(s);b.setObjectName(o or "");bar.addWidget(b)
        self.body.addLayout(bar)
        frame,lay=self.panel(); self.summary=QLabel(); self.summary.setObjectName("pageSubtitle"); lay.addWidget(self.summary)
        self.table=QTableWidget(0,9); self.table.setHorizontalHeaderLabels([translate_text("ID"),translate_text("Full name"),translate_text("Position"),translate_text("Employment"),translate_text("Salary type"),translate_text("Rate"),translate_text("Phone"),translate_text("Status"),translate_text("Attendance")]); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.doubleClicked.connect(self.edit_staff); self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch); self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table,1); self.body.addWidget(frame)

    # الحصول على السجل المحدد من الجدول.
    def selected_id(self):
        r = self.table.currentRow()
        item = self.table.item(r, 0) if r >= 0 else None
        return item.text() if item is not None else None

    # تحميل أو تحديث البيانات المرتبطة بـ load.
    def load(self):
        conn=get_connection()
        try:
            q="SELECT staff_id,full_name,position,employment_type,salary_type,rate,phone,status,attendance_type FROM staff WHERE 1=1";p=[]; search=getattr(self,'search',None); term=search.text().strip() if search is not None else ''
            if term:q+=" AND (full_name LIKE ? OR position LIKE ? OR phone LIKE ?)";p += [f"%{term}%"]*3
            st=self.status.currentText() if hasattr(self,'status') else 'All statuses'
            if st!='All statuses':q+=" AND status=?";p.append(st)
            q+=" ORDER BY full_name";rows=conn.execute(q,p).fetchall();self.table.setRowCount(len(rows))
            for i,r in enumerate(rows):
                for j,v in enumerate(r):
                    it=QTableWidgetItem(money(v) if j==5 else ("" if v is None else str(v)));it.setTextAlignment(Qt.AlignmentFlag.AlignCenter if j!=1 else Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft);self.table.setItem(i,j,it)
            total=conn.execute("SELECT COUNT(*) FROM staff").fetchone()[0];active=conn.execute("SELECT COUNT(*) FROM staff WHERE status='Active'").fetchone()[0];self.summary.setText(translate_text(f"{total} registered • {active} active"))
        finally:conn.close()

    # إضافة سجل جديد إلى النظام.
    def add_staff(self):self.staff_dialog()

    # تعديل السجل المحدد وفتح بياناته للتحرير.
    def edit_staff(self):
        sid=self.selected_id(); self.staff_dialog(sid) if sid else self.error("Select a staff member first.")

    # حذف السجل المحدد بعد التحقق من الاختيار.
    def delete_staff(self):
        sid=self.selected_id()
        if not sid:self.error("Select a staff member first.");return
        if not self.confirm("Delete this staff member? Attendance records intentionally prevent unsafe deletion.","Delete staff"):return
        conn=get_connection()
        try:conn.execute("DELETE FROM staff WHERE staff_id=?",(sid,));conn.commit();self.load()
        except sqlite3.IntegrityError as e:conn.rollback();self.error(f"Cannot delete this staff member because existing records reference it.\n\n{e}")
        finally:conn.close()

    # تنفيذ وظيفة staff_dialog ضمن هذا الجزء من البرنامج.
    def staff_dialog(self,staff_id=None):
        conn=get_connection(); existing=conn.execute("SELECT * FROM staff WHERE staff_id=?",(staff_id,)).fetchone() if staff_id else None; projects=conn.execute("SELECT project_id,project_name FROM projects WHERE status='Active' ORDER BY project_name").fetchall(); assigned={r['project_id'] for r in conn.execute("SELECT project_id FROM staff_projects WHERE staff_id=? AND active=1",(staff_id,)).fetchall()} if staff_id else set();conn.close()
        d=QDialog(self);d.setWindowTitle(translate_text("Edit Staff" if existing else "Add Staff"));d.resize(620,600);f=QFormLayout(d);full=QLineEdit();position=QLineEdit();employment=LocalizedComboBox();employment.addItems([translate_text("Permanent"),translate_text("Temporary"),translate_text("Contract")]);salary=LocalizedComboBox();salary.addItems([translate_text("Monthly"),translate_text("Daily"),translate_text("Hourly")]);rate=QDoubleSpinBox();rate.setRange(0,1e12);rate.setDecimals(2);phone=QLineEdit();status=LocalizedComboBox();status.addItems([translate_text("Active"),translate_text("Inactive")]);attendance=LocalizedComboBox();attendance.addItems([translate_text("On Site"),translate_text("Administration")])
        for label,w in [("Full name",full),("Position",position),("Employment",employment),("Salary type",salary),("Rate",rate),("Phone",phone),("Status",status),("Attendance type",attendance)]:f.addRow(translate_text(label),w)
        box=QGroupBox(translate_text("Project assignments"));bl=QVBoxLayout(box);lst=QListWidget();
        for r in projects:it=QListWidgetItem(r['project_name']);it.setData(Qt.ItemDataRole.UserRole,r['project_id']);it.setCheckState(Qt.CheckState.Checked if r['project_id'] in assigned else Qt.CheckState.Unchecked);lst.addItem(it)
        bl.addWidget(lst);f.addRow(box);hint=QLabel(translate_text("Assign the staff member only to projects where attendance is allowed."));hint.setObjectName("pageSubtitle");f.addRow(hint)
        # تنفيذ وظيفة toggle ضمن هذا الجزء من البرنامج.
        def toggle():box.setEnabled(attendance.currentText()!="Administration")
        attendance.currentIndexChanged.connect(toggle)
        if existing:
            full.setText(existing['full_name'] or '');position.setText(existing['position'] or '');employment.setCurrentText(existing['employment_type'] or 'Permanent');salary.setCurrentText(existing['salary_type'] or 'Monthly');rate.setValue(float(existing['rate'] or 0));phone.setText(existing['phone'] or '');status.setCurrentText(existing['status'] or 'Active');attendance.setCurrentText(existing['attendance_type'] or 'On Site')
        toggle();b=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);b.accepted.connect(d.accept);b.rejected.connect(d.reject);f.addRow(b)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        if not full.text().strip():self.error("Full name is required.");return
        vals=(full.text().strip(),position.text().strip() or None,employment.currentText(),salary.currentText(),rate.value(),phone.text().strip() or None,status.currentText(),attendance.currentText())
        selected=[] if attendance.currentText()=="Administration" else [lst.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lst.count()) if lst.item(i).checkState()==Qt.CheckState.Checked]
        conn=get_connection()
        try:
            conn.execute("BEGIN")
            if existing:conn.execute("UPDATE staff SET full_name=?,position=?,employment_type=?,salary_type=?,rate=?,phone=?,status=?,attendance_type=?,updated_at=CURRENT_TIMESTAMP WHERE staff_id=?",vals+(staff_id,));sid=staff_id
            else:sid=next_id('staff','staff_id','stf',3);conn.execute("INSERT INTO staff(staff_id,full_name,position,employment_type,salary_type,rate,phone,status,attendance_type) VALUES(?,?,?,?,?,?,?,?,?)",(sid,)+vals)
            conn.execute("DELETE FROM staff_projects WHERE staff_id=?",(sid,));conn.executemany("INSERT INTO staff_projects(staff_id,project_id,active) VALUES(?,?,1)",[(sid,p) for p in selected]);conn.commit();self.load()
        except sqlite3.IntegrityError as e:conn.rollback();self.error(translate_text(f"Could not save staff member.\n\n{e}"))
        finally:conn.close()

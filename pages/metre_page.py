# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
# ============================================================
# شرح الملف: metre_page.py
# يحتوي هذا الملف على جزء من وظائف وتفاصيل تطبيق BuildOffice Pro.
# التعليقات العربية هنا للتوضيح فقط ولا تغيّر منطق البرنامج.
# ============================================================
import sqlite3

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection

from .base_page import BasePage, money
from .id_service import next_child_id


# هذا الصنف مسؤول عن جزء MetrePage من التطبيق.
class MetrePage(BasePage):
    # تهيئة الكائن وتجهيز الواجهة والبيانات اللازمة.
    def __init__(self):
        super().__init__("Métré", "Manage bill of quantities and calculate item totals")
        bar=QHBoxLayout(); self.project=LocalizedComboBox(); self.project.currentIndexChanged.connect(self.load);bar.addWidget(QLabel(translate_text("Project")));bar.addWidget(self.project,1)
        for t,s,o in [("+ Add item",self.add_item,"primaryButton"),("Edit",self.edit_item,None),("Delete",self.delete_item,"dangerButton"),("Refresh",self.refresh_projects,None)]:b=QPushButton(translate_text(t));b.clicked.connect(s);b.setObjectName(o or "");bar.addWidget(b)
        self.body.addLayout(bar)
        frame,lay=self.panel();self.summary=QLabel();self.summary.setObjectName("pageSubtitle");lay.addWidget(self.summary);self.table=QTableWidget(0,7);self.table.setHorizontalHeaderLabels([translate_text("ID"),translate_text("No."),translate_text("Description"),translate_text("Unit"),translate_text("Quantity"),translate_text("Unit price"),translate_text("Amount")]);self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.doubleClicked.connect(self.edit_item);self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch);lay.addWidget(self.table,1);self.body.addWidget(frame);self.refresh_projects()

    # تنفيذ وظيفة showEvent ضمن هذا الجزء من البرنامج.
    def showEvent(self,event):super().showEvent(event);self.refresh_projects()

    # تحديث العناصر أو البيانات المعروضة في الواجهة.
    def refresh_projects(self):
        conn=get_connection()
        try:cur=self.project.currentData() if hasattr(self,'project') else None;self.project.blockSignals(True);self.project.clear();
        finally:conn.close()
        conn=get_connection()
        try:
            for r in conn.execute("SELECT project_id,project_name FROM projects ORDER BY project_name"):self.project.addItem(r['project_name'],r['project_id'])
        finally:conn.close()
        idx=self.project.findData(cur) if cur else 0;self.project.setCurrentIndex(max(idx, 0));self.project.blockSignals(False);self.load()

    # تحميل أو تحديث البيانات المرتبطة بـ load.
    def load(self):
        pid=self.project.currentData();
        if not pid:self.table.setRowCount(0);self.summary.setText(translate_text("No project selected"));return
        conn=get_connection()
        try:rows=conn.execute("SELECT item_id,item_number,description,unit,quantity,unit_price,amount FROM metre_items WHERE project_id=? ORDER BY item_number,item_id",(pid,)).fetchall();self.table.setRowCount(len(rows));total=0
        finally:conn.close()
        for i,r in enumerate(rows):
            total += float(r['amount'] or 0)
            vals=[r['item_id'],r['item_number'],r['description'],r['unit'],r['quantity'],r['unit_price'],r['amount']]
            for j,v in enumerate(vals):self.table.setItem(i,j,QTableWidgetItem(money(v) if j in (5,6) else ("" if v is None else str(v))))
        self.summary.setText(translate_text(f"{len(rows)} items • Total: {money(total)}"))

    # الحصول على السجل المحدد من الجدول.
    def selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return str(item.text()).strip() if item else None

    # إضافة سجل جديد إلى النظام.
    def add_item(self):self.item_dialog()

    # تعديل السجل المحدد وفتح بياناته للتحرير.
    def edit_item(self):
        i=self.selected_id();self.item_dialog(i) if i else self.error("Select an item first.")

    # حذف السجل المحدد بعد التحقق من الاختيار.
    def delete_item(self):
        item_id = self.selected_id()
        if not item_id:
            self.error("Select an item first.")
            return
        if not self.confirm("Delete this Métré item?", "Delete item"):
            return

        conn = get_connection()
        try:
            refs = conn.execute(
                "SELECT COUNT(*) FROM situation_items WHERE item_id=?",
                (item_id,),
            ).fetchone()[0]
            if int(refs or 0) > 0:
                conn.rollback()
                self.error(
                    "This Métré item cannot be deleted because it is already "
                    "used in one or more Situations.\n\n"
                    "Remove it from the related Situation(s) first."
                )
                return
            conn.execute("DELETE FROM metre_items WHERE item_id=?", (item_id,))
            conn.commit()
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            self.error(translate_text(f"The Métré item could not be deleted.\n\n{exc}"))
        except sqlite3.OperationalError as exc:
            conn.rollback()
            self.error(translate_text(f"The Métré item could not be deleted.\n\n{exc}"))
        finally:
            conn.close()
        self.load()

    def item_dialog(self,item_id=None):
        pid=self.project.currentData();conn=get_connection();existing=conn.execute("SELECT * FROM metre_items WHERE item_id=?",(item_id,)).fetchone() if item_id else None;conn.close();d=QDialog(self);d.setWindowTitle(translate_text("Edit item" if existing else "Add item"));f=QFormLayout(d);num=QLineEdit();desc=QLineEdit();unit=QLineEdit();qty=QDoubleSpinBox();qty.setRange(0,1e15);qty.setDecimals(3);price=QDoubleSpinBox();price.setRange(0,1e15);price.setDecimals(2)
        for l,w in [("Item number",num),("Description",desc),("Unit",unit),("Quantity",qty),("Unit price",price)]:f.addRow(translate_text(l),w)
        if existing:num.setText(existing['item_number'] or '');desc.setText(existing['description'] or '');unit.setText(existing['unit'] or '');qty.setValue(float(existing['quantity'] or 0));price.setValue(float(existing['unit_price'] or 0))
        b=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);b.accepted.connect(d.accept);b.rejected.connect(d.reject);f.addRow(b)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        if not desc.text().strip():self.error("Description is required.");return
        amount=qty.value()*price.value();conn=get_connection()
        try:
            if existing:conn.execute("UPDATE metre_items SET item_number=?,description=?,unit=?,quantity=?,unit_price=?,amount=? WHERE item_id=?",(num.text().strip() or None,desc.text().strip(),unit.text().strip() or None,qty.value(),price.value(),amount,item_id))
            else:
                 item_id = next_child_id(conn, "mtr", pid, digits=3)
                 conn.execute("INSERT INTO metre_items(item_id,project_id,item_number,description,unit,quantity,unit_price,amount) VALUES(?,?,?,?,?,?,?,?)",(item_id,pid,num.text().strip() or None,desc.text().strip(),unit.text().strip() or None,qty.value(),price.value(),amount))
            conn.commit();self.load()
        except sqlite3.IntegrityError as e:conn.rollback();self.error(translate_text(f"Could not save item. Item number may already exist for this project.\n\n{e}"))
        finally:conn.close()

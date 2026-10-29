# ============================================================
# شرح الملف: واجهة العمليات الميدانية وربط التقرير اليومي بالتقدم والموارد.
# ============================================================
from __future__ import annotations

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
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
)

from core.i18n import LocalizedComboBox, translate_text
from services.site_operations_service import (
    delete_progress,
    delete_report,
    get_report,
    list_progress,
    list_report_resources,
    list_reports,
    report_execution_snapshot,
    report_summary,
    save_progress,
    save_report,
)

from .base_page import BasePage


class SiteOperationsPage(BasePage):
    def __init__(self):
        super().__init__("Site Operations", "Daily site reports, execution progress and field resources")
        bar = QHBoxLayout()
        self.project = self._project_combo(True)
        self.search = QLineEdit(); self.search.setPlaceholderText(translate_text("Search reports"))
        add = QPushButton(translate_text("+ New Daily Report")); add.setObjectName("primaryButton"); add.clicked.connect(self.add_report)
        edit = QPushButton(translate_text("Edit")); edit.clicked.connect(self.edit_report)
        delete = QPushButton(translate_text("Delete")); delete.clicked.connect(self.remove_report)
        refresh = QPushButton(translate_text("Refresh")); refresh.clicked.connect(self.refresh)
        bar.addWidget(QLabel(translate_text("Project"))); bar.addWidget(self.project, 1); bar.addWidget(self.search, 1)
        bar.addWidget(add); bar.addWidget(edit); bar.addWidget(delete); bar.addWidget(refresh)
        self.body.addLayout(bar)
        self.summary = QLabel(); self.summary.setObjectName("dashboardText"); self.body.addWidget(self.summary)

        self.tabs = QTabWidget(); self.body.addWidget(self.tabs, 1)
        self._build_reports_tab(); self._build_progress_tab(); self._build_resources_tab()
        self.project.currentIndexChanged.connect(self.refresh); self.search.textChanged.connect(self.refresh)
        self.tabs.currentChanged.connect(lambda _: self.refresh())
        self.refresh()

    def _project_combo(self, include_all=False):
        c = LocalizedComboBox(); c.addItem(translate_text("All projects") if include_all else translate_text("Select project"), None)
        conn = __import__("repositories.db", fromlist=["get_connection"]).get_connection()
        try:
            for p in conn.execute("SELECT project_id, project_name FROM projects ORDER BY project_name").fetchall(): c.addItem(p["project_name"], p["project_id"])
        finally: conn.close()
        return c

    def _build_reports_tab(self):
        w=__import__('PySide6.QtWidgets',fromlist=['QWidget']).QWidget(); l=QVBoxLayout(w)
        frame, lay=self.panel(); self.table=QTableWidget(0,10)
        self.table.setHorizontalHeaderLabels([translate_text(x) for x in ["Report","Project","Date","Weather","Manpower","Progress %","Work performed","Delays","Status","Report ID"]])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.setColumnHidden(9,True)
        for col in (1,6,7): self.table.horizontalHeader().setSectionResizeMode(col,QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table); l.addWidget(frame,1); self.tabs.addTab(w,translate_text("Daily Reports"))

    def _build_progress_tab(self):
        w=__import__('PySide6.QtWidgets',fromlist=['QWidget']).QWidget(); l=QVBoxLayout(w); bar=QHBoxLayout()
        add=QPushButton(translate_text("+ Record BOQ Progress")); add.setObjectName("primaryButton"); add.clicked.connect(self.add_progress)
        delete=QPushButton(translate_text("Delete")); delete.clicked.connect(self.remove_progress)
        bar.addWidget(add); bar.addWidget(delete); bar.addStretch(); l.addLayout(bar)
        self.progress_table=QTableWidget(0,8); self.progress_table.setHorizontalHeaderLabels([translate_text(x) for x in ["Item","Description","Unit","Planned Qty","Executed Qty","Unit Price","Amount","Notes"]]); self.progress_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.progress_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.progress_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch); self.progress_table.horizontalHeader().setSectionResizeMode(7,QHeaderView.ResizeMode.Stretch)
        l.addWidget(self.progress_table,1); self.tabs.addTab(w,translate_text("Daily BOQ Progress"))

    def _build_resources_tab(self):
        w=__import__('PySide6.QtWidgets',fromlist=['QWidget']).QWidget(); l=QVBoxLayout(w)
        self.resource_info=QLabel(); l.addWidget(self.resource_info)
        self.resource_table=QTableWidget(0,6); self.resource_table.setHorizontalHeaderLabels([translate_text(x) for x in ["Type","Resource","Quantity / Hours","Unit Cost","Total Cost","Source ID"]]); self.resource_table.setColumnHidden(5,True); self.resource_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.resource_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.resource_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        l.addWidget(self.resource_table,1); self.tabs.addTab(w,translate_text("Field Resources"))

    def _selected_report_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 9)
        return item.text() if item is not None else None

    def _selected_progress_id(self):
        row = self.progress_table.currentRow()
        if row < 0:
            return None
        item = self.progress_table.item(row, 0)
        return item.data(0x0100) if item is not None else None

    def refresh(self):
        pid=self.project.currentData(); rows=list_reports(pid); term=self.search.text().strip().lower()
        if term: rows=[r for r in rows if term in " ".join(str(v or "") for v in r).lower()]
        self.table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            vals=[r['report_number'],r['project_name'],r['report_date'],r['weather'] or '-',r['manpower_count'],f"{float(r['progress_percent'] or 0):.1f}",r['work_performed'] or '-',r['delays'] or '-',r['status'],r['report_id']]
            for j,v in enumerate(vals): self.table.setItem(i,j,QTableWidgetItem(str(v)))
        s=report_summary(pid); self.summary.setText(translate_text(f"Reports: {s['reports']} • Approved: {s['approved']} • Average reported progress: {s['avg_progress']:.1f}% • Delay flags: {s['delayed_reports']}"))
        self.refresh_details()

    def refresh_details(self):
        rid=self._selected_report_id()
        if not rid:
            self.progress_table.setRowCount(0); self.resource_table.setRowCount(0); self.resource_info.setText(translate_text("Select a daily report to view structured execution details.")); return
        rows=list_progress(rid); self.progress_table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            vals=[r['item_number'],r['description'],r['unit'],f"{float(r['planned_quantity'] or 0):.3f}",f"{float(r['executed_quantity'] or 0):.3f}",f"{float(r['unit_price'] or 0):.2f}",f"{float(r['amount'] or 0):.2f}",r['notes'] or '-']
            for j,v in enumerate(vals):
                self.progress_table.setItem(i,j,QTableWidgetItem(str(v)))
            progress_item = self.progress_table.item(i, 0)
            if progress_item is not None:
                progress_item.setData(0x0100, r['progress_id'])
        rr=list_report_resources(rid); self.resource_table.setRowCount(len(rr))
        for i,r in enumerate(rr):
            vals=[r['resource_type'],r['description'] or '-',f"{float(r['quantity'] or 0):.2f}",f"{float(r['unit_cost'] or 0):.2f}",f"{float(r['total_cost'] or 0):.2f}",r['source_id']]
            for j,v in enumerate(vals): self.resource_table.setItem(i,j,QTableWidgetItem(str(v)))
        snap=report_execution_snapshot(rid)
        self.resource_info.setText(translate_text(f"BOQ value recorded: {snap['progress_value']:.2f} • Material cost: {snap['material_cost']:.2f} • Equipment cost: {snap['equipment_cost']:.2f} • Labor hours: {snap['labor_hours']:.2f}"))

    def add_report(self): self._open_dialog(None)
    def edit_report(self):
        rid=self._selected_report_id()
        if not rid: self.error("Select a report first."); return
        self._open_dialog(rid)
    def remove_report(self):
        rid=self._selected_report_id()
        if not rid: self.error("Select a report first."); return
        if self.confirm("Delete this daily site report?","Delete report"): delete_report(rid); self.refresh()

    def add_progress(self):
        rid=self._selected_report_id()
        if not rid: self.error("Select a daily report first."); return
        d=QDialog(self); d.setWindowTitle(translate_text("Record BOQ Progress")); f=QFormLayout(d)
        item=LocalizedComboBox(); conn=__import__("repositories.db",fromlist=["get_connection"]).get_connection()
        try:
            rep=get_report(rid)
            for r in conn.execute("SELECT item_id,item_number,description FROM metre_items WHERE project_id=? ORDER BY item_number",(rep['project_id'],)).fetchall(): item.addItem(f"{r['item_number']} - {r['description']}",r['item_id'])
        finally: conn.close()
        qty=QDoubleSpinBox(); qty.setRange(0,100000000); qty.setDecimals(3); notes=QTextEdit(); notes.setMinimumHeight(70)
        f.addRow(translate_text("BOQ item"),item); f.addRow(translate_text("Executed quantity"),qty); f.addRow(translate_text("Notes"),notes)
        box=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); box.accepted.connect(d.accept); box.rejected.connect(d.reject); f.addRow(box)
        if d.exec()!=QDialog.DialogCode.Accepted or item.currentData() is None:return
        try: save_progress(rid,item.currentData(),qty.value(),notes.toPlainText().strip())
        except (TypeError, ValueError, KeyError, RuntimeError) as exc:self.error(str(exc)); return
        self.refresh_details()

    def remove_progress(self):
        pid=self._selected_progress_id()
        if not pid:self.error("Select a progress record first.");return
        if self.confirm("Delete this progress record?","Delete progress"): delete_progress(pid); self.refresh_details()

    def _open_dialog(self, report_id):
        existing=get_report(report_id) if report_id else None; d=QDialog(self); d.setWindowTitle(translate_text("Edit Daily Site Report" if report_id else "New Daily Site Report")); form=QFormLayout(d); w={}
        w['project']=self._project_combo(False); w['date']=QDateEdit(QDate.currentDate()); w['date'].setCalendarPopup(True); w['date'].setDisplayFormat('yyyy-MM-dd'); w['weather']=QLineEdit(); w['manpower']=QSpinBox(); w['manpower'].setRange(0,10000); w['progress']=QDoubleSpinBox(); w['progress'].setRange(0,100); w['progress'].setDecimals(1)
        for key,label in [('work','Work performed'),('materials','Materials used'),('equipment','Equipment used'),('delays','Delays / blockers'),('safety','Safety notes'),('notes','General notes')]: w[key]=QTextEdit(); w[key].setMinimumHeight(60)
        w['status']=QComboBox(); w['status'].addItems(['Draft','Submitted','Approved'])
        for key,label in [('project','Project'),('date','Report date'),('weather','Weather'),('manpower','Manpower on site'),('progress','Reported progress %'),('work','Work performed'),('materials','Materials used'),('equipment','Equipment used'),('delays','Delays / blockers'),('safety','Safety notes'),('notes','General notes'),('status','Status')]: form.addRow(translate_text(label),w[key])
        if existing:
            w['project'].setCurrentIndex(w['project'].findData(existing['project_id'])); y,m,day=map(int,existing['report_date'].split('-')); w['date'].setDate(QDate(y,m,day)); w['weather'].setText(existing['weather'] or ''); w['manpower'].setValue(int(existing['manpower_count'] or 0)); w['progress'].setValue(float(existing['progress_percent'] or 0))
            for key,col in [('work','work_performed'),('materials','materials_used'),('equipment','equipment_used'),('delays','delays'),('safety','safety_notes'),('notes','notes')]:w[key].setPlainText(existing[col] or '')
            w['status'].setCurrentText(existing['status'] or 'Draft')
        box=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); box.accepted.connect(d.accept); box.rejected.connect(d.reject); form.addRow(box)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        pid=w['project'].currentData()
        if not pid:self.error('Select a project first.');return
        try: save_report(pid,w['date'].date().toString('yyyy-MM-dd'),w['weather'].text().strip(),w['manpower'].value(),w['progress'].value(),w['work'].toPlainText().strip(),w['materials'].toPlainText().strip(),w['equipment'].toPlainText().strip(),w['delays'].toPlainText().strip(),w['safety'].toPlainText().strip(),w['notes'].toPlainText().strip(),w['status'].currentText(),report_id)
        except (TypeError, ValueError, KeyError, RuntimeError) as exc:self.error(str(exc));return
        self.refresh()

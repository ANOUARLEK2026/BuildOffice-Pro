# ============================================================
# شرح الملف: pages/management_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Executive management center exposing alerts, reconciliation, cash forecast, smart queries and what-if analysis."""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from core.i18n import translate_text
from repositories.db import get_connection
from services.executive_control_service import (
    portfolio_control_snapshot,
    run_governance_scan,
)
from services.management_intelligence import (
    alerts,
    cash_flow_forecast,
    generate_management_report,
    reconciliation,
    what_if,
)
from services.natural_query_service import answer
from services.project_intelligence_service import unified_project_intelligence

from .base_page import BasePage, money


# شرح الصنف ManagementPage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class ManagementPage(BasePage):
    def __init__(self):
        super().__init__("Management Intelligence","Cross-module alerts, forecasts, reconciliation and decisions")
        self._build(); QTimer.singleShot(0, self.refresh)
# شرح الدالة _build: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build(self):
        bar=QHBoxLayout(); self.query=QLineEdit(); self.query.setPlaceholderText(translate_text("Ask: projects losing money, highest expenses, cash flow, what needs attention")); bar.addWidget(self.query,1); q=QPushButton(translate_text("Ask")); q.setObjectName("primaryButton"); q.clicked.connect(self.ask); bar.addWidget(q); a=QPushButton(translate_text("Refresh intelligence")); a.clicked.connect(self.refresh); bar.addWidget(a); self.body.addLayout(bar)
        actions=QHBoxLayout(); w=QPushButton(translate_text("What-if simulation")); w.clicked.connect(self.whatif); actions.addWidget(w); r=QPushButton(translate_text("Run reconciliation")); r.clicked.connect(self.reconcile); actions.addWidget(r); report=QPushButton(translate_text("Generate management report")); report.clicked.connect(self.report); actions.addWidget(report); scan=QPushButton(translate_text("Run executive scan")); scan.clicked.connect(self.executive_scan); actions.addWidget(scan); self.detail_project=QComboBox(); actions.addWidget(self.detail_project); detail=QPushButton(translate_text("Analyze project")); detail.clicked.connect(self.analyze_project); actions.addWidget(detail); actions.addStretch(); self.summary=QLabel(); self.summary.setWordWrap(True); actions.addWidget(self.summary,1); self.body.addLayout(actions)
        self.table=QTableWidget(0,4); self.table.setHorizontalHeaderLabels([translate_text(x) for x in ["Severity","Area","Count","Message"]]); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.body.addWidget(self.table,1)
# شرح الدالة refresh: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def refresh(self):
        self._load_detail_projects()
        rows=alerts(); self.table.setRowCount(len(rows));
        for i,r in enumerate(rows):
            vals=[r.get('severity',''),r.get('title',''),str(r.get('count',1)),r.get('message','')]
            for c,v in enumerate(vals): self.table.setItem(i,c,QTableWidgetItem(str(v)))
        c=cash_flow_forecast(); snapshot = portfolio_control_snapshot()
        self.summary.setText(translate_text(f"Cash forecast ({c['days']} days): projected net {money(c['projected_net'])} • Receivable {money(c['receivable'])} • Payable {money(c['payable'])} • Executive health {snapshot['score']}/100 • Active alerts {snapshot['critical'] + snapshot['high'] + snapshot['medium']}"))

# شرح الدالة _load_detail_projects: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _load_detail_projects(self):
        conn=get_connection()
        try: rows=conn.execute("SELECT project_id,project_name FROM projects ORDER BY project_name").fetchall()
        finally: conn.close()
        current=self.detail_project.currentData(); self.detail_project.blockSignals(True); self.detail_project.clear()
        for r in rows: self.detail_project.addItem(f"{r['project_id']} • {r['project_name']}",r['project_id'])
        if current:
            i=self.detail_project.findData(current)
            if i>=0:self.detail_project.setCurrentIndex(i)
        self.detail_project.blockSignals(False)

# شرح الدالة analyze_project: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def analyze_project(self):
        pid=self.detail_project.currentData()
        if not pid: return
        d=unified_project_intelligence(pid)
        m=d['metrics']; p=d['payment_risk']; w=d['workforce']; mat=d['materials']; v=d['vehicles']; docs=d['documents']
        self.summary.setText(translate_text(f"{m['project_name']} • Overall {d['overall']} • Health {m.get('health_score',0):.0f}/100 • Progress {m.get('progress',0):.1f}% • Cost {m.get('cost_pct',0):.1f}% • Collection {p['collection_rate']:.1f}% • Labor {w['status']} • Materials {mat['status']} • Vehicles {v['status']} • Documents {docs['status']}"))
        rows=[]
        for x in d['risks']: rows.append({'severity':'RISK','title':'Construction Intelligence','count':1,'message':x})
        for x in d['actions']: rows.append({'severity':'ACTION','title':'Recommended action','count':1,'message':x})
        self.table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for c,vv in enumerate([r['severity'],r['title'],str(r['count']),r['message']]): self.table.setItem(i,c,QTableWidgetItem(str(vv)))

# شرح الدالة ask: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def ask(self):
        result=answer(self.query.text()); self.table.setRowCount(len(result.get('rows',[])))
        rows=result.get('rows',[])
        for i,r in enumerate(rows):
            if isinstance(r,dict): vals=[r.get('health',r.get('severity','')),r.get('project_name',r.get('title','')),str(r.get('count',r.get('receivable',r.get('expense_cost','')))),r.get('message',r.get('answer',''))]
            else: vals=['','','',str(r)]
            for c,v in enumerate(vals): self.table.setItem(i,c,QTableWidgetItem(str(v)))
        self.summary.setText(result.get('answer',''))
# شرح الدالة reconcile: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def executive_scan(self):
        try:
            result = run_governance_scan()
            snapshot = portfolio_control_snapshot()
            self.summary.setText(translate_text(
                f"Executive scan complete • Health {snapshot['score']}/100 • "
                f"Critical {snapshot['critical']} • High {snapshot['high']} • Medium {snapshot['medium']} • "
                f"New alerts {result['created_alerts']} • New actions {result['created_actions']}"
            ))
            self.refresh()
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            QMessageBox.warning(self, translate_text("Executive scan"), str(exc))

    def reconcile(self):
        r=reconciliation(); self.summary.setText(translate_text("Reconciliation passed." if r['ok'] else f"Reconciliation found {sum(x['count'] for x in r['issues'])} issue(s).")); self.refresh()

# شرح الدالة report: تنشئ تقرير الإدارة من البيانات الحالية وتعرض نتيجة العملية للمستخدم.
    def report(self):
        default_name = "Management_Report.xlsx"
        path, ok = QFileDialog.getSaveFileName(
            self,
            translate_text("Generate management report"),
            default_name,
            "Excel Workbook (*.xlsx)",
        )
        if not ok or not path:
            return
        try:
            output = generate_management_report(path)
            QMessageBox.information(
                self,
                translate_text("Management report"),
                translate_text(f"Management report generated successfully:\n{output}"),
            )
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            QMessageBox.critical(
                self,
                translate_text("Management report"),
                translate_text(f"Could not generate management report: {exc}"),
            )
# شرح الدالة whatif: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def whatif(self):
        conn=get_connection()
        try: projects=conn.execute("SELECT project_id,project_name FROM projects WHERE status='Active' ORDER BY project_name").fetchall()
        finally: conn.close()
        if not projects: QMessageBox.information(self,translate_text("What-if"),translate_text("No active projects.")); return
        names=[r['project_name'] for r in projects]; name,ok=QInputDialog.getItem(self,translate_text("Project"),translate_text("Project:"),names,0,False)
        if not ok:return
        pid=projects[names.index(name)]['project_id']; mat,ok=QInputDialog.getDouble(self,translate_text("Material increase"),translate_text("Material price increase %:"),0,-100,500,1); 
        if not ok:return
        delay,ok=QInputDialog.getInt(self,translate_text("Delay"),translate_text("Delay days:"),0,0,3650,1)
        if not ok:return
        labor,ok=QInputDialog.getDouble(self,translate_text("Labor increase"),translate_text("Labor cost increase %:"),0,-100,500,1)
        if not ok:return
        r=what_if(pid,mat,delay,labor); QMessageBox.information(self,translate_text("What-if result"),translate_text(f"Forecast cost: {money(r['forecast_cost'])}\nVariance vs budget: {money(r['forecast_variance'])}\nForecast margin: {money(r['forecast_margin'])}"))

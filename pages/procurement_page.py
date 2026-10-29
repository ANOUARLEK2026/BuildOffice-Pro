from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.procurement_service import create_purchase_order

from .base_page import BasePage, money


class ProcurementPage(BasePage):
    def __init__(self):
        super().__init__("Procurement", "Purchase orders, supplier buying and material receipts")
        bar=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText(translate_text("Search purchase orders")); add=QPushButton(translate_text("+ New Purchase Order")); add.setObjectName("primaryButton"); add.clicked.connect(self.add); refresh=QPushButton(translate_text("Refresh")); refresh.clicked.connect(self.load)
        bar.addWidget(self.search,1); bar.addWidget(add); bar.addWidget(refresh); self.body.addLayout(bar); self.search.textChanged.connect(self.load)
        frame,lay=self.panel(); self.table=QTableWidget(0,8); self.table.setHorizontalHeaderLabels([translate_text(x) for x in ["Order","Supplier","Project","Date","Expected","Status","Subtotal","Total"]]); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch); lay.addWidget(self.table); self.body.addWidget(frame); self.load()
    def load(self):
        c=get_connection(); term=f"%{self.search.text().strip()}%"
        try: rows=c.execute("SELECT po.order_number,COALESCE(bp.display_name,bp.legal_name,'-') supplier,COALESCE(p.project_name,'-') project,po.order_date,COALESCE(po.expected_date,'-') expected,po.status,po.subtotal,po.total_amount FROM purchase_orders po LEFT JOIN business_partners bp ON bp.partner_id=po.supplier_id LEFT JOIN projects p ON p.project_id=po.project_id WHERE po.order_number LIKE ? OR COALESCE(bp.display_name,bp.legal_name,'') LIKE ? OR COALESCE(p.project_name,'') LIKE ? ORDER BY po.order_date DESC,po.order_number DESC",(term,term,term)).fetchall()
        finally:c.close()
        self.table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for j,v in enumerate(r): self.table.setItem(i,j,QTableWidgetItem(money(v) if isinstance(v,(int,float)) else str(v)))
    def add(self):
        c=get_connection()
        try:
            suppliers=c.execute("SELECT partner_id,COALESCE(display_name,legal_name) name FROM business_partners WHERE partner_type IN ('Supplier','Both') AND status='Active' ORDER BY name").fetchall(); projects=c.execute("SELECT project_id,project_name FROM projects ORDER BY project_name").fetchall()
        finally:c.close()
        if not suppliers:self.error("No active supplier found."); return
        d=QDialog(self); d.setWindowTitle(translate_text("New Purchase Order")); f=QFormLayout(d); s=LocalizedComboBox(); [s.addItem(x['name'],x['partner_id']) for x in suppliers]; p=LocalizedComboBox(); p.addItem(translate_text("No project"),None); [p.addItem(x['project_name'],x['project_id']) for x in projects]; today = datetime.now(timezone.utc).date().isoformat(); od=QLineEdit(today); ed=QLineEdit(today); desc=QLineEdit(); qty=QDoubleSpinBox(); qty.setRange(.001,1e9); qty.setValue(1); price=QDoubleSpinBox(); price.setRange(0,1e15); price.setDecimals(2); unit=QLineEdit(); tax=QDoubleSpinBox(); tax.setRange(0,100); tax.setValue(19); notes=QTextEdit();
        for lab,w in [("Supplier",s),("Project",p),("Order date",od),("Expected date",ed),("Item description",desc),("Quantity",qty),("Unit",unit),("Unit price",price),("TVA %",tax),("Notes",notes)]:f.addRow(translate_text(lab),w)
        bb=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); f.addRow(bb)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        if not desc.text().strip():self.error("Item description is required.");return
        try:create_purchase_order(s.currentData(),p.currentData(),od.text().strip(),ed.text().strip(),[{"description":desc.text().strip(),"quantity":qty.value(),"unit":unit.text().strip(),"unit_price":price.value(),"tax_rate":tax.value()}],notes.toPlainText().strip())
        except (ValueError, TypeError, RuntimeError) as exc:self.error(str(exc));return
        self.load()

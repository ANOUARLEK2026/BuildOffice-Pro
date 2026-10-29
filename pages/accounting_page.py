from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Callable
from typing import Any, cast

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
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
from services.accounting_integration import (
    post_invoice,
    sync_existing_financial_records,
)
from services.accounting_service import (
    account_balance,
    create_account,
    ensure_default_accounts,
    invoice_totals,
)

from .base_page import BasePage, money

# The accounting service accepts numeric values at runtime. These adapters
# express that runtime contract to Pylance without changing business behavior.
_INVOICE_TOTALS = cast(
    Callable[[float, float, float], tuple[float, float, float]],
    invoice_totals,
)
_CREATE_ACCOUNT = cast(Callable[..., Any], create_account)


def _item_text(table: QTableWidget, row: int, column: int) -> str:
    item = table.item(row, column)
    return item.text() if item is not None else ""


def _safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _id(p): return f'{p}-{uuid.uuid4().hex[:12].upper()}'

class InvoiceDialog(QDialog):
    def __init__(self,parent=None,invoice_id=None):
        super().__init__(parent); self.invoice_id=invoice_id; self.setWindowTitle(translate_text('Edit invoice') if invoice_id else translate_text('New invoice')); self.resize(900,650)
        f=QFormLayout(); self.type=LocalizedComboBox(); self.type.addItems(['Sales','Purchase']); self.partner=LocalizedComboBox(); self.partner.addItem(translate_text('No partner'),None); self.project=LocalizedComboBox(); self.project.addItem(translate_text('No project'),None)
        self.number=QLineEdit(); self.date=QDateEdit(QDate.currentDate()); self.date.setCalendarPopup(True); self.due=QDateEdit(QDate.currentDate()); self.due.setCalendarPopup(True); self.discount=QDoubleSpinBox(); self.discount.setRange(0,1e15); self.discount.setDecimals(2); self.tax=QDoubleSpinBox(); self.tax.setRange(0,100); self.tax.setDecimals(2); self.tax.setValue(19); self.notes=QLineEdit()
        for label,w in [('Invoice type',self.type),('Invoice number',self.number),('Partner',self.partner),('Project',self.project),('Invoice date',self.date),('Due date',self.due),('Discount',self.discount),('TVA %',self.tax),('Notes',self.notes)]:f.addRow(translate_text(label),w)
        self.items=QTableWidget(0,5); self.items.setHorizontalHeaderLabels([translate_text('Description'),translate_text('Qty'),translate_text('Unit'),translate_text('Unit price'),translate_text('Amount')]); self.items.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        add=QPushButton(translate_text('+ Add item')); rem=QPushButton(translate_text('Remove item')); add.clicked.connect(self.add_item); rem.clicked.connect(lambda:self.items.removeRow(self.items.currentRow()) if self.items.currentRow()>=0 else None)
        bar=QHBoxLayout(); bar.addWidget(add); bar.addWidget(rem); bar.addStretch(); f.addRow(bar); f.addRow(self.items)
        self.total_label=QLabel('0.00'); self.tax_label=QLabel('0.00'); self.subtotal_label=QLabel('0.00');
        for label,w in [('Subtotal',self.subtotal_label),('TVA',self.tax_label),('Total',self.total_label)]:f.addRow(translate_text(label),w)
        self.discount.valueChanged.connect(self.recalc); self.tax.valueChanged.connect(self.recalc); self.items.cellChanged.connect(lambda *_:self.recalc())
        bb=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); f.addRow(bb); self.setLayout(f); self._load_data()
    def _load_data(self):
        conn=get_connection()
        try:
            for r in conn.execute("SELECT partner_id,legal_name FROM business_partners WHERE status='Active' ORDER BY legal_name"):self.partner.addItem(r['legal_name'],r['partner_id'])
            for r in conn.execute('SELECT project_id,project_name FROM projects ORDER BY project_name'):self.project.addItem(r['project_name'],r['project_id'])
            if self.invoice_id:
                i=conn.execute('SELECT * FROM invoices WHERE invoice_id=?',(self.invoice_id,)).fetchone()
                if i:
                    self.type.setCurrentText(i['invoice_type']); self.number.setText(i['invoice_number']); self.partner.setCurrentIndex(max(0,self.partner.findData(i['partner_id']))); self.project.setCurrentIndex(max(0,self.project.findData(i['project_id']))); self.date.setDate(QDate.fromString(i['invoice_date'],'yyyy-MM-dd')); self.due.setDate(QDate.fromString(i['due_date'],'yyyy-MM-dd') if i['due_date'] else QDate.currentDate()); self.discount.setValue(float(i['discount'] or 0)); self.tax.setValue(float(i['tax_rate'] or 19)); self.notes.setText(i['notes'] or '')
                    for r in conn.execute('SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY rowid',(self.invoice_id,)):self.add_item(r['description'],r['quantity'],r['unit'],r['unit_price'])
            else:self.add_item()
        finally:conn.close()
        self.recalc()
    def add_item(self,desc='',qty=1,unit='',price=0):
        r=self.items.rowCount(); self.items.insertRow(r); vals=[desc,qty,unit,price,0]
        for c,v in enumerate(vals):self.items.setItem(r,c,QTableWidgetItem(str(v)))
        self.recalc()
    def recalc(self):
        subtotal = 0.0
        for row in range(self.items.rowCount()):
            quantity = _safe_float(_item_text(self.items, row, 1))
            price = _safe_float(_item_text(self.items, row, 3))
            amount = quantity * price
            subtotal += amount
            self.items.blockSignals(True)
            self.items.setItem(row, 4, QTableWidgetItem(f"{amount:,.2f}"))
            self.items.blockSignals(False)

        taxable, tax, total = _INVOICE_TOTALS(
            subtotal,
            float(self.discount.value()),
            float(self.tax.value()),
        )
        self.subtotal_label.setText(f"{taxable:,.2f}")
        self.tax_label.setText(f"{tax:,.2f}")
        self.total_label.setText(f"{total:,.2f}")
    def payload(self):
        rows = []
        for row in range(self.items.rowCount()):
            desc = _item_text(self.items, row, 0).strip()
            quantity = _safe_float(_item_text(self.items, row, 1))
            price = _safe_float(_item_text(self.items, row, 3))
            unit = _item_text(self.items, row, 2).strip() or None
            if desc and quantity > 0 and price >= 0:
                rows.append((desc, quantity, unit, price, quantity * price))

        subtotal = sum(item[4] for item in rows)
        taxable, tax, total = _INVOICE_TOTALS(
            subtotal,
            float(self.discount.value()),
            float(self.tax.value()),
        )
        return rows, taxable, tax, total

class PaymentDialog(QDialog):
    def __init__(self,parent,invoice,customer=True):
        super().__init__(parent); self.invoice=invoice; self.customer=customer; self.setWindowTitle(translate_text('Receive payment') if customer else translate_text('Pay supplier')); self.resize(520,420); f=QFormLayout(self)
        self.date=QDateEdit(QDate.currentDate());self.date.setCalendarPopup(True);self.amount=QDoubleSpinBox();self.amount.setRange(.01,float(invoice['total_amount'])-float(invoice['paid_amount'] or 0));self.amount.setDecimals(2);self.amount.setValue(self.amount.maximum());self.account=LocalizedComboBox();self.method=LocalizedComboBox();self.method.addItems(['Cash','Bank Transfer','Cheque']);self.reference=QLineEdit();self.notes=QLineEdit()
        conn=get_connection()
        try:
            for r in conn.execute("SELECT financial_account_id,account_name,account_kind FROM financial_accounts WHERE is_active=1 ORDER BY account_kind,account_name"):self.account.addItem(f"{r['account_name']} ({r['account_kind']})",r['financial_account_id'])
        finally:conn.close()
        if self.account.count()==0:self.account.addItem(translate_text('Create a cash/bank account first'),None)
        for l,w in [('Payment date',self.date),('Outstanding',QLabel(f"{float(invoice['total_amount'])-float(invoice['paid_amount'] or 0):,.2f}")),('Amount',self.amount),('Financial account',self.account),('Method',self.method),('Reference',self.reference),('Notes',self.notes)]:f.addRow(translate_text(l),w)
        b=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);b.accepted.connect(self.accept);b.rejected.connect(self.reject);f.addRow(b)

def _ensure_financial_accounts():
    conn=get_connection()
    try:
        ensure_default_accounts(conn)
        for code,name,kind in [('1000','Caisse','Cash'),('1100','Banque','Bank')]:
            aid=conn.execute('SELECT account_id FROM chart_of_accounts WHERE account_code=?',(code,)).fetchone()[0]
            if not conn.execute('SELECT 1 FROM financial_accounts WHERE account_id=?',(aid,)).fetchone():conn.execute("INSERT INTO financial_accounts(financial_account_id,account_id,account_name,account_kind,currency) VALUES(?,?,?,?,?)",(_id('FA'),aid,name,kind,'DZD'))
        conn.commit()
    finally:conn.close()

class AccountingPage(BasePage):
    def __init__(self):
        super().__init__('Accounting & Finance','Full accounting, invoices, receivables, payables and cash control'); _ensure_financial_accounts(); self._build(); self.refresh()
    def _build(self):
        tabs=QTabWidget(); self.tabs=tabs
        # Chart
        w=QWidget();l=QVBoxLayout(w);bar=QHBoxLayout();a=QPushButton(translate_text('Add account'));a.clicked.connect(self.add_account);bar.addWidget(a);fa=QPushButton(translate_text('Financial accounts'));fa.clicked.connect(self.add_financial);bar.addWidget(fa);sync=QPushButton(translate_text('Sync all financial records'));sync.clicked.connect(self.sync_all);bar.addWidget(sync);bar.addStretch();l.addLayout(bar);self.accounts=QTableWidget(0,5);self.accounts.setHorizontalHeaderLabels([translate_text(x) for x in ['Code','Account','Type','Opening','Balance']]);l.addWidget(self.accounts,1);tabs.addTab(w,translate_text('Chart of Accounts'))
        # invoices
        w=QWidget();l=QVBoxLayout(w);bar=QHBoxLayout();n=QPushButton(translate_text('+ New invoice'));n.clicked.connect(self.new_invoice);bar.addWidget(n);e=QPushButton(translate_text('Edit'));e.clicked.connect(self.edit_invoice);bar.addWidget(e);issue=QPushButton(translate_text('Issue / Post'));issue.clicked.connect(self.issue_invoice);bar.addWidget(issue);pay=QPushButton(translate_text('Payment'));pay.clicked.connect(self.invoice_payment);bar.addWidget(pay);bar.addStretch();l.addLayout(bar);self.invoices=QTableWidget(0,9);self.invoices.setHorizontalHeaderLabels([translate_text(x) for x in ['Number','Type','Partner','Project','Date','Due','Subtotal','TVA','Total / Paid']]);self.invoices.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch);l.addWidget(self.invoices,1);tabs.addTab(w,translate_text('Invoices & Ledger'))
        # journal
        w=QWidget();l=QVBoxLayout(w);self.journal=QTableWidget(0,6);self.journal.setHorizontalHeaderLabels([translate_text(x) for x in ['Number','Date','Description','Debit','Credit','Status']]);l.addWidget(self.journal,1);tabs.addTab(w,translate_text('Journal'))
        # cash
        w=QWidget();l=QVBoxLayout(w);self.cash=QTableWidget(0,6);self.cash.setHorizontalHeaderLabels([translate_text(x) for x in ['Date','Account','Type','Amount','Reference','Description']]);l.addWidget(self.cash,1);tabs.addTab(w,translate_text('Cash & Bank'))
        # receivable/payable
        w=QWidget();l=QVBoxLayout(w);self.ledger=QTableWidget(0,7);self.ledger.setHorizontalHeaderLabels([translate_text(x) for x in ['Partner','Type','Invoices','Invoiced','Paid','Outstanding','Overdue']]);l.addWidget(self.ledger,1);tabs.addTab(w,translate_text('Receivables & Payables'))
        # reports
        w=QWidget();l=QVBoxLayout(w);self.report=QPlainTextEdit();self.report.setReadOnly(True);b=QPushButton(translate_text('Refresh financial reports'));b.clicked.connect(self.load_report);l.addWidget(b);l.addWidget(self.report,1);tabs.addTab(w,translate_text('Financial Reports'));self.body.addWidget(tabs)
    def selected_invoice(self):
        r=self.invoices.currentRow();it=self.invoices.item(r,0) if r>=0 else None
        if not it:return None
        conn=get_connection()
        try:return conn.execute('SELECT * FROM invoices WHERE invoice_number=?',(it.text(),)).fetchone()
        finally:conn.close()
    def add_account(self):
        d=QDialog(self);f=QFormLayout(d);code=QLineEdit();name=QLineEdit();typ=LocalizedComboBox();typ.addItems(['Asset','Liability','Equity','Revenue','Expense']);opening=QDoubleSpinBox();opening.setRange(-1e15,1e15);opening.setDecimals(2)
        for x,w in [('Account code',code),('Account name',name),('Type',typ),('Opening balance',opening)]:f.addRow(translate_text(x),w)
        b=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);b.accepted.connect(d.accept);b.rejected.connect(d.reject);f.addRow(b)
        if d.exec()==QDialog.DialogCode.Accepted and code.text().strip() and name.text().strip():
            try:create_account(code.text(),name.text(),typ.currentText(),opening_balance=opening.value())
            except (sqlite3.Error, ValueError, TypeError, OSError, RuntimeError) as e:self.error(str(e));return
            self.refresh()
    def add_financial(self):
        d=QDialog(self);f=QFormLayout(d);kind=LocalizedComboBox();kind.addItems(['Cash','Bank']);name=QLineEdit();bank=QLineEdit();num=QLineEdit();opening=QDoubleSpinBox();opening.setRange(-1e15,1e15);opening.setDecimals(2);acc=LocalizedComboBox();conn=get_connection()
        try:
            for r in conn.execute("SELECT account_id,account_code,account_name FROM chart_of_accounts WHERE is_cash_account=1 OR is_bank_account=1 ORDER BY account_code"):acc.addItem(f"{r['account_code']} - {r['account_name']}",r['account_id'])
        finally:conn.close()
        for x,w in [('Kind',kind),('Account',acc),('Name',name),('Bank name',bank),('Account number / RIB',num),('Opening balance',opening)]:f.addRow(translate_text(x),w)
        b=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);b.accepted.connect(d.accept);b.rejected.connect(d.reject);f.addRow(b)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        conn=get_connection()
        try:conn.execute("INSERT INTO financial_accounts(financial_account_id,account_id,account_name,account_kind,currency,bank_name,account_number,opening_balance,current_balance) VALUES(?,?,?,?,?,?,?,?,?)",(_id('FA'),acc.currentData(),name.text().strip() or acc.currentText(),kind.currentText(),'DZD',bank.text().strip() or None,num.text().strip() or None,opening.value(),opening.value()));conn.commit()
        finally:conn.close()
        self.refresh()
    def new_invoice(self):self._save_invoice()
    def edit_invoice(self):
        i=self.selected_invoice()
        if i:self._save_invoice(i['invoice_id'])
    def _save_invoice(self,invoice_id=None):
        d=InvoiceDialog(self,invoice_id)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        rows,subtotal,tax,total=d.payload()
        if not d.number.text().strip() or not rows:self.error('Invoice number and at least one valid item are required.');return
        conn=get_connection()
        try:
            if invoice_id:
                old=conn.execute('SELECT status FROM invoices WHERE invoice_id=?',(invoice_id,)).fetchone()
                if old and old['status']!='Draft':self.error('Only draft invoices can be edited.');return
                iid=invoice_id;conn.execute("UPDATE invoices SET invoice_type=?,invoice_number=?,partner_id=?,project_id=?,invoice_date=?,due_date=?,subtotal=?,discount=?,tax_rate=?,tax_amount=?,total_amount=?,notes=?,updated_at=CURRENT_TIMESTAMP WHERE invoice_id=?",(d.type.currentText(),d.number.text().strip(),d.partner.currentData(),d.project.currentData(),d.date.date().toString('yyyy-MM-dd'),d.due.date().toString('yyyy-MM-dd'),subtotal,d.discount.value(),d.tax.value(),tax,total,d.notes.text().strip() or None,iid));conn.execute('DELETE FROM invoice_items WHERE invoice_id=?',(iid,))
            else:
                iid=_id('INV');conn.execute("INSERT INTO invoices(invoice_id,invoice_number,invoice_type,partner_id,project_id,invoice_date,due_date,subtotal,discount,tax_rate,tax_amount,total_amount,status,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(iid,d.number.text().strip(),d.type.currentText(),d.partner.currentData(),d.project.currentData(),d.date.date().toString('yyyy-MM-dd'),d.due.date().toString('yyyy-MM-dd'),subtotal,d.discount.value(),d.tax.value(),tax,total,'Draft',d.notes.text().strip() or None))
            for desc,q,u,p,a in rows:conn.execute('INSERT INTO invoice_items(invoice_item_id,invoice_id,description,quantity,unit,unit_price,amount,tax_rate) VALUES(?,?,?,?,?,?,?,?)',(_id('IIT'),iid,desc,q,u,p,a,d.tax.value()))
            conn.commit()
        except (sqlite3.Error, ValueError, TypeError, OSError, RuntimeError) as e:conn.rollback();self.error(str(e));return
        finally:conn.close()
        self.refresh()
    def issue_invoice(self):
        i=self.selected_invoice()
        if not i:self.error('Select an invoice first.');return
        if i['status']!='Draft':self.error('Only draft invoices can be issued.');return
        conn=get_connection()
        try:conn.execute("UPDATE invoices SET status='Issued',updated_at=CURRENT_TIMESTAMP WHERE invoice_id=?",(i['invoice_id'],));conn.commit()
        finally:conn.close()
        try:post_invoice(i['invoice_id'])
        except (sqlite3.Error, ValueError, TypeError, OSError, RuntimeError) as e:self.error(str(e));return
        self.refresh()
    def invoice_payment(self):
        i=self.selected_invoice()
        if not i:self.error('Select an invoice first.');return
        outstanding=float(i['total_amount'] or 0)-float(i['paid_amount'] or 0)
        if i['status'] not in ('Issued','Partially Paid','Paid') or outstanding<=0:self.error('This invoice has no outstanding amount.');return
        d=PaymentDialog(self,i,i['invoice_type']=='Sales')
        if d.exec()!=QDialog.DialogCode.Accepted:return
        if not d.account.currentData():self.error('Create a financial cash/bank account first.');return
        conn=get_connection()
        try:
            amount=d.amount.value();typ='Receipt' if i['invoice_type']=='Sales' else 'Payment';cash=conn.execute('SELECT account_id FROM financial_accounts WHERE financial_account_id=?',(d.account.currentData(),)).fetchone()[0]
            # payment journal
            debit, _credit = ('1200', cash) if typ == 'Payment' else (cash, '1200')
            partner=i['partner_id'];desc=f"Payment for invoice {i['invoice_number']}"
            from services.accounting_service import (
                create_journal_entry,
                next_entry_number,
            )
            jid=create_journal_entry(next_entry_number(conn),d.date.date().toString('yyyy-MM-dd'),desc,[{'account_id':conn.execute('SELECT account_id FROM chart_of_accounts WHERE account_code=?',(debit,)).fetchone()[0],'partner_id':partner,'project_id':i['project_id'],'debit':amount,'credit':0},{'account_id':cash,'partner_id':partner,'project_id':i['project_id'],'debit':0,'credit':amount}],'InvoicePayment',i['invoice_id'],conn)
            tx=_id('CTX');r=conn.execute('SELECT transaction_number FROM cash_transactions ORDER BY rowid DESC LIMIT 1').fetchone();n=int(str(r[0]).split('-')[-1])+1 if r else 1;conn.execute('INSERT INTO cash_transactions(transaction_id,transaction_number,transaction_date,financial_account_id,transaction_type,partner_id,project_id,amount,reference,description,journal_entry_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(tx,f'TX-{n:06d}',d.date.date().toString('yyyy-MM-dd'),d.account.currentData(),typ,partner,i['project_id'],amount,d.reference.text().strip() or None,d.notes.text().strip() or desc,jid));conn.execute('INSERT INTO payment_allocations(allocation_id,transaction_id,invoice_id,amount) VALUES(?,?,?,?)',(_id('ALLOC'),tx,i['invoice_id'],amount));conn.execute('INSERT INTO invoice_payments(invoice_payment_id,invoice_id,payment_date,amount,financial_account_id,payment_method,reference,notes,cash_transaction_id) VALUES(?,?,?,?,?,?,?,?,?)',(_id('IPAY'),i['invoice_id'],d.date.date().toString('yyyy-MM-dd'),amount,d.account.currentData(),d.method.currentText(),d.reference.text().strip() or None,d.notes.text().strip() or None,tx));newpaid=float(i['paid_amount'] or 0)+amount;status='Paid' if newpaid+0.005>=float(i['total_amount']) else 'Partially Paid';conn.execute('UPDATE invoices SET paid_amount=?,status=?,updated_at=CURRENT_TIMESTAMP WHERE invoice_id=?',(newpaid,status,i['invoice_id']));conn.commit()
        except (sqlite3.Error, ValueError, TypeError, OSError, RuntimeError) as e:conn.rollback();self.error(str(e));return
        finally:conn.close()
        self.refresh()
    def sync_all(self):
        try:self._sync_result(sync_existing_financial_records())
        except (sqlite3.Error, ValueError, TypeError, OSError, RuntimeError) as e:self.error(str(e))
    def _sync_result(self,r):QMessageBox.information(self,translate_text('Accounting'),translate_text('Sync complete: ') + ', '.join(f'{k}={v}' for k,v in r.items()));self.refresh()
    def load_report(self):
        conn=get_connection()
        try:
            sales=float(conn.execute("SELECT COALESCE(SUM(total_amount),0) FROM invoices WHERE invoice_type='Sales' AND status<>'Cancelled'").fetchone()[0]); purchases=float(conn.execute("SELECT COALESCE(SUM(total_amount),0) FROM invoices WHERE invoice_type='Purchase' AND status<>'Cancelled'").fetchone()[0]); vat_out=float(conn.execute("SELECT COALESCE(SUM(credit-debit),0) FROM journal_lines jl JOIN chart_of_accounts a ON a.account_id=jl.account_id WHERE a.account_code='4457'").fetchone()[0]); vat_in=float(conn.execute("SELECT COALESCE(SUM(debit-credit),0) FROM journal_lines jl JOIN chart_of_accounts a ON a.account_id=jl.account_id WHERE a.account_code='4456'").fetchone()[0]); cash=float(conn.execute("SELECT COALESCE(SUM(debit-credit),0) FROM journal_lines jl JOIN chart_of_accounts a ON a.account_id=jl.account_id WHERE a.account_code='1000'").fetchone()[0]);bank=float(conn.execute("SELECT COALESCE(SUM(debit-credit),0) FROM journal_lines jl JOIN chart_of_accounts a ON a.account_id=jl.account_id WHERE a.account_code='1100'").fetchone()[0]);recv=float(conn.execute("SELECT COALESCE(SUM(debit-credit),0) FROM journal_lines jl JOIN chart_of_accounts a ON a.account_id=jl.account_id WHERE a.account_code='1200'").fetchone()[0]);pay=float(conn.execute("SELECT COALESCE(SUM(credit-debit),0) FROM journal_lines jl JOIN chart_of_accounts a ON a.account_id=jl.account_id WHERE a.account_code='2000'").fetchone()[0])
        finally:conn.close()
        self.report.setPlainText('\n'.join([translate_text('FINANCIAL SNAPSHOT'),'',f'{translate_text("Sales invoiced")}: {money(sales)}',f'{translate_text("Purchases invoiced")}: {money(purchases)}',f'{translate_text("Cash balance")}: {money(cash)}',f'{translate_text("Bank balance")}: {money(bank)}',f'{translate_text("Customer receivables")}: {money(recv)}',f'{translate_text("Supplier payables")}: {money(pay)}',f'{translate_text("Output VAT")}: {money(vat_out)}',f'{translate_text("Input VAT")}: {money(vat_in)}',f'{translate_text("Net VAT position")}: {money(vat_out-vat_in)}']))
    def refresh(self,*_):
        conn=get_connection()
        try:
            ensure_default_accounts(conn)
            rows=conn.execute('SELECT * FROM chart_of_accounts ORDER BY account_code').fetchall();self.accounts.setRowCount(len(rows))
            for r,x in enumerate(rows):
                vals=[x['account_code'],x['account_name'],x['account_type'],money(x['opening_balance']),money(account_balance(x['account_id']))]
                for c,v in enumerate(vals):self.accounts.setItem(r,c,QTableWidgetItem(str(v)))
            inv=conn.execute("""SELECT i.*,COALESCE(bp.legal_name,'-') partner,COALESCE(p.project_name,'-') project FROM invoices i LEFT JOIN business_partners bp ON bp.partner_id=i.partner_id LEFT JOIN projects p ON p.project_id=i.project_id ORDER BY i.invoice_date DESC,i.invoice_number DESC""").fetchall();self.invoices.setRowCount(len(inv))
            for r,x in enumerate(inv):
                vals=[x['invoice_number'],x['invoice_type'],x['partner'],x['project'],x['invoice_date'],x['due_date'] or '-',money(x['subtotal']),money(x['tax_amount']),f"{money(x['total_amount'])} / {money(x['paid_amount'])} ({x['status']})"]
                for c,v in enumerate(vals):self.invoices.setItem(r,c,QTableWidgetItem(str(v)))
            jr=conn.execute("SELECT je.entry_number,je.entry_date,je.description,COALESCE(SUM(jl.debit),0),COALESCE(SUM(jl.credit),0),je.status FROM journal_entries je LEFT JOIN journal_lines jl ON jl.journal_entry_id=je.journal_entry_id GROUP BY je.journal_entry_id ORDER BY je.entry_date DESC,je.rowid DESC LIMIT 1000").fetchall();self.journal.setRowCount(len(jr))
            for r,x in enumerate(jr):
                for c,v in enumerate([x[0],x[1],x[2],money(x[3]),money(x[4]),x[5]]):self.journal.setItem(r,c,QTableWidgetItem(str(v)))
            cr=conn.execute("SELECT ct.transaction_date,fa.account_name,ct.transaction_type,ct.amount,COALESCE(ct.reference,'-'),COALESCE(ct.description,'-') FROM cash_transactions ct JOIN financial_accounts fa ON fa.financial_account_id=ct.financial_account_id ORDER BY ct.transaction_date DESC,ct.rowid DESC LIMIT 1000").fetchall();self.cash.setRowCount(len(cr))
            for r,x in enumerate(cr):
                for c,v in enumerate([x[0],x[1],x[2],money(x[3]),x[4],x[5]]):self.cash.setItem(r,c,QTableWidgetItem(str(v)))
            led=conn.execute("""SELECT bp.legal_name,i.invoice_type,COUNT(i.invoice_id),COALESCE(SUM(i.total_amount),0),COALESCE(SUM(i.paid_amount),0),COALESCE(SUM(i.total_amount-i.paid_amount),0),COALESCE(SUM(CASE WHEN i.due_date<date('now') AND i.total_amount>i.paid_amount THEN i.total_amount-i.paid_amount ELSE 0 END),0) FROM invoices i JOIN business_partners bp ON bp.partner_id=i.partner_id WHERE i.status<>'Cancelled' GROUP BY bp.partner_id,i.invoice_type ORDER BY bp.legal_name""").fetchall();self.ledger.setRowCount(len(led))
            for r,x in enumerate(led):
                for c,v in enumerate([x[0],x[1],x[2],money(x[3]),money(x[4]),money(x[5]),money(x[6])]):self.ledger.setItem(r,c,QTableWidgetItem(str(v)))
        finally:conn.close()
        self.load_report()

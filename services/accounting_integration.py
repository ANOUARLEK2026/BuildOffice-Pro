from __future__ import annotations

import uuid

from repositories.db import get_connection
from services.accounting_service import (
    create_journal_entry,
    ensure_default_accounts,
    next_entry_number,
)


def _id(p): return f"{p}-{uuid.uuid4().hex[:12].upper()}"
def _account(conn,code):
    r=conn.execute("SELECT account_id FROM chart_of_accounts WHERE account_code=?",(code,)).fetchone()
    if not r: raise ValueError(f"Missing account {code}")
    return r["account_id"]
def _posted(conn,typ,sid): return conn.execute("SELECT journal_entry_id FROM accounting_postings WHERE source_type=? AND source_id=?",(typ,sid)).fetchone()
def _cash_code(method):
    t=str(method or '').lower(); return '1100' if any(x in t for x in ('bank','بنك','virement','transfer')) else '1000'
def _post_two(conn,typ,sid,date,desc,debit,credit,amount,partner=None,project=None):
    if float(amount or 0)<=0: raise ValueError('Amount must be greater than zero.')
    jid=create_journal_entry(next_entry_number(conn),date,desc,[{'account_id':_account(conn,debit),'partner_id':partner,'project_id':project,'debit':float(amount),'credit':0,'description':desc},{'account_id':_account(conn,credit),'partner_id':partner,'project_id':project,'debit':0,'credit':float(amount),'description':desc}],typ,sid,conn)
    conn.execute("INSERT INTO accounting_postings(posting_id,source_type,source_id,journal_entry_id) VALUES(?,?,?,?)",(_id('POST'),typ,sid,jid)); return jid
def _cash_tx(conn,date,code,typ,amount,reference,desc,project,jid):
    fa=conn.execute("SELECT financial_account_id FROM financial_accounts WHERE account_id=? AND is_active=1 ORDER BY rowid LIMIT 1",(_account(conn,code),)).fetchone()
    if not fa: return
    r=conn.execute("SELECT transaction_number FROM cash_transactions ORDER BY rowid DESC LIMIT 1").fetchone()
    try: n=int(str(r[0]).split('-')[-1])+1 if r else 1
    except (TypeError, ValueError): n=1
    conn.execute("INSERT INTO cash_transactions(transaction_id,transaction_number,transaction_date,financial_account_id,transaction_type,project_id,amount,reference,description,journal_entry_id) VALUES(?,?,?,?,?,?,?,?,?,?)",(_id('CTX'),f'TX-{n:06d}',date,fa[0],typ,project,float(amount),reference,desc,jid))
def post_expense(expense_id):
    conn=get_connection()
    try:
        ensure_default_accounts(conn); e=conn.execute('SELECT * FROM expenses WHERE expense_id=?',(expense_id,)).fetchone()
        if not e: raise ValueError('Expense not found.')
        old=_posted(conn,'Expense',expense_id)
        if old:return old[0],False
        payment_count=int(conn.execute('SELECT COUNT(*) FROM expense_payments WHERE expense_id=?',(expense_id,)).fetchone()[0] or 0); total=float(e['amount'] or 0)
        # If explicit payment records exist, expense recognition is accrued to supplier.
        # The payment records then clear the supplier balance. Otherwise preserve the
        # legacy direct-payment behavior encoded by the expense payment method.
        credit='2000' if payment_count else _cash_code(e['payment_method']); jid=_post_two(conn,'Expense',expense_id,e['date'],e['description'] or 'Expense','5000',credit,total,project=e['project_id']); conn.commit(); return jid,True
    finally: conn.close()
def post_expense_payment(payment_id):
    conn=get_connection()
    try:
        ensure_default_accounts(conn); p=conn.execute('SELECT ep.*,e.project_id,e.description FROM expense_payments ep JOIN expenses e ON e.expense_id=ep.expense_id WHERE ep.payment_id=?',(payment_id,)).fetchone()
        if not p: raise ValueError('Expense payment not found.')
        old=_posted(conn,'ExpensePayment',payment_id)
        if old:return old[0],False
        code=_cash_code(p['payment_method']); jid=_post_two(conn,'ExpensePayment',payment_id,p['payment_date'],p['description'] or 'Supplier payment','2000',code,p['amount'],project=p['project_id']); _cash_tx(conn,p['payment_date'],code,'Payment',p['amount'],p['reference'],p['description'] or 'Supplier payment',p['project_id'],jid); conn.commit(); return jid,True
    finally: conn.close()
def post_project_payment(payment_id):
    conn=get_connection()
    try:
        ensure_default_accounts(conn); p=conn.execute('SELECT * FROM project_payments WHERE payment_id=?',(payment_id,)).fetchone()
        if not p: raise ValueError('Project payment not found.')
        old=_posted(conn,'ProjectPayment',payment_id)
        if old:return old[0],False
        code=_cash_code(p['payment_method']); jid=_post_two(conn,'ProjectPayment',payment_id,p['date'],'Customer receipt',code,'1200',p['amount'],project=p['project_id']); _cash_tx(conn,p['date'],code,'Receipt',p['amount'],p['reference'],'Customer receipt',p['project_id'],jid); conn.commit(); return jid,True
    finally: conn.close()
def post_debt_payment(payment_id):
    conn=get_connection()
    try:
        ensure_default_accounts(conn); p=conn.execute('SELECT dp.*,d.project_id,d.lender FROM debt_payments dp JOIN debt d ON d.debt_id=dp.debt_id WHERE dp.payment_id=?',(payment_id,)).fetchone()
        if not p: raise ValueError('Debt payment not found.')
        old=_posted(conn,'DebtPayment',payment_id)
        if old:return old[0],False
        code=_cash_code(p['payment_method']); jid=_post_two(conn,'DebtPayment',payment_id,p['payment_date'],f"Debt payment: {p['lender']}",'2000',code,p['amount'],project=p['project_id']); _cash_tx(conn,p['payment_date'],code,'Payment',p['amount'],p['reference'],f"Debt payment: {p['lender']}",p['project_id'],jid); conn.commit(); return jid,True
    finally: conn.close()
def post_invoice(invoice_id):
    conn=get_connection()
    try:
        ensure_default_accounts(conn); i=conn.execute('SELECT * FROM invoices WHERE invoice_id=?',(invoice_id,)).fetchone()
        if not i: raise ValueError('Invoice not found.')
        old=_posted(conn,'Invoice',invoice_id)
        if old:return old[0],False
        if i['status'] not in ('Issued','Partially Paid','Paid'): raise ValueError('Only issued invoices can be posted.')
        total=float(i['total_amount'] or 0); taxable=max(0,total-float(i['tax_amount'] or 0)); tax=float(i['tax_amount'] or 0); partner=i['partner_id']; project=i['project_id']; desc=f"{i['invoice_type']} invoice {i['invoice_number']}"
        if i['invoice_type']=='Sales':
            lines=[{'account_id':_account(conn,'1200'),'partner_id':partner,'project_id':project,'debit':total,'credit':0,'description':desc},{'account_id':_account(conn,'4000'),'partner_id':partner,'project_id':project,'debit':0,'credit':taxable,'description':desc}]
            if tax:lines.append({'account_id':_account(conn,'4457'),'partner_id':partner,'project_id':project,'debit':0,'credit':tax,'description':'Output VAT'})
        else:
            lines=[{'account_id':_account(conn,'5000'),'partner_id':partner,'project_id':project,'debit':taxable,'credit':0,'description':desc},{'account_id':_account(conn,'2000'),'partner_id':partner,'project_id':project,'debit':0,'credit':total,'description':desc}]
            if tax:lines.insert(1,{'account_id':_account(conn,'4456'),'partner_id':partner,'project_id':project,'debit':tax,'credit':0,'description':'Input VAT'})
        jid=create_journal_entry(next_entry_number(conn),i['invoice_date'],desc,lines,'Invoice',invoice_id,conn); conn.execute("INSERT INTO accounting_postings(posting_id,source_type,source_id,journal_entry_id) VALUES(?,?,?,?)",(_id('POST'),'Invoice',invoice_id,jid)); conn.commit(); return jid,True
    finally: conn.close()
def sync_existing_financial_records():
    conn=get_connection()
    try:
        ids=lambda q:[r[0] for r in conn.execute(q)]
        data=[ids('SELECT expense_id FROM expenses'),ids('SELECT payment_id FROM expense_payments'),ids('SELECT payment_id FROM project_payments'),ids('SELECT payment_id FROM debt_payments'),ids("SELECT invoice_id FROM invoices WHERE status IN ('Issued','Partially Paid','Paid')")]
    finally:conn.close()
    funcs=[post_expense,post_expense_payment,post_project_payment,post_debt_payment,post_invoice]; names=['expenses','expense_payments','project_payments','debt_payments','invoices']; out={n:0 for n in names}
    for name,fn,rows in zip(names,funcs,data):
        for x in rows: fn(x); out[name]+=1
    return out
sync_existing_expenses=lambda limit=100000: sync_existing_financial_records()['expenses']

def post_payroll(payroll_id):
    """Post payroll accrual: gross salary debit, deductions and net payable credits."""
    conn=get_connection()
    try:
        ensure_default_accounts(conn)
        p=conn.execute("SELECT * FROM payroll_records WHERE payroll_id=?",(payroll_id,)).fetchone()
        if not p: raise ValueError("Payroll record not found.")
        old=_posted(conn,'Payroll',payroll_id)
        if old:return old[0],False
        if str(p['status']) not in ('Approved','Paid'):
            raise ValueError("Only approved or paid payroll can be posted.")
        gross=float(p['base_amount'] or 0)+float(p['overtime_amount'] or 0)+float(p['bonuses'] or 0)
        deductions=float(p['deductions'] or 0)+float(p['advances'] or 0)
        net=float(p['net_amount'] or 0)
        if gross<=0: raise ValueError("Payroll gross amount must be greater than zero.")
        lines=[{'account_id':_account(conn,'5100'),'debit':gross,'credit':0,'description':f"Payroll {p['period']}"}]
        if deductions: lines.append({'account_id':_account(conn,'2200'),'debit':0,'credit':deductions,'description':'Payroll deductions'})
        if net: lines.append({'account_id':_account(conn,'2000'),'debit':0,'credit':net,'description':'Net payroll payable'})
        # Keep the entry balanced even when legacy records contain rounding differences.
        if abs(sum(x['debit'] for x in lines)-sum(x['credit'] for x in lines))>.005:
            raise ValueError("Payroll values are inconsistent: gross must equal net plus deductions.")
        jid=create_journal_entry(next_entry_number(conn),str(p['period'])+'-28',f"Payroll {p['period']}",lines,'Payroll',payroll_id,conn)
        conn.execute("INSERT INTO accounting_postings(posting_id,source_type,source_id,journal_entry_id) VALUES(?,?,?,?)",(_id('POST'),'Payroll',payroll_id,jid))
        conn.commit(); return jid,True
    finally: conn.close()

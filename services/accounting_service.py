from __future__ import annotations

import sqlite3
import uuid

from repositories.db import get_connection

DEFAULT_ACCOUNTS = [
("1000","Caisse","Asset",1,0),("1100","Banque","Asset",0,1),("1200","Clients","Asset",0,0),
("1300","Avances aux fournisseurs","Asset",0,0),("2000","Fournisseurs","Liability",0,0),("2100","Dettes fiscales","Liability",0,0),
("2200","Dettes sociales","Liability",0,0),("3000","Capitaux propres","Equity",0,0),("4000","Chiffre d'affaires","Revenue",0,0),
("5000","Achats et sous-traitance","Expense",0,0),("5100","Salaires","Expense",0,0),("5200","Carburant et véhicules","Expense",0,0),
("5300","Frais généraux","Expense",0,0),("5400","Matériaux et fournitures","Expense",0,0),("4456","TVA déductible","Asset",0,0),("4457","TVA collectée","Liability",0,0)]

def _id(prefix): return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"
def ensure_default_accounts(conn=None):
    own=conn is None; conn=conn or get_connection()
    try:
        for code,name,typ,cash,bank in DEFAULT_ACCOUNTS:
            if not conn.execute("SELECT 1 FROM chart_of_accounts WHERE account_code=?",(code,)).fetchone():
                conn.execute("INSERT INTO chart_of_accounts(account_id,account_code,account_name,account_type,is_cash_account,is_bank_account) VALUES(?,?,?,?,?,?)",(_id("ACC"),code,name,typ,cash,bank))
        if own: conn.commit()
    finally:
        if own: conn.close()

def create_account(code,name,account_type,parent_id=None,cash=False,bank=False,opening_balance:float = 0.0):
    conn=get_connection()
    try:
        aid=_id("ACC"); conn.execute("INSERT INTO chart_of_accounts(account_id,account_code,account_name,account_type,parent_id,is_cash_account,is_bank_account,opening_balance) VALUES(?,?,?,?,?,?,?,?)",(aid,code.strip(),name.strip(),account_type,parent_id,int(cash),int(bank),float(opening_balance))); conn.commit(); return aid
    finally: conn.close()

def next_entry_number(conn):
    r=conn.execute("SELECT entry_number FROM journal_entries ORDER BY rowid DESC LIMIT 1").fetchone()
    try: n=int(str(r["entry_number"]).split("-")[-1])+1 if r else 1
    except (TypeError, ValueError): n=1
    return f"JE-{n:06d}"

def create_journal_entry(entry_number,entry_date,description,lines,reference_type=None,reference_id=None,conn=None):
    debit=sum(float(x.get("debit",0) or 0) for x in lines); credit=sum(float(x.get("credit",0) or 0) for x in lines)
    if not lines or abs(debit-credit)>0.005: raise ValueError("Journal entry is not balanced.")
    for x in lines:
        d=float(x.get("debit",0) or 0); c=float(x.get("credit",0) or 0)
        if (d>0)==(c>0): raise ValueError("Each journal line must contain either debit or credit.")
    own=conn is None; conn=conn or get_connection()
    try:
        jid=_id("JE"); conn.execute("INSERT INTO journal_entries(journal_entry_id,entry_number,entry_date,reference_type,reference_id,description,status) VALUES(?,?,?,?,?,?,?)",(jid,entry_number,entry_date,reference_type,reference_id,description,"Posted"))
        for x in lines: conn.execute("INSERT INTO journal_lines(journal_line_id,journal_entry_id,account_id,partner_id,project_id,debit,credit,description) VALUES(?,?,?,?,?,?,?,?)",(_id("JL"),jid,x["account_id"],x.get("partner_id"),x.get("project_id"),float(x.get("debit",0) or 0),float(x.get("credit",0) or 0),x.get("description")))
        if own: conn.commit()
        return jid
    except (sqlite3.Error, ValueError, TypeError, OSError):
        if own: conn.rollback()
        raise
    finally:
        if own: conn.close()

def invoice_totals(subtotal,discount=0,tax_rate=19):
    taxable=max(0,float(subtotal)-float(discount)); tax=taxable*float(tax_rate)/100; return round(taxable,2),round(tax,2),round(taxable+tax,2)

def account_balance(account_id):
    conn=get_connection()
    try:
        r=conn.execute("SELECT COALESCE(SUM(debit),0)-COALESCE(SUM(credit),0) balance FROM journal_lines jl JOIN journal_entries je ON je.journal_entry_id=jl.journal_entry_id WHERE jl.account_id=? AND je.status='Posted'",(account_id,)).fetchone(); o=conn.execute("SELECT opening_balance FROM chart_of_accounts WHERE account_id=?",(account_id,)).fetchone(); return float((o["opening_balance"] if o else 0) or 0)+float(r["balance"] or 0)
    finally: conn.close()

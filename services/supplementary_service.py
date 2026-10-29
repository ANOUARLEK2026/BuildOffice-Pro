# ============================================================
# شرح الملف: services/supplementary_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Supplementary/additional works business logic."""
from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from core.id_service import next_child_id
from repositories.db import get_connection

from .audit_service import audit

STATUSES = ("Draft","Submitted","Approved","Executed","Valued","Included","Paid")
FLOW = {"Draft":"Submitted","Submitted":"Approved","Approved":"Executed","Executed":"Valued","Valued":"Included","Included":"Paid"}

# شرح الدالة amount_for: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def amount_for(work: Mapping[str, Any]) -> float | None:
    mode = str(work.get("work_mode") or "Pending")
    if mode == "Measured":
        q, p = work.get("quantity"), work.get("unit_price")
        return None if q is None or p is None else max(0.0, float(q) * float(p))
    if mode == "Lump Sum":
        return None if work.get("lump_sum_amount") is None else max(0.0, float(work["lump_sum_amount"]))
    return None

# شرح الدالة list_supplementary: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def list_supplementary(project_id: str) -> list[dict[str, Any]]:
    conn=get_connection()
    try: return [dict(r) for r in conn.execute("SELECT * FROM supplementary_works WHERE project_id=? ORDER BY work_number",(project_id,)).fetchall()]
    finally: conn.close()

# شرح الدالة save_supplementary: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def save_supplementary(project_id: str, description: str, unit: str|None=None, quantity: float|None=None, unit_price: float|None=None, lump_sum_amount: float|None=None, work_mode: str="Pending", work_date: str|None=None, reason: str|None=None, reference_no: str|None=None, notes: str|None=None, supplementary_id: str|None=None) -> str:
    if not project_id or not description.strip(): raise ValueError("Project and description are required.")
    if work_mode not in ("Measured","Lump Sum","Pending"): raise ValueError("Invalid supplementary work mode.")
    if work_mode=="Measured" and (quantity is None or unit_price is None): raise ValueError("Quantity and unit price are required for measured work.")
    if work_mode=="Lump Sum" and lump_sum_amount is None: raise ValueError("Lump-sum amount is required.")
    conn=get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if not conn.execute("SELECT 1 FROM projects WHERE project_id=?",(project_id,)).fetchone(): raise ValueError("Project not found.")
        if supplementary_id:
            old=conn.execute("SELECT status FROM supplementary_works WHERE supplementary_id=? AND project_id=?",(supplementary_id,project_id)).fetchone()
            if not old: raise ValueError("Supplementary work not found.")
            if old["status"] not in ("Draft",): raise ValueError("Only Draft supplementary works can be edited.")
            sid=supplementary_id
            conn.execute("""UPDATE supplementary_works SET description=?,unit=?,quantity=?,unit_price=?,lump_sum_amount=?,work_mode=?,work_date=?,reason=?,reference_no=?,notes=?,updated_at=CURRENT_TIMESTAMP WHERE supplementary_id=?""",(description.strip(),unit or None,quantity,unit_price,lump_sum_amount,work_mode,work_date or datetime.now(timezone.utc).date().isoformat(),reason,reference_no,notes,sid))
        else:
            n=int(conn.execute("SELECT COALESCE(MAX(work_number),0)+1 FROM supplementary_works WHERE project_id=?",(project_id,)).fetchone()[0])
            sid=next_child_id(conn,"supp",project_id,digits=4)
            conn.execute("""INSERT INTO supplementary_works(supplementary_id,project_id,work_number,description,unit,quantity,unit_price,lump_sum_amount,work_mode,work_date,reason,reference_no,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",(sid,project_id,n,description.strip(),unit or None,quantity,unit_price,lump_sum_amount,work_mode,work_date or datetime.now(timezone.utc).date().isoformat(),reason,reference_no,notes))
        audit("Created" if not supplementary_id else "Updated","Supplementary Work",sid,description.strip(),conn=conn)
        conn.commit(); return sid
    except (sqlite3.Error, ValueError, TypeError, OSError): conn.rollback(); raise
    finally: conn.close()

# شرح الدالة transition_supplementary: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def transition_supplementary(supplementary_id: str, target_status: str) -> None:
    conn=get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row=conn.execute("SELECT status FROM supplementary_works WHERE supplementary_id=?",(supplementary_id,)).fetchone()
        if not row: raise ValueError("Supplementary work not found.")
        if FLOW.get(row["status"])!=target_status: raise ValueError(f"Invalid transition from {row['status']} to {target_status}.")
        if target_status in ("Valued","Included"):
            w=conn.execute("SELECT * FROM supplementary_works WHERE supplementary_id=?",(supplementary_id,)).fetchone()
            if amount_for(w) is None: raise ValueError("This supplementary work still needs a quantity/unit price or lump-sum valuation.")
        conn.execute("UPDATE supplementary_works SET status=?,updated_at=CURRENT_TIMESTAMP WHERE supplementary_id=?",(target_status,supplementary_id)); conn.commit()
    except (sqlite3.Error, ValueError, TypeError, OSError): conn.rollback(); raise
    finally: conn.close()

# شرح الدالة project_supplementary_summary: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def project_supplementary_summary(project_id: str) -> dict[str,Any]:
    rows=list_supplementary(project_id)
    valued=sum(amount_for(r) or 0 for r in rows if r["status"] in ("Approved","Executed","Valued","Included","Paid"))
    pending=sum(1 for r in rows if amount_for(r) is None)
    included=sum(amount_for(r) or 0 for r in rows if r["status"] in ("Included","Paid"))
    return {"count":len(rows),"valued":valued,"included":included,"pending_valuation":pending,"rows":rows}

# شرح الدالة include_approved_in_situation: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def include_approved_in_situation(situation_id: str) -> int:
    """Attach all valued/approved supplementary works to a draft situation."""
    conn=get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        s=conn.execute("SELECT project_id,status FROM situations WHERE situation_id=?",(situation_id,)).fetchone()
        if not s: raise ValueError("Situation not found.")
        if s["status"]!="Draft": raise ValueError("Only a Draft situation can receive supplementary works.")
        rows=conn.execute("SELECT * FROM supplementary_works WHERE project_id=? AND status IN ('Approved','Executed','Valued') ORDER BY work_number",(s["project_id"],)).fetchall()
        count=0
        for r in rows:
            amt=amount_for(dict(r))
            if amt is None: continue
            q=float(r["quantity"] or 0) if r["work_mode"]=="Measured" else 1.0
            conn.execute("INSERT OR REPLACE INTO supplementary_situation_items(supplementary_situation_item_id,situation_id,supplementary_id,executed_quantity,amount) VALUES(?,?,?,?,?)",(next_child_id(conn,"ssitem",situation_id,digits=4),situation_id,r["supplementary_id"],q,amt))
            conn.execute("UPDATE supplementary_works SET status='Included',updated_at=CURRENT_TIMESTAMP WHERE supplementary_id=?",(r["supplementary_id"],)); count+=1
        conn.commit(); return count
    except (sqlite3.Error, ValueError, TypeError, OSError): conn.rollback(); raise
    finally: conn.close()

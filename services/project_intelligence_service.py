# ============================================================
# شرح الملف: services/project_intelligence_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Unified construction intelligence and controlled project closeout checks."""
from __future__ import annotations

import sqlite3
from typing import Any

from repositories.db import get_connection

from .analytics_service import project_smart_analytics
from .supplementary_service import project_supplementary_summary


# شرح الدالة _f: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _f(v):
    try: return float(v or 0)
    except (TypeError, ValueError): return 0.0


# شرح الدالة client_payment_risk: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def client_payment_risk(project_id: str) -> dict[str, Any]:
    """Calculate collection exposure using earned value and received payments."""
    conn = get_connection()
    try:
        m = project_smart_analytics(project_id)
        received = _f(m.get("received")); earned = _f(m.get("earned")); receivable = max(0.0, earned-received)
        rate = received/earned*100 if earned else 100.0
        age_days = int(conn.execute("SELECT COALESCE(MAX(CAST(julianday('now')-julianday(situation_date) AS INTEGER)),0) FROM situations WHERE project_id=? AND status IN ('Approved','Paid')", (project_id,)).fetchone()[0] or 0)
        if receivable <= 0: level = "Low"
        elif rate < 35 or age_days > 90: level = "Critical"
        elif rate < 60 or age_days > 60: level = "High"
        elif rate < 80 or age_days > 30: level = "Medium"
        else: level = "Low"
        return {"earned":earned,"received":received,"receivable":receivable,"collection_rate":rate,"aging_days":age_days,"risk":level}
    finally: conn.close()


# شرح الدالة workforce_intelligence: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def workforce_intelligence(project_id: str) -> dict[str, Any]:
    """Reconcile attendance, payroll and site labor without creating a second source of truth."""
    conn = get_connection()
    try:
# شرح الدالة one: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
        def one(sql): return _f(conn.execute(sql,(project_id,)).fetchone()[0])
        attendance = one("SELECT COALESCE(SUM(working_hours),0) FROM attendance WHERE project_id=?")
        overtime = one("SELECT COALESCE(SUM(overtime_hours),0) FROM attendance WHERE project_id=?")
        labor = one("SELECT COALESCE(SUM(amount),0) FROM labor_allocations WHERE project_id=?")
        allocated = one("SELECT COALESCE(SUM(allocated_hours),0) FROM labor_allocations WHERE project_id=?")
        return {"attendance_hours":attendance,"overtime_hours":overtime,"labor_cost":labor,"payroll_allocated_hours":allocated,"hours_gap":max(0,attendance-allocated),"status":"Reconcile" if attendance>allocated+0.01 else "Aligned"}
    except (sqlite3.Error, TypeError, ValueError):
        return {"attendance_hours":0,"overtime_hours":0,"labor_cost":0,"payroll_allocated_hours":0,"hours_gap":0,"status":"Unavailable"}
    finally: conn.close()


# شرح الدالة material_intelligence: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def material_intelligence(project_id: str) -> dict[str, Any]:
    """Compare material consumption cost against recorded quantities and flag abnormal intensity."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT COALESCE(SUM(quantity),0),COALESCE(SUM(quantity*unit_cost),0) FROM material_movements WHERE project_id=? AND movement_type='Consumption'", (project_id,)).fetchone()
        qty,cost=_f(row[0]),_f(row[1]); m=project_smart_analytics(project_id); baseline=_f(m.get("material_cost"))
        variance = cost-baseline if baseline else 0.0
        return {"consumption_quantity":qty,"consumption_cost":cost,"analytics_material_cost":baseline,"cost_variance":variance,"status":"Review" if baseline and cost>baseline*1.15 else "Normal"}
    finally: conn.close()


# شرح الدالة vehicle_intelligence: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def vehicle_intelligence(project_id: str) -> dict[str, Any]:
    """Return fleet fuel and maintenance intensity for the project."""
    conn=get_connection()
    try:
        fuel=conn.execute("SELECT COALESCE(SUM(total_cost),0),COALESCE(SUM(quantity),0),MIN(mileage),MAX(mileage) FROM fuel_records WHERE project_id=?",(project_id,)).fetchone()
        maint=_f(conn.execute("SELECT COALESCE(SUM(cost),0) FROM maintenance_records WHERE project_id=?",(project_id,)).fetchone()[0])
        fuel_cost,fuel_qty=_f(fuel[0]),_f(fuel[1]); start,end=fuel[2],fuel[3]
        km=max(0,_f(end)-_f(start)) if start is not None and end is not None else 0
        total=fuel_cost+maint; per_km=total/km if km else 0
        return {"fuel_cost":fuel_cost,"fuel_quantity":fuel_qty,"maintenance_cost":maint,"km":km,"cost_per_km":per_km,"total_operating_cost":total,"status":"Review" if per_km and per_km>100 else "Normal"}
    finally: conn.close()


# شرح الدالة document_compliance: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def document_compliance(project_id: str) -> dict[str, Any]:
    """Check project document presence and expiry without assuming a fixed document taxonomy."""
    conn=get_connection()
    try:
        total=int(conn.execute("SELECT COUNT(*) FROM documents WHERE owner_type='project' AND owner_id=?",(project_id,)).fetchone()[0] or 0)
        expired=int(conn.execute("SELECT COUNT(*) FROM documents WHERE owner_type='project' AND owner_id=? AND expiry_date IS NOT NULL AND date(expiry_date)<date('now')",(project_id,)).fetchone()[0] or 0)
        soon=int(conn.execute("SELECT COUNT(*) FROM documents WHERE owner_type='project' AND owner_id=? AND expiry_date IS NOT NULL AND date(expiry_date) BETWEEN date('now') AND date('now','+30 day')",(project_id,)).fetchone()[0] or 0)
        return {"total":total,"expired":expired,"expiring_30d":soon,"status":"Critical" if expired else ("Watch" if soon else "Complete")}
    finally: conn.close()


# شرح الدالة unified_project_intelligence: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def unified_project_intelligence(project_id: str) -> dict[str, Any]:
    """Fuse financial, contractual, workforce, material, fleet and document signals."""
    m=project_smart_analytics(project_id); supp=project_supplementary_summary(project_id)
    pay=client_payment_risk(project_id); workforce=workforce_intelligence(project_id); material=material_intelligence(project_id); vehicle=vehicle_intelligence(project_id); docs=document_compliance(project_id)
    risks=[]; actions=[]
    if m.get("cost_pct",0)-m.get("progress",0)>15: risks.append("Cost consumption is materially ahead of physical progress."); actions.append("Review productivity, materials and uncontrolled site costs.")
    if pay["risk"] in {"High","Critical"}: risks.append(f"Client collection risk is {pay['risk']}."); actions.append("Follow up outstanding client receivables before increasing exposure.")
    if workforce["status"]=="Reconcile": risks.append("Attendance hours exceed allocated payroll hours."); actions.append("Reconcile labor allocation before relying on labor cost analytics.")
    if material["status"]=="Review": risks.append("Material consumption cost is unusually high versus the recorded material cost baseline."); actions.append("Review material issues, waste and approved variations.")
    if vehicle["status"]=="Review": risks.append("Vehicle operating cost per kilometre is unusually high."); actions.append("Review fuel records, mileage and maintenance.")
    if docs["status"]!="Complete": risks.append(f"Project documents: {docs['expired']} expired, {docs['expiring_30d']} expiring within 30 days."); actions.append("Renew or complete project documents.")
    if supp.get("pending",0): risks.append(f"{supp['pending']} supplementary work(s) still need valuation/inclusion."); actions.append("Value and include approved supplementary works in the next situation.")
    return {"metrics":m,"payment_risk":pay,"workforce":workforce,"materials":material,"vehicles":vehicle,"documents":docs,"supplementary":supp,"risks":risks,"actions":actions,"overall":"Critical" if len(risks)>=3 or m.get('health')=='Critical' else ('Watch' if risks else 'Healthy')}


# شرح الدالة project_closeout_checklist: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def project_closeout_checklist(project_id: str) -> dict[str, Any]:
    """Build a final reconciliation checklist before a project can be closed."""
    conn=get_connection()
    try:
        checks=[]
# شرح الدالة add: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
        def add(name, ok, detail, blocking=True): checks.append({"name":name,"ok":bool(ok),"detail":detail,"blocking":blocking})
        boq=conn.execute("SELECT COUNT(*),SUM(CASE WHEN COALESCE((SELECT SUM(si.executed_quantity) FROM situation_items si JOIN situations s ON s.situation_id=si.situation_id WHERE si.item_id=m.item_id AND s.project_id=?),0)+0.0005 < m.quantity THEN 1 ELSE 0 END) FROM metre_items m WHERE m.project_id=?",(project_id,project_id)).fetchone()
        add("BOQ quantities reconciled", int(boq[0] or 0)>0 and int(boq[1] or 0)==0, f"{int(boq[1] or 0)} item(s) still have unexecuted quantity.")
        sit=conn.execute("SELECT COUNT(*),SUM(CASE WHEN status NOT IN ('Approved','Paid') THEN 1 ELSE 0 END) FROM situations WHERE project_id=?",(project_id,)).fetchone()
        add("All situations approved or paid", int(sit[0] or 0)>0 and int(sit[1] or 0)==0, f"{int(sit[1] or 0)} unfinished situation(s).")
        sp=project_supplementary_summary(project_id)
        add("Supplementary works valued and included", sp.get("pending",0)==0 and sp.get("unvalued",0)==0, f"{sp.get('pending',0)} pending, {sp.get('unvalued',0)} unvalued.")
        unlinked=int(conn.execute("SELECT COUNT(*) FROM expenses WHERE project_id=? AND (description IS NULL OR TRIM(description)='')",(project_id,)).fetchone()[0] or 0)
        add("Project expenses identifiable",unlinked==0,f"{unlinked} expense(s) have no description.")
        docs=document_compliance(project_id); add("Project documents complete",docs["expired"]==0, f"{docs['expired']} expired document(s); {docs['expiring_30d']} expiring soon.",False)
        rec=client_payment_risk(project_id); add("Client receivable reconciled",True,f"Outstanding earned receivable: {rec['receivable']:,.2f}",False)
        add("Labor reconciliation",workforce_intelligence(project_id)["status"]!="Reconcile", "Attendance and allocated payroll hours are aligned.")
        blocking=[c for c in checks if c["blocking"] and not c["ok"]]
        return {"project_id":project_id,"checks":checks,"ready":not blocking,"blocking_count":len(blocking),"financial":project_smart_analytics(project_id)}
    finally: conn.close()

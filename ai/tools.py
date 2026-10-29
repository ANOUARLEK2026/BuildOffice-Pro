# ============================================================
# شرح الملف: ai/tools.py
# أدوات قراءة آمنة تستخدم خدمات BuildOffice الحالية كمصدر للحقيقة.
# لا توجد هنا عمليات كتابة أو حذف أو تعديل لقاعدة البيانات.
# ============================================================
from __future__ import annotations

from repositories.db import get_connection
from services.analytics_service import smart_analytics


def projects() -> list[dict]: return list(smart_analytics().get("projects", []))
def project(project_id: str) -> dict | None:
    try:
        from services.project_intelligence_service import unified_project_intelligence
        return unified_project_intelligence(project_id)
    except (KeyError, TypeError, ValueError, RuntimeError):
        return None
def company_summary() -> dict:
    conn = get_connection()
    try:
        p=conn.execute("SELECT COUNT(*) c, COALESCE(SUM(budget_ht),0) budget FROM projects").fetchone()
        e=conn.execute("SELECT COALESCE(SUM(amount),0) total FROM expenses").fetchone()
        s=conn.execute("SELECT COUNT(*) c FROM staff").fetchone(); v=conn.execute("SELECT COUNT(*) c FROM vehicles").fetchone()
        return {"projects":int(p[0]),"budget":float(p[1] or 0),"expenses":float(e[0] or 0),"staff":int(s[0]),"vehicles":int(v[0])}
    finally: conn.close()
def portfolio_health() -> list[dict]:
    keys=("project_id","project_name","health","health_score","progress","cost_pct","cpi","spi","actual_cost","budget","margin")
    return [{k:p.get(k) for k in keys} for p in projects()]
def expense_rows(limit:int=10)->list[dict]: return sorted(projects(),key=lambda p:float(p.get("expense_cost",0) or 0),reverse=True)[:limit]

def debts() -> list[dict]:
    conn=get_connection()
    try:
        rows=conn.execute("SELECT debt_id, project_id, lender, amount, status, notes FROM debt ORDER BY amount DESC").fetchall()
        return [dict(r) for r in rows]
    finally: conn.close()

def workforce_summary() -> dict:
    conn=get_connection()
    try:
        a=conn.execute("SELECT COALESCE(SUM(working_hours),0) h, COALESCE(SUM(overtime_hours),0) ot FROM attendance").fetchone()
        l=conn.execute("SELECT COALESCE(SUM(hours),0) h, COALESCE(SUM(overtime_hours),0) ot FROM labor_allocations").fetchone()
        return {"attendance_hours":float(a[0] or 0),"attendance_overtime":float(a[1] or 0),"allocated_hours":float(l[0] or 0),"allocated_overtime":float(l[1] or 0),"gap_hours":float(a[0] or 0)-float(l[0] or 0)}
    finally: conn.close()

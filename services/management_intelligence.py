# ============================================================
# شرح الملف: services/management_intelligence.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Cross-module management intelligence: alerts, reconciliation, forecasting and what-if analysis."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from repositories.db import get_connection

from .analytics_service import project_smart_analytics, smart_analytics
from .settings_service import (
    alert_collection_rate,
    alert_cost_progress_gap,
    alert_document_days,
    alert_progress_gap,
    setting_bool,
)


# شرح الدالة _f: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _f(v):
    try:return float(v or 0)
    except (TypeError, ValueError):return 0.0

# شرح الدالة alerts: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def alerts(conn=None):
    own=conn is None; conn=conn or get_connection(); out=[]
    if not setting_bool("intelligence_enabled", True):
        return out
    document_days = alert_document_days()
    progress_gap = alert_progress_gap()
    collection_threshold = alert_collection_rate() / 100.0
    cost_progress_gap = alert_cost_progress_gap()
    try:
        # Data integrity
        checks=[
            ("Duplicate expenses","SELECT COUNT(*) FROM (SELECT project_id,description,amount,expense_date,COUNT(*) c FROM expenses GROUP BY project_id,description,amount,expense_date HAVING c>1)","HIGH"),
            ("Payments above project earned value","SELECT COUNT(*) FROM (SELECT p.project_id,COALESCE(SUM(p.amount),0) paid,COALESCE((SELECT SUM(amount) FROM (SELECT si.amount AS amount FROM situation_items si JOIN situations s ON s.situation_id=si.situation_id WHERE s.project_id=p.project_id AND s.status IN ('Submitted','Approved','Paid') UNION ALL SELECT ssi.amount AS amount FROM supplementary_situation_items ssi JOIN situations s ON s.situation_id=ssi.situation_id WHERE s.project_id=p.project_id AND s.status IN ('Submitted','Approved','Paid'))),0) earned FROM project_payments p GROUP BY p.project_id HAVING paid>earned+0.01)","HIGH"),
            ("BOQ quantity overruns","SELECT COUNT(*) FROM (SELECT m.item_id,m.quantity,COALESCE(SUM(si.executed_quantity),0) x FROM metre_items m LEFT JOIN situation_items si ON si.item_id=m.item_id GROUP BY m.item_id HAVING x>quantity+0.001)","HIGH"),
            ("Unvalued supplementary works","SELECT COUNT(*) FROM supplementary_works WHERE work_mode='Pending' OR (work_mode='Measured' AND (quantity IS NULL OR unit_price IS NULL)) OR (work_mode='Lump Sum' AND lump_sum_amount IS NULL)","MEDIUM"),
            ("Documents expiring soon",f"SELECT COUNT(*) FROM documents WHERE expiry_date IS NOT NULL AND date(expiry_date)<=date('now','+{document_days} day')","MEDIUM"),
        ]
        for title,sql,severity in checks:
            try:
                n=int(conn.execute(sql).fetchone()[0] or 0)
                if n: out.append({"severity":severity,"title":title,"count":n})
            except sqlite3.Error: pass
        # Project intelligence
        data=smart_analytics(conn)
        for r in data.get("risks",[])[:20]: out.append({"severity":r["severity"],"title":r["project_name"],"count":1,"message":r["message"]})
        # Schedule risk and client aging
        for m in data.get("projects",[]):
            if m["status"]=="Active" and m["planned_progress"]>m["progress"]+progress_gap: out.append({"severity":"HIGH","title":m["project_name"],"count":1,"message":"Physical progress is materially behind elapsed schedule."})
            if m["receivable"]>0 and m["earned"]>0 and m["received"]/m["earned"]<collection_threshold: out.append({"severity":"MEDIUM","title":m["project_name"],"count":1,"message":"Client collection is below the configured risk threshold."})
            if m["progress"]>0 and m["cost_pct"]-m["progress"]>cost_progress_gap: out.append({"severity":"HIGH","title":m["project_name"],"count":1,"message":"Cost consumption is ahead of physical progress beyond the configured threshold."})
        return out
    finally:
        if own: conn.close()

# شرح الدالة reconciliation: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def reconciliation(project_id: str|None=None)->dict[str,Any]:
    conn=get_connection()
    try:
        params=(project_id,) if project_id else ()
        checks=[]
# شرح الدالة q: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
        def q(sql,ps=()):
            try:return int(conn.execute(sql,ps).fetchone()[0] or 0)
            except (sqlite3.Error, TypeError, ValueError):return 0
        checks.append(("Expenses without project",q("SELECT COUNT(*) FROM expenses WHERE project_id IS NULL OR TRIM(project_id)=''")))
        checks.append(("Payroll without attendance source",q("SELECT COUNT(*) FROM payroll_records WHERE COALESCE(attendance_hours,0)>0 AND COALESCE(allocated_hours,0)=0")))
        checks.append(("Unvalued supplementary works",q("SELECT COUNT(*) FROM supplementary_works WHERE project_id IS NOT NULL AND (work_mode='Pending' OR (work_mode='Measured' AND (quantity IS NULL OR unit_price IS NULL)) OR (work_mode='Lump Sum' AND lump_sum_amount IS NULL))",params)))
        return {"issues":[{"name":n,"count":c} for n,c in checks if c],"ok":not any(c for _,c in checks)}
    finally:conn.close()

# شرح الدالة cash_flow_forecast: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def cash_flow_forecast(days:int=30)->dict[str,Any]:
    conn=get_connection()
    try:
        received=_f(conn.execute("SELECT COALESCE(SUM(amount),0) FROM project_payments").fetchone()[0]); expenses=_f(conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]); paid=_f(conn.execute("SELECT COALESCE(SUM(amount),0) FROM expense_payments").fetchone()[0]);
        outstanding=max(0, _f(conn.execute("SELECT COALESCE(SUM(net_due),0) FROM situations WHERE status IN ('Approved','Paid')").fetchone()[0])-received)
        unpaid=max(0,expenses-paid); daily=max(expenses/90,0)
        return {"received":received,"receivable":outstanding,"payable":unpaid,"estimated_daily_outflow":daily,"forecast_outflow":daily*days,"projected_net":outstanding-unpaid-daily*days,"days":days}
    finally:conn.close()

# شرح الدالة what_if: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def what_if(project_id:str, material_pct:float=0, delay_days:int=0, labor_pct:float=0)->dict[str,Any]:
    m=project_smart_analytics(project_id)
    extra_material=m.get("material_cost",0)*material_pct/100; extra_labor=m.get("labor_cost",0)*labor_pct/100
    daily=m.get("actual_cost",0)/max(1,m.get("days_elapsed",0)); delay_cost=daily*max(0,delay_days)
    forecast=m.get("eac",m.get("actual_cost",0))+extra_material+extra_labor+delay_cost
    budget=m.get("budget",0)
    return {"project_id":project_id,"baseline_eac":m.get("eac",0),"extra_material":extra_material,"extra_labor":extra_labor,"delay_cost":delay_cost,"forecast_cost":forecast,"forecast_variance":forecast-budget,"forecast_margin":m.get("earned",0)-forecast}

# شرح الدالة management_snapshot: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def management_snapshot()->dict[str,Any]:
    conn=get_connection()
    try:
        data=smart_analytics(conn); return {"analytics":data,"alerts":alerts(conn),"reconciliation":reconciliation(),"cash_flow":cash_flow_forecast(),"generated_at":datetime.now(timezone.utc).date().isoformat()}
    finally:conn.close()

# شرح الدالة save_snapshot: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def save_snapshot(payload:dict[str,Any],scope="portfolio",project_id=None):
    conn=get_connection()
    try:
        conn.execute("INSERT INTO intelligence_snapshots(scope,project_id,payload_json) VALUES(?,?,?)",(scope,project_id,json.dumps(payload,ensure_ascii=False,default=str)));conn.commit()
    finally:conn.close()

# شرح الدالة generate_management_report: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def generate_management_report(output_path: str|None=None):
    """Create a management report from the same live intelligence sources used by the UI."""
    from datetime import datetime
    from pathlib import Path

    from openpyxl import Workbook
    data=management_snapshot(); path=Path(output_path) if output_path else Path("reports")/f"Management_Report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xlsx"; path.parent.mkdir(parents=True,exist_ok=True)
    try:
        wb = Workbook()
        ws = wb.active

        if ws is None:
            ws = wb.create_sheet("Management")
        else:
            ws.title = "Management"

        ws.append(["BuildOffice Pro - Management Report"])
        ws.append(["Generated", data["generated_at"]])
        ws.append([])

        p = data["analytics"]["portfolio"]

        ws.append(["Portfolio Budget", p["portfolio_budget"]])
        ws.append(["Portfolio Cost", p["portfolio_cost"]])
        ws.append(["Forecast EAC", p["portfolio_eac"]])
        ws.append(["Receivable", p["receivable"]])
        ws.append(["Payable", p["payable"]])
        ws.append(["CPI", p["portfolio_cpi"]])
        ws.append([])

        ws.append(["Severity", "Area", "Count", "Message"])

        for a in data["alerts"]:
            ws.append([
                a.get("severity"),
                a.get("title"),
                a.get("count"),
                a.get("message", ""),
            ])

        widths = {
            "A": 16,
            "B": 34,
            "C": 12,
            "D": 70,
        }

        for col, width in widths.items():
            ws.column_dimensions[col].width = width

        wb.save(path)
        return path
    except ImportError as exc: raise RuntimeError("Management report requires openpyxl.") from exc

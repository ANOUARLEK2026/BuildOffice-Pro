# ============================================================
# شرح الملف: ai/assistant.py
# طبقة المساعد المحلي الخفيف. البيانات والحسابات تأتي من خدمات التطبيق.
# ============================================================
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.management_intelligence import alerts, cash_flow_forecast
from services.settings_service import money_display

from . import tools
from .intent_router import QueryIntent, route_query


@dataclass
class AssistantResult:
    title:str; answer:str; rows:list[dict[str,Any]]; intent:str; project_id:str|None=None; open_page:str|None=None; confidence:float=0.0
class BuildOfficeAssistant:
    def __init__(self, project_id:str|None=None): self.project_id=project_id
    def ask(self,question:str)->AssistantResult:
        i=route_query(question); pid=i.project_id or self.project_id
        if i.name=="GENERAL": return self._help(i)
        if i.name=="LOSING_PROJECTS":
            rows=[p for p in tools.projects() if float(p.get("margin",0) or 0)<0]
            return self._result("Losing projects",f"{len(rows)} project(s) have a negative indicative margin.",rows,i,"Management Intelligence")
        if i.name=="TOP_EXPENSES":
            rows=tools.expense_rows(); return self._result("Highest project expenses","Projects ranked by recorded direct expense cost.",rows,i,"Expenses")
        if i.name=="ALERTS":
            rows=alerts(); return self._result("Management alerts",f"{len(rows)} actionable alert(s) are currently reported.",rows,i,"Management Intelligence")
        if i.name=="DEBTS":
            rows=tools.debts(); total=sum(float(r.get("amount",0) or 0) for r in rows); return self._result("Debt exposure",f"Recorded debt exposure is {money_display(total)} across {len(rows)} debt record(s).",rows,i,"Debts")
        if i.name=="WORKFORCE" and not pid:
            w=tools.workforce_summary(); return self._result("Workforce overview",f"Attendance hours: {w["attendance_hours"]:.1f}; allocated hours: {w["allocated_hours"]:.1f}; reconciliation gap: {w["gap_hours"]:.1f} hours.",[w],i,"Attendance")
        if i.name=="CASH_FLOW":
            c=cash_flow_forecast(); ans=f"Projected net position over {c['days']} days: {money_display(c['projected_net'])}. Receivable: {money_display(c['receivable'])}. Payable: {money_display(c['payable'])}."
            return self._result("Cash-flow forecast",ans,[c],i,"Financial Reports")
        if i.name=="COMPANY_SUMMARY":
            c=tools.company_summary(); ans=f"The company has {c['projects']} project(s), {c['staff']} staff record(s) and {c['vehicles']} vehicle record(s). Total project budget HT is {money_display(c['budget'])}; recorded expenses are {money_display(c['expenses'])}."
            return self._result("Company overview",ans,[c],i,"Company")
        if i.name=="PROJECT_PORTFOLIO":
            rows=sorted(tools.portfolio_health(),key=lambda r:float(r.get("health_score",100) or 0)); return self._result("Project portfolio health","Projects are ranked from the lowest health score upward.",rows,i,"Project Control Center")
        if pid:
            data=tools.project(pid)
            if data: return self._project_result(data,i)
        return self._result("BuildOffice AI",self._not_found(pid),[],i,None)
    def _project_result(self,d:dict,i:QueryIntent)->AssistantResult:
        m=d.get("metrics",{}); p=d.get("payment_risk",{}); w=d.get("workforce",{})
        if i.name=="PROJECT_FINANCIAL":
            ans=f"{m.get('project_name','')}: budget {money_display(m.get('budget',0))}, controlled cost {money_display(m.get('actual_cost',0))}, cost consumption {m.get('cost_pct',0):.1f}%, CPI {m.get('cpi',0):.2f}, indicative earned margin {money_display(m.get('earned_margin',0))}."
            return self._result("Project financial analysis",ans,[m],i,"Project Control Center")
        if i.name=="PROJECT_PROGRESS":
            ans=f"{m.get('project_name','')}: physical progress {m.get('progress',0):.1f}%, SPI {m.get('spi',0):.2f}, earned value {money_display(m.get('earned',0))}, estimated remaining cost {money_display(m.get('etc',0))}."
            return self._result("Project progress",ans,[m],i,"Progress / Situations")
        if i.name=="WORKFORCE":
            ans=f"{m.get('project_name','')}: workforce status {w.get('status','Unknown')}. Attendance hours {w.get('attendance_hours',0):.1f}; allocated hours {w.get('allocated_hours',0):.1f}; reconciliation gap {w.get('gap',0):.1f} hours."
            return self._result("Workforce intelligence",ans,[w],i,"Attendance")
        if i.name=="RECEIVABLES":
            ans=f"{m.get('project_name','')}: received {money_display(p.get('received',0))}, receivable {money_display(p.get('receivable',0))}, collection rate {p.get('collection_rate',0):.1f}%."
            return self._result("Project collection",ans,[p],i,"Income / Payments")
        if i.name=="VEHICLES": return self._result("Project vehicle intelligence",str(d.get('vehicles',{}).get('status','No vehicle status available.')),[d.get('vehicles',{})],i,"Vehicles")
        if i.name=="DOCUMENTS": return self._result("Project document compliance",str(d.get('documents',{}).get('status','No document status available.')),[d.get('documents',{})],i,"Documents")
        if i.name=="MATERIALS": return self._result("Project materials",str(d.get('materials',{}).get('status','No material status available.')),[d.get('materials',{})],i,"Métré")
        risks=d.get('risks',[]); actions=d.get('actions',[]); ans=f"{m.get('project_name','')}: overall status {d.get('overall','Unknown')}, health {m.get('health_score',0):.0f}/100, progress {m.get('progress',0):.1f}%, cost {m.get('cost_pct',0):.1f}%."
        if risks: ans+=" Main risks: "+" | ".join(map(str,risks[:3]))
        if actions: ans+=" Recommended: "+" | ".join(map(str,actions[:2]))
        return self._result("Project health",ans,[m],i,"Project Control Center")
    def _help(self,i): return AssistantResult("BuildOffice AI","Try asking about projects, expenses, progress, workforce, receivables, debts, vehicles, documents, materials, cash flow, alerts, or company overview.",[],i.name,i.project_id,"Management Intelligence",i.confidence)
    def _not_found(self,pid): return f"I could not find enough information for {pid}. Select a project or include a project ID such as PRG-007." if pid else "I could not identify the requested subject. Include a project ID such as PRG-007 or ask about expenses, progress, workforce, cash flow, or alerts."
    def _result(self,title,answer,rows,i,page): return AssistantResult(title,answer,rows,i.name,i.project_id,page,i.confidence)

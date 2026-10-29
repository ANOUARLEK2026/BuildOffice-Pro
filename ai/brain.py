# ============================================================
# BuildOffice Pro program-wide AI brain.
# Read-only reasoning over program knowledge + live application data.
# ============================================================
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from services.management_intelligence import alerts, cash_flow_forecast
from services.settings_service import money_display

from . import tools
from .intent_router import route_query
from .parameters import parse_parameters
from .program_knowledge import ProgramKnowledge, normalize
from .program_qa import ProgramQA


@dataclass
class AIResponse:
    title: str
    answer: str
    rows: list[dict[str,Any]] = field(default_factory=list)
    intent: str = 'GENERAL'
    project_id: str|None = None
    open_page: str|None = None
    confidence: float = 0.0
    insights: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    parameters: dict[str,Any] = field(default_factory=dict)
    followups: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class BuildOfficeBrain:
    def __init__(self, project_id: str|None=None):
        self.project_id=project_id
        self.knowledge=ProgramKnowledge()
        self.qa=ProgramQA(self.knowledge)
        self.history:list[str]=[]

    def ask(self, question: str) -> AIResponse:
        q=str(question or '').strip()
        if not q: return self._help()
        self.history.append(q)
        self.history=self.history[-12:]
        params=parse_parameters(q, context_project=self.project_id)
        route=route_query(q)
        pid=params.project_ids[0] if params.project_ids else route.project_id or self.project_id
        program_q=self._is_program_question(q) or params.compare
        # First-class program QA: answer broad natural-language questions from the indexed
        # application itself, instead of requiring a narrow keyword/intention match.
        r=self.qa.answer(q)
        if r:
            return AIResponse(
                title=r.get('title','BuildOffice Copilot'),
                answer=r.get('answer',''),
                rows=r.get('rows',[]),
                intent=r.get('intent','PROGRAM_QA'),
                project_id=pid,
                open_page=r.get('open_page'),
                confidence=float(r.get('confidence',.85)),
                evidence=r.get('evidence',[]),
                parameters=params.to_dict(),
                followups=r.get('followups',[]),
                warnings=r.get('warnings',[]),
            )
        if program_q:
            r=self._answer_program(q, params, pid)
            if r: return r
        # Multi-project comparisons must be resolved before single-project analysis.
        if params.compare and len(params.project_ids) >= 2:
            r=self._compare_projects(params.project_ids,params)
            if r: return r
        # Program + live data composite questions.
        if pid and self._asks_live_data(q):
            data=tools.project(pid)
            if data:
                r=self._project_analysis(data, q, params, route.name)
                r.evidence.append(f'Live project record: {pid}')
                return r
        # Existing management intelligence, now parameterized.
        if route.name in ('LOSING_PROJECTS','TOP_EXPENSES','PROJECT_PORTFOLIO','ALERTS','DEBTS','WORKFORCE','CASH_FLOW','COMPANY_SUMMARY') or params.compare or params.metric or params.limit or params.threshold is not None:
            r=self._live_global(q,params,route.name,pid)
            if r: return r
        if pid:
            data=tools.project(pid)
            if data: return self._project_analysis(data,q,params,route.name)
        return self._help()

    def _answer_program(self,q,params,pid):
        concept=self.knowledge.concept(q)
        if concept:
            return AIResponse('How BuildOffice Pro works',concept,intent='PROGRAM_ARCHITECTURE',confidence=.95,evidence=['BuildOffice Pro.py','core/database/services/repositories structure'],open_page='Settings')
        page=self.knowledge.page(q)
        table=self.knowledge.table(q)
        fn=self.knowledge.function(q)
        nq=normalize(q)
        # Explicit catalog questions should answer from the navigation manifest.
        if any(x in nq for x in ('what pages','which pages','list pages','all pages','pages in buildoffice','ما هي الصفحات','كل الصفحات','قائمة الصفحات')):
            rows=[{'order':i+1,'page':p['name'],'class':p['class'],'group':p['group']} for i,p in enumerate(self.knowledge.pages)]
            return AIResponse('BuildOffice pages',f'BuildOffice Pro has {len(rows)} navigable pages in the current program.',rows,intent='PROGRAM_PAGE_CATALOG',confidence=.99,evidence=['BuildOffice Pro.py MENU'])
        # Explicit database questions are resolved against real table names first.
        if any(x in nq for x in ('table stores','table store','table for','which table','database table','اي جدول','أي جدول')):
            if any(x in nq for x in ('expense','expenses','مصاريف','مصروف','صرف')):
                table=next((t for t in self.knowledge.tables if t['name']=='expenses'),table)
            elif any(x in nq for x in ('project','projects','مشروع','مشاريع')):
                table=next((t for t in self.knowledge.tables if t['name']=='projects'),table)
            elif any(x in nq for x in ('payment','payments','قبض','تحصيل')):
                table=next((t for t in self.knowledge.tables if t['name']=='project_payments'),table)
            if table:
                cols=', '.join(c['name'] for c in table['columns'])
                ans=f"The live SQLite table '{table['name']}' stores this data. It currently has {table['row_count']} rows. Columns: {cols}."
                return AIResponse('Database structure',ans,[{'table':table['name'],'rows':table['row_count'],'columns':cols}],intent='PROGRAM_DATABASE',confidence=.99,evidence=['database/schema.py','live buildoffice.db'])
        if page and any(x in normalize(q) for x in ('what','how','where','page','button','screen','صفحه','كيف','اين','أين','زر','شاشه')):
            e=self.knowledge.explain_page(page['name'])
            src=e.get('source') if e else None
            [] if not src else [x['name'] for x in src['functions']]
            methods=[] if not src else [m['name'] for c in src['classes'] for m in c['methods']][:18]
            ans=f"{page['name']} is implemented by {page['class']}. It belongs to {page['group']} and is loaded lazily by the main application navigation."
            if methods: ans+=f" Key methods include: {', '.join(methods[:10])}."
            return AIResponse(page['name'],ans,[{'page':page['name'],'class':page['class'],'group':page['group'],'source':src['path'] if src else ''}],intent='PROGRAM_PAGE',open_page=page['name'],confidence=.93,evidence=[page['class']+' source file'])
        if table and any(x in normalize(q) for x in ('table','column','database','schema','جدول','عمود','قاعدة','بيانات')):
            cols=', '.join(c['name'] for c in table['columns'])
            ans=f"SQLite table '{table['name']}' currently has {table['row_count']} rows. Columns: {cols}."
            if table.get('foreign_keys'): ans+=' Foreign keys: '+', '.join(f"{x.get('from')} → {x.get('table')}.{x.get('to')}" for x in table['foreign_keys'])+'.'
            return AIResponse('Database structure',ans,[{'table':table['name'],'rows':table['row_count'],'columns':cols}],intent='PROGRAM_DATABASE',confidence=.94,evidence=['database/schema.py','live buildoffice.db'])
        if fn and any(x in normalize(q) for x in ('function','method','code','source','def','داله','دالة','كود','مصدر')):
            f,file=fn
            return AIResponse('Code element',f"{f['name']} is defined in {file['path']} around line {f['line']}. {f.get('doc','') or 'It is a callable application component.'}",[{'file':file['path'],'function':f['name'],'line':f['line']}],intent='PROGRAM_CODE',confidence=.88,evidence=[file['path']])
        s=self.knowledge.settings_search(q)
        if s and any(x in normalize(q) for x in ('setting','settings','configuration','إعدادات','اعدادات')):
            return AIResponse('Application setting',f"I found {len(s)} matching setting(s).",s,intent='PROGRAM_SETTINGS',open_page='Settings',confidence=.86,evidence=['settings table'])
        results=self.knowledge.search(q,limit=8)
        if results:
            rows=[]
            for r in results:
                item=r['item']; rows.append({'kind':r['kind'],'score':r['score'],'name':item.get('name') or item.get('path') or item.get('table'),'detail':item.get('class') or item.get('group') or ''})
            return AIResponse('BuildOffice program knowledge',f"I found {len(results)} relevant program elements. The strongest match is {rows[0]['name']}.",rows,intent='PROGRAM_KNOWLEDGE',confidence=min(.94,.55+results[0]['score']*.4),evidence=['generated program knowledge index'],followups=['Explain the implementation of this element','Show the database table behind it','Tell me which page opens it'])
        return None

    def _live_global(self,q,p,route,pid):
        if route=='LOSING_PROJECTS' or (p.metric=='margin' and p.operator in ('<','below') and p.threshold is not None):
            rows=tools.projects(); threshold=p.threshold if p.threshold is not None else 0
            rows=[r for r in rows if float(r.get('margin',0) or 0)<threshold]
            return self._global('Projects at financial risk',rows,'margin','Projects with negative or below-threshold indicative margin.', 'Management Intelligence')
        if route=='TOP_EXPENSES' or p.metric in ('expense','cost'):
            rows=tools.projects(); rows=sorted(rows,key=lambda r:float(r.get('expense_cost',r.get('expenses',0)) or 0),reverse=p.sort_desc)
            n=p.limit or 10
            return self._global('Expense ranking',rows[:n],'expense_cost','Projects ranked by recorded direct expense cost.','Expenses')
        if route=='PROJECT_PORTFOLIO':
            rows=tools.portfolio_health(); rows=sorted(rows,key=lambda r:float(r.get('health_score',100) or 0),reverse=p.sort_desc)
            return self._global('Project portfolio health',rows[:(p.limit or 20)],'health_score','Portfolio health ranked from the live intelligence calculations.','Project Control Center')
        if route=='ALERTS':
            rows=alerts(); return self._global('Management alerts',rows,None,'Current actionable alerts generated by the application.','Management Intelligence')
        if route=='DEBTS':
            rows=tools.debts(); return self._global('Debt exposure',rows,'amount','Recorded company/project debt exposure.','Debts')
        if route=='WORKFORCE':
            return self._global('Workforce overview',[tools.workforce_summary()],None,'Attendance, allocation and reconciliation status.','Attendance')
        if route=='CASH_FLOW':
            c=cash_flow_forecast(); return AIResponse('Cash-flow forecast',f"Projected net position over {c['days']} days: {money_display(c['projected_net'])}. Receivable: {money_display(c['receivable'])}. Payable: {money_display(c['payable'])}.",[c],intent='CASH_FLOW',open_page='Financial Reports',confidence=.94,evidence=['services/management_intelligence.py','live SQLite data'])
        if route=='COMPANY_SUMMARY':
            c=tools.company_summary(); return AIResponse('Company overview',f"The live database contains {c['projects']} project(s), {c['staff']} staff record(s) and {c['vehicles']} vehicle record(s). Project budget HT: {money_display(c['budget'])}. Recorded expenses: {money_display(c['expenses'])}.",[c],intent='COMPANY_SUMMARY',open_page='Company',confidence=.94,evidence=['company info/settings/projects tables'])
        if p.compare and len(p.project_ids)>=2:
            return self._compare_projects(p.project_ids,p)
        return None

    def _project_analysis(self,d,q,p,route):
        m=d.get('metrics',{}); pid=(m.get('project_id') or p.project_ids[0]) if p.project_ids else self.project_id
        name=m.get('project_name') or pid or 'Project'
        qn=normalize(q)
        if any(x in qn for x in ('progress','tقدم','انجاز','متاخر','متاخره','late','schedule')) or route=='PROJECT_PROGRESS':
            ans=f"{name}: physical progress {m.get('progress',0):.1f}%, SPI {m.get('spi',0):.2f}, earned value {money_display(m.get('earned',0))}, ETC {money_display(m.get('etc',0))}."
            return AIResponse('Project progress',ans,[m],intent='PROJECT_PROGRESS',project_id=pid,open_page='Progress / Situations',confidence=.95,evidence=['project intelligence service','live project data'])
        if any(x in qn for x in ('financial','budget','cost','expense','profit','margin','ربح','ميزاني','تكلف','مصاريف','خساره','خسائر')) or route=='PROJECT_FINANCIAL':
            ans=f"{name}: budget HT {money_display(m.get('budget',0))}, controlled cost {money_display(m.get('actual_cost',0))}, cost consumption {m.get('cost_pct',0):.1f}%, CPI {m.get('cpi',0):.2f}, indicative earned margin {money_display(m.get('earned_margin',0))}."
            return AIResponse('Project financial analysis',ans,[m],intent='PROJECT_FINANCIAL',project_id=pid,open_page='Project Control Center',confidence=.95,evidence=['project_intelligence_service','live project data'])
        risks=d.get('risks',[]); actions=d.get('actions',[])
        ans=f"{name}: overall status {d.get('overall','Unknown')}, health {m.get('health_score',0):.0f}/100, progress {m.get('progress',0):.1f}%, cost consumption {m.get('cost_pct',0):.1f}%."
        if risks: ans+=' Main risks: '+' | '.join(map(str,risks[:4]))+'.'
        if actions: ans+=' Recommended actions: '+' | '.join(map(str,actions[:3]))+'.'
        return AIResponse('Project health',ans,[m],intent='PROJECT_HEALTH',project_id=pid,open_page='Project Control Center',confidence=.94,insights=[str(x) for x in risks[:5]],recommendations=[str(x) for x in actions[:5]],evidence=['services/project_intelligence_service.py','live project data'])

    def _compare_projects(self,ids,p):
        rows=[]
        for pid in ids:
            d=tools.project(pid)
            if d: rows.append(d.get('metrics',{}))
        if not rows: return None
        metric=p.metric or 'health_score'
        key={'cost':'actual_cost','expense':'actual_cost','progress':'progress','margin':'earned_margin','health':'health_score','cpi':'cpi','spi':'spi'}.get(metric,metric)
        rows.sort(key=lambda r:float(r.get(key,0) or 0),reverse=p.sort_desc)
        ans='; '.join(f"{r.get('project_id')}: {key}={r.get(key,0)}" for r in rows)
        return AIResponse('Project comparison',ans,rows,intent='PROJECT_COMPARISON',open_page='Project Control Center',confidence=.93,evidence=['live project intelligence'])

    def _global(self,title,rows,key,desc,page):
        if key: rows=sorted(rows,key=lambda r:float(r.get(key,0) or 0),reverse=True)
        return AIResponse(title,desc,rows,intent='LIVE_ANALYTICS',open_page=page,confidence=.93,evidence=['live SQLite data','existing BuildOffice analytics'])

    def _is_program_question(self,q):
        n=normalize(q)
        triggers=['how does','how do','where is','what does','what is this','which file','which table','source code','function','button','field','page','database','sqlite','schema','setting','theme','translation','error','traceback','connected','connection','linked','relationship','كيف','اين','أين','ما هو','ماذا','زر','حقل','صفحه','قاعدة','جدول','كود','خطأ']
        return any(t in n for t in triggers)

    def _asks_live_data(self,q):
        n=normalize(q); return bool(re.search(r'prg[-_ ]?\d+',n)) or any(x in n for x in ('project','مشروع','budget','expense','cost','progress','payment','debt','attendance','risk','health','ربح','مصاريف','انجاز'))

    def _help(self):
        return AIResponse('BuildOffice Copilot','I can now reason about the whole BuildOffice program: pages, navigation, UI elements, source files and functions, SQLite tables/columns, settings, translations, workflows, plus live project and management data.',intent='GENERAL',confidence=.9,followups=['Explain how Projects, Expenses and Payments are connected','Which database table stores project expenses?','What does the Project Control Center calculate?'])

BuildOfficeAssistant = BuildOfficeBrain

# ============================================================
# شرح الملف: services/natural_query_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Safe, deterministic natural-language management queries."""
from __future__ import annotations

from .analytics_service import smart_analytics
from .management_intelligence import alerts, cash_flow_forecast


# شرح الدالة answer: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def answer(query:str)->dict:
    q=(query or '').strip().lower(); data=smart_analytics(); projects=data.get('projects',[])
    if any(x in q for x in ('losing','loss','خاسر','خسارة')):
        rows=[p for p in projects if p['margin']<0]; return {'title':'Projects losing money','rows':rows,'answer':f'{len(rows)} project(s) currently have negative indicative margin.'}
    if any(x in q for x in ('owe','receivable','debt','مدين','مستحق')):
        rows=sorted(projects,key=lambda p:p['receivable'],reverse=True); return {'title':'Receivables by project','rows':rows,'answer':f"Total receivables: {data['receivable']:,.2f}"}
    if 'most' in q and ('expense' in q or 'spend' in q):
        rows=sorted(projects,key=lambda p:p['expense_cost'],reverse=True); return {'title':'Highest direct expenses','rows':rows[:10],'answer':rows[0]['project_name'] if rows else 'No project data.'}
    if any(x in q for x in ('attention','urgent','what should','تنبيه','انتباه')):
        a=alerts(); return {'title':'Management action list','rows':a,'answer':f'{len(a)} actionable alert(s).'}
    if 'cash' in q or 'flow' in q or 'نقد' in q:
        c=cash_flow_forecast(); return {'title':'Cash-flow forecast','rows':[c],'answer':f"Projected net position over {c['days']} days: {c['projected_net']:,.2f}"}
    return {'title':'Smart query','rows':[],'answer':'Try: projects losing money, client receivables, highest expenses, cash flow, or what needs attention.'}

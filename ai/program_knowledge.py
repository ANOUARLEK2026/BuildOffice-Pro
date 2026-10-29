# ============================================================
# BuildOffice Pro program-wide knowledge and retrieval layer.
# Generated from the complete source tree + current SQLite schema.
# ============================================================
from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).resolve().parent / 'program_knowledge.json'


def normalize(text: str) -> str:
    s = unicodedata.normalize('NFKC', str(text or '')).lower()
    s = re.sub(r'[إأآا]', 'ا', s).replace('ى','ي').replace('ة','ه')
    s = re.sub(r'[ًٌٍَُِّْـ]', '', s)
    s = re.sub(r'[^\w\s./:-]', ' ', s, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', s).strip()


def tokens(text: str) -> set[str]:
    return {x for x in normalize(text).split() if len(x) > 1}


class ProgramKnowledge:
    """Searchable map of pages, source symbols, UI strings and database structure."""
    def __init__(self) -> None:
        self.data = json.loads(MANIFEST.read_text(encoding='utf8'))
        self.pages = self.data.get('pages', [])
        self.files = self.data.get('files', [])
        self.tables = self.data.get('database', {}).get('tables', [])
        self.settings = self.data.get('settings', [])
        self.translations = self.data.get('translations', {})
        self.aliases = self._aliases()

    def _aliases(self) -> dict[str,set[str]]:
        return {
            'projects': {'project','projects','مشروع','مشاريع','المشاريع','مشاريعنا'},
            'expenses': {'expense','expenses','cost','spending','مصاريف','مصروف','تكلفه','تكلفة','صرف'},
            'payments': {'payment','payments','income','receivable','قبض','تحصيل','دفعات','مدفوعات'},
            'staff': {'staff','employee','employees','workers','موظفين','عمال','المستخدمين'},
            'attendance': {'attendance','presence','hours','حضور','ساعات'},
            'payroll': {'payroll','salary','salaries','رواتب','اجور','أجور'},
            'documents': {'document','documents','file','expiry','وثائق','مستندات','ملفات','انتهاء'},
            'vehicles': {'vehicle','vehicles','fleet','مركبات','سيارات','اسطول','أسطول'},
            'metre': {'metre','métré','boq','quantity','bill','جدول','كميات','بند','متره'},
            'progress': {'progress','situations','execution','تقدم','وضعيات','انجاز','إنجاز'},
            'database': {'database','db','sqlite','table','column','schema','قاعدة','بيانات','جدول','عمود'},
            'settings': {'settings','configuration','options','إعدادات','اعدادات','تهيئه'},
            'code': {'code','source','python','function','class','module','file','كود','مصدر','دالة','صنف','ملف'},
            'ui': {'page','screen','button','field','form','dialog','صفحة','شاشه','زر','حقل','نموذج','نافذه'},
            'error': {'error','traceback','exception','bug','broken','crash','خطأ','استثناء','مشكلة','تعطل'},
            'translation': {'translation','language','arabic','english','ترجمه','لغة','عربي','انجليزي'},
            'theme': {'theme','dark','light','color','palette','ثيم','مظهر','الوان','ألوان'},
        }

    def page(self, query: str) -> dict[str,Any]|None:
        q=normalize(query)
        best=None; score=0
        for p in self.pages:
            s=self._score(q,p['name']+' '+p['class']+' '+p['group'])
            if s>score: score=s; best=p
        return best if score >= .35 else None

    def table(self, query: str) -> dict[str,Any]|None:
        q=normalize(query)
        best=None; score=0
        for t in self.tables:
            hay=t['name']+' '+' '.join(c['name'] for c in t['columns'])
            s=self._score(q,hay)
            if s>score: score=s; best=t
        return best if score >= .42 else None

    def search(self, query: str, limit: int=8) -> list[dict[str,Any]]:
        q=normalize(query); out=[]
        for p in self.pages:
            out.append((self._score(q,p['name']+' '+p['class']+' '+p['group']), 'page', p))
        for t in self.tables:
            text=t['name']+' '+' '.join(c['name'] for c in t['columns'])
            out.append((self._score(q,text), 'table', t))
        for f in self.files:
            text=f['path']+' '+' '.join(c['name'] for c in f['classes'])+' '+' '.join(x['name'] for x in f['functions'])
            for c in f['classes']:
                text += ' '+c['doc']+' '+' '.join(m['name']+' '+m['doc'] for m in c['methods'])
            s=self._score(q,text)
            if s>=.20: out.append((s,'file',f))
        out.sort(key=lambda x:x[0],reverse=True)
        return [{'score':round(s,3),'kind':k,'item':v} for s,k,v in out[:limit] if s>=.20]

    def _score(self,q: str, hay: str) -> float:
        qtok=tokens(q); htok=tokens(hay)
        if not qtok: return 0.0
        overlap=len(qtok & htok)/len(qtok)
        seq=SequenceMatcher(None,q,normalize(hay)[:500]).ratio()
        alias_bonus=0
        for vals in self.aliases.values():
            if qtok & vals and normalize(hay) in vals: alias_bonus=.2; break
        return min(1.0, overlap*.72+seq*.18+alias_bonus)

    def explain_page(self, name: str) -> dict[str,Any]|None:
        p=self.page(name)
        if not p: return None
        f=next((x for x in self.files if any(c['name']==p['class'] for c in x['classes'])),None)
        return {'page':p,'source':f,'ui': (f or {}).get('ui',[]) if f else []}

    def explain_table(self, name: str) -> dict[str,Any]|None:
        t=self.table(name)
        if not t: return None
        return {'table':t}

    def function(self, query: str) -> tuple[dict[str,Any],dict[str,Any]]|None:
        q=normalize(query); best=None; bestfile=None; score=0
        for f in self.files:
            for fn in f['functions']:
                s=self._score(q,fn['name']+' '+fn.get('doc','')+' '+f['path'])
                if s>score: score=s; best=fn; bestfile=f
            for cls in f['classes']:
                for fn in cls['methods']:
                    s=self._score(q,fn['name']+' '+fn.get('doc','')+' '+f['path'])
                    if s>score: score=s; best=fn; bestfile=f
        return (best, bestfile) if best is not None and bestfile is not None and score >= .45 else None

    def settings_search(self, query: str) -> list[dict[str,str]]:
        q=normalize(query)
        return [s for s in self.settings if self._score(q,s['key']+' '+str(s['value']))>=.35]

    def concept(self, query: str) -> str|None:
        q=normalize(query)
        if any(x in q for x in ('how does the program work','architecture','كيف يعمل','بنيه','معماريه')): return self.data['concepts']['architecture']
        if any(x in q for x in ('navigation','menu','sidebar','التنقل','القائمه','القائمة')): return self.data['concepts']['navigation']
        if any(x in q for x in ('translate','translation','language','ترجمه','الترجمه','اللغة')): return self.data['concepts']['localization']
        if any(x in q for x in ('theme','palette','dark mode','light mode','الوان','المظهر')): return self.data['concepts']['themes']
        if ((('project' in q or 'projects' in q) and ('expense' in q or 'expenses' in q or 'مصاريف' in q) and ('payment' in q or 'payments' in q or 'دفعات' in q or 'مدفوعات' in q)) or any(x in q for x in ('المشاريع والمصاريف والدفعات','المشاريع والمصاريف والمدفوعات','المشروع والمصاريف'))): return self.data['concepts']['financial_workflow']
        if any(x in q for x in ('staff attendance payroll','staff and attendance','الموظفين والحضور والرواتب','العمال والحضور')): return self.data['concepts']['people_workflow']
        if any(x in q for x in ('vehicles fuel maintenance','fleet equipment','المركبات والوقود والصيانة','المركبات والمعدات')): return self.data['concepts']['operations_workflow']
        if any(x in q for x in ('documents generation','documents workflow','الوثائق والتوليد','المستندات والتوليد')): return self.data['concepts']['documents_workflow']
        if any(x in q for x in ('data flow','database flow','يرتبط','تدفق البيانات','كيف ترتبط')): return self.data['concepts']['data_flow']
        return None

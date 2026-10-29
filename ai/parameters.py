# Parameter extraction for BuildOffice Copilot.
from __future__ import annotations

import re
from dataclasses import asdict, dataclass


@dataclass
class QueryParameters:
    project_ids:list[str]
    period:str|None=None
    limit:int|None=None
    sort_field:str|None=None
    sort_desc:bool=True
    metric:str|None=None
    operator:str|None=None
    threshold:float|None=None
    status:str|None=None
    currency:str|None=None
    unit:str|None=None
    group_by:str|None=None
    compare:bool=False
    why:bool=False
    recommend:bool=False
    detail:bool=False
    raw:str=''
    def to_dict(self): return asdict(self)

def parse_parameters(q:str, context_project:str|None=None)->QueryParameters:
    n=q.lower(); ids=[]
    for raw in re.findall(r'\bPRG[-_ ]?\d+\b',q,re.IGNORECASE):
            match = re.search(r'\d+', raw)
            if match:
                ids.append(f'PRG-{int(match.group()):03d}')
    if context_project and not ids and ('this project' in n or 'current project' in n or 'هذا المشروع' in n): ids=[context_project]
    m=re.search(r'\btop\s+(\d+)\b|(?:اول|أول|اعلى|أعلى)\s+(\d+)',n)
    limit=int(next(x for x in m.groups() if x)) if m else None
    metric=None
    for k,vals in {'health':('health','صحه','صحة'),'progress':('progress','تقدم','انجاز'),'cost':('cost','تكلفه','تكلفة'),'expense':('expense','مصاريف','صرف'),'margin':('margin','margin','هامش','ربح'),'cpi':('cpi',),'spi':('spi',)}.items():
        if any(v in n for v in vals): metric=k; break
    op=None; th=None
    m=re.search(r'(?:below|under|less than|under|اقل من|أقل من)\s*([0-9]+(?:\.[0-9]+)?)',n)
    if m: op='<'; th=float(m.group(1))
    else:
        m=re.search(r'(?:above|over|greater than|more than|فوق|اكثر من|أكثر من)\s*([0-9]+(?:\.[0-9]+)?)',n)
        if m: op='>'; th=float(m.group(1))
    compare=len(ids)>=2 or any(x in n for x in ('compare','versus','vs','مقارنة','بين'))
    return QueryParameters(ids,limit=limit,metric=metric,operator=op,threshold=th,compare=compare,why=any(x in n for x in ('why','لماذا','سبب')),recommend=any(x in n for x in ('recommend','what should','اقترح','ماذا افعل','ماذا نفعل')),detail=any(x in n for x in ('detail','detailed','بالتفصيل')),raw=q)

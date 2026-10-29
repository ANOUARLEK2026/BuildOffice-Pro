# ============================================================
# شرح الملف: tools/button_audit.py
# هذا الملف جزء من أدوات الفحص والتحقق المساعدة للمشروع.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
"""Static UI control audit. Runtime testing remains mandatory on a Windows/PySide6 host."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

# شرح الدالة audit: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def audit(path: Path):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    handlers={n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    buttons=[]; connects=0
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in {'QPushButton','QToolButton'}:
            label=''
            if node.args and isinstance(node.args[0],ast.Constant): label=str(node.args[0].value)
            buttons.append((label,node.lineno))
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='connect': connects+=1
    return buttons,connects,handlers

if __name__=='__main__':
    print('BuildOffice Pro static button audit')
    print('='*88)
    total=0
    for page in sorted((ROOT/'pages').glob('*_page.py')):
        buttons,connects,handlers=audit(page); total+=len(buttons)
        print(f'{page.name:28} buttons={len(buttons):2d} connects={connects:2d} methods={len(handlers):3d}')
        for label,line in buttons:
            print(f'  - L{line:<5} {label or "<dynamic label>"}')
    print(f'\nTotal buttons detected: {total}')
    print('Static analysis cannot prove runtime signal behavior.')

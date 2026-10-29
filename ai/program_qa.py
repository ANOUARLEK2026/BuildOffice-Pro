# ============================================================
# شرح الملف: محرك فهم أسئلة البرنامج ككل.
# يحول سؤال المستخدم العام إلى إجابة مبنية على معرفة BuildOffice Pro الفعلية.
# ============================================================
from __future__ import annotations

from typing import Any

from .program_knowledge import ProgramKnowledge, normalize, tokens


class ProgramQA:
    """Program-wide question answering over the generated application knowledge."""

    def __init__(self, knowledge: ProgramKnowledge | None = None) -> None:
        self.knowledge = knowledge or ProgramKnowledge()

    def answer(self, question: str) -> dict[str, Any] | None:
        q = normalize(question)
        if not q:
            return None

        # Broad overview / capability questions.
        if self._has(q, 'what is buildoffice', 'what is the program', 'what does buildoffice do',
                      'what can buildoffice do', 'what does the program do', 'what does this program do', 'what does this program do as a whole', 'what is this program',
                      'about buildoffice', 'برنامج buildoffice', 'ماذا يفعل البرنامج',
                      'ما هو البرنامج', 'ماذا يفعل بيلد اوفيس', 'ما هي قدرات البرنامج'):
            return self._overview()

        if self._has(q, 'how does the program work', 'how does buildoffice work', 'how is buildoffice built',
                      'how is the program structured', 'architecture', 'program architecture',
                      'كيف يعمل البرنامج', 'كيف يعمل بيلد اوفيس', 'بنية البرنامج', 'معمارية البرنامج'):
            return self._concept('architecture', 'Program architecture')

        if self._has(q, 'how are projects expenses payments connected', 'how are projects expenses and payments connected',
                      'how are projects costs and payments linked', 'projects expenses payments relationship',
                      'كيف ترتبط المشاريع والمصاريف والدفعات', 'كيف ترتبط المشاريع والمصاريف والمدفوعات',
                      'العلاقة بين المشاريع والمصاريف والدفعات'):
            return self._concept('financial_workflow', 'Financial workflow')

        if self._has(q, 'how does data flow', 'how does information flow', 'how are modules connected',
                      'how are the modules connected', 'database flow', 'data flow',
                      'كيف تتدفق البيانات', 'كيف ترتبط الوحدات', 'كيف ترتبط الصفحات', 'تدفق البيانات'):
            return self._concept('data_flow', 'Application data flow')

        if self._has(q, 'how does staff attendance payroll work', 'staff attendance payroll relationship',
                      'people workflow', 'كيف ترتبط العمال والحضور والرواتب', 'الموظفين والحضور والرواتب'):
            return self._concept('people_workflow', 'People workflow')

        if self._has(q, 'how do vehicles fuel maintenance work', 'vehicles fuel maintenance relationship',
                      'fleet workflow', 'كيف ترتبط المركبات والوقود والصيانة', 'المركبات والوقود والصيانة'):
            return self._concept('operations_workflow', 'Operations workflow')

        if self._has(q, 'how do documents work', 'document workflow', 'how are documents generated',
                      'كيف تعمل الوثائق', 'كيف تعمل المستندات', 'كيف يتم توليد الوثائق', 'كيف يتم توليد المستندات'):
            return self._concept('documents_workflow', 'Document workflow')

        if self._has(q, 'list pages', 'what pages', 'which pages', 'all pages', 'pages in buildoffice',
                      'what modules', 'which modules', 'program modules', 'قائمة الصفحات', 'ما هي الصفحات',
                      'كل الصفحات', 'ما هي الوحدات'):
            return self._pages()

        if self._has(q, 'what groups', 'sections of the program', 'main sections', 'program sections',
                      'ما هي أقسام البرنامج', 'اقسام البرنامج', 'الأقسام الرئيسية'):
            return self._groups()

        # Find the page/module referenced by the question before generic retrieval.
        page = self._best_page(q)
        if page:
            if self._has(q, 'what can i do in', 'what can you do in', 'what does this page do', 'what does the page do',
                          'purpose of', 'role of', 'what is the purpose', 'how do i use', 'how to use',
                          'what is this page', 'ماذا افعل في', 'ماذا يفعل', 'ما فائدة', 'وظيفة الصفحة', 'كيف استخدم'):
                return self._page_explanation(page)
            if self._has(q, 'where do i', 'where can i', 'where is', 'where to add', 'where to enter',
                          'where can i add', 'where do i create', 'where do i record', 'where do i enter', 'اين اضيف', 'أين أضيف', 'اين اجد', 'أين أجد', 'اين اسجل', 'أين اسجل'):
                return self._page_navigation(page, q)

        # Database questions, including relationship questions.
        if self._has(q, 'which table', 'what table', 'table stores', 'database table', 'sqlite table',
                      'which database', 'what columns', 'table relationship', 'foreign key',
                      'أي جدول', 'اي جدول', 'ما هو جدول', 'أين تخزن', 'اين تخزن', 'العلاقة بين الجداول'):
            return self._database_answer(q)

        # Settings / localization / theme questions.
        if self._has(q, 'settings', 'setting', 'configuration', 'preferences', 'اعدادات', 'إعدادات', 'تهيئة'):
            return self._settings_answer(q)
        if self._has(q, 'translation', 'language', 'arabic', 'english', 'localization', 'ترجمة', 'لغة', 'عربي', 'انجليزي'):
            return self._concept('localization', 'Language and localization')
        if self._has(q, 'theme', 'dark mode', 'light mode', 'palette', 'colors', 'الوان', 'الألوان', 'المظهر', 'الثيم'):
            return self._concept('themes', 'Theme system')
        if self._has(q, 'backup', 'restore database', 'backup and restore', 'نسخة احتياطية', 'استعادة قاعدة البيانات'):
            return self._backup_answer()

        # Source-code questions.
        if self._has(q, 'where is the code', 'which file', 'source file', 'where is this implemented',
                      'which function', 'which class', 'source code', 'implementation',
                      'اين الكود', 'أين الكود', 'في اي ملف', 'في أي ملف', 'الدالة', 'الكلاس', 'الصنف'):
            return self._code_answer(q)

        # Generic page lookup such as "vehicles" or "what is payroll".
        if page and self._has(q, 'what is', 'what are', 'what does', 'what can i do in', 'explain', 'tell me about',
                              'ما هو', 'ما هي', 'اشرح', 'شرح'):
            return self._page_explanation(page)

        # Last-resort evidence-backed retrieval. This always answers with useful facts instead of a bare "I don't know".
        results = self.knowledge.search(question, limit=6)
        if results and results[0]['score'] >= .30:
            return self._retrieval_answer(question, results)
        return None

    def _overview(self) -> dict[str, Any]:
        groups_data = self.knowledge.data.get('groups', [])
        groups = ', '.join((g.get('label') or g.get('code') or 'Unknown') if isinstance(g, dict) else str(g) for g in groups_data)
        pages = self.knowledge.pages
        self.knowledge.data.get('concepts', {})
        answer = (
            f"BuildOffice Pro is a desktop construction-management system built with PySide6 and SQLite. "
            f"The current application has {len(pages)} navigable pages across these functional areas: {groups}. "
            f"It manages projects and contracts, BOQ/Métré, progress and situations, expenses and income/payments, "
            f"debts and financial reporting, staff/attendance/payroll, vehicles and site operations, documents and document generation, "
            f"statistics and management intelligence, plus company/settings/backup controls. "
            f"Its main design is local-first: the UI works through services/repositories against the local SQLite database, "
            f"while analytics and management intelligence consume the same records."
        )
        return {'title':'What BuildOffice Pro is', 'answer':answer,
                'rows':[{'page':p['name'], 'group':p['group'], 'class':p['class']} for p in pages],
                'intent':'PROGRAM_OVERVIEW', 'open_page':'Dashboard', 'confidence':.99,
                'evidence':['BuildOffice Pro.py', 'program_knowledge.json']}

    def _concept(self, key: str, title: str) -> dict[str, Any] | None:
        text = self.knowledge.data.get('concepts', {}).get(key)
        if not text:
            return None
        return {'title':title, 'answer':text, 'intent':'PROGRAM_CONCEPT', 'confidence':.98,
                'evidence':['program_knowledge.json']}

    def _pages(self) -> dict[str, Any]:
        return {'title':'BuildOffice Pro pages',
                'answer':f"The current program exposes {len(self.knowledge.pages)} navigable pages. They are ordered by the main application menu and grouped by function.",
                'rows':[{'order':i+1,'page':p['name'],'group':p['group'],'class':p['class']} for i,p in enumerate(self.knowledge.pages)],
                'intent':'PROGRAM_PAGE_CATALOG','open_page':'Dashboard','confidence':.99,
                'evidence':['BuildOffice Pro.py MENU']}

    def _groups(self) -> dict[str, Any]:
        groups = self.knowledge.data.get('groups', [])
        return {'title':'Program sections', 'answer':f"BuildOffice Pro organizes the application into {len(groups)} functional sections.",
                'rows':[{'section':g} for g in groups], 'intent':'PROGRAM_GROUPS','confidence':.98,
                'evidence':['BuildOffice Pro.py GROUPS']}

    def _best_page(self, q: str) -> dict[str, Any] | None:
        aliases = getattr(self.knowledge, '_aliases', dict)()
        explicit = {
            'Projects': {'project','projects','مشروع','مشاريع'},
            'Project Control Center': {'project control','control center','control','تحكم المشروع','مركز التحكم'},
            'Métré': {'metre','métré','boq','quantity','bill','جدول الكميات','متره','كميات'},
            'Progress / Situations': {'progress','situation','situations','تقدم','وضعيات','انجاز'},
            'Project Closeout': {'closeout','close out','closing project','اغلاق المشروع','إغلاق المشروع'},
            'Supplementary Works': {'supplementary','additional works','اشغال اضافية','أشغال إضافية'},
            'Expenses': {'expense','expenses','cost','spending','مصاريف','مصروف','تكلفة','صرف'},
            'Income / Payments': {'payment','payments','income','receipt','receipts','قبض','تحصيل','دفعات'},
            'Debts': {'debt','debts','owe','liability','دين','ديون','التزامات'},
            'Financial Reports': {'financial report','financial reports','report','reports','تقارير مالية','تقرير مالي'},
            'Staff': {'staff','employee','employees','worker','workers','موظف','عمال'},
            'Attendance': {'attendance','presence','working hours','حضور','ساعات العمل'},
            'Payroll': {'payroll','salary','salaries','راتب','رواتب','اجور','أجور'},
            'Vehicles': {'vehicle','vehicles','fleet','car','مركبة','مركبات','سيارة','سيارات','اسطول','أسطول'},
            'Construction Control': {'construction control','site control','materials','labor allocations','subcontractor','مراقبة الاشغال','مواد','مقاول فرعي'},
            'Documents': {'document','documents','file','files','وثيقة','وثائق','مستند','مستندات'},
            'Document Generation': {'document generation','generate document','generate files','توليد الوثائق','توليد المستندات'},
            'Statistics': {'statistics','statistic','analytics','analysis','احصائيات','إحصائيات','تحليل'},
            'Management Intelligence': {'management intelligence','management','alerts','forecast','what if','ذكاء الادارة','ذكاء الإدارة','تنبيهات'},
            'Company': {'company','company profile','الشركة','معلومات الشركة'},
            'Settings': {'settings','setting','preferences','configuration','إعدادات','اعدادات'},
            'Backup & Restore': {'backup','restore','backup and restore','نسخة احتياطية','استعادة'},
        }
        best = None; best_score = 0.0
        for p in self.knowledge.pages:
            hay = normalize(p['name']+' '+p['class']+' '+p['group'])
            score = self.knowledge._score(q, hay)
            key = p['name']
            for alias in explicit.get(key, set()) | aliases.get(normalize(key), set()):
                a=normalize(alias)
                if a and a in q: score += .34 if len(a.split()) > 1 else .24
            if normalize(key) in q: score += .40
            if score > best_score:
                best, best_score = p, score
        return best if best_score >= .22 else None

    def _page_explanation(self, page: dict[str, Any]) -> dict[str, Any]:
        e = self.knowledge.explain_page(page['name']) or {}
        src = e.get('source') or {}
        methods = []
        for c in src.get('classes', []):
            if c.get('name') == page['class']:
                methods = [m['name'] for m in c.get('methods', []) if m['name'] not in ('__init__',)][:18]
        ui = src.get('ui', [])[:24]
        concepts = {
            'Projects':'creates and manages project master records and their contract data.',
            'Project Control Center':'combines project contract, BOQ, progress, cost, workforce, payment and forecast indicators.',
            'Métré':'manages BOQ/quantity-control information used for project valuation and execution tracking.',
            'Progress / Situations':'records executed work and situations/certifications that feed progress and earned-value calculations.',
            'Project Closeout':'supports completion and closing information for projects.',
            'Supplementary Works':'tracks supplementary project works outside the original baseline.',
            'Expenses':'records direct project/company expenses and their payment/control information.',
            'Income / Payments':'records receipts and money received against projects.',
            'Debts':'tracks recorded debt and outstanding obligations.',
            'Financial Reports':'presents financial reporting derived from project and company records.',
            'Staff':'stores personnel master records used by attendance and payroll.',
            'Attendance':'records working presence/hours and project attendance allocations.',
            'Payroll':'handles payroll calculations based on staff/work records.',
            'Vehicles':'tracks vehicles, fuel, maintenance and related asset operations.',
            'Construction Control':'combines site-control records such as materials, labor, equipment and subcontracting.',
            'Documents':'stores and manages company/project administrative records and compliance information.',
            'Document Generation':'produces output files from trusted BuildOffice data.',
            'Statistics':'provides analytical views over stored operational and financial data.',
            'Management Intelligence':'provides alerts, reconciliation, forecasts, what-if analysis and cross-module decisions.',
            'Company':'stores the authoritative company identity used throughout the application.',
            'Settings':'controls application behavior, themes, localization, thresholds and safety preferences.',
            'Backup & Restore':'protects and restores the local SQLite application database.'
        }
        purpose = concepts.get(page['name'], f"provides the {page['group'].lower()} functions implemented by {page['class']}.")
        answer = f"{page['name']} is the {page['group'].lower()} module implemented by {page['class']}. Its purpose is to {purpose}"
        if methods:
            answer += " Important implementation methods include " + ', '.join(methods[:10]) + "."
        if ui:
            labels = [x['value'] for x in ui if x.get('kind') == 'setObjectName'][:8]
            if labels:
                answer += " The page also contains UI elements such as " + ', '.join(labels) + "."
        return {'title':f'{page["name"]} explained','answer':answer,
                'rows':[{'page':page['name'],'group':page['group'],'class':page['class'],'source':src.get('path',''),'methods':', '.join(methods[:12])}],
                'intent':'PROGRAM_PAGE','open_page':page['name'],'confidence':.96,
                'evidence':[src.get('path', page['class'])]}

    def _page_navigation(self, page: dict[str, Any], q: str) -> dict[str, Any]:
        r = self._page_explanation(page)
        r['answer'] += f" To reach it from the main program, open the {page['name']} page from the left navigation; the application loads pages lazily when selected."
        if page['name'] == 'Vehicles' and self._has(normalize(q), 'where do i add', 'where can i add', 'اين اضيف'):
            r['answer'] += " On that page, use the '+ Add vehicle' action to create a vehicle record."
        elif page['name'] == 'Expenses' and self._has(normalize(q), 'where do i add', 'where can i add', 'اين اضيف'):
            r['answer'] += " On that page, use the '+ Add Expense' action to record an expense."
        elif page['name'] == 'Staff' and self._has(normalize(q), 'where do i add', 'where can i add', 'اين اضيف'):
            r['answer'] += " On that page, use the '+ Add staff' action to create a staff record."
        return r

    def _database_answer(self, q: str) -> dict[str, Any] | None:
        # Identify one or two domain words and rank tables using the actual schema.
        terms = tokens(q)
        ranked=[]
        for t in self.knowledge.tables:
            hay = normalize(t['name']+' '+' '.join(c['name'] for c in t['columns']))
            overlap = len(terms & tokens(hay))
            ranked.append((overlap, self.knowledge._score(q, hay), t))
        ranked.sort(key=lambda x:(x[0],x[1]), reverse=True)
        top=[x[2] for x in ranked[:6] if x[0] or x[1] >= .38]
        if not top: return None
        # Relationship explanation when the question explicitly asks how tables/modules connect.
        if self._has(q, 'relationship','foreign key','connected','linked','العلاقة','ترتبط','مرتبط','يرتبط'):
            pairs=[]
            for t in top:
                for fk in t.get('foreign_keys',[]):
                    pairs.append(f"{t['name']}.{fk.get('from')} → {fk.get('table')}.{fk.get('to')}")
            ans='The relevant database relationships I can verify are: ' + (', '.join(pairs[:15]) if pairs else 'no matching foreign-key relationship was found in the selected tables.')
        else:
            t=top[0]; cols=', '.join(c['name'] for c in t['columns'])
            ans=f"The strongest schema match is the SQLite table '{t['name']}'. It has {t['row_count']} current rows and these columns: {cols}."
        return {'title':'Database structure','answer':ans,
                'rows':[{'table':t['name'],'rows':t['row_count'],'columns':', '.join(c['name'] for c in t['columns'])} for t in top],
                'intent':'PROGRAM_DATABASE','open_page':'Settings','confidence':.96,
                'evidence':['live buildoffice.db','program_knowledge.json']}

    def _settings_answer(self, q: str) -> dict[str, Any] | None:
        results=self.knowledge.settings_search(q)
        if results:
            return {'title':'BuildOffice settings', 'answer':f"I found {len(results)} relevant application setting(s) in the current configuration.",
                    'rows':results[:20], 'intent':'PROGRAM_SETTINGS','open_page':'Settings','confidence':.93,
                    'evidence':['settings table']}
        return self._concept('themes','Theme system') if 'theme' in q else {
            'title':'BuildOffice settings',
            'answer':'Settings is the central control page for application preferences, localization, theme/palette behavior, management thresholds, financial defaults, backup safety and AI preferences.',
            'intent':'PROGRAM_SETTINGS','open_page':'Settings','confidence':.93,
            'evidence':['pages/settings_page.py','settings table']}

    def _backup_answer(self) -> dict[str, Any]:
        return {'title':'Backup & Restore','answer':'BuildOffice Pro keeps its operational data in the local SQLite database and includes a dedicated Backup & Restore page. The application can create a safety copy of the database before destructive replacement/restore operations, reducing the risk of accidental data loss.',
                'intent':'PROGRAM_BACKUP','open_page':'Backup & Restore','confidence':.94,
                'evidence':['pages/backup_page.py','BuildOffice Pro.py']}

    def _code_answer(self, q: str) -> dict[str, Any] | None:
        result=self.knowledge.function(q)
        if result:
            f,file=result
            return {'title':'Source-code element','answer':f"The strongest code match is {f['name']} in {file['path']} around line {f['line']}. {f.get('doc') or 'The current knowledge index identifies it as an application function/method.'}",
                    'rows':[{'file':file['path'],'name':f['name'],'line':f['line']}],
                    'intent':'PROGRAM_CODE','confidence':.92,'evidence':[file['path']]}
        return self._retrieval_answer(q,self.knowledge.search(q,limit=6))

    def _retrieval_answer(self, q: str, results: list[dict[str, Any]]) -> dict[str, Any]:
        strongest=results[0]
        item=strongest['item']
        name=item.get('name') or item.get('path') or item.get('table') or 'program element'
        kind=strongest['kind']
        detail=''
        if kind=='page': detail=f"It is the {item.get('group','')} page implemented by {item.get('class','')}"
        elif kind=='table': detail=f"It is the SQLite table '{item.get('name','')}' containing {item.get('row_count',0)} current rows"
        elif kind=='file': detail=f"It is source file '{item.get('path','')}'"
        answer=f"The closest verified match for your question is {name}. {detail}."
        answer += " I am answering from the current BuildOffice source/schema knowledge index rather than inventing behavior."
        return {'title':'BuildOffice program knowledge','answer':answer,
                'rows':[{'kind':r['kind'],'name':r['item'].get('name') or r['item'].get('path') or r['item'].get('table'),'score':r['score']} for r in results],
                'intent':'PROGRAM_KNOWLEDGE','confidence':min(.90,max(.60,strongest['score'])),
                'evidence':['generated program knowledge index']}

    @staticmethod
    def _has(q: str, *phrases: str) -> bool:
        return any(normalize(p) in q for p in phrases)

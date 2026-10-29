# BuildOffice Pro Localization Deep Audit

## Scope
This pass targets the failure mode where user-facing English text is stored inside lists/tuples/dictionaries and later rendered by helper functions, rather than being passed directly to a Qt constructor.

## Changes
- Added missing dashboard UI catalog entries, including KPI titles such as `Total Receivables`.
- Added conservative dynamic phrase translations used by dashboard labels (`active`, `this month`, `received this month`, counts, maintenance, records, etc.).
- Dashboard `_label()` now stores the stable English source in `bo_i18n_text` so language switching can return reliably from Arabic to English for both static and dynamic labels.
- Added `On Hold` to the central catalog because it is rendered by the dashboard status section.
- Extended `tools/translation_audit.py` with a conservative second-pass scan for phrase-like literals inside common UI data collections, specifically to catch KPI/card/list patterns that constructor-only scans cannot see.
- Kept the collection scan conservative to avoid treating SQL, identifiers, format fragments, and document-export headers as UI text.
- Preserved the four-palette system and corrected option 4 foreground contrast regressions introduced by the previous palette pass.

## Verification
- English catalog keys: 2092
- Arabic catalog keys: 2118
- Missing/blank Arabic keys: 0
- Uncatalogued static UI literals: 0
- Uncatalogued literal `translate_text()` calls: 0
- UI collection literals reviewed: 33
- Uncatalogued UI collection literals: 0
- Project validation errors: 0
- Python compile check: passed
- Test suite: 44/44 passed

## Runtime note
The automated source/test environment does not provide the Windows desktop GUI context used by the production application, so final visual verification should still be performed on Windows. The code paths and catalogs are statically verified here.

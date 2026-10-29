# BuildOffice Pro Localization Implementation Audit

## What was changed

- Kept `core/i18n.py` as the central localization authority.
- Added a cached process-wide active language so normal `translate_text()` calls do not query SQLite repeatedly.
- Added `set_language()` to synchronize the in-memory language state immediately when Settings changes language.
- Kept the existing explicit page/window localization flow and combo-box source-value protection.
- Expanded the English and Arabic catalogs with the remaining static UI strings found in the project audit, including developer tools and automation UI.
- Added Arabic handling for runtime-generated UI messages that are composed with values such as amounts, counts, project IDs, and file paths.
- Added `tools/translation_audit.py` as a repeatable static check for catalog coverage and common Qt UI literals.

## Verification

- Python compileall: passed.
- Existing regression suite: 44 passed.
- English catalog: 2,024 keys.
- Arabic catalog: 2,050 keys.
- Missing or blank Arabic values for English keys: 0.
- Uncatalogued static UI literals: 0.
- Uncatalogued literal `translate_text()` calls: 0.

## Runtime limitation

The available execution environment does not provide the Windows/PySide6 runtime, so the desktop GUI itself could not be launched here. The source was syntax-compiled and the existing test suite was executed successfully. Windows GUI verification should still be performed on the target machine.

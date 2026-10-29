# BuildOffice Pro

**GitHub description:**
Desktop management suite for construction companies, with projects, accounting, expenses, staff, documents, reporting, and an integrated local AI assistant.
BuildOffice Pro brings day-to-day construction administration into one desktop application. Its modules cover project records and progress, company and staff administration, expenses and accounting, documents, attendance, payroll, procurement, vehicles, debts, and reports. A local application-aware assistant helps users explore the program and ask questions about its structure and available business data.

## Highlights
- Project, site-operation, progress, and construction-control workflows.
- Expense, income, accounting, debt, procurement, and payroll modules.
- Company, contacts, staff, attendance, vehicles, and document management.
- Dashboards, statistics, reports, and database backup tools.
- Arabic/multilingual UI support, themes, keyboard shortcuts, and navigation search.
- SQLite persistence and an AI assistant grounded in application knowledge.

## Run on Windows
1. Install Python 3.10+.
2. From this folder run `py -m pip install -r requirements.txt`.
3. Start with `py "BuildOffice Pro.py"`.

The included `Install BuildOffice Pro Dependencies.bat` may also be used to install dependencies. Consult the source and configuration before using this application with real company records.

## Tech stack
Python · PySide6 · SQLite · python-docx · openpyxl · cryptography

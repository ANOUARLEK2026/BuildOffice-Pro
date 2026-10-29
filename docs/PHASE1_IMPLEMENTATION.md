# Phase 1 — Foundation, Company, Partners, Media and Security

Version 1.08.

Implemented:
1. Company identity remains the authoritative company profile.
2. Business partner master data: clients, suppliers and both.
3. Project-partner relationship database foundation.
4. Managed media store for photos, receipts and documents.
5. Central Photos & Attachments page with search/filter/open/delete.
6. Administration page with user creation, roles, activation/deactivation and audit viewer.
7. Existing authentication and audit services preserved.
8. Existing backup/restore preserved.
9. Arabic/English localization entries added for new UI.
10. Additive SQLite migration design preserved; historical records are not deleted.

Security note:
- User creation uses the existing password hashing service.
- The currently signed-in account cannot deactivate itself.
- User management is restricted to Administrator/Developer roles.

Next phase:
- Connect clients/suppliers to project, expense, invoice and payment workflows.
- Build the accounting ledger, accounts, cash/bank, receivables/payables and invoices.

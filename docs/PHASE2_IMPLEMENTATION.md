# BuildOffice Pro Phase 2 — Accounting Integration

Version 1.10.

Completed:
- Accounting core: chart of accounts, journal, invoices, cash/bank.
- Accounting mappings for expense, invoice and payment workflows.
- Accounting posting registry prevents duplicate journal entries.
- Existing expenses can be posted into the ledger without altering their original records.
- Existing project payments and expense payments have posting services.
- Invoice payment structure and payment allocation foundation.
- Accounting page now includes a controlled "Sync existing expenses" action.

Data safety:
- Existing expenses, projects, debts, payments and partners are preserved.
- No destructive rewrite of legacy financial tables.
- Posting is idempotent: the same source transaction is not posted twice.

Remaining Phase 2 work:
- Full invoice create/edit form.
- Customer/supplier receivable and payable screens.
- Payment entry + allocation UI.
- Automatic posting hooks directly from expense/income/payment save actions.
- VAT reports, trial balance, P&L and balance sheet.
- Project profitability and cost-center accounting.

## Phase 2 completion - v1.11
- Full invoice creation/editing workflow with Sales/Purchase types, partners, projects, line items, discount and default TVA 19%.
- Invoice issuing posts balanced double-entry entries.
- TVA accounts 4456 (input) and 4457 (output) are provisioned.
- Customer/supplier payment workflow with cash/bank financial accounts, cash transactions, payment allocations and invoice payment history.
- Receivables/payables ledger by partner with invoiced, paid, outstanding and overdue values.
- Financial snapshot covering sales, purchases, cash, bank, receivables, payables and VAT position.
- Automatic accounting hooks for project receipts, expense payments and debt payments.
- Existing financial records can be synchronized idempotently through the accounting page.
- Migration 17 adds missing Phase 2 integration tables without deleting existing data.

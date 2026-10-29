# Phase 3 - Project Profitability & Job Costing

## First increment

BuildOffice Pro v1.12 introduces a read-only, live project profitability layer without changing existing database contracts.

### Included
- Project-level contract HT/TTC, BOQ value and earned value.
- Physical progress based on approved/submitted/paid situations, including supplementary situation amounts.
- Direct job cost from existing expenses, labor allocations, equipment usage, material consumption, subcontractor situations, fuel and maintenance.
- Forecast cost (EAC), remaining forecast cost (ETC), CPI, budget utilization and margin.
- Invoiced, collected and outstanding customer amounts.
- Cost-center budget vs actual analysis using existing `project_cost_centers` data.
- Ranked cost components to identify the main cost driver.
- Dedicated Project Profitability page with CSV export.

## Safety

No existing tables or columns were renamed or removed. The service is read-only. Existing accounting and operational pages remain the source of transaction entry.

## Next Phase 3 increments

- Procurement and purchase workflow linked to suppliers and stock.
- Payroll-to-project/cost-center accounting postings.
- Stronger subcontractor payable integration.
- Portfolio profitability view and period filters.
- Formal trial balance, P&L and balance sheet reports.
- Budget vs actual controls and approval workflow.

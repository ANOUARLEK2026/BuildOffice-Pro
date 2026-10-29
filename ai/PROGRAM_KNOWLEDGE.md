# BuildOffice Pro Program Knowledge

Pages: 23
Tables: 41
Python files indexed: 123

- Dashboard [DashboardPage] (WORKSPACE)
- Projects [ProjectsPage] (WORKSPACE)
- Project Control Center [ProjectControlPage] (WORKSPACE)
- Métré [MetrePage] (WORKSPACE)
- Progress / Situations [ProgressPage] (WORKSPACE)
- Project Closeout [ProjectCloseoutPage] (WORKSPACE)
- Supplementary Works [SupplementaryPage] (WORKSPACE)
- Expenses [ExpensesPage] (FINANCE)
- Income / Payments [IncomePage] (FINANCE)
- Debts [DebtsPage] (FINANCE)
- Financial Reports [ReportsPage] (FINANCE)
- Staff [StaffPage] (PEOPLE)
- Attendance [AttendancePage] (PEOPLE)
- Payroll [PayrollPage] (PEOPLE)
- Vehicles [VehiclesPage] (ASSETS)
- Construction Control [ConstructionControlPage] (OPERATIONS)
- Documents [DocumentsPage] (DOCUMENTS)
- Document Generation [DocumentGenerationPage] (DOCUMENTS)
- Statistics [StatisticsPage] (ANALYTICS)
- Management Intelligence [ManagementPage] (ANALYTICS)
- Company [CompanyPage] (SYSTEM)
- Settings [SettingsPage] (SYSTEM)
- Backup & Restore [BackupPage] (SYSTEM)

## Database tables

- app_license (0 rows): license_id, license_key, customer_name, product_name, issued_at, expires_at, activated_at, device_id, status, created_at
- app_users (0 rows): user_id, username, password_hash, password_salt, role, active, created_at, last_login_at
- attendance (72 rows): record_id, staff_id, project_id, date, working_hours, overtime_hours, status, created_at, notes
- audit_log (4 rows): audit_id, occurred_at, user_name, action, entity, entity_id, description
- company documents (0 rows): document_id, document name, document path, upload date, expiring date, description, status, category, nature, reference_no, issue_date, reminder_days, metadata_json
- company info (1 rows): id, company name, company name ar, owner, address, phone 1, phone 2, fax, email 1, email 2, reg com, nif, nis, bea, cpa, created_at, updated_at, legal form, activity, wilaya, postal code, website, bank name, bank account, bank branch, logo path, notes
- debt (3 rows): debt_id, project_id, lender, date, amount, due_date, status, notes
- debt_payments (3 rows): payment_id, debt_id, payment_date, amount, payment_method, reference, notes, created_at
- documents (7 rows): document_id, owner_type, owner_id, document_name, file_path, category, issue_date, expiry_date, reminder_days, status, notes, created_at, updated_at
- equipment_usage (8 rows): usage_id, vehicle_id, project_id, cost_center_id, usage_date, operating_hours, hourly_cost, fuel_cost, operator_staff_id, meter_start, meter_end, notes, created_at
- expense_payments (13 rows): payment_id, expense_id, payment_date, amount, payment_method, reference, notes, created_at
- expenses (535 rows): expense_id, project_id, date, description, category, amount, quantity, unit, unit_price, payment_method, payment_status, due_date, notes, created_at, updated_at, attachments, cost_center_id, boq_item_id
- fuel_records (8 rows): fuel_id, vehicle_id, date, quantity, unit_price, total_cost, mileage, project_id, notes, created_at
- id_registry (3 rows): entity_id, entity_type, created_at
- id_sequences (12 rows): sequence_key, next_value, updated_at
- intelligence_snapshots (0 rows): snapshot_id, created_at, scope, project_id, payload_json
- labor_allocations (72 rows): allocation_id, staff_id, project_id, cost_center_id, work_date, hours, overtime_hours, hourly_cost, activity, notes, created_at, attendance_id, source_type
- maintenance_records (8 rows): maintenance_id, vehicle_id, maintenance_date, maintenance_type, description, cost, mileage, next_maintenance_date, project_id, notes, created_at
- material_movements (6 rows): movement_id, material_id, project_id, movement_date, movement_type, warehouse, quantity, unit_cost, reference, notes, created_at
- materials (6 rows): material_id, code, name, unit, standard_cost, minimum_stock, created_at, updated_at
- metre_items (18 rows): item_id, project_id, item_number, description, unit, quantity, unit_price, amount
- notifications (1 rows): notification_id, created_at, title, message, severity, entity, entity_id, is_read
- payroll_records (7 rows): payroll_id, staff_id, period, base_amount, overtime_amount, bonuses, deductions, advances, net_amount, status, notes, created_at, updated_at, attendance_hours, attendance_overtime, allocated_hours, allocated_overtime, reconciliation_status
- project_cost_centers (12 rows): cost_center_id, project_id, code, name, budget_amount, boq_item_id, parent_id, created_at, updated_at
- project_payments (7 rows): payment_id, project_id, date, amount, payment_method, reference, notes, created_at, situation_id, payment_type
- projects (9 rows): project_id, project_name, summarised_name, contracting_authority, project_type, contract_code, contract_date, start_date, period, end_date, budget_ht, tva_percent, tva, budget_ttc, expenses, revenue, revenue %, status, created_at, updated_at, location, description, actual_completion_date
- projects documents (0 rows): item_id, project_id, document_name, document_path, upload_date, expiring_date, description, status, category, nature, reference_no, issue_date, reminder_days, metadata_json, related_entity
- schema_version (1 rows): version, applied_at
- settings (16 rows): setting_key, setting_value
- situation_documents (0 rows): document_id, situation_id, project_id, document_name, document_path, document_type, generated_at
- situation_items (42 rows): situation_item_id, situation_id, item_id, executed_quantity, unit_price, amount, previous_quantity, created_at
- situations (7 rows): situation_id, project_id, situation_number, situation_date, title, notes, status, created_at, updated_at, is_final, finalized_at, gross_amount, retention_amount, advance_recovery, other_deductions, net_due, retention_percent, tva_percent, advance_percent
- staff (8 rows): staff_id, full_name, position, placement, employment_type, salary_type, rate, hire_date, phone, status, notes, visible, attendance_type, created_at, updated_at
- staff_projects (19 rows): staff_id, project_id, active, assignment_start_date, assignment_end_date, role_on_project
- subcontractor_contracts (1 rows): contract_id, subcontractor_id, project_id, contract_no, contract_date, contract_amount, notes, created_at, updated_at
- subcontractor_payments (0 rows): payment_id, situation_id, payment_date, amount, payment_method, reference, notes, created_at
- subcontractor_situations (1 rows): situation_id, contract_id, situation_date, gross_amount, retention_amount, advance_recovery, other_deductions, net_amount, progress_percent, notes, created_at, updated_at
- subcontractors (1 rows): subcontractor_id, name, contact, phone, tax_id, notes, created_at, updated_at
- supplementary_situation_items (0 rows): supplementary_situation_item_id, situation_id, supplementary_id, executed_quantity, amount, created_at
- supplementary_works (1 rows): supplementary_id, project_id, work_number, description, unit, quantity, unit_price, lump_sum_amount, work_mode, work_date, reason, reference_no, status, notes, created_at, updated_at
- vehicles (4 rows): vehicle_id, brand, model, serial_number, licence_plate, buy_date, notes, status, current_project_id, vin
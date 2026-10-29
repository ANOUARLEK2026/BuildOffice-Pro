from __future__ import annotations

import sqlite3

from services.project_profitability_service import project_profitability


def test_project_profitability_includes_operational_costs_and_supplementary_work():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE projects (project_id TEXT PRIMARY KEY, project_name TEXT, status TEXT, budget_ht REAL, budget_ttc REAL);
        CREATE TABLE metre_items (item_id TEXT PRIMARY KEY, project_id TEXT, amount REAL);
        CREATE TABLE situations (situation_id TEXT PRIMARY KEY, project_id TEXT, status TEXT);
        CREATE TABLE situation_items (situation_item_id TEXT, situation_id TEXT, item_id TEXT, amount REAL);
        CREATE TABLE supplementary_situation_items (situation_item_id TEXT, situation_id TEXT, supplementary_id TEXT, amount REAL);
        CREATE TABLE expenses (expense_id TEXT, project_id TEXT, amount REAL, cost_center_id TEXT);
        CREATE TABLE labor_allocations (allocation_id TEXT, project_id TEXT, cost_center_id TEXT, hours REAL, overtime_hours REAL, hourly_cost REAL);
        CREATE TABLE equipment_usage (usage_id TEXT, project_id TEXT, cost_center_id TEXT, operating_hours REAL, hourly_cost REAL, fuel_cost REAL);
        CREATE TABLE material_movements (movement_id TEXT, project_id TEXT, movement_type TEXT, quantity REAL, unit_cost REAL);
        CREATE TABLE subcontractor_contracts (contract_id TEXT, project_id TEXT);
        CREATE TABLE subcontractor_situations (situation_id TEXT, contract_id TEXT, net_amount REAL);
        CREATE TABLE fuel_records (id TEXT, project_id TEXT, total_cost REAL);
        CREATE TABLE maintenance_records (id TEXT, project_id TEXT, cost REAL);
        CREATE TABLE project_payments (payment_id TEXT, project_id TEXT, amount REAL);
        CREATE TABLE invoices (invoice_id TEXT, project_id TEXT, invoice_type TEXT, total_amount REAL, paid_amount REAL);
        CREATE TABLE project_cost_centers (cost_center_id TEXT, project_id TEXT, code TEXT, name TEXT, budget_amount REAL);
    """)
    conn.execute("INSERT INTO projects VALUES ('P1','Test','Active',10000,11900)")
    conn.execute("INSERT INTO metre_items VALUES ('M1','P1',10000)")
    conn.execute("INSERT INTO situations VALUES ('S1','P1','Approved')")
    conn.execute("INSERT INTO situation_items VALUES ('SI1','S1','M1',4000)")
    conn.execute("INSERT INTO supplementary_situation_items VALUES ('SSI1','S1','SW1',500)")
    conn.execute("INSERT INTO expenses VALUES ('E1','P1',1000,NULL)")
    conn.execute("INSERT INTO labor_allocations VALUES ('L1','P1',NULL,10,0,100)")
    conn.execute("INSERT INTO equipment_usage VALUES ('Q1','P1',NULL,5,100,50)")
    conn.execute("INSERT INTO material_movements VALUES ('M1','P1','Consumption',2,200)")
    conn.execute("INSERT INTO subcontractor_contracts VALUES ('SC1','P1')")
    conn.execute("INSERT INTO subcontractor_situations VALUES ('SS1','SC1',300)")
    conn.execute("INSERT INTO fuel_records VALUES ('F1','P1',100)")
    conn.execute("INSERT INTO maintenance_records VALUES ('MT1','P1',50)")
    conn.execute("INSERT INTO project_payments VALUES ('PP1','P1',2000)")
    conn.execute("INSERT INTO invoices VALUES ('I1','P1','Sales',4500,2000)")
    conn.commit()
    try:
        d = project_profitability('P1', conn)
        assert d['earned_value'] == 4500
        assert d['direct_cost'] == 3400
        assert round(d['margin'], 2) == 1100
        assert d['invoiced'] == 4500
        assert d['invoice_paid'] == 2000
        assert d['receivable'] == 2500
        assert d['progress'] == 45
    finally:
        conn.close()

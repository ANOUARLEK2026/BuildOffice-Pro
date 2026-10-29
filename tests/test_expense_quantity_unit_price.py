import sqlite3

from database.migrations import _migration_13


def test_expense_quantity_unit_price_migration_preserves_legacy_total():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE expenses (
            expense_id TEXT PRIMARY KEY,
            project_id TEXT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT,
            payment_method TEXT,
            payment_status TEXT NOT NULL DEFAULT 'Paid',
            due_date TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )"""
    )
    conn.execute(
        "INSERT INTO expenses(expense_id,date,description,amount) VALUES('E1','2026-01-01','Cement',42500)"
    )

    _migration_13(conn)
    row = conn.execute(
        "SELECT quantity, unit, unit_price, amount FROM expenses WHERE expense_id='E1'"
    ).fetchone()

    assert row["quantity"] == 1
    assert row["unit"] == "Lump Sum"
    assert row["unit_price"] == 42500
    assert row["amount"] == 42500


def test_expense_quantity_unit_price_columns_are_idempotent():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE expenses (expense_id TEXT PRIMARY KEY, amount REAL NOT NULL, date TEXT NOT NULL, description TEXT NOT NULL)"
    )
    _migration_13(conn)
    _migration_13(conn)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(expenses)")}
    assert {"quantity", "unit", "unit_price"}.issubset(columns)

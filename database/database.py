# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.

# ============================================================
# شرح الملف: database.py
# يحتوي هذا الملف على جزء من وظائف وتفاصيل تطبيق BuildOffice Pro.
# التعليقات العربية هنا للتوضيح فقط ولا تغيّر منطق البرنامج.
# ============================================================
import sqlite3
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from core.config import (
    DATABASE_BUSY_TIMEOUT_MS,
    DATABASE_FILENAME,
    DATABASE_SYNCHRONOUS,
    DATABASE_TIMEOUT_SECONDS,
    ROOT_DIR,
)
from dev_tools.dev_runtime import is_enabled, maybe_delay, record_metric

BASE_DIR: Path = Path(ROOT_DIR)
class DeveloperSQLiteConnection(sqlite3.Connection):
    """SQLite connection that exposes optional developer timing hooks."""

    def execute(self, sql, parameters=(), /):
        started = time.perf_counter()
        maybe_delay()
        try:
            return super().execute(sql, parameters)
        finally:
            if is_enabled():
                record_metric("query", (time.perf_counter() - started) * 1000.0)

    def executemany(self, sql, seq_of_parameters, /):
        started = time.perf_counter()
        maybe_delay()
        try:
            return super().executemany(sql, seq_of_parameters)
        finally:
            if is_enabled():
                record_metric("query", (time.perf_counter() - started) * 1000.0)

    def executescript(self, sql_script, /):
        started = time.perf_counter()
        maybe_delay()
        try:
            return super().executescript(sql_script)
        finally:
            if is_enabled():
                record_metric("query", (time.perf_counter() - started) * 1000.0)


# هذا الاسم يبقى متاحًا للتوافق مع أدوات الاختبار والتطوير القديمة.
# يمكن للاختبارات تغييره مؤقتًا إلى قاعدة بيانات معزولة.
DATABASE_FILE: Path = Path(BASE_DIR) / DATABASE_FILENAME

# تنفيذ وظيفة get_connection ضمن هذا الجزء من البرنامج.
def get_connection():
    """Return a consistently configured SQLite connection.

    All application connections use the same timeout/PRAGMAs.  In particular,
    WAL improves read/write concurrency and busy_timeout prevents transient
    locks from immediately surfacing as application errors.
    """
    conn = sqlite3.connect(
        DATABASE_FILE,
        timeout=DATABASE_TIMEOUT_SECONDS,
        isolation_level=None,
        factory=DeveloperSQLiteConnection,
    )
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout = {DATABASE_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL is configured once by create_database(). Do not change journal mode
    # on every connection because doing so can itself contend for the writer lock.
    conn.execute(f"PRAGMA synchronous = {DATABASE_SYNCHRONOUS}")
    return conn


# تنفيذ وظيفة _table_exists ضمن هذا الجزء من البرنامج.
def _table_exists(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


# تنفيذ وظيفة _columns ضمن هذا الجزء من البرنامج.
def _columns(conn, table):
    return {row[1]: row for row in conn.execute(f'PRAGMA table_info("{table}")')}


# تنفيذ وظيفة _ensure_attendance_schema ضمن هذا الجزء من البرنامج.
def _ensure_attendance_schema(conn):
    """Migrate older attendance tables to the current nullable-project design."""
    if not _table_exists(conn, "attendance"):
        return

    cols = _columns(conn, "attendance")
    needs_rebuild = (
        "working_hours" not in cols
        or "overtime_hours" not in cols
        or "notes" not in cols
        or ("project_id" in cols and cols["project_id"][3] == 1)
    )
    if not needs_rebuild:
        return

    conn.execute("ALTER TABLE attendance RENAME TO attendance_old")
    conn.execute("""
        CREATE TABLE attendance (
            record_id TEXT NOT NULL PRIMARY KEY,
            staff_id TEXT NOT NULL,
            project_id TEXT,
            date TEXT NOT NULL,
            working_hours REAL NOT NULL DEFAULT 0 CHECK(working_hours >= 0),
            overtime_hours REAL NOT NULL DEFAULT 0 CHECK(overtime_hours >= 0),
            status TEXT NOT NULL DEFAULT 'Present' CHECK(status IN ('Present','Absent','Leave','Sick','Holiday')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY(staff_id) REFERENCES staff(staff_id) ON DELETE RESTRICT ON UPDATE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE RESTRICT ON UPDATE CASCADE
        )
    """)

    old_cols = set(cols)
    if {"record_id", "staff_id", "date"}.issubset(old_cols):
        project_expr = "project_id" if "project_id" in old_cols else "NULL"
        wh_expr = "working_hours" if "working_hours" in old_cols else "attendance_value"
        ot_expr = "overtime_hours" if "overtime_hours" in old_cols else "0"
        status_expr = "status" if "status" in old_cols else "'Present'"
        notes_expr = "notes" if "notes" in old_cols else "NULL"
        conn.execute(f"""
            INSERT OR IGNORE INTO attendance
            (record_id, staff_id, project_id, date, working_hours, overtime_hours, status, notes)
            SELECT record_id, staff_id, {project_expr}, date,
                   COALESCE({wh_expr},0), COALESCE({ot_expr},0),
                   COALESCE({status_expr},'Present'), {notes_expr}
            FROM attendance_old
        """)

    conn.execute("DROP TABLE attendance_old")


# تنفيذ وظيفة create_database ضمن هذا الجزء من البرنامج.
# إنشاء قاعدة البيانات مع الحفاظ على دورة المعاملة الحالية.
def create_database():
    conn = get_connection()
    try:
        # تفعيل وضع WAL مرة واحدة أثناء التهيئة مع إبقاء الاتصالات اللاحقة مستقرة.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("BEGIN IMMEDIATE")
        try:
            if __package__ in (None, ""):
                from database.schema import initialize_database_schema
            else:
                from .schema import initialize_database_schema
        except ImportError:
            from database.schema import initialize_database_schema
        initialize_database_schema(conn)
        conn.commit()
    except (sqlite3.Error, ValueError, TypeError, OSError):
        conn.rollback()
        raise
    finally:
        conn.close()




# إضافة سجل جديد إلى النظام.
# =========================
# Expense Payments
# =========================

# إضافة سجل جديد إلى النظام.
def add_expense_payment(
    payment_id,
    expense_id,
    payment_date,
    amount,
    payment_method=None,
    reference=None,
    notes=None,
    conn=None,
):
    """Add a payment to an expense; accepts caller transaction connection."""

    owns = conn is None
    conn = conn or get_connection()

    try:
        conn.execute(
            """
            INSERT INTO expense_payments (
                payment_id,
                expense_id,
                payment_date,
                amount,
                payment_method,
                reference,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payment_id,
                expense_id,
                payment_date,
                amount,
                payment_method,
                reference,
                notes,
            ),
        )

        if owns:
            conn.commit()

    except (sqlite3.Error, ValueError, TypeError, OSError):
        if owns:
            conn.rollback()
        raise
    finally:
        if owns:
            conn.close()


# تنفيذ وظيفة get_expense_paid_amount ضمن هذا الجزء من البرنامج.
def get_expense_paid_amount(expense_id, conn=None):
    """Return the total amount already paid for an expense."""

    owns = conn is None
    conn = conn or get_connection()

    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS paid_amount
            FROM expense_payments
            WHERE expense_id = ?
            """,
            (expense_id,),
        ).fetchone()

        return float(row["paid_amount"] or 0)

    finally:
        if owns:
            conn.close()


# تنفيذ وظيفة get_expense_outstanding ضمن هذا الجزء من البرنامج.
def get_expense_outstanding(expense_id, conn=None):
    """Return the remaining unpaid amount."""

    owns = conn is None
    conn = conn or get_connection()

    try:
        row = conn.execute(
            """
            SELECT
                e.amount
                - COALESCE(
                    (
                        SELECT SUM(ep.amount)
                        FROM expense_payments ep
                        WHERE ep.expense_id = e.expense_id
                    ),
                    0
                ) AS outstanding
            FROM expenses e
            WHERE e.expense_id = ?
            """,
            (expense_id,),
        ).fetchone()

        if not row:
            return None

        return max(0, float(row["outstanding"] or 0))

    finally:
        if owns:
            conn.close()


# تنفيذ وظيفة get_expense_payment_history ضمن هذا الجزء من البرنامج.
def get_expense_payment_history(expense_id, conn=None):
    """Return the payment history of an expense."""

    owns = conn is None
    conn = conn or get_connection()

    try:
        return conn.execute(
            """
            SELECT
                payment_id,
                expense_id,
                payment_date,
                amount,
                payment_method,
                reference,
                notes,
                created_at
            FROM expense_payments
            WHERE expense_id = ?
            ORDER BY payment_date ASC, created_at ASC
            """,
            (expense_id,),
        ).fetchall()

    finally:
        if owns:
            conn.close()

        
if __name__ == "__main__":
    create_database()
    print(f"Database ready: {DATABASE_FILE}")
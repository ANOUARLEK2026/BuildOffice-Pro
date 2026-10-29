# ============================================================
# شرح الملف: database/migrations.py
# هذا الملف جزء من طبقة قاعدة البيانات والمخططات والترقيات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
"""ترحيلات آمنة وإضافية لمخطط قاعدة بيانات BuildOffice Pro.

الترحيلات لا تحذف سجلات المستخدم، وتحافظ على الأسماء القديمة للتوافق،
وتضيف التغييرات المطلوبة بطريقة تدريجية.
"""
from __future__ import annotations

import sqlite3


# شرح الدالة _table_exists: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


# شرح الدالة _columns: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}


# شرح الدالة _add_column: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _add_column(conn, table: str, column: str, definition: str) -> None:
    if column not in _columns(conn, table):
        conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}')


# شرح الدالة _ensure_version_table: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _ensure_version_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    if conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 0:
        conn.execute("INSERT INTO schema_version(version) VALUES (1)")


# شرح الدالة _version: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _version(conn) -> int:
    return int(conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] or 1)


# شرح الدالة _set_version: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _set_version(conn, version: int) -> None:
    conn.execute("UPDATE schema_version SET version=?, applied_at=CURRENT_TIMESTAMP", (version,))


# شرح الدالة _migration_2: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.


def _migration_2(conn) -> None:
    # حقول المشاريع المطلوبة لمساحة عمل المشاريع المتكاملة.
    _add_column(conn, "projects", "location", "TEXT")
    _add_column(conn, "projects", "description", "TEXT")
    _add_column(conn, "projects", "actual_completion_date", "TEXT")

    # بيانات إضافية لتكليف الموظفين بالمشاريع مع الحفاظ على المفاتيح والعلاقات الحالية.
    _add_column(conn, "staff_projects", "assignment_start_date", "TEXT")
    _add_column(conn, "staff_projects", "assignment_end_date", "TEXT")
    _add_column(conn, "staff_projects", "role_on_project", "TEXT")

    # مرفقات المصروفات تخزن كمسارات فقط، ولا تحذف الملفات الفعلية تلقائيًا.
    
    _add_column(conn, "expenses", "attachments", "TEXT")

    # إضافة بيانات المستندات مع الحفاظ على أسماء الجداول والأعمدة القديمة.
    _add_column(conn, "company documents", "category", "TEXT")
    _add_column(conn, "projects documents", "category", "TEXT")
    _add_column(conn, "projects documents", "related_entity", "TEXT")

    # إضافة بيانات تشغيل المركبات.
    _add_column(conn, "vehicles", "current_project_id", "TEXT")
    _add_column(conn, "vehicles", "vin", "TEXT")
    # لا توجد حاجة لإعادة بناء جدول المركبات؛ التحقق من العلاقة يتم في طبقة الخدمات.

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS project_payments (
            payment_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            date TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            payment_method TEXT,
            reference TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(project_id)
                ON DELETE RESTRICT ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS debt_payments (
            payment_id TEXT PRIMARY KEY,
            debt_id TEXT NOT NULL,
            payment_date TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            payment_method TEXT,
            reference TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(debt_id) REFERENCES debt(debt_id)
                ON DELETE CASCADE ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS maintenance_records (
            maintenance_id TEXT PRIMARY KEY,
            vehicle_id TEXT NOT NULL,
            maintenance_date TEXT NOT NULL,
            maintenance_type TEXT,
            description TEXT,
            cost REAL NOT NULL DEFAULT 0 CHECK(cost >= 0),
            mileage REAL CHECK(mileage IS NULL OR mileage >= 0),
            next_maintenance_date TEXT,
            project_id TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(vehicle_id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(project_id)
                ON DELETE SET NULL ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS fuel_records (
            fuel_id TEXT PRIMARY KEY,
            vehicle_id TEXT NOT NULL,
            date TEXT NOT NULL,
            quantity REAL NOT NULL CHECK(quantity > 0),
            unit_price REAL NOT NULL DEFAULT 0 CHECK(unit_price >= 0),
            total_cost REAL NOT NULL DEFAULT 0 CHECK(total_cost >= 0),
            mileage REAL CHECK(mileage IS NULL OR mileage >= 0),
            project_id TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(vehicle_id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(project_id)
                ON DELETE SET NULL ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS situations (
            situation_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            situation_number INTEGER NOT NULL,
            situation_date TEXT NOT NULL,
            title TEXT,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'Draft'
                CHECK(status IN ('Draft','Submitted','Approved','Paid')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            UNIQUE(project_id, situation_number),
            FOREIGN KEY(project_id) REFERENCES projects(project_id)
                ON DELETE CASCADE ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS situation_items (
            situation_item_id TEXT PRIMARY KEY,
            situation_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            executed_quantity REAL NOT NULL DEFAULT 0 CHECK(executed_quantity >= 0),
            unit_price REAL NOT NULL DEFAULT 0 CHECK(unit_price >= 0),
            amount REAL NOT NULL DEFAULT 0 CHECK(amount >= 0),
            previous_quantity REAL NOT NULL DEFAULT 0 CHECK(previous_quantity >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(situation_id, item_id),
            FOREIGN KEY(situation_id) REFERENCES situations(situation_id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(item_id) REFERENCES metre_items(item_id)
                ON DELETE RESTRICT ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS payroll_records (
            payroll_id TEXT PRIMARY KEY,
            staff_id TEXT NOT NULL,
            period TEXT NOT NULL,
            base_amount REAL NOT NULL DEFAULT 0 CHECK(base_amount >= 0),
            overtime_amount REAL NOT NULL DEFAULT 0 CHECK(overtime_amount >= 0),
            bonuses REAL NOT NULL DEFAULT 0 CHECK(bonuses >= 0),
            deductions REAL NOT NULL DEFAULT 0 CHECK(deductions >= 0),
            advances REAL NOT NULL DEFAULT 0 CHECK(advances >= 0),
            net_amount REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Draft',
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            UNIQUE(staff_id, period),
            FOREIGN KEY(staff_id) REFERENCES staff(staff_id)
                ON DELETE RESTRICT ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            user_name TEXT NOT NULL DEFAULT 'Local User',
            action TEXT NOT NULL,
            entity TEXT NOT NULL,
            entity_id TEXT,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'Info',
            entity TEXT,
            entity_id TEXT,
            is_read INTEGER NOT NULL DEFAULT 0 CHECK(is_read IN (0,1))
        );

        CREATE INDEX IF NOT EXISTS idx_project_payments_project_date
            ON project_payments(project_id, date);
        CREATE INDEX IF NOT EXISTS idx_debt_payments_debt_date
            ON debt_payments(debt_id, payment_date);
        CREATE INDEX IF NOT EXISTS idx_maintenance_vehicle_date
            ON maintenance_records(vehicle_id, maintenance_date);
        CREATE INDEX IF NOT EXISTS idx_maintenance_project
            ON maintenance_records(project_id);
        CREATE INDEX IF NOT EXISTS idx_fuel_vehicle_date
            ON fuel_records(vehicle_id, date);
        CREATE INDEX IF NOT EXISTS idx_fuel_project
            ON fuel_records(project_id);
        CREATE INDEX IF NOT EXISTS idx_situations_project_date
            ON situations(project_id, situation_date);
        CREATE INDEX IF NOT EXISTS idx_situation_items_situation
            ON situation_items(situation_id);
        CREATE INDEX IF NOT EXISTS idx_payroll_staff_period
            ON payroll_records(staff_id, period);
        CREATE INDEX IF NOT EXISTS idx_audit_entity
            ON audit_log(entity, entity_id);
        CREATE INDEX IF NOT EXISTS idx_notifications_unread
            ON notifications(is_read, created_at);
        CREATE INDEX IF NOT EXISTS idx_expenses_status
            ON expenses(payment_status);
        CREATE INDEX IF NOT EXISTS idx_documents_expiry
            ON "projects documents"(expiring_date);
        CREATE INDEX IF NOT EXISTS idx_company_documents_expiry
            ON "company documents"("expiring date");
    """)

    # كان القيد القديم يمنع تسجيل تجاوز المصروفات للميزانية. تتم إعادة بناء الجدول
    # للسماح بتمثيل الربح أو الخسارة الفعلية دون تغيير بيانات المستخدم.
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='projects'"
    ).fetchone()[0]
    if "revenue REAL NOT NULL DEFAULT 0" in sql and "CHECK(revenue >= 0)" in sql:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.executescript("""
            DROP TRIGGER IF EXISTS trg_expense_insert_project;
            DROP TRIGGER IF EXISTS trg_expense_update_project;
            DROP TRIGGER IF EXISTS trg_expense_delete_project;

            CREATE TABLE projects__new (
                project_id TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                summarised_name TEXT,
                contracting_authority TEXT,
                project_type TEXT,
                contract_code TEXT UNIQUE,
                contract_date TEXT,
                start_date TEXT,
                period INTEGER,
                end_date TEXT,
                budget_ht REAL NOT NULL DEFAULT 0 CHECK(budget_ht >= 0),
                tva_percent REAL NOT NULL DEFAULT 19 CHECK(tva_percent >= 0 AND tva_percent <= 100),
                tva REAL NOT NULL DEFAULT 0 CHECK(tva >= 0),
                budget_ttc REAL NOT NULL DEFAULT 0 CHECK(budget_ttc >= 0),
                expenses REAL NOT NULL DEFAULT 0 CHECK(expenses >= 0),
                revenue REAL NOT NULL DEFAULT 0,
                "revenue %" REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                location TEXT,
                description TEXT,
                actual_completion_date TEXT
            );

            INSERT INTO projects__new (
                project_id,project_name,summarised_name,contracting_authority,
                project_type,contract_code,contract_date,start_date,period,end_date,
                budget_ht,tva_percent,tva,budget_ttc,expenses,revenue,"revenue %",
                status,created_at,updated_at,location,description,actual_completion_date
            )
            SELECT project_id,project_name,summarised_name,contracting_authority,
                project_type,contract_code,contract_date,start_date,period,end_date,
                budget_ht,tva_percent,tva,budget_ttc,expenses,revenue,"revenue %",
                status,created_at,updated_at,location,description,actual_completion_date
            FROM projects;

            DROP TABLE projects;
            ALTER TABLE projects__new RENAME TO projects;

            CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
            CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(project_name);
            CREATE INDEX IF NOT EXISTS idx_projects_contract_code ON projects(contract_code);
        """)
        conn.execute("PRAGMA foreign_keys=ON")

        conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS trg_expense_insert_project
            AFTER INSERT ON expenses
            WHEN NEW.project_id IS NOT NULL
            BEGIN
                UPDATE projects SET
                    expenses=(SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project_id=NEW.project_id),
                    revenue=budget_ht-(SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project_id=NEW.project_id),
                    "revenue %"=CASE WHEN budget_ht>0 THEN
                        ((budget_ht-(SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project_id=NEW.project_id))/budget_ht)*100
                        ELSE 0 END,
                    updated_at=CURRENT_TIMESTAMP
                WHERE project_id=NEW.project_id;
            END;

            CREATE TRIGGER IF NOT EXISTS trg_expense_update_project
            AFTER UPDATE ON expenses
            BEGIN
                UPDATE projects SET
                    expenses=(SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project_id=projects.project_id),
                    revenue=budget_ht-(SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project_id=projects.project_id),
                    "revenue %"=CASE WHEN budget_ht>0 THEN
                        ((budget_ht-(SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project_id=projects.project_id))/budget_ht)*100
                        ELSE 0 END,
                    updated_at=CURRENT_TIMESTAMP
                WHERE project_id IN (OLD.project_id,NEW.project_id);
            END;

            CREATE TRIGGER IF NOT EXISTS trg_expense_delete_project
            AFTER DELETE ON expenses
            WHEN OLD.project_id IS NOT NULL
            BEGIN
                UPDATE projects SET
                    expenses=(SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project_id=OLD.project_id),
                    revenue=budget_ht-(SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project_id=OLD.project_id),
                    "revenue %"=CASE WHEN budget_ht>0 THEN
                        ((budget_ht-(SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project_id=OLD.project_id))/budget_ht)*100
                        ELSE 0 END,
                    updated_at=CURRENT_TIMESTAMP
                WHERE project_id=OLD.project_id;
            END;
        """)

    # توحيد قيد الضريبة للسماح بالمعدلات القابلة للضبط مع إبقاء القيم الحالية صالحة.
    conn.execute("INSERT OR IGNORE INTO settings(setting_key,setting_value) VALUES ('schema_version', '2')")


def _migration_3(conn) -> None:
    # إضافة تاريخ الاستحقاق للديون القديمة دون تغيير القيم الموجودة.
    _add_column(conn, "debt", "due_date", "TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_debt_due_date ON debt(due_date)")


def _migration_4(conn) -> None:
    """تقوية سلامة البيانات وتوحيد بيانات المستندات."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            owner_type TEXT NOT NULL CHECK(owner_type IN ('company','project','staff','vehicle','personal','general')),
            owner_id TEXT,
            document_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            category TEXT,
            issue_date TEXT,
            expiry_date TEXT,
            reminder_days INTEGER NOT NULL DEFAULT 30 CHECK(reminder_days >= 0),
            status TEXT NOT NULL DEFAULT 'Active',
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_documents_owner ON documents(owner_type, owner_id);
        CREATE INDEX IF NOT EXISTS idx_documents_expiry_v4 ON documents(expiry_date);
        CREATE INDEX IF NOT EXISTS idx_attendance_staff_date ON attendance(staff_id, date);
        CREATE INDEX IF NOT EXISTS idx_expenses_project_date ON expenses(project_id, date);
        CREATE INDEX IF NOT EXISTS idx_expense_payments_expense_date ON expense_payments(expense_id, payment_date);
        CREATE INDEX IF NOT EXISTS idx_debt_project_due ON debt(project_id, due_date);

        CREATE TRIGGER IF NOT EXISTS trg_expense_payment_insert_status
        AFTER INSERT ON expense_payments BEGIN
            UPDATE expenses SET payment_status = CASE
                WHEN (SELECT COALESCE(SUM(amount),0) FROM expense_payments WHERE expense_id=NEW.expense_id) >= amount THEN 'Paid'
                WHEN (SELECT COALESCE(SUM(amount),0) FROM expense_payments WHERE expense_id=NEW.expense_id) > 0 THEN 'Partial'
                WHEN due_date IS NOT NULL AND due_date < date('now') THEN 'Overdue' ELSE 'Unpaid' END,
                updated_at=CURRENT_TIMESTAMP WHERE expense_id=NEW.expense_id;
        END;
        CREATE TRIGGER IF NOT EXISTS trg_expense_payment_delete_status
        AFTER DELETE ON expense_payments BEGIN
            UPDATE expenses SET payment_status = CASE
                WHEN (SELECT COALESCE(SUM(amount),0) FROM expense_payments WHERE expense_id=OLD.expense_id) >= amount THEN 'Paid'
                WHEN (SELECT COALESCE(SUM(amount),0) FROM expense_payments WHERE expense_id=OLD.expense_id) > 0 THEN 'Partial'
                WHEN due_date IS NOT NULL AND due_date < date('now') THEN 'Overdue' ELSE 'Unpaid' END,
                updated_at=CURRENT_TIMESTAMP WHERE expense_id=OLD.expense_id;
        END;
        CREATE TRIGGER IF NOT EXISTS trg_expense_payment_update_status
        AFTER UPDATE ON expense_payments BEGIN
            UPDATE expenses SET payment_status = CASE
                WHEN (SELECT COALESCE(SUM(amount),0) FROM expense_payments WHERE expense_id=NEW.expense_id) >= amount THEN 'Paid'
                WHEN (SELECT COALESCE(SUM(amount),0) FROM expense_payments WHERE expense_id=NEW.expense_id) > 0 THEN 'Partial'
                WHEN due_date IS NOT NULL AND due_date < date('now') THEN 'Overdue' ELSE 'Unpaid' END,
                updated_at=CURRENT_TIMESTAMP WHERE expense_id=NEW.expense_id;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_attendance_duplicate_guard
        BEFORE INSERT ON attendance
        WHEN EXISTS (SELECT 1 FROM attendance a WHERE a.staff_id=NEW.staff_id AND a.project_id IS NEW.project_id AND a.date=NEW.date AND a.record_id<>NEW.record_id)
        BEGIN SELECT RAISE(ABORT, 'Duplicate attendance for staff, project and date'); END;
        CREATE TRIGGER IF NOT EXISTS trg_attendance_duplicate_guard_update
        BEFORE UPDATE OF staff_id,project_id,date ON attendance
        WHEN EXISTS (SELECT 1 FROM attendance a WHERE a.staff_id=NEW.staff_id AND a.project_id IS NEW.project_id AND a.date=NEW.date AND a.record_id<>NEW.record_id)
        BEGIN SELECT RAISE(ABORT, 'Duplicate attendance for staff, project and date'); END;

        CREATE TRIGGER IF NOT EXISTS trg_debt_payment_insert_status
        AFTER INSERT ON debt_payments BEGIN
            UPDATE debt SET status=CASE
                WHEN (SELECT COALESCE(SUM(amount),0) FROM debt_payments WHERE debt_id=NEW.debt_id)>=amount THEN 'Paid'
                WHEN (SELECT COALESCE(SUM(amount),0) FROM debt_payments WHERE debt_id=NEW.debt_id)>0 THEN 'Partial'
                WHEN due_date IS NOT NULL AND due_date<date('now') THEN 'Overdue' ELSE 'Open' END
            WHERE debt_id=NEW.debt_id;
        END;
        CREATE TRIGGER IF NOT EXISTS trg_debt_payment_delete_status
        AFTER DELETE ON debt_payments BEGIN
            UPDATE debt SET status=CASE
                WHEN (SELECT COALESCE(SUM(amount),0) FROM debt_payments WHERE debt_id=OLD.debt_id)>=amount THEN 'Paid'
                WHEN (SELECT COALESCE(SUM(amount),0) FROM debt_payments WHERE debt_id=OLD.debt_id)>0 THEN 'Partial'
                WHEN due_date IS NOT NULL AND due_date<date('now') THEN 'Overdue' ELSE 'Open' END
            WHERE debt_id=OLD.debt_id;
        END;
        CREATE TRIGGER IF NOT EXISTS trg_debt_payment_update_status
        AFTER UPDATE ON debt_payments BEGIN
            UPDATE debt SET status=CASE
                WHEN (SELECT COALESCE(SUM(amount),0) FROM debt_payments WHERE debt_id=NEW.debt_id)>=amount THEN 'Paid'
                WHEN (SELECT COALESCE(SUM(amount),0) FROM debt_payments WHERE debt_id=NEW.debt_id)>0 THEN 'Partial'
                WHEN due_date IS NOT NULL AND due_date<date('now') THEN 'Overdue' ELSE 'Open' END
            WHERE debt_id=NEW.debt_id;
        END;
    """)
    # توحيد قيم الحالات القديمة دون تغيير حقائق المدفوعات.
    conn.execute("UPDATE expenses SET payment_status='Partial' WHERE payment_status='Partial Payment'")


def _migration_5(conn) -> None:
    """إزالة فهارس مكررة لا تغيّر سلوك البرنامج وتقلل تكلفة الكتابة والصيانة."""
    # الفهرسان التاليان مكرران فعليًا، وإزالتهما لا تغيّر نتائج الاستعلامات.
    conn.execute("DROP INDEX IF EXISTS idx_exp_project_date")
    conn.execute("DROP INDEX IF EXISTS idx_projects_contract_code")


def _migration_6(conn) -> None:
    """Add durable situation finalization and generated-document tracking."""
    _add_column(conn, "situations", "is_final", "INTEGER NOT NULL DEFAULT 0")
    _add_column(conn, "situations", "finalized_at", "TEXT")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS situation_documents (
            document_id TEXT PRIMARY KEY,
            situation_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            document_name TEXT NOT NULL,
            document_path TEXT NOT NULL,
            document_type TEXT NOT NULL,
            generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(situation_id) REFERENCES situations(situation_id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(project_id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            UNIQUE(situation_id, document_path)
        );
        CREATE INDEX IF NOT EXISTS idx_situation_documents_situation
            ON situation_documents(situation_id);
        CREATE INDEX IF NOT EXISTS idx_situation_documents_project
            ON situation_documents(project_id);
    """)


def _migration_7(conn) -> None:
    """Add nature-specific document metadata without removing legacy fields."""
    for table in ("company documents", "projects documents"):
        _add_column(conn, table, "nature", "TEXT")
        _add_column(conn, table, "reference_no", "TEXT")
        _add_column(conn, table, "issue_date", "TEXT")
        _add_column(conn, table, "reminder_days", "INTEGER")
        _add_column(conn, table, "metadata_json", "TEXT")


def _migration_8(conn) -> None:
    """Add authentication and local license activation tables."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS app_users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Administrator',
            active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login_at TEXT
        );

        CREATE TABLE IF NOT EXISTS app_license (
            license_id TEXT PRIMARY KEY,
            license_key TEXT NOT NULL UNIQUE,
            customer_name TEXT NOT NULL,
            product_name TEXT NOT NULL,
            issued_at TEXT NOT NULL,
            expires_at TEXT,
            activated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            device_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active'
                CHECK(status IN ('Active','Expired','Revoked')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_app_users_active ON app_users(active);
        CREATE INDEX IF NOT EXISTS idx_app_license_status ON app_license(status);
    """)


def _migration_9(conn) -> None:
    """Add construction-control entities and analytical allocation fields."""
    for table, columns in {
        "expenses": [("cost_center_id", "TEXT"), ("boq_item_id", "TEXT")],
        "project_payments": [("situation_id", "TEXT"), ("payment_type", "TEXT")],
        "situations": [("gross_amount", "REAL NOT NULL DEFAULT 0"), ("retention_amount", "REAL NOT NULL DEFAULT 0"), ("advance_recovery", "REAL NOT NULL DEFAULT 0"), ("other_deductions", "REAL NOT NULL DEFAULT 0"), ("net_due", "REAL NOT NULL DEFAULT 0")],
    }.items():
        for col, definition in columns:
            _add_column(conn, table, col, definition)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS project_cost_centers (
            cost_center_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, code TEXT, name TEXT NOT NULL,
            budget_amount REAL NOT NULL DEFAULT 0 CHECK(budget_amount>=0), boq_item_id TEXT, parent_id TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(boq_item_id) REFERENCES metre_items(item_id) ON DELETE SET NULL ON UPDATE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_cost_centers_project ON project_cost_centers(project_id);

        CREATE TABLE IF NOT EXISTS labor_allocations (
            allocation_id TEXT PRIMARY KEY, staff_id TEXT NOT NULL, project_id TEXT NOT NULL, cost_center_id TEXT,
            work_date TEXT NOT NULL, hours REAL NOT NULL DEFAULT 0 CHECK(hours>=0), overtime_hours REAL NOT NULL DEFAULT 0 CHECK(overtime_hours>=0),
            hourly_cost REAL NOT NULL DEFAULT 0 CHECK(hourly_cost>=0), activity TEXT, notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(staff_id) REFERENCES staff(staff_id) ON DELETE RESTRICT ON UPDATE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(cost_center_id) REFERENCES project_cost_centers(cost_center_id) ON DELETE SET NULL ON UPDATE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_labor_project_date ON labor_allocations(project_id,work_date);

        CREATE TABLE IF NOT EXISTS equipment_usage (
            usage_id TEXT PRIMARY KEY, vehicle_id TEXT NOT NULL, project_id TEXT NOT NULL, cost_center_id TEXT, usage_date TEXT NOT NULL,
            operating_hours REAL NOT NULL DEFAULT 0 CHECK(operating_hours>=0), hourly_cost REAL NOT NULL DEFAULT 0 CHECK(hourly_cost>=0),
            fuel_cost REAL NOT NULL DEFAULT 0 CHECK(fuel_cost>=0), operator_staff_id TEXT, meter_start REAL, meter_end REAL, notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE RESTRICT ON UPDATE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(cost_center_id) REFERENCES project_cost_centers(cost_center_id) ON DELETE SET NULL ON UPDATE CASCADE,
            FOREIGN KEY(operator_staff_id) REFERENCES staff(staff_id) ON DELETE SET NULL ON UPDATE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_equipment_project_date ON equipment_usage(project_id,usage_date);

        CREATE TABLE IF NOT EXISTS materials (
            material_id TEXT PRIMARY KEY, code TEXT UNIQUE, name TEXT NOT NULL, unit TEXT, standard_cost REAL NOT NULL DEFAULT 0 CHECK(standard_cost>=0),
            minimum_stock REAL NOT NULL DEFAULT 0 CHECK(minimum_stock>=0), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS material_movements (
            movement_id TEXT PRIMARY KEY, material_id TEXT NOT NULL, project_id TEXT, movement_date TEXT NOT NULL,
            movement_type TEXT NOT NULL CHECK(movement_type IN ('Receipt','Transfer In','Transfer Out','Consumption','Adjustment')),
            warehouse TEXT, quantity REAL NOT NULL CHECK(quantity>0), unit_cost REAL NOT NULL DEFAULT 0 CHECK(unit_cost>=0), reference TEXT, notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(material_id) REFERENCES materials(material_id) ON DELETE RESTRICT ON UPDATE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE SET NULL ON UPDATE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_material_movements_material_date ON material_movements(material_id,movement_date);

        CREATE TABLE IF NOT EXISTS subcontractors (
            subcontractor_id TEXT PRIMARY KEY, name TEXT NOT NULL, contact TEXT, phone TEXT, tax_id TEXT, notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS subcontractor_contracts (
            contract_id TEXT PRIMARY KEY, subcontractor_id TEXT NOT NULL, project_id TEXT NOT NULL, contract_no TEXT, contract_date TEXT,
            contract_amount REAL NOT NULL DEFAULT 0 CHECK(contract_amount>=0), notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT,
            FOREIGN KEY(subcontractor_id) REFERENCES subcontractors(subcontractor_id) ON DELETE RESTRICT ON UPDATE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        CREATE TABLE IF NOT EXISTS subcontractor_situations (
            situation_id TEXT PRIMARY KEY, contract_id TEXT NOT NULL, situation_date TEXT NOT NULL, gross_amount REAL NOT NULL DEFAULT 0 CHECK(gross_amount>=0),
            retention_amount REAL NOT NULL DEFAULT 0 CHECK(retention_amount>=0), advance_recovery REAL NOT NULL DEFAULT 0 CHECK(advance_recovery>=0),
            other_deductions REAL NOT NULL DEFAULT 0 CHECK(other_deductions>=0), net_amount REAL NOT NULL DEFAULT 0 CHECK(net_amount>=0),
            progress_percent REAL, notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT,
            FOREIGN KEY(contract_id) REFERENCES subcontractor_contracts(contract_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        CREATE TABLE IF NOT EXISTS subcontractor_payments (
            payment_id TEXT PRIMARY KEY, situation_id TEXT NOT NULL, payment_date TEXT NOT NULL, amount REAL NOT NULL CHECK(amount>0),
            payment_method TEXT, reference TEXT, notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(situation_id) REFERENCES subcontractor_situations(situation_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_subcontract_project ON subcontractor_contracts(project_id);
    """)
    conn.execute("""UPDATE situations SET gross_amount=COALESCE((SELECT SUM(amount) FROM situation_items si WHERE si.situation_id=situations.situation_id),0), net_due=COALESCE((SELECT SUM(amount) FROM situation_items si WHERE si.situation_id=situations.situation_id),0) WHERE gross_amount=0""")


def _migration_10(conn) -> None:
    """Link site labor to attendance and add payroll reconciliation fields."""
    _add_column(conn, "labor_allocations", "attendance_id", "TEXT")
    _add_column(conn, "labor_allocations", "source_type", "TEXT NOT NULL DEFAULT 'Legacy'")
    for col, definition in [
        ("attendance_hours", "REAL NOT NULL DEFAULT 0"),
        ("attendance_overtime", "REAL NOT NULL DEFAULT 0"),
        ("allocated_hours", "REAL NOT NULL DEFAULT 0"),
        ("allocated_overtime", "REAL NOT NULL DEFAULT 0"),
        ("reconciliation_status", "TEXT NOT NULL DEFAULT 'Unreconciled'"),
    ]:
        _add_column(conn, "payroll_records", col, definition)
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_labor_attendance ON labor_allocations(attendance_id);
        CREATE INDEX IF NOT EXISTS idx_labor_staff_date ON labor_allocations(staff_id,work_date);
        CREATE INDEX IF NOT EXISTS idx_payroll_staff_period ON payroll_records(staff_id,period);
    """)
    conn.execute("""
        UPDATE labor_allocations
        SET source_type=CASE WHEN attendance_id IS NULL THEN 'Legacy' ELSE 'Attendance' END
        WHERE source_type IS NULL OR source_type=''
    """)


def _migration_11(conn) -> None:
    """Add supplementary works and management-intelligence persistence."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS supplementary_works (
            supplementary_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            work_number INTEGER NOT NULL,
            description TEXT NOT NULL,
            unit TEXT,
            quantity REAL,
            unit_price REAL,
            lump_sum_amount REAL,
            work_mode TEXT NOT NULL DEFAULT 'Pending' CHECK(work_mode IN ('Measured','Lump Sum','Pending')),
            work_date TEXT,
            reason TEXT,
            reference_no TEXT,
            status TEXT NOT NULL DEFAULT 'Draft' CHECK(status IN ('Draft','Submitted','Approved','Executed','Valued','Included','Paid')),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            UNIQUE(project_id, work_number),
            FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE ON UPDATE CASCADE,
            CHECK((work_mode='Measured' AND quantity IS NOT NULL AND unit_price IS NOT NULL) OR
                  (work_mode='Lump Sum' AND lump_sum_amount IS NOT NULL) OR
                  (work_mode='Pending'))
        );
        CREATE TABLE IF NOT EXISTS supplementary_situation_items (
            supplementary_situation_item_id TEXT PRIMARY KEY,
            situation_id TEXT NOT NULL,
            supplementary_id TEXT NOT NULL,
            executed_quantity REAL NOT NULL DEFAULT 0 CHECK(executed_quantity>=0),
            amount REAL NOT NULL DEFAULT 0 CHECK(amount>=0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(situation_id, supplementary_id),
            FOREIGN KEY(situation_id) REFERENCES situations(situation_id) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(supplementary_id) REFERENCES supplementary_works(supplementary_id) ON DELETE RESTRICT ON UPDATE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_supplementary_project ON supplementary_works(project_id, status);
        CREATE INDEX IF NOT EXISTS idx_supplementary_situation ON supplementary_situation_items(situation_id);
        CREATE TABLE IF NOT EXISTS intelligence_snapshots (
            snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            scope TEXT NOT NULL,
            project_id TEXT,
            payload_json TEXT NOT NULL
        );
    """)


def _migration_12(conn) -> None:
    """Add document/report metadata needed by the intelligent document engine."""
    _add_column(conn, "situations", "retention_percent", "REAL NOT NULL DEFAULT 0")
    _add_column(conn, "situations", "tva_percent", "REAL NOT NULL DEFAULT 19")
    _add_column(conn, "situations", "advance_percent", "REAL NOT NULL DEFAULT 0")


def _migration_13(conn) -> None:
    """Add durable quantity/unit/unit-price fields to expenses.

    The legacy ``amount`` column remains the authoritative total so existing
    analytics, payments and reports continue to work without a data rewrite.
    Existing expenses are migrated as lump-sum records: quantity=1 and
    unit_price=the legacy amount.
    """
    _add_column(conn, "expenses", "quantity", "REAL NOT NULL DEFAULT 1 CHECK(quantity > 0)")
    _add_column(conn, "expenses", "unit", "TEXT NOT NULL DEFAULT 'Lump Sum'")
    _add_column(conn, "expenses", "unit_price", "REAL NOT NULL DEFAULT 0 CHECK(unit_price >= 0)")

    # Preserve every historical total while giving old records a valid
    # quantity/unit/unit-price representation.
    conn.execute("""
        UPDATE expenses
        SET quantity = 1,
            unit = CASE WHEN TRIM(COALESCE(unit, '')) = '' THEN 'Lump Sum' ELSE unit END,
            unit_price = COALESCE(amount, 0)
        WHERE quantity IS NULL OR quantity <= 0
           OR unit IS NULL OR TRIM(unit) = ''
           OR unit_price IS NULL
           OR (unit_price = 0 AND COALESCE(amount, 0) > 0)
    """)


def _migration_14(conn) -> None:
    """Add optional company identity, branding and banking fields safely."""
    additions = {
        "legal form": "TEXT",
        "activity": "TEXT",
        "wilaya": "TEXT",
        "postal code": "TEXT",
        "website": "TEXT",
        "bank name": "TEXT",
        "bank account": "TEXT",
        "bank branch": "TEXT",
        "logo path": "TEXT",
        "notes": "TEXT",
    }
    for column, definition in additions.items():
        _add_column(conn, "company info", column, definition)


def _migration_15(conn) -> None:
    """Add a durable business-partner directory and project relationships.

    This is intentionally additive. Existing tables and historical records are
    preserved, while the new foundation gives future accounting/procurement
    modules a single source for clients and suppliers.
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS business_partners (
            partner_id TEXT PRIMARY KEY,
            partner_type TEXT NOT NULL DEFAULT 'Both'
                CHECK(partner_type IN ('Client','Supplier','Both')),
            legal_name TEXT NOT NULL,
            display_name TEXT,
            contact_person TEXT,
            phone TEXT,
            phone_2 TEXT,
            email TEXT,
            address TEXT,
            wilaya TEXT,
            postal_code TEXT,
            tax_id TEXT,
            nis TEXT,
            rc TEXT,
            ai TEXT,
            rib TEXT,
            bank_name TEXT,
            payment_terms_days INTEGER NOT NULL DEFAULT 0
                CHECK(payment_terms_days >= 0),
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'Active'
                CHECK(status IN ('Active','Inactive')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_business_partners_type_status
            ON business_partners(partner_type, status);
        CREATE INDEX IF NOT EXISTS idx_business_partners_name
            ON business_partners(legal_name);

        CREATE TABLE IF NOT EXISTS project_partners (
            project_id TEXT NOT NULL,
            partner_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL
                CHECK(relationship_type IN ('Client','Supplier')),
            is_primary INTEGER NOT NULL DEFAULT 0
                CHECK(is_primary IN (0,1)),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(project_id, partner_id, relationship_type),
            FOREIGN KEY(project_id) REFERENCES projects(project_id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(partner_id) REFERENCES business_partners(partner_id)
                ON DELETE RESTRICT ON UPDATE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_project_partners_project
            ON project_partners(project_id, relationship_type);
        CREATE INDEX IF NOT EXISTS idx_project_partners_partner
            ON project_partners(partner_id, relationship_type);

        CREATE TABLE IF NOT EXISTS media_items (
            media_id TEXT PRIMARY KEY,
            owner_type TEXT NOT NULL
                CHECK(owner_type IN (
                    'company','project','partner','staff','vehicle',
                    'expense','invoice','purchase','other'
                )),
            owner_id TEXT,
            media_type TEXT NOT NULL DEFAULT 'Document'
                CHECK(media_type IN ('Photo','Document','Receipt','Other')),
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            mime_type TEXT,
            file_size INTEGER NOT NULL DEFAULT 0
                CHECK(file_size >= 0),
            issue_date TEXT,
            expiry_date TEXT,
            description TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_media_owner
            ON media_items(owner_type, owner_id);
        CREATE INDEX IF NOT EXISTS idx_media_expiry
            ON media_items(expiry_date);
    """)


def _migration_16(conn) -> None:
    """Add the accounting core without replacing existing expense/payment data."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS chart_of_accounts (
            account_id TEXT PRIMARY KEY,
            account_code TEXT NOT NULL UNIQUE,
            account_name TEXT NOT NULL,
            account_type TEXT NOT NULL CHECK(account_type IN
                ('Asset','Liability','Equity','Revenue','Expense')),
            parent_id TEXT,
            is_cash_account INTEGER NOT NULL DEFAULT 0 CHECK(is_cash_account IN (0,1)),
            is_bank_account INTEGER NOT NULL DEFAULT 0 CHECK(is_bank_account IN (0,1)),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
            opening_balance REAL NOT NULL DEFAULT 0,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY(parent_id) REFERENCES chart_of_accounts(account_id)
                ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_accounts_type ON chart_of_accounts(account_type);
        CREATE INDEX IF NOT EXISTS idx_accounts_parent ON chart_of_accounts(parent_id);

        CREATE TABLE IF NOT EXISTS financial_accounts (
            financial_account_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            account_name TEXT NOT NULL,
            account_kind TEXT NOT NULL CHECK(account_kind IN ('Cash','Bank')),
            currency TEXT NOT NULL DEFAULT 'DZD',
            bank_name TEXT,
            account_number TEXT,
            rib TEXT,
            opening_balance REAL NOT NULL DEFAULT 0,
            current_balance REAL NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY(account_id) REFERENCES chart_of_accounts(account_id)
                ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_financial_accounts_kind
            ON financial_accounts(account_kind, is_active);

        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id TEXT PRIMARY KEY,
            invoice_number TEXT NOT NULL UNIQUE,
            invoice_type TEXT NOT NULL CHECK(invoice_type IN ('Sales','Purchase')),
            partner_id TEXT,
            project_id TEXT,
            invoice_date TEXT NOT NULL,
            due_date TEXT,
            subtotal REAL NOT NULL DEFAULT 0 CHECK(subtotal >= 0),
            discount REAL NOT NULL DEFAULT 0 CHECK(discount >= 0),
            tax_rate REAL NOT NULL DEFAULT 19 CHECK(tax_rate >= 0),
            tax_amount REAL NOT NULL DEFAULT 0 CHECK(tax_amount >= 0),
            total_amount REAL NOT NULL DEFAULT 0 CHECK(total_amount >= 0),
            paid_amount REAL NOT NULL DEFAULT 0 CHECK(paid_amount >= 0),
            status TEXT NOT NULL DEFAULT 'Draft'
                CHECK(status IN ('Draft','Issued','Partially Paid','Paid','Cancelled')),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY(partner_id) REFERENCES business_partners(partner_id)
                ON DELETE RESTRICT,
            FOREIGN KEY(project_id) REFERENCES projects(project_id)
                ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_invoices_partner_date
            ON invoices(partner_id, invoice_date);
        CREATE INDEX IF NOT EXISTS idx_invoices_project_date
            ON invoices(project_id, invoice_date);
        CREATE INDEX IF NOT EXISTS idx_invoices_status_due
            ON invoices(status, due_date);

        CREATE TABLE IF NOT EXISTS invoice_items (
            invoice_item_id TEXT PRIMARY KEY,
            invoice_id TEXT NOT NULL,
            description TEXT NOT NULL,
            quantity REAL NOT NULL DEFAULT 1 CHECK(quantity >= 0),
            unit TEXT,
            unit_price REAL NOT NULL DEFAULT 0 CHECK(unit_price >= 0),
            tax_rate REAL NOT NULL DEFAULT 19 CHECK(tax_rate >= 0),
            amount REAL NOT NULL DEFAULT 0 CHECK(amount >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(invoice_id) REFERENCES invoices(invoice_id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice
            ON invoice_items(invoice_id);

        CREATE TABLE IF NOT EXISTS journal_entries (
            journal_entry_id TEXT PRIMARY KEY,
            entry_number TEXT NOT NULL UNIQUE,
            entry_date TEXT NOT NULL,
            reference_type TEXT,
            reference_id TEXT,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Posted'
                CHECK(status IN ('Draft','Posted','Cancelled')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS journal_lines (
            journal_line_id TEXT PRIMARY KEY,
            journal_entry_id TEXT NOT NULL,
            account_id TEXT NOT NULL,
            partner_id TEXT,
            project_id TEXT,
            debit REAL NOT NULL DEFAULT 0 CHECK(debit >= 0),
            credit REAL NOT NULL DEFAULT 0 CHECK(credit >= 0),
            description TEXT,
            FOREIGN KEY(journal_entry_id) REFERENCES journal_entries(journal_entry_id)
                ON DELETE CASCADE,
            FOREIGN KEY(account_id) REFERENCES chart_of_accounts(account_id)
                ON DELETE RESTRICT,
            FOREIGN KEY(partner_id) REFERENCES business_partners(partner_id)
                ON DELETE RESTRICT,
            FOREIGN KEY(project_id) REFERENCES projects(project_id)
                ON DELETE SET NULL,
            CHECK((debit = 0 AND credit > 0) OR (credit = 0 AND debit > 0))
        );

        CREATE INDEX IF NOT EXISTS idx_journal_entries_date
            ON journal_entries(entry_date);
        CREATE INDEX IF NOT EXISTS idx_journal_lines_account
            ON journal_lines(account_id);
        CREATE INDEX IF NOT EXISTS idx_journal_lines_project
            ON journal_lines(project_id);
        CREATE INDEX IF NOT EXISTS idx_journal_lines_partner
            ON journal_lines(partner_id);

        CREATE TABLE IF NOT EXISTS cash_transactions (
            transaction_id TEXT PRIMARY KEY,
            transaction_number TEXT NOT NULL UNIQUE,
            transaction_date TEXT NOT NULL,
            financial_account_id TEXT NOT NULL,
            transaction_type TEXT NOT NULL CHECK(transaction_type IN
                ('Receipt','Payment','Transfer In','Transfer Out')),
            partner_id TEXT,
            project_id TEXT,
            amount REAL NOT NULL CHECK(amount > 0),
            reference TEXT,
            description TEXT,
            journal_entry_id TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(financial_account_id) REFERENCES financial_accounts(financial_account_id)
                ON DELETE RESTRICT,
            FOREIGN KEY(partner_id) REFERENCES business_partners(partner_id)
                ON DELETE RESTRICT,
            FOREIGN KEY(project_id) REFERENCES projects(project_id)
                ON DELETE SET NULL,
            FOREIGN KEY(journal_entry_id) REFERENCES journal_entries(journal_entry_id)
                ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_cash_transactions_account_date
            ON cash_transactions(financial_account_id, transaction_date);
        CREATE INDEX IF NOT EXISTS idx_cash_transactions_project_date
            ON cash_transactions(project_id, transaction_date);

        CREATE TABLE IF NOT EXISTS payment_allocations (
            allocation_id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            invoice_id TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(transaction_id) REFERENCES cash_transactions(transaction_id)
                ON DELETE CASCADE,
            FOREIGN KEY(invoice_id) REFERENCES invoices(invoice_id)
                ON DELETE RESTRICT,
            UNIQUE(transaction_id, invoice_id)
        );

        CREATE INDEX IF NOT EXISTS idx_payment_allocations_invoice
            ON payment_allocations(invoice_id);

        CREATE TABLE IF NOT EXISTS accounting_periods (
            period_id TEXT PRIMARY KEY,
            period_name TEXT NOT NULL UNIQUE,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open'
                CHECK(status IN ('Open','Closed')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK(end_date >= start_date)
        );

        CREATE TABLE IF NOT EXISTS financial_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT,
            updated_at TEXT
        );
    """)


def _migration_17(conn) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS accounting_mappings (
            mapping_id TEXT PRIMARY KEY, transaction_kind TEXT NOT NULL UNIQUE,
            debit_account_id TEXT NOT NULL, credit_account_id TEXT NOT NULL,
            description TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT,
            FOREIGN KEY(debit_account_id) REFERENCES chart_of_accounts(account_id) ON DELETE RESTRICT,
            FOREIGN KEY(credit_account_id) REFERENCES chart_of_accounts(account_id) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS accounting_postings (
            posting_id TEXT PRIMARY KEY, source_type TEXT NOT NULL, source_id TEXT NOT NULL,
            journal_entry_id TEXT NOT NULL, posted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_type, source_id), FOREIGN KEY(journal_entry_id) REFERENCES journal_entries(journal_entry_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS invoice_payments (
            invoice_payment_id TEXT PRIMARY KEY, invoice_id TEXT NOT NULL, payment_date TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0), financial_account_id TEXT NOT NULL, payment_method TEXT,
            reference TEXT, notes TEXT, cash_transaction_id TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(invoice_id) REFERENCES invoices(invoice_id) ON DELETE RESTRICT,
            FOREIGN KEY(financial_account_id) REFERENCES financial_accounts(financial_account_id) ON DELETE RESTRICT,
            FOREIGN KEY(cash_transaction_id) REFERENCES cash_transactions(transaction_id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_invoice_payments_invoice ON invoice_payments(invoice_id);
    """)
    # Ensure VAT accounts exist without changing existing account IDs.
    defaults=[('4456','TVA déductible','Asset'),('4457','TVA collectée','Liability')]
    import uuid
    for code,name,typ in defaults:
        if not conn.execute('SELECT 1 FROM chart_of_accounts WHERE account_code=?',(code,)).fetchone():
            conn.execute('INSERT INTO chart_of_accounts(account_id,account_code,account_name,account_type) VALUES(?,?,?,?)',(f'ACC-{uuid.uuid4().hex[:12].upper()}',code,name,typ))


def _migration_18(conn) -> None:
    """Add procurement workflow and payroll project allocations."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS purchase_orders (
            purchase_order_id TEXT PRIMARY KEY,
            order_number TEXT NOT NULL UNIQUE,
            supplier_id TEXT, project_id TEXT, order_date TEXT NOT NULL,
            expected_date TEXT, status TEXT NOT NULL DEFAULT 'Draft'
                CHECK(status IN ('Draft','Submitted','Approved','Partially Received','Received','Cancelled')),
            subtotal REAL NOT NULL DEFAULT 0 CHECK(subtotal>=0), discount REAL NOT NULL DEFAULT 0 CHECK(discount>=0),
            tax_amount REAL NOT NULL DEFAULT 0 CHECK(tax_amount>=0), total_amount REAL NOT NULL DEFAULT 0 CHECK(total_amount>=0),
            notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT,
            FOREIGN KEY(supplier_id) REFERENCES business_partners(partner_id) ON DELETE RESTRICT,
            FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE SET NULL ON UPDATE CASCADE
        );
        CREATE TABLE IF NOT EXISTS purchase_order_items (
            purchase_order_item_id TEXT PRIMARY KEY, purchase_order_id TEXT NOT NULL, material_id TEXT,
            description TEXT NOT NULL, quantity REAL NOT NULL CHECK(quantity>0), unit TEXT, unit_price REAL NOT NULL DEFAULT 0 CHECK(unit_price>=0),
            tax_rate REAL NOT NULL DEFAULT 19 CHECK(tax_rate>=0), amount REAL NOT NULL DEFAULT 0 CHECK(amount>=0), received_quantity REAL NOT NULL DEFAULT 0 CHECK(received_quantity>=0),
            cost_center_id TEXT, notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders(purchase_order_id) ON DELETE CASCADE,
            FOREIGN KEY(material_id) REFERENCES materials(material_id) ON DELETE SET NULL,
            FOREIGN KEY(cost_center_id) REFERENCES project_cost_centers(cost_center_id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_po_supplier_date ON purchase_orders(supplier_id,order_date);
        CREATE INDEX IF NOT EXISTS idx_po_project_date ON purchase_orders(project_id,order_date);
        CREATE TABLE IF NOT EXISTS purchase_receipts (
            receipt_id TEXT PRIMARY KEY, purchase_order_id TEXT NOT NULL, receipt_number TEXT NOT NULL UNIQUE,
            receipt_date TEXT NOT NULL, warehouse TEXT, notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders(purchase_order_id) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS purchase_receipt_items (
            receipt_item_id TEXT PRIMARY KEY, receipt_id TEXT NOT NULL, purchase_order_item_id TEXT NOT NULL,
            quantity REAL NOT NULL CHECK(quantity>0), unit_cost REAL NOT NULL DEFAULT 0 CHECK(unit_cost>=0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(receipt_id) REFERENCES purchase_receipts(receipt_id) ON DELETE CASCADE,
            FOREIGN KEY(purchase_order_item_id) REFERENCES purchase_order_items(purchase_order_item_id) ON DELETE RESTRICT
        );
        CREATE INDEX IF NOT EXISTS idx_receipts_po ON purchase_receipts(purchase_order_id);
        CREATE TABLE IF NOT EXISTS payroll_allocations (
            payroll_allocation_id TEXT PRIMARY KEY, payroll_id TEXT NOT NULL, project_id TEXT NOT NULL, cost_center_id TEXT,
            amount REAL NOT NULL CHECK(amount>=0), hours REAL NOT NULL DEFAULT 0 CHECK(hours>=0), notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(payroll_id) REFERENCES payroll_records(payroll_id) ON DELETE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
            FOREIGN KEY(cost_center_id) REFERENCES project_cost_centers(cost_center_id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_payroll_alloc_project ON payroll_allocations(project_id);
    """)


def _migration_19(conn) -> None:
    """Add daily site reporting without replacing existing construction-control data."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS site_daily_reports (
            report_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            report_number TEXT NOT NULL UNIQUE,
            report_date TEXT NOT NULL,
            weather TEXT,
            manpower_count INTEGER NOT NULL DEFAULT 0 CHECK(manpower_count >= 0),
            progress_percent REAL NOT NULL DEFAULT 0 CHECK(progress_percent >= 0 AND progress_percent <= 100),
            work_performed TEXT,
            materials_used TEXT,
            equipment_used TEXT,
            delays TEXT,
            safety_notes TEXT,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'Draft' CHECK(status IN ('Draft','Submitted','Approved')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_site_reports_project_date ON site_daily_reports(project_id, report_date);
        CREATE INDEX IF NOT EXISTS idx_site_reports_status ON site_daily_reports(status);
    """)


def _migration_20(conn) -> None:
    """Add structured daily progress and report-resource links without duplicating source transactions."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS site_report_progress (
            progress_id TEXT PRIMARY KEY, report_id TEXT NOT NULL, item_id TEXT NOT NULL,
            executed_quantity REAL NOT NULL DEFAULT 0 CHECK(executed_quantity >= 0),
            notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(report_id) REFERENCES site_daily_reports(report_id) ON DELETE CASCADE,
            FOREIGN KEY(item_id) REFERENCES metre_items(item_id) ON DELETE RESTRICT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_site_report_progress_item ON site_report_progress(report_id,item_id);
        CREATE INDEX IF NOT EXISTS idx_site_progress_item ON site_report_progress(item_id);
        CREATE TABLE IF NOT EXISTS site_report_resources (
            resource_link_id TEXT PRIMARY KEY, report_id TEXT NOT NULL, resource_type TEXT NOT NULL
                CHECK(resource_type IN ('Labor','Material','Equipment')),
            source_id TEXT NOT NULL, quantity REAL NOT NULL DEFAULT 0 CHECK(quantity >= 0),
            unit_cost REAL NOT NULL DEFAULT 0 CHECK(unit_cost >= 0), total_cost REAL NOT NULL DEFAULT 0 CHECK(total_cost >= 0),
            notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(report_id) REFERENCES site_daily_reports(report_id) ON DELETE CASCADE
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_site_report_resource ON site_report_resources(report_id,resource_type,source_id);
        CREATE INDEX IF NOT EXISTS idx_site_resource_report ON site_report_resources(report_id);
    """)


def _migration_21(conn) -> None:
    """Add project governance registers without changing existing business tables."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS project_milestones (
            milestone_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            planned_date TEXT NOT NULL,
            actual_date TEXT,
            status TEXT NOT NULL DEFAULT 'Open'
                CHECK(status IN ('Open','In Progress','Completed','Delayed','Cancelled')),
            priority INTEGER NOT NULL DEFAULT 3 CHECK(priority BETWEEN 1 AND 5),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_milestones_project_date ON project_milestones(project_id, planned_date);
        CREATE TABLE IF NOT EXISTS project_risks (
            risk_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT,
            probability INTEGER NOT NULL DEFAULT 3 CHECK(probability BETWEEN 1 AND 5),
            impact INTEGER NOT NULL DEFAULT 3 CHECK(impact BETWEEN 1 AND 5),
            score INTEGER NOT NULL DEFAULT 9 CHECK(score BETWEEN 1 AND 25),
            status TEXT NOT NULL DEFAULT 'Open'
                CHECK(status IN ('Open','Monitoring','Mitigated','Closed')),
            owner TEXT,
            due_date TEXT,
            mitigation TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_project_risks_project_score ON project_risks(project_id, score DESC);
        CREATE TABLE IF NOT EXISTS governance_actions (
            action_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            owner TEXT,
            due_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open'
                CHECK(status IN ('Open','In Progress','Completed','Cancelled')),
            priority INTEGER NOT NULL DEFAULT 3 CHECK(priority BETWEEN 1 AND 5),
            source_type TEXT,
            source_id TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_governance_actions_project_due ON governance_actions(project_id, due_date);
    """)


def _migration_22(conn) -> None:
    """Add durable, deduplicated intelligence alerts for executive control."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS intelligence_alerts (
            alert_id TEXT PRIMARY KEY,
            fingerprint TEXT NOT NULL UNIQUE,
            project_id TEXT,
            severity TEXT NOT NULL DEFAULT 'INFO'
                CHECK(severity IN ('CRITICAL','HIGH','MEDIUM','LOW','INFO')),
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            source_type TEXT,
            source_id TEXT,
            first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
            resolved_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_intelligence_alerts_active ON intelligence_alerts(is_active,severity);
        CREATE INDEX IF NOT EXISTS idx_intelligence_alerts_project ON intelligence_alerts(project_id,is_active);
    """)


CURRENT_SCHEMA_VERSION = 22


def apply_migrations(conn) -> None:
    """Apply every schema migration exactly once and keep the process idempotent."""
    _ensure_version_table(conn)
    v = _version(conn)
    migrations = {
        2: _migration_2,
        3: _migration_3,
        4: _migration_4,
        5: _migration_5,
        6: _migration_6,
        7: _migration_7,
        8: _migration_8,
        9: _migration_9,
        10: _migration_10,
        11: _migration_11,
        12: _migration_12,
        13: _migration_13,
        14: _migration_14,
        15: _migration_15,
        16: _migration_16,
        17: _migration_17,
        18: _migration_18,
        19: _migration_19,
        20: _migration_20,
        21: _migration_21,
        22: _migration_22,
    }
    for version in range(v + 1, CURRENT_SCHEMA_VERSION + 1):
        migrations[version](conn)
        _set_version(conn, version)
    conn.commit()


# ============================================================
# شرح الملف: database/schema.py
# هذا الملف جزء من طبقة قاعدة البيانات والمخططات والترقيات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""تهيئة مخطط قاعدة بيانات BuildOffice Pro بصورة مستقلة عن فتح الاتصال."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from .migrations import apply_migrations
except ImportError:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from database.migrations import apply_migrations



# شرح الدالة _table_exists: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _table_exists(conn, name: str) -> bool:
    """التحقق من وجود جدول قبل محاولة ترحيله."""
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


# شرح الدالة _columns: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _columns(conn, table: str) -> dict:
    """قراءة تعريفات أعمدة الجدول المطلوب."""
    return {row[1]: row for row in conn.execute(f'PRAGMA table_info("{table}")')}


# شرح الدالة _ensure_attendance_schema: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _ensure_attendance_schema(conn) -> None:
    """ترحيل جدول الحضور القديم إلى المخطط الحالي عند الحاجة."""
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
            FOREIGN KEY(attendance_id) REFERENCES attendance(record_id) ON DELETE RESTRICT ON UPDATE CASCADE,
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


# شرح الدالة initialize_database_schema: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def initialize_database_schema(conn) -> None:
    """إنشاء الجداول والفهارس والمشغلات ثم تطبيق الترحيلات."""
    c = conn.cursor()

    # =========================
    # معلومات الشركة
    # =========================

    c.executescript("""
    CREATE TABLE IF NOT EXISTS "company info" (
        id INTEGER PRIMARY KEY,
        "company name" TEXT NOT NULL,
        "company name ar" TEXT,
        owner TEXT,
        address TEXT,
        "phone 1" TEXT,
        "phone 2" TEXT,
        fax TEXT,
        "email 1" TEXT,
        "email 2" TEXT,
        "reg com" TEXT,
        nif TEXT,
        nis TEXT,
        bea TEXT,
        cpa TEXT,
        created_at TEXT NOT NULL
            DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT
    );


    -- =========================
    -- المشاريع
    -- =========================

    CREATE TABLE IF NOT EXISTS projects (
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

        budget_ht REAL NOT NULL DEFAULT 0
            CHECK(budget_ht >= 0),

        tva_percent REAL NOT NULL DEFAULT 19
            CHECK(tva_percent IN (0, 9, 19)),

        tva REAL NOT NULL DEFAULT 0
            CHECK(tva >= 0),

        budget_ttc REAL NOT NULL DEFAULT 0
            CHECK(budget_ttc >= 0),

        expenses REAL NOT NULL DEFAULT 0
            CHECK(expenses >= 0),

        -- الربح التقديري للمشروع
        revenue REAL NOT NULL DEFAULT 0
            CHECK(revenue >= 0),

        "revenue %" REAL NOT NULL DEFAULT 0
            CHECK("revenue %" >= 0),

        status TEXT NOT NULL DEFAULT 'Active',

        created_at TEXT NOT NULL
            DEFAULT CURRENT_TIMESTAMP,

        updated_at TEXT
    );


    -- =========================
    -- العمال والموظفون
    -- =========================

    CREATE TABLE IF NOT EXISTS staff (
        staff_id TEXT PRIMARY KEY,
        full_name TEXT NOT NULL,
        position TEXT,
        placement TEXT,
        employment_type TEXT,
        salary_type TEXT,

        rate REAL
            CHECK(rate IS NULL OR rate >= 0),

        hire_date TEXT,
        phone TEXT,

        status TEXT NOT NULL DEFAULT 'Active',

        notes TEXT,

        visible INTEGER NOT NULL DEFAULT 1
            CHECK(visible IN (0, 1)),

        attendance_type TEXT NOT NULL DEFAULT 'On Site',

        created_at TEXT NOT NULL
            DEFAULT CURRENT_TIMESTAMP,

        updated_at TEXT
    );


    -- =========================
    -- ربط العمال بالمشاريع
    -- =========================

    CREATE TABLE IF NOT EXISTS staff_projects (
        staff_id TEXT NOT NULL,
        project_id TEXT NOT NULL,

        active INTEGER NOT NULL DEFAULT 1
            CHECK(active IN (0, 1)),

        PRIMARY KEY(staff_id, project_id),

        FOREIGN KEY(staff_id)
            REFERENCES staff(staff_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE,

        FOREIGN KEY(project_id)
            REFERENCES projects(project_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    );


    -- =========================
    -- الحضور
    -- =========================

    CREATE TABLE IF NOT EXISTS attendance (
        record_id TEXT NOT NULL PRIMARY KEY,

        staff_id TEXT NOT NULL,
        project_id TEXT,

        date TEXT NOT NULL,

        working_hours REAL NOT NULL DEFAULT 0
            CHECK(working_hours >= 0),

        overtime_hours REAL NOT NULL DEFAULT 0
            CHECK(overtime_hours >= 0),

        status TEXT NOT NULL DEFAULT 'Present'
            CHECK(
                status IN (
                    'Present',
                    'Absent',
                    'Leave',
                    'Sick',
                    'Holiday'
                )
            ),

        created_at TEXT NOT NULL
            DEFAULT CURRENT_TIMESTAMP,

        notes TEXT,

        FOREIGN KEY(staff_id)
            REFERENCES staff(staff_id)
            ON DELETE RESTRICT
            ON UPDATE CASCADE,

        FOREIGN KEY(project_id)
            REFERENCES projects(project_id)
            ON DELETE RESTRICT
            ON UPDATE CASCADE
    );


    -- =========================
    -- المصاريف
    -- =========================

    CREATE TABLE IF NOT EXISTS expenses (
        expense_id TEXT PRIMARY KEY,

        project_id TEXT,

        date TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT,

        amount REAL NOT NULL
            CHECK(amount >= 0),

        quantity REAL NOT NULL DEFAULT 1
            CHECK(quantity > 0),

        unit TEXT NOT NULL DEFAULT 'Lump Sum',

        unit_price REAL NOT NULL DEFAULT 0
            CHECK(unit_price >= 0),

        payment_method TEXT,

        payment_status TEXT NOT NULL
            DEFAULT 'Paid',

        due_date TEXT,

        notes TEXT,

        created_at TEXT NOT NULL
            DEFAULT CURRENT_TIMESTAMP,

        updated_at TEXT,

        FOREIGN KEY(project_id)
            REFERENCES projects(project_id)
            ON DELETE RESTRICT
            ON UPDATE CASCADE
    );

    -- =========================
    -- دفعات المصاريف
    -- =========================

    CREATE TABLE IF NOT EXISTS expense_payments (
        payment_id TEXT PRIMARY KEY,

        expense_id TEXT NOT NULL,

        payment_date TEXT NOT NULL,

        amount REAL NOT NULL
            CHECK(amount > 0),

        payment_method TEXT,

        reference TEXT,

        notes TEXT,

        created_at TEXT NOT NULL
            DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(expense_id)
            REFERENCES expenses(expense_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    );

    CREATE INDEX IF NOT EXISTS
        idx_expense_payments_expense_date
    ON expense_payments(expense_id, payment_date);

    -- =========================
    -- المترية
    -- =========================

    CREATE TABLE IF NOT EXISTS metre_items (
        item_id TEXT PRIMARY KEY,

        project_id TEXT NOT NULL,
        item_number TEXT,

        description TEXT NOT NULL,
        unit TEXT,

        quantity REAL NOT NULL DEFAULT 0
            CHECK(quantity >= 0),

        unit_price REAL NOT NULL DEFAULT 0
            CHECK(unit_price >= 0),

        amount REAL NOT NULL DEFAULT 0
            CHECK(amount >= 0),

        FOREIGN KEY(project_id)
            REFERENCES projects(project_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE,

        UNIQUE(project_id, item_number)
    );
    -- =========================
    -- وثائق الشركة
    -- =========================

    CREATE TABLE IF NOT EXISTS "company documents" (
        document_id TEXT PRIMARY KEY,

        "document name" TEXT NOT NULL,
        "document path" TEXT NOT NULL,

        "upload date" TEXT NOT NULL
            DEFAULT CURRENT_TIMESTAMP,

        "expiring date" TEXT,

        description TEXT,

        status TEXT NOT NULL DEFAULT 'Active',
        category TEXT,
        nature TEXT,
        reference_no TEXT,
        issue_date TEXT,
        reminder_days INTEGER,
        metadata_json TEXT
    );


    -- =========================
    -- وثائق المشاريع
    -- =========================

    CREATE TABLE IF NOT EXISTS "projects documents" (
        item_id TEXT PRIMARY KEY,

        project_id TEXT NOT NULL,

        document_name TEXT NOT NULL,
        document_path TEXT NOT NULL,

        upload_date TEXT NOT NULL
            DEFAULT CURRENT_TIMESTAMP,

        expiring_date TEXT,

        description TEXT,

        status TEXT NOT NULL DEFAULT 'Active',
        category TEXT,
        nature TEXT,
        reference_no TEXT,
        issue_date TEXT,
        reminder_days INTEGER,
        metadata_json TEXT,

        FOREIGN KEY(project_id)
            REFERENCES projects(project_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    );


    -- =========================
    -- الديون
    -- =========================

    CREATE TABLE IF NOT EXISTS debt (
        debt_id TEXT PRIMARY KEY,

        project_id TEXT,

        lender TEXT NOT NULL,
        date TEXT NOT NULL,

        amount REAL NOT NULL
            CHECK(amount >= 0),

        due_date TEXT,
        status TEXT NOT NULL DEFAULT 'Open',

        notes TEXT,

        FOREIGN KEY(project_id)
            REFERENCES projects(project_id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
    );


    -- =========================
    -- المركبات
    -- =========================

    CREATE TABLE IF NOT EXISTS vehicles (
        vehicle_id TEXT PRIMARY KEY,

        brand TEXT NOT NULL,
        model TEXT NOT NULL,

        serial_number TEXT,

        licence_plate TEXT NOT NULL UNIQUE,

        buy_date TEXT,

        notes TEXT,

        status TEXT NOT NULL DEFAULT 'Active',
        current_project_id TEXT,
        vin TEXT,

        FOREIGN KEY(current_project_id)
            REFERENCES projects(project_id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
    );


    -- =========================
    -- سجل المعرفات المحجوزة
    -- =========================
    -- =========================
    -- دفعات المشاريع
    -- =========================
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

    -- =========================
    -- دفعات الديون
    -- =========================
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

    -- =========================
    -- صيانة المركبات
    -- =========================
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

    -- =========================
    -- وقود المركبات
    -- =========================
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

    -- =========================
    -- تقدم المشاريع / Situations
    -- =========================
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
        is_final INTEGER NOT NULL DEFAULT 0,
        finalized_at TEXT,
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

    CREATE TABLE IF NOT EXISTS situation_documents (
        document_id TEXT PRIMARY KEY,
        situation_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        document_name TEXT NOT NULL,
        document_path TEXT NOT NULL,
        document_type TEXT NOT NULL,
        generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(situation_id, document_path),
        FOREIGN KEY(situation_id) REFERENCES situations(situation_id)
            ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY(project_id) REFERENCES projects(project_id)
            ON DELETE CASCADE ON UPDATE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_situation_documents_situation
        ON situation_documents(situation_id);
    CREATE INDEX IF NOT EXISTS idx_situation_documents_project
        ON situation_documents(project_id);

    -- =========================
    -- الرواتب
    -- =========================
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

    -- =========================
    -- التدقيق والإشعارات
    -- =========================
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

    CREATE TABLE IF NOT EXISTS id_sequences (
        sequence_key TEXT PRIMARY KEY,
        next_value INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS id_registry (
        entity_id TEXT PRIMARY KEY,
        entity_type TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    -- =========================
    -- الإعدادات
    -- =========================

    CREATE TABLE IF NOT EXISTS settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT
    );
    """)


    # =========================
    # إصلاح قاعدة البيانات القديمة
    # =========================

    columns = {
        row["name"]
        for row in c.execute(
            "PRAGMA table_info(projects)"
        ).fetchall()
    }

    # تحويل الاسم القديم إلى الاسم الجديد
    if "summerised name" in columns:
        if "summarised_name" not in columns:
            c.execute("""
                ALTER TABLE projects
                RENAME COLUMN "summerised name"
                TO summarised_name
            """)

        else:
            c.execute("""
                UPDATE projects
                SET summarised_name =
                    COALESCE(
                        summarised_name,
                        "summerised name"
                    )
                WHERE summarised_name IS NULL
            """)


    # =========================
    # تحديث نظام الحضور القديم
    # =========================

    _ensure_attendance_schema(conn)

    c.execute("""
        UPDATE staff
        SET attendance_type = 'On Site'
        WHERE attendance_type IN (
            'Chantier',
            'Projects',
            'Project'
        )
    """)

    c.execute("""
        UPDATE staff
        SET attendance_type = 'Administration'
        WHERE LOWER(TRIM(attendance_type))
            = 'administration'
    """)

    c.execute("""
        UPDATE staff
        SET attendance_type = 'Other'
        WHERE LOWER(TRIM(attendance_type))
            = 'other'
    """)


    # =========================
    # فهارس الحضور
    # =========================

    c.executescript("""
    CREATE UNIQUE INDEX IF NOT EXISTS
        idx_attendance_project_unique
    ON attendance(
        staff_id,
        project_id,
        date
    )
    WHERE project_id IS NOT NULL;


    CREATE UNIQUE INDEX IF NOT EXISTS
        idx_attendance_admin_unique
    ON attendance(
        staff_id,
        date
    )
    WHERE project_id IS NULL;


    CREATE INDEX IF NOT EXISTS
        idx_att_staff
    ON attendance(staff_id);


    CREATE INDEX IF NOT EXISTS
        idx_att_project_date
    ON attendance(project_id, date);


    -- =========================
    -- فهارس المصاريف
    -- =========================

    CREATE INDEX IF NOT EXISTS
        idx_exp_project_date
    ON expenses(project_id, date);


    CREATE INDEX IF NOT EXISTS
        idx_expense_date
    ON expenses(date);


    -- =========================
    -- فهارس المشاريع
    -- =========================

    CREATE INDEX IF NOT EXISTS
        idx_projects_status
    ON projects(status);


    CREATE INDEX IF NOT EXISTS
        idx_projects_name
    ON projects(project_name);


    -- =========================
    -- فهارس المترية
    -- =========================

    CREATE INDEX IF NOT EXISTS
        idx_metre_project
    ON metre_items(project_id);


    -- =========================
    -- فهارس الوثائق
    -- =========================

    CREATE INDEX IF NOT EXISTS
        idx_pd_project
    ON "projects documents"(project_id);


    -- =========================
    -- فهارس الديون
    -- =========================

    CREATE INDEX IF NOT EXISTS
        idx_debt_project
    ON debt(project_id);


    -- =========================
    -- فهارس العمال
    -- =========================

    CREATE INDEX IF NOT EXISTS
        idx_staff_name
    ON staff(full_name);
    """)


    # =========================
    # حساب مصاريف وربح المشروع
    # =========================

    c.executescript("""
    CREATE TRIGGER IF NOT EXISTS
        trg_expense_insert_project
    AFTER INSERT ON expenses
    WHEN NEW.project_id IS NOT NULL
    BEGIN

        UPDATE projects
        SET
            expenses = (
                SELECT COALESCE(
                    SUM(amount),
                    0
                )
                FROM expenses
                WHERE project_id = NEW.project_id
            ),

            revenue = (
                budget_ht -
                (
                    SELECT COALESCE(
                        SUM(amount),
                        0
                    )
                    FROM expenses
                    WHERE project_id = NEW.project_id
                )
            ),

            "revenue %" = CASE
                WHEN budget_ht > 0 THEN
                    (
                        (
                            budget_ht -
                            (
                                SELECT COALESCE(
                                    SUM(amount),
                                    0
                                )
                                FROM expenses
                                WHERE project_id = NEW.project_id
                            )
                        )
                        / budget_ht
                    ) * 100
                ELSE 0
            END,

            updated_at = CURRENT_TIMESTAMP

        WHERE project_id = NEW.project_id;

    END;


    CREATE TRIGGER IF NOT EXISTS
        trg_expense_update_project
    AFTER UPDATE ON expenses
    BEGIN

        UPDATE projects
        SET
            expenses = (
                SELECT COALESCE(
                    SUM(amount),
                    0
                )
                FROM expenses
                WHERE project_id = projects.project_id
            ),

            revenue = (
                budget_ht -
                (
                    SELECT COALESCE(
                        SUM(amount),
                        0
                    )
                    FROM expenses
                    WHERE project_id = projects.project_id
                )
            ),

            "revenue %" = CASE
                WHEN budget_ht > 0 THEN
                    (
                        (
                            budget_ht -
                            (
                                SELECT COALESCE(
                                    SUM(amount),
                                    0
                                )
                                FROM expenses
                                WHERE project_id = projects.project_id
                            )
                        )
                        / budget_ht
                    ) * 100
                ELSE 0
            END,

            updated_at = CURRENT_TIMESTAMP

        WHERE project_id IN (
            OLD.project_id,
            NEW.project_id
        );

    END;


    CREATE TRIGGER IF NOT EXISTS
        trg_expense_delete_project
    AFTER DELETE ON expenses
    WHEN OLD.project_id IS NOT NULL
    BEGIN

        UPDATE projects
        SET
            expenses = (
                SELECT COALESCE(
                    SUM(amount),
                    0
                )
                FROM expenses
                WHERE project_id = OLD.project_id
            ),

            revenue = (
                budget_ht -
                (
                    SELECT COALESCE(
                        SUM(amount),
                        0
                    )
                    FROM expenses
                    WHERE project_id = OLD.project_id
                )
            ),

            "revenue %" = CASE
                WHEN budget_ht > 0 THEN
                    (
                        (
                            budget_ht -
                            (
                                SELECT COALESCE(
                                    SUM(amount),
                                    0
                                )
                                FROM expenses
                                WHERE project_id = OLD.project_id
                            )
                        )
                        / budget_ht
                    ) * 100
                ELSE 0
            END,

            updated_at = CURRENT_TIMESTAMP

        WHERE project_id = OLD.project_id;

    END;
    """)


    # =========================
    # إعادة حساب المشاريع الحالية
    # =========================

    c.execute("""
        UPDATE projects
        SET
            expenses = COALESCE(
                (
                    SELECT SUM(e.amount)
                    FROM expenses e
                    WHERE e.project_id =
                          projects.project_id
                ),
                0
            )
    """)

    c.execute("""
        UPDATE projects
        SET
            revenue =
                budget_ht - expenses,

            "revenue %" = CASE
                WHEN budget_ht > 0 THEN
                    (
                        (budget_ht - expenses)
                        / budget_ht
                    ) * 100
                ELSE 0
            END
    """)


    apply_migrations(conn)
    conn.commit()

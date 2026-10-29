# ============================================================
# شرح الملف: tests/test_id_and_health.py
# هذا الملف جزء من اختبارات السلامة والتكامل وصحة الوظائف.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# شرح الدالة test_id_reservation_is_transactional_and_non_reusing:
# تتحقق من أن حجز المعرفات متسلسل ولا يعيد استخدام المعرف المحذوف.
def test_id_reservation_is_transactional_and_non_reusing():
    import database.database as db
    from pages.id_service import next_child_id, next_sequence_id

    with tempfile.TemporaryDirectory() as td:
        old = db.DATABASE_FILE
        setattr(db, "DATABASE_FILE", Path(td) / "id.db")

        conn = None

        try:
            db.create_database()

            conn = db.get_connection()

            first = next_sequence_id(
                conn,
                "prj",
                digits=3,
            )

            conn.execute(
                """
                INSERT INTO projects(
                    project_id,
                    project_name,
                    budget_ht,
                    budget_ttc
                )
                VALUES(?,?,?,?)
                """,
                (
                    first,
                    "A",
                    1,
                    1,
                ),
            )
            conn.commit()

            child = next_child_id(
                conn,
                "mtr",
                first,
                digits=3,
            )

            conn.execute(
                """
                INSERT INTO metre_items(
                    item_id,
                    project_id,
                    description,
                    quantity,
                    unit_price,
                    amount
                )
                VALUES(?,?,?,?,?,?)
                """,
                (
                    child,
                    first,
                    "x",
                    1,
                    2,
                    2,
                ),
            )
            conn.commit()

            conn.execute(
                "DELETE FROM metre_items WHERE item_id=?",
                (child,),
            )
            conn.commit()

            child2 = next_child_id(
                conn,
                "mtr",
                first,
                digits=3,
            )

            assert child2 != child
            assert child2.endswith("-002")

        finally:
            if conn is not None:
                conn.close()

            db.DATABASE_FILE = old


# شرح الدالة test_database_health:
# تتحقق من سلامة قاعدة البيانات الأساسية وعدد الجداول وأخطاء العلاقات.
def test_database_health():
    import database.database as db
    from services.data_quality_service import database_health

    with tempfile.TemporaryDirectory() as td:
        old = db.DATABASE_FILE
        setattr(db, "DATABASE_FILE", Path(td) / "health.db")

        try:
            db.create_database()

            result = database_health()

            assert result["integrity"] == "ok"
            assert result["foreign_key_errors"] == 0
            assert result["tables"] >= 15

        finally:
            db.DATABASE_FILE = old
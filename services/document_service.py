# ============================================================
# شرح الملف: services/document_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Document categorization and retrieval helpers for the Documents library."""
from __future__ import annotations

import sqlite3
from typing import Any

from repositories.db import get_connection

# Stable internal category keys. Keep these values in the database so UI language
# changes do not rewrite existing records.
DOCUMENT_CATEGORIES = (
    ("Contracts", "📑", "Agreements, contracts and amendments"),
    ("BOQ / Métré", "📐", "Bill of quantities, métré and pricing files"),
    ("Situations", "🏗", "Progress situations and generated situation packages"),
    ("Payments", "💰", "Invoices, payment requests and receipts"),
    ("Administrative", "🗂", "Official letters, requests and administrative files"),
    ("Certificates", "📜", "Certificates, attestations and compliance documents"),
    ("Technical", "⚙", "Plans, drawings, specifications and technical studies"),
    ("HR / Staff", "👥", "Personnel, employment and staff-related records"),
    ("Insurance & Tax", "🛡", "Insurance, tax and statutory records"),
    ("Correspondence", "✉", "Incoming/outgoing correspondence"),
    ("Other", "📁", "Documents that do not fit another category"),
)

_CATEGORY_KEYS = {key for key, _icon, _description in DOCUMENT_CATEGORIES}


DOCUMENT_NATURES = {
    "company": (
        ("Staff", "👤"), ("Invoice", "🧾"), ("Renting", "🏠"), ("Legal", "⚖"),
        ("Tax", "🧮"), ("Insurance", "🛡"), ("Certificate", "📜"),
        ("Company Contract", "📑"), ("Administrative", "🗂"), ("Correspondence", "✉"), ("Other", "📁"),
    ),
    "project": (
        ("Contract", "📑"), ("Situation", "🏗"), ("Request", "📝"), ("Payment", "💰"),
        ("BOQ / Métré", "📐"), ("Technical", "⚙"), ("Certificate", "📜"),
        ("Correspondence", "✉"), ("Administrative", "🗂"), ("Other", "📁"),
    ),
}

NATURE_TO_CATEGORY = {
    "Staff": "HR / Staff", "Invoice": "Payments", "Renting": "Other", "Legal": "Administrative",
    "Tax": "Insurance & Tax", "Insurance": "Insurance & Tax", "Certificate": "Certificates",
    "Company Contract": "Contracts", "Contract": "Contracts", "Situation": "Situations",
    "Request": "Administrative", "Payment": "Payments", "BOQ / Métré": "BOQ / Métré",
    "Technical": "Technical", "Correspondence": "Correspondence", "Administrative": "Administrative", "Other": "Other",
}


# شرح الدالة infer_nature: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def infer_nature(scope: str, name: str | None, description: str | None = None, category: str | None = None) -> str:
    """Infer a precise nature conservatively for legacy records without one."""
    haystack = f"{name or ''} {description or ''} {category or ''}".casefold()
    patterns = (
        ("Situation", ("situation", "وضعية", "وضعيات")),
        ("Invoice", ("invoice", "facture", "فاتورة")),
        ("Payment", ("payment", "paiement", "دفعة", "دفع")),
        ("Request", ("request", "demande", "طلب")),
        ("Contract" if scope == "project" else "Company Contract", ("contract", "contrat", "marché", "agreement", "عقد", "صفقة")),
        ("BOQ / Métré", ("boq", "metre", "métré", "dqe", "bpu", "quantity", "مترé", "جدول الكميات")),
        ("Certificate", ("certificate", "certificat", "attestation", "شهادة", "إفادة")),
        ("Insurance", ("insurance", "assurance", "تأمين")),
        ("Tax", ("tax", "fiscal", "impôt", "ضريبة", "جباية")),
        ("Staff", ("staff", "employee", "personnel", "موظف", "عامل")),
        ("Renting", ("rent", "rental", "lease", "location", "loyer", "كراء", "إيجار")),
        ("Legal", ("legal", "law", "court", "jurid", "قانون", "قضائي")),
        ("Technical", ("plan", "drawing", "technical", "étude", "study", "specification", "مخطط", "تقني")),
        ("Correspondence", ("correspondence", "courrier", "letter", "lettre", "مراسلة", "رسالة")),
        ("Administrative", ("administrative", "administratif", "declaration", "تصريح", "إدارية")),
    )
    for nature, keys in patterns:
        if any(k.casefold() in haystack for k in keys):
            return nature
    return "Other"


# شرح الدالة ensure_document_schema: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def ensure_document_schema(conn: sqlite3.Connection) -> None:
    """Ensure nature-aware fields exist and legacy rows receive a safe nature."""
    for table in ("company documents", "projects documents"):
        cols = {r["name"] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}
        for column, definition in (("nature", "TEXT"), ("reference_no", "TEXT"), ("issue_date", "TEXT"),
                                   ("reminder_days", "INTEGER"), ("metadata_json", "TEXT")):
            if column not in cols:
                conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}')
    for table, name_col, scope in (("company documents", "document name", "company"), ("projects documents", "document_name", "project")):
        rows = conn.execute(
            f'SELECT rowid AS _rowid, "{name_col}" AS name, description, category, nature FROM "{table}" '
            'WHERE nature IS NULL OR TRIM(nature) = ""'
        ).fetchall()
        for row in rows:
            conn.execute(f'UPDATE "{table}" SET nature=? WHERE rowid=?', (infer_nature(scope, row["name"], row["description"], row["category"]), row["_rowid"]))

# Existing records often predate document categorization. These conservative rules
# only classify records whose category is empty and never overwrite an explicit value.
_CATEGORY_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Situations", ("situation", "situation-", "situations", "وضعية", "وضعيات")),
    ("BOQ / Métré", ("boq", "metre", "métré", "devis quantitatif", "bpu", "dqe", "quantity")),
    ("Contracts", ("contract", "marché", "contrat", "agreement", "amendment", "avenant")),
    ("Payments", ("payment", "paiement", "invoice", "facture", "receipt", "mandat", "règlement")),
    ("Certificates", ("certificate", "certificat", "attestation", "certificat de bonne")),
    ("Insurance & Tax", ("insurance", "assurance", "tax", "fiscal", "cnas", "casnos", "nis", "nif")),
    ("HR / Staff", ("staff", "employee", "personnel", "employee", "cv", "contract employment", "travail")),
    ("Technical", ("plan", "drawing", "technical", "étude", "study", "specification", "cctp", "execution")),
    ("Correspondence", ("correspondence", "courrier", "letter", "lettre", "mail", "demande")),
    ("Administrative", ("administrative", "administratif", "declaration", "déclaration", "request", "authorisation", "autorisation")),
)


# شرح الدالة category_label: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def category_label(category: str | None) -> str:
    """Return a stable English category key for UI translation."""
    value = str(category or "").strip()
    # Compatibility with the situation-generation implementation shipped in the
    # previous build. Existing records remain valid and simply appear under the
    # new Situations nature.
    if value.casefold() in {"situation package", "situation packages"}:
        return "Situations"
    return value if value in _CATEGORY_KEYS else "Other"


# شرح الدالة infer_category: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def infer_category(name: str | None, description: str | None = None) -> str:
    """Infer a category from safe filename/description keywords."""
    haystack = f"{name or ''} {description or ''}".casefold()
    for category, patterns in _CATEGORY_PATTERNS:
        if any(pattern.casefold() in haystack for pattern in patterns):
            return category
    return "Other"


# شرح الدالة ensure_document_categories: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def ensure_document_categories(conn: sqlite3.Connection) -> None:
    """Backfill missing categories without changing explicitly categorized records."""
    tables = (
        ("company documents", "document name", "description"),
        ("projects documents", "document_name", "description"),
    )
    for table, name_column, description_column in tables:
        rows = conn.execute(
            f'SELECT rowid AS _rowid, "{name_column}" AS name, "{description_column}" AS description '
            f'FROM "{table}" WHERE category IS NULL OR TRIM(category) = ""'
        ).fetchall()
        for row in rows:
            category = infer_category(row["name"], row["description"])
            conn.execute(
                f'UPDATE "{table}" SET category=? WHERE rowid=?',
                (category, row["_rowid"]),
            )


# شرح الدالة ensure_categories_persisted: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def ensure_categories_persisted() -> None:
    """Safely backfill categories using one transaction."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        ensure_document_categories(conn)
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


# شرح الدالة category_counts: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def category_counts(conn: sqlite3.Connection, scope: str = "all") -> dict[str, int]:
    """Return document counts by category for cards and filters."""
    result = {key: 0 for key in _CATEGORY_KEYS}
    if scope == "company":
        sql = 'SELECT category, COUNT(*) AS n FROM "company documents" GROUP BY category'
    elif scope == "project":
        sql = 'SELECT category, COUNT(*) AS n FROM "projects documents" GROUP BY category'
    else:
        sql = '''
            SELECT category, COUNT(*) AS n FROM (
                SELECT category FROM "company documents"
                UNION ALL
                SELECT category FROM "projects documents"
            ) GROUP BY category
        '''
    for row in conn.execute(sql).fetchall():
        result[category_label(row["category"])] += int(row["n"] or 0)
    return result


# شرح الدالة normalized_document_row: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def normalized_document_row(row: sqlite3.Row, *, company: bool) -> dict[str, Any]:
    """Normalize company/project document rows to one UI-facing shape."""
    return {
        "id": str(row["document_id"] if company else row["item_id"]),
        "name": str(row["document name"] if company else row["document_name"] or ""),
        "path": str(row["document path"] if company else row["document_path"] or ""),
        "upload_date": row["upload date"] if company else row["upload_date"],
        "expiry": row["expiring date"] if company else row["expiring_date"],
        "status": row["status"] or "Active",
        "category": category_label(row["category"]),
        "nature": row["nature"] or infer_nature("company" if company else "project", row["document name"] if company else row["document_name"], row["description"], row["category"]),
        "description": row["description"] or "",
        "company": company,
        "project_id": None if company else row["project_id"],
        "project_name": "Company" if company else (row["project_name"] or "No project"),
        "related_entity": None if company else row["related_entity"],
    }

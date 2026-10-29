# ============================================================
# شرح الملف: services/situation_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Business logic for project progress situations.

This module keeps situation calculations and lifecycle rules outside the Qt page.
The database remains the source of truth; UI and generated documents consume these
read-only/reporting structures.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from core.id_service import next_child_id
from repositories.db import get_connection

from .audit_service import audit
from .supplementary_service import amount_for

VALID_STATUS_FLOW = {
    "Draft": "Submitted",
    "Submitted": "Approved",
    "Approved": "Paid",
}


# شرح الدالة _float: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


# شرح الدالة _round_qty: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _round_qty(value: float) -> float:
    return round(float(value), 3)


# شرح الدالة _project: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _project(conn: sqlite3.Connection, project_id: str):
    return conn.execute(
        "SELECT * FROM projects WHERE project_id=?", (project_id,)
    ).fetchone()


# شرح الدالة get_project_progress: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def get_project_progress(project_id: str) -> dict[str, Any]:
    """Return one consistent progress snapshot for a project."""
    conn = get_connection()
    try:
        project = _project(conn, project_id)
        if not project:
            return {}

        items = conn.execute(
            """
            SELECT
                m.item_id,
                m.item_number,
                m.description,
                m.unit,
                m.quantity,
                m.unit_price,
                m.amount,
                COALESCE(x.cumulative_quantity, 0) AS cumulative_quantity
            FROM metre_items m
            LEFT JOIN (
                SELECT si.item_id, SUM(si.executed_quantity) AS cumulative_quantity
                FROM situation_items si
                JOIN situations s ON s.situation_id=si.situation_id
                WHERE s.project_id=?
                GROUP BY si.item_id
            ) x ON x.item_id=m.item_id
            WHERE m.project_id=?
            ORDER BY m.item_number, m.item_id
            """,
            (project_id, project_id),
        ).fetchall()

        # The BOQ is authoritative for contract value. Progress is weighted by
        # each item's contract amount so high-value work contributes proportionally.
        boq_value = sum(_float(row["amount"]) for row in items)
        executed_value = 0.0
        remaining_value = 0.0
        outstanding_items = []
        for row in items:
            contract_qty = _float(row["quantity"])
            cumulative_qty = _float(row["cumulative_quantity"])
            price = _float(row["unit_price"])
            clamped_qty = min(max(cumulative_qty, 0.0), max(contract_qty, 0.0))
            executed_value += clamped_qty * price
            remaining = max(contract_qty - cumulative_qty, 0.0)
            remaining_value += remaining * price
            if cumulative_qty + 0.0005 < contract_qty:
                outstanding_items.append(
                    {
                        "item_id": row["item_id"],
                        "item_number": row["item_number"],
                        "description": row["description"],
                        "contract_quantity": contract_qty,
                        "cumulative_quantity": cumulative_qty,
                        "remaining_quantity": remaining,
                    }
                )

        situations = conn.execute(
            """
            SELECT situation_id, situation_number, situation_date, title,
                   notes, status, created_at, updated_at, is_final, finalized_at
            FROM situations
            WHERE project_id=?
            ORDER BY situation_number
            """,
            (project_id,),
        ).fetchall()

        supplementary_rows = conn.execute("SELECT * FROM supplementary_works WHERE project_id=? ORDER BY work_number", (project_id,)).fetchall()
        supplementary_value = sum(amount_for(dict(r)) or 0 for r in supplementary_rows if r["status"] in ("Approved","Executed","Valued","Included","Paid"))
        supplementary_included = sum(amount_for(dict(r)) or 0 for r in supplementary_rows if r["status"] in ("Included","Paid"))
        supplementary_pending = sum(1 for r in supplementary_rows if amount_for(dict(r)) is None)

        period_rows = conn.execute(
            """
            SELECT s.situation_id, COALESCE(SUM(si.amount),0) AS period_value
            FROM situations s
            LEFT JOIN situation_items si ON si.situation_id=s.situation_id
            WHERE s.project_id=?
            GROUP BY s.situation_id
            """,
            (project_id,),
        ).fetchall()
        period_values = {row["situation_id"]: _float(row["period_value"]) for row in period_rows}

        draft_count = sum(1 for row in situations if row["status"] == "Draft")
        latest = situations[-1] if situations else None
        progress_pct = (executed_value / boq_value * 100.0) if boq_value > 0 else 0.0
        progress_pct = min(max(progress_pct, 0.0), 100.0)
        all_complete = bool(items) and not outstanding_items
        can_finalize = (
            project["status"] not in ("Completed", "Archived")
            and bool(situations)
            and all_complete
            and draft_count == 0
            and all(row["status"] in ("Approved", "Paid") for row in situations)
        )

        return {
            "project": dict(project),
            "items": [dict(row) | {"cumulative_quantity": _float(row["cumulative_quantity"])} for row in items],
            "situations": [dict(row) | {"period_value": period_values[row["situation_id"]]} for row in situations],
            "boq_value": boq_value,
            "supplementary_value": supplementary_value,
            "supplementary_included": supplementary_included,
            "supplementary_pending": supplementary_pending,
            "total_contract_value": boq_value + supplementary_value,
            "executed_value": executed_value + supplementary_included,
            "remaining_value": max(0.0, remaining_value),
            "progress_percent": progress_pct,
            "outstanding_items": outstanding_items,
            "draft_count": draft_count,
            "latest_situation": dict(latest) if latest else None,
            "can_finalize": can_finalize,
        }
    finally:
        conn.close()


# شرح الدالة get_situation: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def get_situation(situation_id: str) -> dict[str, Any]:
    """Return one situation and its item-level progress detail."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT s.*, p.project_name, p.project_id,
                   p.contract_code, p.contracting_authority, p.project_type,
                   p.start_date, p.end_date, p.budget_ht, p.tva_percent,
                   p.budget_ttc
            FROM situations s
            JOIN projects p ON p.project_id=s.project_id
            WHERE s.situation_id=?
            """,
            (situation_id,),
        ).fetchone()
        if not row:
            return {}

        items = conn.execute(
            """
            SELECT
                m.item_id,
                m.item_number,
                m.description,
                m.unit,
                m.quantity AS contract_quantity,
                m.unit_price,
                m.amount AS contract_amount,
                COALESCE((
                    SELECT SUM(si2.executed_quantity)
                    FROM situation_items si2
                    JOIN situations s2 ON s2.situation_id=si2.situation_id
                    WHERE si2.item_id=m.item_id
                      AND s2.project_id=(SELECT project_id FROM situations WHERE situation_id=?)
                      AND s2.situation_number < (SELECT situation_number FROM situations WHERE situation_id=?)
                ), 0) AS previous_quantity,
                COALESCE(si.executed_quantity, 0) AS current_quantity,
                COALESCE(si.amount, 0) AS current_amount
            FROM metre_items m
            LEFT JOIN situation_items si
                ON si.item_id=m.item_id AND si.situation_id=?
            WHERE m.project_id=?
            ORDER BY m.item_number, m.item_id
            """,
            (situation_id, situation_id, situation_id, row["project_id"]),
        ).fetchall()

        detailed = []
        for item in items:
            previous = _float(item["previous_quantity"])
            current = _float(item["current_quantity"])
            contract = _float(item["contract_quantity"])
            detailed.append(
                dict(item)
                | {
                    "previous_quantity": previous,
                    "current_quantity": current,
                    "cumulative_quantity": previous + current,
                    "remaining_quantity": max(contract - previous - current, 0.0),
                }
            )
        supplement_rows = conn.execute(
            """SELECT sw.*, COALESCE(ssi.executed_quantity,0) AS current_quantity, COALESCE(ssi.amount,0) AS current_amount
               FROM supplementary_works sw LEFT JOIN supplementary_situation_items ssi
               ON ssi.supplementary_id=sw.supplementary_id AND ssi.situation_id=?
               WHERE sw.project_id=? AND sw.status IN ('Approved','Executed','Valued','Included','Paid')
               ORDER BY sw.work_number""", (situation_id, row["project_id"])
        ).fetchall()
        supplement_detail=[]
        for sw in supplement_rows:
            d=dict(sw); amt=amount_for(d)
            current=_float(d.get("current_quantity"))
            if d["work_mode"]=="Lump Sum" and current==0 and d.get("current_amount"):
                current_amount=_float(d["current_amount"])
            elif current>0 and d["unit_price"] is not None:
                current_amount=current*_float(d["unit_price"])
            else:
                current_amount=_float(d.get("current_amount"))
            d.update({"calculated_amount":amt,"current_amount":current_amount})
            supplement_detail.append(d)
        supplement_period=sum(_float(x["current_amount"]) for x in supplement_detail)
        period_value = sum(_float(item["current_amount"]) for item in detailed) + supplement_period
        previous_value = sum(
            min(_float(item["previous_quantity"]), _float(item["contract_quantity"]))
            * _float(item["unit_price"])
            for item in detailed
        )
        cumulative_value = previous_value + period_value
        boq_value = sum(_float(item["contract_amount"]) for item in detailed)
        tva_percent = _float(row["tva_percent"])
        period_tva = period_value * tva_percent / 100.0
        period_ttc = period_value + period_tva
        cumulative_tva = cumulative_value * tva_percent / 100.0
        cumulative_ttc = cumulative_value + cumulative_tva

        return {
            "situation": dict(row),
            "items": detailed,
            "supplementary_items": supplement_detail,
            "supplementary_period_value": supplement_period,
            "period_value": period_value,
            "previous_value": previous_value,
            "cumulative_value": cumulative_value,
            "remaining_value": max(0.0, boq_value - cumulative_value),
            "boq_value": boq_value,
            "tva_percent": tva_percent,
            "period_tva": period_tva,
            "period_ttc": period_ttc,
            "cumulative_tva": cumulative_tva,
            "cumulative_ttc": cumulative_ttc,
            "project_progress_percent": (cumulative_value / boq_value * 100.0) if boq_value else 0.0,
        }
    finally:
        conn.close()


# شرح الدالة _validate_quantities: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _validate_quantities(
    conn: sqlite3.Connection,
    project_id: str,
    situation_id: str | None,
    quantities: Mapping[str, float],
) -> dict[str, tuple[float, float, float]]:
    """Validate current quantities and return item -> (planned, previous, current)."""
    rows = conn.execute(
        """
        SELECT m.item_id, m.quantity,
               COALESCE((
                    SELECT SUM(si.executed_quantity)
                    FROM situation_items si
                    JOIN situations s ON s.situation_id=si.situation_id
                    WHERE si.item_id=m.item_id
                      AND s.project_id=?
                      AND (? IS NULL OR s.situation_id<>?)
               ),0) AS previous_quantity
        FROM metre_items m
        WHERE m.project_id=?
        """,
        (project_id, situation_id, situation_id, project_id),
    ).fetchall()
    item_limits = {
        row["item_id"]: (_float(row["quantity"]), _float(row["previous_quantity"]))
        for row in rows
    }

    unknown = set(quantities) - set(item_limits)
    if unknown:
        raise ValueError("One or more selected BOQ items no longer belong to this project.")

    validated: dict[str, tuple[float, float, float]] = {}
    for item_id, (planned, previous) in item_limits.items():
        current = _round_qty(_float(quantities.get(item_id, 0.0)))
        if current < -0.0005:
            raise ValueError("Executed quantities cannot be negative.")
        if previous + current > planned + 0.0005:
            raise ValueError(
                f"Executed quantity exceeds the BOQ quantity for item {item_id}."
            )
        validated[item_id] = (planned, previous, max(0.0, current))
    return validated


# شرح الدالة save_situation: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def save_situation(
    project_id: str,
    situation_date: str,
    title: str | None,
    notes: str | None,
    quantities: Mapping[str, float],
    situation_id: str | None = None,
) -> str:
    """Create or update a Draft situation and its current-period quantities."""
    if not project_id:
        raise ValueError("Project is required.")
    if not situation_date:
        raise ValueError("Situation date is required.")

    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        project = _project(conn, project_id)
        if not project:
            raise ValueError("Project not found.")
        if project["status"] in ("Completed", "Archived"):
            raise ValueError("Completed or archived projects cannot receive new situations.")

        validated = _validate_quantities(conn, project_id, situation_id, quantities)

        if situation_id:
            existing = conn.execute(
                "SELECT * FROM situations WHERE situation_id=? AND project_id=?",
                (situation_id, project_id),
            ).fetchone()
            if not existing:
                raise ValueError("Situation not found.")
            if existing["status"] != "Draft":
                raise ValueError("Only Draft situations can be edited.")
            number = int(existing["situation_number"])
            sid = situation_id
            conn.execute(
                """
                UPDATE situations
                SET situation_date=?, title=?, notes=?, updated_at=CURRENT_TIMESTAMP
                WHERE situation_id=?
                """,
                (situation_date, title or None, notes or None, sid),
            )
            conn.execute("DELETE FROM situation_items WHERE situation_id=?", (sid,))
        else:
            number = int(
                conn.execute(
                    "SELECT COALESCE(MAX(situation_number),0)+1 FROM situations WHERE project_id=?",
                    (project_id,),
                ).fetchone()[0]
            )
            sid = next_child_id(conn, "sit", project_id, digits=3)
            conn.execute(
                """
                INSERT INTO situations(
                    situation_id, project_id, situation_number, situation_date,
                    title, notes, status
                ) VALUES(?,?,?,?,?,?, 'Draft')
                """,
                (sid, project_id, number, situation_date, title or None, notes or None),
            )

        for item_id, (planned, previous, current) in validated.items():
            if current <= 0:
                continue
            item = conn.execute(
                "SELECT unit_price FROM metre_items WHERE item_id=? AND project_id=?",
                (item_id, project_id),
            ).fetchone()
            if not item:
                raise ValueError("A BOQ item is missing while saving the situation.")
            unit_price = _float(item["unit_price"])
            conn.execute(
                """
                INSERT INTO situation_items(
                    situation_item_id, situation_id, item_id,
                    executed_quantity, unit_price, amount, previous_quantity
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    next_child_id(conn, "sititem", sid, digits=4),
                    sid,
                    item_id,
                    current,
                    unit_price,
                    current * unit_price,
                    previous,
                ),
            )

        audit(
            "Created" if not situation_id else "Updated",
            "Situation",
            sid,
            f"Situation N°{number} saved for project {project_id}.",
            conn=conn,
        )
        conn.commit()
        return sid
    except (sqlite3.Error, ValueError, TypeError, OSError):
        conn.rollback()
        raise
    finally:
        conn.close()


# شرح الدالة transition_situation: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def transition_situation(situation_id: str, target_status: str) -> None:
    """Advance one situation through Draft -> Submitted -> Approved -> Paid."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT project_id, situation_number, status FROM situations WHERE situation_id=?",
            (situation_id,),
        ).fetchone()
        if not row:
            raise ValueError("Situation not found.")
        expected = VALID_STATUS_FLOW.get(row["status"])
        if expected != target_status:
            raise ValueError(
                f"Situation status can move from {row['status']} to {expected or 'no further state'} only."
            )
        conn.execute(
            "UPDATE situations SET status=?, updated_at=CURRENT_TIMESTAMP WHERE situation_id=?",
            (target_status, situation_id),
        )
        audit(
            "Status changed",
            "Situation",
            situation_id,
            f"Situation N°{row['situation_number']} moved to {target_status}.",
            conn=conn,
        )
        conn.commit()
    except (sqlite3.Error, ValueError, TypeError, OSError):
        conn.rollback()
        raise
    finally:
        conn.close()


# شرح الدالة delete_situation: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def delete_situation(situation_id: str) -> None:
    """Delete a Draft situation; historical workflow states are preserved otherwise."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT project_id, situation_number, status FROM situations WHERE situation_id=?",
            (situation_id,),
        ).fetchone()
        if not row:
            raise ValueError("Situation not found.")
        if row["status"] != "Draft":
            raise ValueError("Only Draft situations can be deleted.")
        conn.execute("DELETE FROM situations WHERE situation_id=?", (situation_id,))
        audit(
            "Deleted",
            "Situation",
            situation_id,
            f"Draft situation N°{row['situation_number']} deleted.",
            conn=conn,
        )
        conn.commit()
    except (sqlite3.Error, ValueError, TypeError, OSError):
        conn.rollback()
        raise
    finally:
        conn.close()


# شرح الدالة finalize_project: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def finalize_project(project_id: str, completion_date: str | None = None) -> dict[str, Any]:
    """Finalize a project only when its complete BOQ has been executed and approved."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        project = _project(conn, project_id)
        if not project:
            raise ValueError("Project not found.")
        if project["status"] == "Completed":
            return get_project_progress(project_id)
        if project["status"] == "Archived":
            raise ValueError("Archived projects cannot be finalized.")

        pending_supp = conn.execute("SELECT COUNT(*) FROM supplementary_works WHERE project_id=? AND status NOT IN ('Included','Paid')", (project_id,)).fetchone()[0]
        unvalued_supp = conn.execute("SELECT COUNT(*) FROM supplementary_works WHERE project_id=? AND (work_mode='Pending' OR (work_mode='Measured' AND (quantity IS NULL OR unit_price IS NULL)) OR (work_mode='Lump Sum' AND lump_sum_amount IS NULL))", (project_id,)).fetchone()[0]
        if unvalued_supp:
            raise ValueError(f"The project has {unvalued_supp} supplementary work(s) without final valuation.")
        if pending_supp:
            raise ValueError(f"The project has {pending_supp} supplementary work(s) not yet included in a situation.")

        item_rows = conn.execute(
            """
            SELECT m.item_id, m.quantity,
                   COALESCE(x.cumulative_quantity,0) AS cumulative_quantity
            FROM metre_items m
            LEFT JOIN (
                SELECT si.item_id, SUM(si.executed_quantity) AS cumulative_quantity
                FROM situation_items si
                JOIN situations s ON s.situation_id=si.situation_id
                WHERE s.project_id=?
                GROUP BY si.item_id
            ) x ON x.item_id=m.item_id
            WHERE m.project_id=?
            """,
            (project_id, project_id),
        ).fetchall()
        if not item_rows:
            raise ValueError("The project cannot be finalized without BOQ items.")

        missing = [
            row for row in item_rows
            if _float(row["cumulative_quantity"]) + 0.0005 < _float(row["quantity"])
        ]
        if missing:
            raise ValueError(
                f"The project still has {len(missing)} BOQ item(s) with unexecuted quantities."
            )

        situations = conn.execute(
            "SELECT situation_id, situation_number, status FROM situations WHERE project_id=? ORDER BY situation_number",
            (project_id,),
        ).fetchall()
        if not situations:
            raise ValueError("The project cannot be finalized without at least one situation.")
        unfinished = [row for row in situations if row["status"] not in ("Approved", "Paid")]
        if unfinished:
            raise ValueError("All situations must be Approved or Paid before finalization.")

        date_value = completion_date or str(project["actual_completion_date"] or "")
        if not date_value:
            from datetime import datetime, timezone
            date_value = datetime.now(tz=timezone.utc).date().isoformat()

        final_situation_id = situations[-1]["situation_id"]
        conn.execute(
            "UPDATE situations SET is_final=0, finalized_at=NULL WHERE project_id=?",
            (project_id,),
        )
        conn.execute(
            "UPDATE situations SET is_final=1, finalized_at=? , updated_at=CURRENT_TIMESTAMP WHERE situation_id=?",
            (date_value, final_situation_id),
        )
        conn.execute(
            """
            UPDATE projects
            SET status='Completed', actual_completion_date=?, updated_at=CURRENT_TIMESTAMP
            WHERE project_id=?
            """,
            (date_value, project_id),
        )
        audit(
            "Completed",
            "Project",
            project_id,
            f"Project finalized using Situation N°{situations[-1]['situation_number']}.",
            conn=conn,
        )
        conn.commit()
        # Return a fresh post-commit snapshot through the normal connection boundary.
        return get_project_progress(project_id)
    except (sqlite3.Error, ValueError, TypeError, OSError):
        conn.rollback()
        raise
    finally:
        conn.close()


__all__ = [
    "VALID_STATUS_FLOW",
    "delete_situation",
    "finalize_project",
    "get_project_progress",
    "get_situation",
    "save_situation",
    "transition_situation",
]

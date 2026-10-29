# ============================================================
# شرح الملف: services/payroll_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================

"""Payroll calculations and attendance/site-labor reconciliation."""
from __future__ import annotations

import sqlite3
from typing import Any

from core.decimal_utils import amount, q2
from core.id_service import next_random_id
from repositories.db import get_connection


# شرح الدالة calculate_gross: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def calculate_gross(
    base: float = 0.0,
    overtime: float = 0.0,
    bonuses: float = 0.0,
) -> float:
    """Calculate gross payroll amount."""
    return float(q2(
        amount(base)
        + amount(overtime)
        + amount(bonuses)
    ))


# شرح الدالة calculate_net: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def calculate_net(
    base: float = 0.0,
    overtime: float = 0.0,
    bonuses: float = 0.0,
    deductions: float = 0.0,
    advances: float = 0.0,
) -> float:
    """Calculate net payroll amount."""
    gross = amount(calculate_gross(base, overtime, bonuses))

    return float(q2(
        max(
            gross
            - amount(deductions)
            - amount(advances),
            amount(0),
        )
    ))


# شرح الدالة attendance_totals: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def attendance_totals(
    conn: Any,
    staff_id: str,
    period: str,
) -> dict[str, float | int]:
    """Return attendance totals for an employee and payroll period."""
    row = conn.execute(
        """
        SELECT
            COUNT(
                CASE
                    WHEN status = 'Present' THEN 1
                END
            ) AS present_days,

            COALESCE(
                SUM(
                    CASE
                        WHEN status = 'Present'
                        THEN working_hours
                        ELSE 0
                    END
                ),
                0
            ) AS hours,

            COALESCE(
                SUM(
                    CASE
                        WHEN status = 'Present'
                        THEN overtime_hours
                        ELSE 0
                    END
                ),
                0
            ) AS overtime

        FROM attendance
        WHERE staff_id = ?
          AND substr(date, 1, 7) = ?
        """,
        (staff_id, period),
    ).fetchone()

    return {
        "present_days": int(row["present_days"] or 0),
        "hours": float(row["hours"] or 0),
        "overtime": float(row["overtime"] or 0),
    }


# شرح الدالة labor_reconciliation: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def labor_reconciliation(
    conn: Any,
    staff_id: str,
    period: str,
) -> dict[str, float | str]:
    """Reconcile attendance hours against project/site labor allocations."""
    att = attendance_totals(conn, staff_id, period)

    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(hours), 0) AS hours,
            COALESCE(SUM(overtime_hours), 0) AS overtime,
            COALESCE(
                SUM(
                    hours * hourly_cost
                    + overtime_hours * hourly_cost * 1.5
                ),
                0
            ) AS cost

        FROM labor_allocations

        WHERE staff_id = ?
          AND substr(work_date, 1, 7) = ?
          AND attendance_id IS NOT NULL
        """,
        (staff_id, period),
    ).fetchone()

    allocated_hours = float(row["hours"] or 0)
    allocated_overtime = float(row["overtime"] or 0)

    attendance_hours = float(att["hours"])
    attendance_overtime = float(att["overtime"])

    regular_gap = round(
        attendance_hours - allocated_hours,
        3,
    )

    overtime_gap = round(
        attendance_overtime - allocated_overtime,
        3,
    )

    over_allocated = (
        regular_gap < -0.001
        or overtime_gap < -0.001
    )

    if over_allocated:
        status = "Over-allocated"
    elif (
        abs(regular_gap) <= 0.001
        and abs(overtime_gap) <= 0.001
    ):
        status = "Reconciled"
    else:
        status = "Partially allocated"

    return {
        "attendance_hours": attendance_hours,
        "attendance_overtime": attendance_overtime,
        "allocated_hours": allocated_hours,
        "allocated_overtime": allocated_overtime,
        "unallocated_hours": max(0.0, regular_gap),
        "unallocated_overtime": max(0.0, overtime_gap),
        "labor_cost": float(row["cost"] or 0),
        "regular_gap": regular_gap,
        "overtime_gap": overtime_gap,
        "status": status,
    }


# شرح الدالة attendance_available_for_allocation: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def attendance_available_for_allocation(
    conn: Any,
    attendance_id: str,
) -> dict[str, Any]:
    """Return remaining attendance hours available for site allocation."""
    row = conn.execute(
        """
        SELECT
            record_id,
            staff_id,
            project_id,
            date,
            status,
            working_hours,
            overtime_hours

        FROM attendance

        WHERE record_id = ?
        """,
        (attendance_id,),
    ).fetchone()

    if not row:
        raise ValueError("Attendance record not found.")

    used = conn.execute(
        """
        SELECT
            COALESCE(SUM(hours), 0) AS hours,
            COALESCE(SUM(overtime_hours), 0) AS overtime

        FROM labor_allocations

        WHERE attendance_id = ?
        """,
        (attendance_id,),
    ).fetchone()

    working_hours = float(row["working_hours"] or 0)
    overtime_hours = float(row["overtime_hours"] or 0)

    used_hours = float(used["hours"] or 0)
    used_overtime = float(used["overtime"] or 0)

    return {
        **dict(row),
        "available_hours": max(
            0.0,
            working_hours - used_hours,
        ),
        "available_overtime": max(
            0.0,
            overtime_hours - used_overtime,
        ),
    }


# شرح الدالة save_payroll: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def save_payroll(
    staff_id: str,
    period: str,
    base: float,
    overtime: float = 0.0,
    bonuses: float = 0.0,
    deductions: float = 0.0,
    advances: float = 0.0,
    status: str = "Draft",
    notes: str | None = None,
    conn: Any | None = None,
) -> str:
    """
    Create or update a payroll record.

    All monetary values intentionally use float-compatible parameters
    because the UI uses QDoubleSpinBox.
    """

    owns_connection = conn is None
    connection = conn or get_connection()

    try:
        staff_exists = connection.execute(
            """
            SELECT 1
            FROM staff
            WHERE staff_id = ?
            """,
            (staff_id,),
        ).fetchone()

        if not staff_exists:
            raise ValueError("Staff member not found.")

        reconciliation = labor_reconciliation(
            connection,
            staff_id,
            period,
        )

        net = calculate_net(
            base=base,
            overtime=overtime,
            bonuses=bonuses,
            deductions=deductions,
            advances=advances,
        )

        existing = connection.execute(
            """
            SELECT payroll_id
            FROM payroll_records
            WHERE staff_id = ?
              AND period = ?
            """,
            (staff_id, period),
        ).fetchone()

        payroll_id = (
            existing["payroll_id"]
            if existing
            else next_random_id(
                connection,
                "prl",
                digits=10,
            )
        )

        connection.execute(
            """
            INSERT INTO payroll_records (
                payroll_id,
                staff_id,
                period,
                base_amount,
                overtime_amount,
                bonuses,
                deductions,
                advances,
                net_amount,
                status,
                notes,
                attendance_hours,
                attendance_overtime,
                allocated_hours,
                allocated_overtime,
                reconciliation_status,
                updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
            )

            ON CONFLICT(staff_id, period)
            DO UPDATE SET
                base_amount = excluded.base_amount,
                overtime_amount = excluded.overtime_amount,
                bonuses = excluded.bonuses,
                deductions = excluded.deductions,
                advances = excluded.advances,
                net_amount = excluded.net_amount,
                status = excluded.status,
                notes = excluded.notes,
                attendance_hours = excluded.attendance_hours,
                attendance_overtime = excluded.attendance_overtime,
                allocated_hours = excluded.allocated_hours,
                allocated_overtime = excluded.allocated_overtime,
                reconciliation_status =
                    excluded.reconciliation_status,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                payroll_id,
                staff_id,
                period,
                q2(base),
                q2(overtime),
                q2(bonuses),
                q2(deductions),
                q2(advances),
                net,
                status,
                notes,
                reconciliation["attendance_hours"],
                reconciliation["attendance_overtime"],
                reconciliation["allocated_hours"],
                reconciliation["allocated_overtime"],
                reconciliation["status"],
            ),
        )

        if owns_connection:
            connection.commit()

        return str(payroll_id)

    except (sqlite3.Error, ValueError, TypeError, OSError):
        if owns_connection:
            connection.rollback()
        raise

    finally:
        if owns_connection:
            connection.close()


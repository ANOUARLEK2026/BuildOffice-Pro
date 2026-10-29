# ============================================================
# شرح الملف: services/analytics_hub.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Central read-only analytics facade used by pages and visualizations."""
from __future__ import annotations

from repositories.db import get_connection
from services.visual_analytics_service import (
    expense_overview,
    project_cost_exposure,
    workforce_overview,
)


# شرح الدالة expense_datasets: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def expense_datasets(conn=None, limit: int = 8) -> dict:
    """Return all expense chart datasets through one stable service entry point."""
    own = conn is None
    connection = conn or get_connection()
    try:
        return expense_overview(connection, limit=limit)
    finally:
        if own:
            connection.close()


# شرح الدالة project_cost_dataset: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def project_cost_dataset(conn=None, limit: int = 8):
    """Return project cost exposure data."""
    own = conn is None
    connection = conn or get_connection()
    try:
        return project_cost_exposure(connection, limit=limit)
    finally:
        if own:
            connection.close()


# شرح الدالة workforce_datasets: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def workforce_datasets(conn=None, limit: int = 12) -> dict:
    """Return workforce visual datasets."""
    own = conn is None
    connection = conn or get_connection()
    try:
        return workforce_overview(connection, limit=limit)
    finally:
        if own:
            connection.close()


__all__ = ["expense_datasets", "project_cost_dataset", "workforce_datasets"]

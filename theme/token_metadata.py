# ============================================================
# شرح الملف: theme/token_metadata.py
# هذا الملف جزء من نظام الألوان والثيمات وأنماط الواجهة.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Human-readable metadata for Theme Inspector tokens."""
from __future__ import annotations

from typing import Final

_LABELS: Final[dict[str, str]] = {
    "semantic": "Semantic",
    "brand": "Brand",
    "status": "Status",
    "kpi": "KPI",
    "charts": "Charts",
    "tables": "Tables",
    "components": "Components",
}

# شرح الدالة describe_token: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def describe_token(token: str) -> dict[str, str]:
    """Return stable display metadata without affecting theme behavior."""
    value = str(token).strip()
    if "." in value:
        category, role = value.split(".", 1)
    else:
        category, role = "semantic", value
    label = role.replace("_", " ").strip().title() or value
    return {
        "category": _LABELS.get(category, category.title()),
        "label": label,
        "role": role,
    }

__all__ = ["describe_token"]

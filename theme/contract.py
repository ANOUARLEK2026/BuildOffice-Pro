# ============================================================
# شرح الملف: theme/contract.py
# هذا الملف جزء من نظام الألوان والثيمات وأنماط الواجهة.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Hard separation and contrast contract for BuildOffice Pro themes."""
from __future__ import annotations

from .colors import OPTIONS
from .themes import get_token_palette


# شرح الدالة _luminance: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _luminance(value: str) -> float:
    rgb = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

# شرح الدالة contrast_ratio: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def contrast_ratio(first: str, second: str) -> float:
    a, b = _luminance(first), _luminance(second)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)

# شرح الدالة validate_theme_contract: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def validate_theme_contract() -> list[str]:
    errors: list[str] = []
    core = ("background", "surface", "surface_alt", "border", "divider", "hover", "pressed", "disabled")
    for theme in ("Dark", "Light"):
        for option in OPTIONS:
            bg = get_token_palette(theme, "background")[option]
            surface = get_token_palette(theme, "surface")[option]
            primary = get_token_palette(theme, "text_primary")[option]
            secondary = get_token_palette(theme, "text_secondary")[option]
            if theme == "Dark" and _luminance(bg) >= 0.18:
                errors.append(f"{theme}/{option}: background is not dark enough")
            if theme == "Light" and _luminance(bg) <= 0.55:
                errors.append(f"{theme}/{option}: background is not light enough")
            if contrast_ratio(primary, surface) < 4.5:
                errors.append(f"{theme}/{option}: text_primary/surface contrast is below 4.5")
            if contrast_ratio(secondary, surface) < 4.5:
                errors.append(f"{theme}/{option}: text_secondary/surface contrast is below 4.5")
    for token in core:
        for option in OPTIONS:
            if get_token_palette("Dark", token)[option] == get_token_palette("Light", token)[option]:
                errors.append(f"Theme isolation violation: {token}/{option} is shared")
    return errors

__all__ = ["contrast_ratio", "validate_theme_contract"]

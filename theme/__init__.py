# ============================================================
# شرح الملف: theme/__init__.py
# هذا الملف جزء من نظام الألوان والثيمات وأنماط الواجهة.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""BuildOffice Pro central theme package."""
from .colors import ALL_TOKENS
from .contract import contrast_ratio, validate_theme_contract
from .qss import (
    apply_card_shadow,
    apply_widget_theme,
    build_application_style,
    resolve_style,
    resolve_token_value,
    set_theme_property,
    set_theme_style,
    theme_color,
    theme_qcolor,
    validate_qss,
)
from .store import ThemeStore
from .themes import get_token_palette, resolve_color, validate_themes

__all__=[
    "ALL_TOKENS",
    "apply_card_shadow",
    "ThemeStore",
    "apply_widget_theme",
    "build_application_style",
    "contrast_ratio",
    "get_token_palette",
    "resolve_color",
    "resolve_style",
    "resolve_token_value",
    "set_theme_property",
    "set_theme_style",
    "theme_color",
    "theme_qcolor",
    "validate_qss",
    "validate_theme_contract",
    "validate_themes",
]

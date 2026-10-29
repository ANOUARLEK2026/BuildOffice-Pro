# ============================================================
# شرح الملف: theme/metrics.py
# هذا الملف جزء من نظام الألوان والثيمات وأنماط الواجهة.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""المقاييس المشتركة للخطوط والمسافات والأحجام في واجهة التطبيق."""
from typing import Final

UI_FONT_FAMILY: Final[str] = "Segoe UI"

# مقياس الخطوط (بالبكسل في QSS). رُفعت القيم لتحسين القراءة، خصوصًا للنص العربي،
# مع الحفاظ على تدرّج واضح بين الأحجام: توضيحي < أساسي < عنوان < مؤشر.
FONT_SIZE_ROOT: Final[int] = 13
FONT_SIZE_BRAND: Final[int] = 14
FONT_SIZE_TINY: Final[int] = 10
FONT_SIZE_SMALL: Final[int] = 11
FONT_SIZE_BODY: Final[int] = 12
FONT_SIZE_LABEL: Final[int] = 12
FONT_SIZE_SUBTITLE: Final[int] = 12
FONT_SIZE_SECTION: Final[int] = 15
FONT_SIZE_HEADING: Final[int] = 16
FONT_SIZE_TITLE: Final[int] = 22
FONT_SIZE_KPI: Final[int] = 26

# حجم الخط (بالنقاط) المستخدم عند رسم النصوص يدويًا داخل الرسوم البيانية عبر QFont.
CHART_FONT_POINTS: Final[int] = 9

# أوزان أنعم: خط Segoe UI يملك Regular/Semibold/Bold فقط، لذلك تُجمَع الأوزان الثقيلة
# القديمة (800/850/900) في 700 كي لا يظهر النص بوزن Black الثقيل والمزدحم.
FONT_WEIGHT_NORMAL: Final[int] = 400
FONT_WEIGHT_SEMIBOLD: Final[int] = 600
FONT_WEIGHT_BOLD: Final[int] = 600
FONT_WEIGHT_EXTRABOLD: Final[int] = 700
FONT_WEIGHT_HEAVY: Final[int] = 700
FONT_WEIGHT_BLACK: Final[int] = 700

# مقياس المسافات الموحد للقيم المتكررة، مع السماح للقيم الخاصة عندما يفرض التصميم ذلك.
SPACE_XS: Final[int] = 4
SPACE_SM: Final[int] = 8
SPACE_MD: Final[int] = 12
SPACE_LG: Final[int] = 16
SPACE_XL: Final[int] = 20
SPACE_XXL: Final[int] = 24
SPACE_XXXL: Final[int] = 32

# الارتفاع المشترك لعناصر الإدخال والأزرار وأدوات الشريط.
CONTROL_HEIGHT: Final[int] = 40

__all__ = [
    "CHART_FONT_POINTS",
    "CONTROL_HEIGHT",
    "FONT_SIZE_BODY",
    "FONT_SIZE_BRAND",
    "FONT_SIZE_HEADING",
    "FONT_SIZE_KPI",
    "FONT_SIZE_LABEL",
    "FONT_SIZE_ROOT",
    "FONT_SIZE_SECTION",
    "FONT_SIZE_SMALL",
    "FONT_SIZE_SUBTITLE",
    "FONT_SIZE_TINY",
    "FONT_SIZE_TITLE",
    "FONT_WEIGHT_BLACK",
    "FONT_WEIGHT_BOLD",
    "FONT_WEIGHT_EXTRABOLD",
    "FONT_WEIGHT_HEAVY",
    "FONT_WEIGHT_NORMAL",
    "FONT_WEIGHT_SEMIBOLD",
    "SPACE_LG",
    "SPACE_MD",
    "SPACE_SM",
    "SPACE_XL",
    "SPACE_XS",
    "SPACE_XXL",
    "SPACE_XXXL",
    "UI_FONT_FAMILY",
]

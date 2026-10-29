# ============================================================
# شرح الملف: core/decimal_utils.py
# هذا الملف جزء من المكوّنات الأساسية المشتركة في التطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")

# شرح الدالة amount: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def amount(value) -> Decimal:
    try:
        result = Decimal(str(value or 0))
        if not result.is_finite():
            raise ValueError("Invalid monetary amount.")
        return result.quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Invalid monetary amount.") from exc

# شرح الدالة q2: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def q2(value) -> float:
    return float(amount(value))

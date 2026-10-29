# ============================================================
# شرح الملف: tests/test_numeric_validation.py
# هذا الملف جزء من اختبارات السلامة والتكامل وصحة الوظائف.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


# شرح الدالة test_money_rejects_non_finite_values: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_money_rejects_non_finite_values():
    from core.decimal_utils import amount
    for value in ("NaN", "Infinity", "-Infinity", float("nan"), float("inf"), float("-inf")):
        try:
            amount(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Non-finite value accepted: {value!r}")


# شرح الدالة test_numeric_validators_reject_non_finite_values: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_numeric_validators_reject_non_finite_values():
    from core.validators import non_negative, positive
    for fn in (non_negative, positive):
        for value in (float("nan"), float("inf"), float("-inf")):
            try:
                fn(value, "Amount")
            except ValueError:
                pass
            else:
                raise AssertionError(f"Non-finite value accepted by {fn.__name__}: {value!r}")

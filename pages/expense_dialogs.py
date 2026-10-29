# ============================================================
# شرح الملف: pages/expense_dialogs.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""واجهات توافقية لحوارات المصروفات المتخصصة."""
from .expense_details_dialog import _expense_details
from .expense_dialog_form import _expense_dialog
from .expense_payment_dialog import _record_payment_dialog

__all__=["_expense_details", "_expense_dialog", "_record_payment_dialog"]

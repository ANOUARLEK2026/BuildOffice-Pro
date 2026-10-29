# ============================================================
# شرح الملف: core/i18n.py
# هذا الملف جزء من المكوّنات الأساسية المشتركة في التطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Centralized application localization for BuildOffice Pro.

مركزية اللغة: كل النصوص المعروفة في الواجهة تمر من هنا.
مهم: لا يتم تغيير اتجاه الواجهة إلى RTL. التخطيط والمحاذاة والـ QSS تبقى كما هي.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QProgressBar,
    QSpinBox,
    QTableWidget,
    QTabWidget,
    QWidget,
)

LANGUAGE_EN = "en"
LANGUAGE_AR = "ar"

# مدة الانتظار قبل السماح بالتمرير بعجلة الفأرة فوق القوائم المنسدلة
COMBO_WHEEL_DELAY_MS = 2000

# النصوص المركزية. المفتاح دائمًا هو النص الإنجليزي الأصلي.
TRANSLATIONS_DIR = Path(__file__).resolve().parent.parent / "translations"

# شرح الدالة _load_catalog: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _load_catalog(language: str) -> dict[str, str]:
    """تحميل قاموس اللغة من المصدر المركزي JSON."""
    path = TRANSLATIONS_DIR / f"{language}.json"
    try:
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data.items()}
    except (OSError, ValueError, TypeError):
        return {}

EN = _load_catalog(LANGUAGE_EN)
AR = _load_catalog(LANGUAGE_AR)
AR_TO_EN = {value: key for key, value in AR.items()}

# Cached active language. SQLite is read only when the language is initialized or explicitly changed.
_CURRENT_LANGUAGE = LANGUAGE_AR
_LANGUAGE_INITIALIZED = False

# شرح الدالة get_language: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def get_language() -> str:
    """Return the active UI language using an in-memory cache after first load."""
    global _CURRENT_LANGUAGE, _LANGUAGE_INITIALIZED
    if not _LANGUAGE_INITIALIZED:
        try:
            from services.settings_service import get_setting
            _CURRENT_LANGUAGE = set_language_value(get_setting("language", LANGUAGE_EN))
        except (RuntimeError, AttributeError):
            _CURRENT_LANGUAGE = LANGUAGE_EN
        _LANGUAGE_INITIALIZED = True
    return _CURRENT_LANGUAGE

# شرح الدالة set_language_value: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def set_language_value(value: str) -> str:
    value = str(value).strip().lower()
    return LANGUAGE_AR if value in (LANGUAGE_AR, "arabic", "ar") else LANGUAGE_EN

def set_language(language: str) -> str:
    """Update the process-wide active language without touching the database."""
    global _CURRENT_LANGUAGE, _LANGUAGE_INITIALIZED
    _CURRENT_LANGUAGE = set_language_value(language)
    _LANGUAGE_INITIALIZED = True
    return _CURRENT_LANGUAGE

_AR_MONTHS = {
    "January": "يناير", "February": "فبراير", "March": "مارس", "April": "أبريل",
    "May": "مايو", "June": "يونيو", "July": "يوليو", "August": "أغسطس",
    "September": "سبتمبر", "October": "أكتوبر", "November": "نوفمبر", "December": "ديسمبر",
}
_AR_WEEKDAYS = {
    "Monday": "الاثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء",
    "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت", "Sunday": "الأحد",
    "Mon": "الاثنين", "Tue": "الثلاثاء", "Wed": "الأربعاء", "Thu": "الخميس",
    "Fri": "الجمعة", "Sat": "السبت", "Sun": "الأحد",
}

# شرح الدالة _translate_date_words: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _translate_date_words(source: str) -> str:
    result = source
    for word, arabic in {**_AR_MONTHS, **_AR_WEEKDAYS}.items():
        result = re.sub(rf"\b{re.escape(word)}\b", arabic, result)
    return result

# شرح الدالة translate_text: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def translate_text(text: Any, language: str | None = None) -> str:
    source = "" if text is None else str(text)
    lang = set_language_value(language) if language is not None else get_language()
    if lang == LANGUAGE_EN or not source:
        return source
    if source in AR:
        return AR[source]
    # Handle common dynamic English messages without touching arbitrary user data.
    patterns = [
        (r"^Backup created:\n(.+)$", lambda m: f"تم إنشاء النسخة الاحتياطية:\n{m.group(1)}"),
        (r"^Restore completed\.\nSafety backup:\n(.+)\n\nRestart the application to reload all pages\.$", lambda m: f"اكتملت الاستعادة.\nنسخة الأمان:\n{m.group(1)}\n\nأعد تشغيل التطبيق لإعادة تحميل جميع الصفحات."),
        (r"^(\d+(?:\.\d+)?)% paid$", lambda m: f"{m.group(1)}% مدفوع"),
        (r"^Payment for debt #(.+)$", lambda m: f"دفعة عن الدين #{m.group(1)}"),
        (r"^New Situation N°(.+)$", lambda m: f"وضعية جديدة رقم {m.group(1)}"),
        (r"^LOCAL • (DARK|LIGHT) PREVIEW$", lambda m: f"محلي • معاينة {'داكن' if m.group(1).upper() == 'DARK' else 'فاتح'}"),
        (r"^(\d+)\s+total$", lambda m: f"{m.group(1)} إجمالي"),
        (r"^(\d+)\s+registered$", lambda m: f"{m.group(1)} مسجل"),
        (r"^(\d+)\s+active$", lambda m: f"{m.group(1)} نشط"),
        (r"^(\d+)\s+present$", lambda m: f"{m.group(1)} حاضر"),
        (r"^(\d+)\s+employees$", lambda m: f"{m.group(1)} موظف"),
        (r"^(\d+)\s+items$", lambda m: f"{m.group(1)} بند"),
        (r"^(\d+)\s+situations$", lambda m: f"{m.group(1)} وضعية"),
        (r"^(\d+)\s+open records$", lambda m: f"{m.group(1)} سجل مفتوح"),
        (r"^(\d+)\s+records$", lambda m: f"{m.group(1)} سجل"),
        (r"^(\d+)\s+activity logs$", lambda m: f"{m.group(1)} سجل نشاط"),
        (r"^(\d+)\s+total$", lambda m: f"{m.group(1)} إجمالي"),
        (r"^(\d+)\s+expiring soon$", lambda m: f"{m.group(1)} توشك على الانتهاء"),
        (r"^(\d+)\s+maintenance due$", lambda m: f"{m.group(1)} صيانة مستحقة"),
        (r"^(\d+(?:\.\d+)?)%\s+month rate$", lambda m: f"نسبة الشهر {m.group(1)}%"),
        (r"^(\d+)\s+BOQ items$", lambda m: f"{m.group(1)} بند جدول كميات"),
        (r"^(\d+)\s+situations recorded$", lambda m: f"{m.group(1)} وضعية مسجلة"),
        (r"^(.+)\s+this month$", lambda m: f"{m.group(1)} هذا الشهر"),
        (r"^(.+)\s+received this month$", lambda m: f"{m.group(1)} المستلم هذا الشهر"),
        (r"^(\d+)\s+monthly records$", lambda m: f"{m.group(1)} سجل شهري"),
        (r"^Operational fleet$", lambda m: "أسطول التشغيل"),
        (r"^Administrative records$", lambda m: "سجلات إدارية"),
        (r"^No debt data$", lambda m: "لا توجد بيانات ديون"),
        (r"^Budget, expenditure and cash movement at a glance\.$", lambda m: "نظرة سريعة على الميزانية والمصروفات وحركة النقد."),
        (r"^Items that may require attention\.$", lambda m: "العناصر التي قد تتطلب الانتباه."),
        (r"^Active projects are shown first, followed by the highest-budget records\.$", lambda m: "تظهر المشاريع النشطة أولًا، ثم السجلات ذات أعلى الميزانيات."),
        (r"^Active staff ranked by recorded presence and working hours\.$", lambda m: "الموظفون النشطون مرتبين حسب الحضور المسجل وساعات العمل."),
        (r"^Attendance indicators for (.+)\.$", lambda m: f"مؤشرات الحضور لـ {m.group(1)}."),
        (r"^Last refresh • (.+)$", lambda m: f"آخر تحديث • {m.group(1)}"),
        (r"^(\d+)\s+projects?\s+•\s+(\d+)\s+active\s+•\s+Total budget HT:\s*(.+)$", lambda m: f"{m.group(1)} مشروع • {m.group(2)} نشط • إجمالي الميزانية HT: {m.group(3)}"),
        (r"^(\d+)\s+registered\s+•\s+(\d+)\s+active$", lambda m: f"{m.group(1)} مسجل • {m.group(2)} نشط"),
        (r"^(\d+)\s+active\s+of\s+(\d+)\s+registered$", lambda m: f"{m.group(1)} نشط من أصل {m.group(2)} مسجل"),
        (r"^(\d+)\s+vehicles\s+•\s+(\d+)\s+active\s+•\s+(\d+)\s+in maintenance$", lambda m: f"{m.group(1)} مركبة • {m.group(2)} نشطة • {m.group(3)} قيد الصيانة"),
        (r"^(\d+)\s+items\s+•\s+Total:\s*(.+)$", lambda m: f"{m.group(1)} بند • الإجمالي: {m.group(2)}"),
        (r"^Total recorded hours:\s*(.+)$", lambda m: f"إجمالي ساعات العمل المسجلة: {m.group(1)}"),
        (r"^Total item value:\s*(.+)$", lambda m: f"إجمالي قيمة البنود: {m.group(1)}"),
        (r"^(\d+)\s+records$", lambda m: f"{m.group(1)} سجل"),
        (r"^No debt records\. Current open exposure:\s*(.+)$", lambda m: f"لا توجد سجلات ديون. الانكشاف المفتوح الحالي: {m.group(1)}"),
        (r"^No vehicle records\. Registered vehicles:\s*(.+)$", lambda m: f"لا توجد سجلات مركبات. المركبات المسجلة: {m.group(1)}"),
        (r"^BOQ value:\s*(.+)\s+•\s+Executed through situations:\s*(.+)\s+•\s+Remaining:\s*(.+)$", lambda m: f"قيمة جدول الكميات: {m.group(1)} • المنفذ عبر الوضعيات: {m.group(2)} • المتبقي: {m.group(3)}"),
        (r"^Total:\s*(.+)$", lambda m: f"الإجمالي: {m.group(1)}"),
        (r"^Paid:\s*(.+)$", lambda m: f"المدفوع: {m.group(1)}"),
        (r"^Outstanding:\s*(.+)$", lambda m: f"المتبقي: {m.group(1)}"),
        (r"^Theme:\s*(.+)$", lambda m: f"المظهر: {translate_text(m.group(1), lang)}"),
        (r"^Readiness: (READY|NOT READY) • Blocking issues: (\d+) • Final forecast cost: (.+) • Forecast margin: (.+)$",
         lambda m: f"الجاهزية: {'جاهز' if m.group(1).upper() == 'READY' else 'غير جاهز'} • المشكلات المانعة: {m.group(2)} • التكلفة المتوقعة النهائية: {m.group(3)} • الهامش المتوقع: {m.group(4)}"),
        (r"^Cash forecast \((\d+) days\): projected net (.+) • Receivable (.+) • Payable (.+)$",
         lambda m: f"التوقع النقدي ({m.group(1)} يوم): صافي التدفق المتوقع {m.group(2)} • المستحق التحصيل {m.group(3)} • المستحق الدفع {m.group(4)}"),
        (r"^(.+) • Overall (.+) • Health (.+)/100 • Progress (.+)% • Cost (.+)% • Collection (.+)% • Labor (.+) • Materials (.+) • Vehicles (.+) • Documents (.+)$",
         lambda m: f"{m.group(1)} • الحالة العامة {translate_text(m.group(2), LANGUAGE_AR)} • الصحة {m.group(3)}/100 • التقدم {m.group(4)}% • التكلفة {m.group(5)}% • التحصيل {m.group(6)}% • العمالة {translate_text(m.group(7), LANGUAGE_AR)} • المواد {translate_text(m.group(8), LANGUAGE_AR)} • المركبات {translate_text(m.group(9), LANGUAGE_AR)} • الوثائق {translate_text(m.group(10), LANGUAGE_AR)}"),
        (r"^Executive scan complete • Health (\d+)/100 • Critical (\d+) • High (\d+) • Medium (\d+) • New alerts (\d+) • New actions (\d+)$", lambda m: f"اكتمل الفحص التنفيذي • الصحة {m.group(1)}/100 • حرجة {m.group(2)} • عالية {m.group(3)} • متوسطة {m.group(4)} • تنبيهات جديدة {m.group(5)} • إجراءات جديدة {m.group(6)}"),
        (r"^Reconciliation passed\.$", lambda m: "اجتازت المطابقة بنجاح."),
        (r"^Reconciliation found (\d+) issue\(s\)\.$", lambda m: f"أظهرت المطابقة {m.group(1)} مشكلة."),
        (r"^Management report generated successfully:\n(.+)$", lambda m: f"تم إنشاء تقرير الإدارة بنجاح:\n{m.group(1)}"),
        (r"^Could not generate management report: (.+)$", lambda m: f"تعذر إنشاء تقرير الإدارة: {m.group(1)}"),
        (r"^Forecast cost: (.+)\nVariance vs budget: (.+)\nForecast margin: (.+)$", lambda m: f"التكلفة المتوقعة: {m.group(1)}\nالانحراف عن الميزانية: {m.group(2)}\nالهامش المتوقع: {m.group(3)}"),
        (r"^Could not save staff member\.\s*\n\s*(.*)$", lambda m: "تعذر حفظ الموظف." + (f"\n\n{m.group(1)}" if m.group(1) else "")),
        (r"^Statistics could not be calculated\.\s*\n\s*(.*)$", lambda m: "تعذر حساب الإحصائيات." + (f"\n\n{m.group(1)}" if m.group(1) else "")),
        (r"^Could not delete the document\.\s*\n\s*(.*)$", lambda m: "تعذر حذف الوثيقة." + (f"\n\n{m.group(1)}" if m.group(1) else "")),
        (r"^Could not save document\.\s*\n\s*(.*)$", lambda m: "تعذر حفظ الوثيقة." + (f"\n\n{m.group(1)}" if m.group(1) else "")),
        (r"^Could not save item\. Item number may already exist for this project\.\s*\n\s*(.*)$", lambda m: "تعذر حفظ البند. قد يكون رقم البند مستخدمًا بالفعل في هذا المشروع." + (f"\n\n{m.group(1)}" if m.group(1) else "")),
        (r"^(\d+) BOQ item\(s\) still have remaining quantities\.$", lambda m: f"لا تزال هناك كميات متبقية في {m.group(1)} بند من جدول الكميات."),
        (r"^(\d+) situation\(s\) are still Draft\.$", lambda m: f"لا تزال {m.group(1)} وضعية في حالة مسودة."),
        (r"^Situation N°(.+) is not Approved/Paid\.$", lambda m: f"الوضعية رقم {m.group(1)} ليست معتمدة/مدفوعة."),
        (r"^Imported (\d+) row\(s\)\. Skipped: (\d+)\.$", lambda m: f"تم استيراد {m.group(1)} صف. تم تخطي: {m.group(2)}."),
        (r"^Detected (\d+) data row\(s\)\. Map the columns once, then import the batch\.$", lambda m: f"تم اكتشاف {m.group(1)} صف بيانات. طابق الأعمدة مرة واحدة، ثم نفّذ الاستيراد الدفعي."),
        (r"^Delete receipt (.+)\? This changes the project's received amount\.$", lambda m: f"حذف الوصل {m.group(1)}؟ سيؤدي ذلك إلى تغيير المبلغ المستلم للمشروع."),
        (r"^Delete debt #(.+) and its recorded payments\? This changes financial history\.$", lambda m: f"حذف الدين رقم {m.group(1)} والدفعات المسجلة له؟ سيؤدي ذلك إلى تغيير السجل المالي."),
        (r"^Please enter the reference for this (.+) payment\.$", lambda m: f"يرجى إدخال مرجع دفعة {m.group(1)}."),
        (r"^Could not refresh the page\.\s*(.*)$", lambda m: "تعذر تحديث الصفحة." + (f"\n\n{m.group(1)}" if m.group(1) else "")),
        (r"^Global Search •\s*(.+)$", lambda m: f"البحث العام • {m.group(1)}"),
        (r"^BuildOffice Pro\s+•\s+(.+)$", lambda m: f"BuildOffice Pro • {translate_text(m.group(1), lang)}"),
        (r"^Search results for\s+“(.+)”$", lambda m: f"نتائج البحث عن “{m.group(1)}”"),
        (r"^(\d+)\s+records?$", lambda m: f"{m.group(1)} سجل"),
        (r"^(\d+)\s+projects?\s+•\s+(\d+)\s+active\s+•\s+Total budget HT:\s*(.+)$", lambda m: f"{m.group(1)} مشروع • {m.group(2)} نشط • إجمالي الميزانية HT: {m.group(3)}"),
        (r"^Showing\s+(\d+)\s+receipts\s+•\s+Current view:\s*(.+)\s+•\s+Total received:\s*(.+)\s+•\s+Contract HT:\s*(.+)$", lambda m: f"عرض {m.group(1)} وصل • العرض الحالي: {m.group(2)} • إجمالي المستلم: {m.group(3)} • العقد HT: {m.group(4)}"),
        (r"^Estimated revenue after selected-period expenses:\s*(.+)$", lambda m: f"الإيرادات التقديرية بعد مصاريف الفترة المحددة: {m.group(1)}"),
        (r"^Expense Details -\s*(.+)$", lambda m: f"تفاصيل المصروف - {m.group(1)}"),
        (r"^Expense\s+(.+)$", lambda m: f"المصروف {m.group(1)}"),
        (r"^(\d+)\s+project\(s\)$", lambda m: f"{m.group(1)} مشروع(ات)"),
        (r"^Final progress:\s*(.+)%\s+•\s+Executed:\s*(.+)\s+•\s+Remaining:\s*(.+)$", lambda m: f"التقدم النهائي: {m.group(1)}% • المنفذ: {m.group(2)} • المتبقي: {m.group(3)}"),
        (r"^This project has historical records and cannot be deleted\.\s*\n\s*Archive the project instead so its financial and operational history remains intact\.(?:\s*\n\s*(.+))?$", lambda m: "هذا المشروع يحتوي على سجلات تاريخية ولا يمكن حذفه.\n\nأرشف المشروع بدلًا من ذلك للحفاظ على تاريخه المالي والتشغيلي." + (f"\n\n{m.group(1)}" if m.group(1) else "")),
        (r"^Delete project (.+)\? This is allowed only because it has no dependent history\.$", lambda m: f"حذف المشروع {m.group(1)}؟ لا يُسمح بذلك إلا لأنه لا توجد سجلات مرتبطة به."),
        (r"^Archive project (.+)\? Historical data will be preserved\.$", lambda m: f"أرشفة المشروع {m.group(1)}؟ سيتم الحفاظ على البيانات التاريخية."),
        (r"^Could not save project\.\s*\n\s*The contract code may already be used by another project\.\s*\n\s*(.*)$", lambda m: "تعذر حفظ المشروع.\n\nقد يكون رمز العقد مستخدمًا بالفعل من مشروع آخر." + (f"\n\n{m.group(1)}" if m.group(1) else "")),
        (r"^Could not save project\.\s*\n\s*(.*)$", lambda m: "تعذر حفظ المشروع." + (f"\n\n{m.group(1)}" if m.group(1) else "")),
        (r"^Could not save attendance:\s*\n\s*(.*)$", lambda m: "تعذر حفظ الحضور:" + (f"\n\n{m.group(1)}" if m.group(1) else "")),
        (r"^The payment could not be recorded\.\s*\n\s*(.*)$", lambda m: "تعذر تسجيل الدفعة." + (f"\n\n{m.group(1)}" if m.group(1) else "")),
        (r"^The Métré item could not be deleted\.\s*\n\s*(.*)$", lambda m: "تعذر حذف بند جدول الكميات." + (f"\n\n{m.group(1)}" if m.group(1) else "")),
        (r"^Please enter the reference for this (.+) payment\.$", lambda m: f"يرجى إدخال مرجع دفعة {translate_text(m.group(1), lang)}."),
        (r"^Delete debt #(.+) and its recorded payments\? This changes financial history\.$", lambda m: f"حذف الدين #{m.group(1)} والدفعات المسجلة الخاصة به؟ سيؤثر ذلك في السجل المالي."),
        (r"^Archive project (.+)\? Historical data will be preserved\.$", lambda m: f"أرشفة المشروع {m.group(1)}؟ سيتم الحفاظ على البيانات التاريخية."),
        (r"^Could not save item\. Item number may already exist for this project\.\s*\n\s*(.*)$", lambda m: "تعذر حفظ البند. قد يكون رقم البند مستخدمًا بالفعل في هذا المشروع." + (f"\n\n{m.group(1)}" if m.group(1) else "")),
        (r"^Could not save staff member\.\s*\n\s*(.*)$", lambda m: "تعذر حفظ الموظف." + (f"\n\n{m.group(1)}" if m.group(1) else "")),
    ]
    for pattern, fn in patterns:
        m = re.match(pattern, source, re.IGNORECASE | re.DOTALL)
        if m:
            return fn(m)
    # QDate/QDateTime can produce English month/day names depending on the
    # system locale. Translate those words without altering numeric/date data.
    if re.search(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b", source):
        return _translate_date_words(source)
    return source

# شرح الدالة _catalog_source: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _catalog_source(value: str) -> str:
    """Recover the English source when a widget was created in Arabic mode."""
    return AR_TO_EN.get(value, value)

# شرح الدالة _source: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _source(widget: QWidget, attr: str, value: str) -> str:
    key = f"bo_i18n_{attr}"
    old = widget.property(key)
    if old is None:
        source = _catalog_source(value)
        widget.setProperty(key, source)
        return source
    # If application code changed the text after localization, accept the new
    # English source instead of permanently translating the previous value.
    if value != old and value not in AR.values() and not any("\u0600" <= ch <= "\u06ff" for ch in value):
        # النص العربي الناتج عن المترجم ليس مصدرًا جديدًا للنص.
        # هذا يحافظ على إمكانية الرجوع من العربية إلى الإنجليزية.
        widget.setProperty(key, value)
        return value
    if value != old and value not in AR.values():
        return str(old)
    return str(old)

# شرح الدالة _translate_property: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _translate_property(widget: QWidget, attr: str, value: str, language: str) -> str:
    """Translate a stored widget property while preserving its English source."""
    source = _source(widget, attr, value)
    return translate_text(str(source), language)

# شرح الدالة _translate_table_item: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _translate_table_item(item, language: str) -> None:
    """Translate catalog-backed table text without changing user/database data."""
    source_role = Qt.ItemDataRole.UserRole + 99
    value = item.text()
    source = item.data(source_role)
    if source is None:
        source = _catalog_source(value)
        # Only store catalog entries. Arbitrary names, descriptions and IDs
        # must remain untouched and must not become localization sources.
        if source in EN:
            item.setData(source_role, source)
        else:
            return
    item.setText(translate_text(str(source), language))

# شرح الدالة _translate_widget: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _translate_widget(widget: QWidget, language: str):
    if isinstance(widget, QLineEdit):
        value = widget.placeholderText()
        if value:
            widget.setPlaceholderText(
                _translate_property(widget, "placeholder", value, language)
            )

    if isinstance(widget, (QAbstractButton, QLabel)):
        value = widget.text()
        if value:
            src = _source(widget, "text", value)
            widget.setText(translate_text(src, language))

    if isinstance(widget, QGroupBox):
        value = widget.title()
        if value:
            src = _source(widget, "title", value)
            widget.setTitle(translate_text(src, language))

    if isinstance(widget, QDialog):
        value = widget.windowTitle()
        if value:
            src = _source(widget, "title", value)
            widget.setWindowTitle(translate_text(src, language))

    if widget.toolTip():
        widget.setToolTip(
            _translate_property(widget, "tooltip", widget.toolTip(), language)
        )

    if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
        suffix = widget.suffix()
        if suffix:
            widget.setSuffix(
                _translate_property(widget, "suffix", suffix, language)
            )
        prefix = widget.prefix()
        if prefix:
            widget.setPrefix(
                _translate_property(widget, "prefix", prefix, language)
            )
        special = widget.specialValueText()
        if special:
            widget.setSpecialValueText(
                _translate_property(widget, "special_value", special, language)
            )

    if isinstance(widget, QProgressBar):
        format_text = widget.format()
        if format_text:
            widget.setFormat(
                _translate_property(widget, "progress_format", format_text, language)
            )

    if isinstance(widget, QDialogButtonBox):
        standard_labels = {
            QDialogButtonBox.StandardButton.Ok: "OK",
            QDialogButtonBox.StandardButton.Save: "Save",
            QDialogButtonBox.StandardButton.Cancel: "Cancel",
            QDialogButtonBox.StandardButton.Yes: "Yes",
            QDialogButtonBox.StandardButton.No: "No",
            QDialogButtonBox.StandardButton.Close: "Close",
            QDialogButtonBox.StandardButton.Apply: "Apply",
            QDialogButtonBox.StandardButton.Reset: "Reset",
        }
        for button in widget.buttons():
            standard = widget.standardButton(button)
            source = standard_labels.get(standard)
            if source:
                button.setProperty("bo_i18n_text", source)
                button.setText(translate_text(source, language))

    if isinstance(widget, QComboBox):
        for i in range(widget.count()):
            value = widget.itemText(i)
            source_key = f"bo_i18n_item_{i}"
            src = widget.property(source_key)
            if src is None:
                # A combo may have been created while Arabic was active.
                # Always recover the English catalog source before storing it.
                src = _catalog_source(value)
                widget.setProperty(source_key, src)
            widget.setItemText(i, translate_text(str(src), language))

    if isinstance(widget, QTabWidget):
        for i in range(widget.count()):
            value = widget.tabText(i)
            source_key = f"bo_i18n_tab_{i}"
            src = widget.property(source_key)
            if src is None:
                src = _catalog_source(value)
                widget.setProperty(source_key, src)
            widget.setTabText(i, translate_text(str(src), language))

    if isinstance(widget, QTableWidget):
        for i in range(widget.columnCount()):
            item = widget.horizontalHeaderItem(i)
            if item:
                src = item.data(Qt.ItemDataRole.UserRole + 99)
                if src is None:
                    src = _catalog_source(item.text())
                    if src in EN:
                        item.setData(Qt.ItemDataRole.UserRole + 99, src)
                    else:
                        continue
                item.setText(translate_text(str(src), language))
        for i in range(widget.rowCount()):
            item = widget.verticalHeaderItem(i)
            if item:
                _translate_table_item(item, language)
            for j in range(widget.columnCount()):
                cell = widget.item(i, j)
                if cell:
                    _translate_table_item(cell, language)

# شرح الدالة localize_widget_tree: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def localize_widget_tree(root: QWidget | QApplication | None, language: str | None = None):
    """Apply localization once to a widget tree.

    This is intentionally explicit rather than being triggered for every Qt
    Show/WindowTitleChange event. Re-scanning the entire application on every
    visibility event caused noticeable UI lag.
    """
    if root is None:
        return
    if not isinstance(root, QWidget):
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            return
        root = app.activeWindow()
        if not isinstance(root, QWidget):
            return
    lang = set_language_value(language or get_language())
    _translate_widget(root, lang)
    for widget in root.findChildren(QWidget):
        _translate_widget(widget, lang)


# شرح الصنف LocalizedComboBox: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class LocalizedComboBox(QComboBox):
    """ComboBox يعرض العربية ويحافظ على currentText() الإنجليزي للمنطق الداخلي."""

    SOURCE_ROLE = Qt.ItemDataRole.UserRole + 100

# شرح الدالة addItem: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def addItem(self, text, userData=None):
        source = _catalog_source(str(text))
        super().addItem(translate_text(source), userData)
        self.setItemData(self.count() - 1, source, self.SOURCE_ROLE)

# شرح الدالة addItems: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def addItems(self, texts):
        for text in texts:
            self.addItem(text)

# شرح الدالة insertItem: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def insertItem(self, index, text, userData=None):
        source = _catalog_source(str(text))
        super().insertItem(index, translate_text(source), userData)
        self.setItemData(index, source, self.SOURCE_ROLE)

# شرح الدالة setCurrentText: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def setCurrentText(self, text: str):
        wanted = str(text)
        for i in range(self.count()):
            if self.itemSourceText(i) == wanted or self.itemText(i) == wanted:
                self.setCurrentIndex(i)
                return
        super().setCurrentText(wanted)

# شرح الدالة findText: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def findText(self, text: str, flags=Qt.MatchFlag.MatchExactly) -> int:
        wanted = str(text)
        for i in range(self.count()):
            if self.itemSourceText(i) == wanted or self.itemText(i) == wanted:
                return i
        return super().findText(wanted, flags)

# شرح الدالة currentText: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def currentText(self) -> str:
        index = self.currentIndex()
        if index >= 0:
            source = self.itemData(index, self.SOURCE_ROLE)
            if source is not None:
                return str(source)
        return super().currentText()

# شرح الدالة itemSourceText: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def itemSourceText(self, index: int) -> str:
        source = self.itemData(index, self.SOURCE_ROLE)
        return str(source) if source is not None else super().itemText(index)

# شرح الصنف LocalizationController: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class LocalizationController(QObject):
    """يراقب إنشاء/عرض عناصر الواجهة ويطبق اللغة الحالية بدون RTL."""

    def __init__(self, app: QApplication):
        super().__init__(app)
        self.app = app
        self._updating = False
        # حالة مؤقتات عجلة الفأرة لكل ComboBox بشكل مستقل
        self._combo_timers: dict[int, QTimer] = {}
        self._combo_ready: set[int] = set()
        self._combo_refs: dict[int, QComboBox] = {}
        app.installEventFilter(self)
        self.language = set_language(get_language())

# شرح الدالة _combo_from_widget: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _combo_from_widget(self, widget):
        # العثور على ComboBox حتى لو كان الحدث صادرًا من عنصر داخلي
        current = widget
        while current is not None:
            if isinstance(current, QComboBox):
                return current
            current = current.parentWidget() if hasattr(current, "parentWidget") else None
        return None

# شرح الدالة _start_combo_delay: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _start_combo_delay(self, combo):
        key = id(combo)
        self._combo_refs[key] = combo
        self._combo_ready.discard(key)
        timer = self._combo_timers.get(key)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda k=key: self._combo_delay_finished(k))
            self._combo_timers[key] = timer
        timer.start(COMBO_WHEEL_DELAY_MS)

# شرح الدالة _combo_delay_finished: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _combo_delay_finished(self, key):
        combo = self._combo_refs.get(key)
        if combo is not None:
            self._combo_ready.add(key)

# شرح الدالة _reset_combo_delay: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _reset_combo_delay(self, combo):
        key = id(combo)
        timer = self._combo_timers.pop(key, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()
        self._combo_ready.discard(key)
        self._combo_refs.pop(key, None)

# شرح الدالة _cursor_inside_combo: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _cursor_inside_combo(self, combo):
        try:
            pos = combo.mapFromGlobal(self.app.primaryScreen().availableGeometry().center())
            # لا نعتمد على screen center؛ هذه الدالة تُستخدم فقط كحارس احتياطي.
            return combo.rect().contains(pos)
        except (RuntimeError, AttributeError):
            return False

# شرح الدالة _handle_combo_wheel: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _handle_combo_wheel(self, watched, event):
        combo = self._combo_from_widget(watched)
        if combo is None:
            return False

        # عند فتح القائمة، التمرير داخل القائمة يجب أن يعمل فورًا.
        try:
            if combo.view().isVisible():
                return False
        except RuntimeError:
            pass

        key = id(combo)
        if key not in self._combo_refs:
            self._start_combo_delay(combo)

        if key not in self._combo_ready:
            event.ignore()
            return True

        return False

# شرح الدالة set_language: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def set_language(self, language: str):
        """Change the active language and refresh every currently loaded window once."""
        self.language = set_language(language)
        self._updating = True
        try:
            # Only loaded top-level windows are scanned, and only once per language change.
            for top_level in self.app.topLevelWidgets():
                if isinstance(top_level, QWidget):
                    localize_widget_tree(top_level, self.language)
        finally:
            self._updating = False

# شرح الدالة eventFilter: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def eventFilter(self, watched, event):
        if self._updating:
            return False

        # Combo wheel protection remains event-driven because it is an interaction rule,
        # not a localization rule.
        if isinstance(watched, QWidget):
            if isinstance(watched, QComboBox):
                if event.type() == QEvent.Type.Enter:
                    self._start_combo_delay(watched)
                elif event.type() == QEvent.Type.Leave:
                    try:
                        if not watched.view().isVisible():
                            self._reset_combo_delay(watched)
                    except RuntimeError:
                        self._reset_combo_delay(watched)

            if event.type() == QEvent.Type.Wheel:
                return self._handle_combo_wheel(watched, event)

            # Newly opened dialogs can contain widgets created after the last language
            # change. Localize that dialog once when it becomes visible. Do not react to
            # WindowTitleChange, which previously caused unnecessary full-tree rescans.
            if event.type() == QEvent.Type.Show and isinstance(watched, QDialog):
                self._updating = True
                try:
                    localize_widget_tree(watched, self.language)
                finally:
                    self._updating = False
        return False

_CONTROLLER: LocalizationController | None = None

# شرح الدالة install_localization: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def install_localization(app: QApplication) -> LocalizationController:
    global _CONTROLLER
    if _CONTROLLER is None:
        _CONTROLLER = LocalizationController(app)
    return _CONTROLLER

# شرح الدالة controller: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def controller() -> LocalizationController | None:
    return _CONTROLLER

__all__ = [
    "AR",
    "COMBO_WHEEL_DELAY_MS",
    "LANGUAGE_AR",
    "LANGUAGE_EN",
    "LocalizedComboBox",
    "get_language",
    "install_localization",
    "localize_widget_tree",
    "set_language",
    "translate_text",
]

# Short stable alias for UI code.
tr = translate_text


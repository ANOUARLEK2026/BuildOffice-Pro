# ============================================================
# شرح الملف: core/config.py
# هذا الملف جزء من المكوّنات الأساسية المشتركة في التطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. استخدم الإعدادات المركزية وتجنب تعديل منطق الأعمال من الواجهة.
"""
إعدادات BuildOffice Pro المركزية.

غيّر القيم الموجودة هنا أولًا عند الحاجة إلى تعديل إعدادات عامة.
لا تعدّل صفحات الواجهة أو الخدمات فقط من أجل تغيير قيمة إعداد عامة.
"""
from __future__ import annotations

from pathlib import Path

# مسار جذر التطبيق، وهو مجلد المشروع الذي يحتوي على main.py.
ROOT_DIR = Path(__file__).resolve().parent.parent

# -------------------- معلومات التطبيق --------------------
APP_NAME = "BuildOffice Pro"
ORGANIZATION_NAME = "BuildOffice Pro"
# Keep the displayed/application version synchronized with the project VERSION file.
# The fallback preserves startup if the file is missing in an unusual deployment.
_VERSION_FILE = ROOT_DIR / "VERSION"
try:
    APP_VERSION = _VERSION_FILE.read_text(encoding="utf-8").strip() or "1.0.0"
except (OSError, UnicodeError):
    APP_VERSION = "1.0.0"

# -------------------- قاعدة البيانات --------------------
DATABASE_FILENAME = "buildoffice.db"
DATABASE_TIMEOUT_SECONDS = 10.0
DATABASE_BUSY_TIMEOUT_MS = int(DATABASE_TIMEOUT_SECONDS * 1000)
DATABASE_SYNCHRONOUS = "NORMAL"
DATABASE_JOURNAL_MODE = "WAL"

# -------------------- السجل (Logs) --------------------
LOG_DIR_NAME = "logs"
LOG_FILENAME = "buildoffice.log"
LOG_LEVEL = "INFO"
LOG_MAX_BYTES = 2 * 1024 * 1024
LOG_BACKUP_COUNT = 5

# -------------------- النسخ الاحتياطي --------------------
BACKUP_FILENAME_PREFIX = "buildoffice_"
SAFETY_BACKUP_PREFIX = ".safety_"
RESTORE_TEMP_SUFFIX = ".restore.tmp"

# -------------------- توليد مستندات الوضعيات --------------------
GENERATED_DIR_NAME = "generated"
SITUATION_GENERATED_DIR_NAME = "situations"
SITUATION_TEMPLATES_DIR_NAME = "situation_templates"

# -------------------- الواجهة --------------------
DEFAULT_THEME = "Light"
LIGHT_THEME_NAME = "Light"
DARK_THEME_NAME = "Dark"

# -------------------- قواعد مالية عامة --------------------
DEFAULT_TVA_PERCENT = 19
ALLOWED_TVA_PERCENTAGES = (0, 9, 19)

# -------------------- سلوك الصيانة --------------------
# إذا كان True يتم تسجيل معلومات إضافية أثناء التطوير.
DEBUG_MODE = False


# شرح الدالة database_path: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def database_path() -> Path:
    """إرجاع مسار قاعدة البيانات الافتراضي."""
    return ROOT_DIR / DATABASE_FILENAME


# شرح الدالة generated_dir: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def generated_dir() -> Path:
    """إرجاع مجلد الملفات المولدة وإنشاؤه عند الحاجة."""
    path = ROOT_DIR / GENERATED_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


# شرح الدالة situation_generated_dir: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def situation_generated_dir() -> Path:
    """إرجاع مجلد مستندات الوضعيات وإنشاؤه عند الحاجة."""
    path = generated_dir() / SITUATION_GENERATED_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


# شرح الدالة log_dir: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def log_dir() -> Path:
    """إرجاع مجلد السجلات وإنشاؤه عند الحاجة."""
    path = ROOT_DIR / LOG_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path

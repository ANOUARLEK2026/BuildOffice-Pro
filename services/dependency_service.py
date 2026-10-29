# ============================================================
# شرح الملف: services/dependency_service.py
# فحص المكتبات الاختيارية اللازمة لإنشاء Word وExcel.
# ============================================================
from __future__ import annotations

import importlib.util
import sys

DOCUMENT_DEPENDENCIES = {
    "python-docx": "docx",
    "openpyxl": "openpyxl",
}


def missing_document_dependencies() -> list[str]:
    """Return the document-generation packages missing from the active Python interpreter."""
    return [
        package
        for package, module in DOCUMENT_DEPENDENCIES.items()
        if importlib.util.find_spec(module) is None
    ]


def document_dependencies_ready() -> bool:
    """Return True when Word/Excel document dependencies are importable."""
    return not missing_document_dependencies()


def dependency_install_message() -> str:
    """Build an actionable message using the interpreter running BuildOffice Pro."""
    missing = missing_document_dependencies()
    if not missing:
        return "Word/Excel document dependencies are installed."
    packages = ", ".join(missing)
    return (
        f"Missing document-generation packages: {packages}.\n\n"
        "Install them with:\n"
        f'\"{sys.executable}\" -m pip install {" ".join(missing)}\n\n'
        "Or run the included 'Install BuildOffice Pro Dependencies.bat'."
    )

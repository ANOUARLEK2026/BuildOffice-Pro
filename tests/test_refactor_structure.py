# ============================================================
# شرح الملف: tests/test_refactor_structure.py
# هذا الملف جزء من اختبارات السلامة والتكامل وصحة الوظائف.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""اختبارات بنيوية بسيطة للوحدات التي تمت إعادة تنظيمها."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# شرح الدالة _function_args: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _function_args(path: Path, name: str) -> list[str]:
    """إرجاع أسماء وسائط الدالة المطلوبة من الملف."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return [arg.arg for arg in node.args.args]
    raise AssertionError(f"الدالة غير موجودة: {name}")


# شرح الدالة test_expense_dialog_signatures_are_stable: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_expense_dialog_signatures_are_stable():
    assert _function_args(ROOT / "pages/expense_dialog_form.py", "_expense_dialog") == ["page", "expense_id"]
    assert _function_args(ROOT / "pages/expense_details_dialog.py", "_expense_details") == ["page", "expense_id"]
    assert _function_args(ROOT / "pages/expense_payment_dialog.py", "_record_payment_dialog") == ["page", "expense_id"]


# شرح الدالة test_dashboard_refresh_delegates_to_service_and_renderer: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_dashboard_refresh_delegates_to_service_and_renderer():
    path = ROOT / "pages/dashboard_page.py"
    text = path.read_text(encoding="utf-8")
    assert "load_dashboard_data" in text
    assert "_build_kpis" in text
    assert "_build_projects" in text
    assert text.count("def refresh(self):") == 1


# شرح الدالة test_metrics_expose_shared_spacing_and_control_height: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_metrics_expose_shared_spacing_and_control_height():
    text = (ROOT / "theme/metrics.py").read_text(encoding="utf-8")
    for name in ("SPACE_XS", "SPACE_SM", "SPACE_MD", "SPACE_LG", "SPACE_XL", "SPACE_XXL", "SPACE_XXXL", "CONTROL_HEIGHT"):
        assert f"{name}:" in text

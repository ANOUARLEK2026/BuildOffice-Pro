# ============================================================
# شرح الملف: tests/test_theme_registry.py
# هذا الملف جزء من اختبارات السلامة والتكامل وصحة الوظائف.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""اختبارات اتساق سجل السمات مع تنسيقات QSS ومنع رجوع الأسماء القديمة."""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# شرح الدالة _application_qss: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _application_qss() -> str:
    """استخراج نص QSS الخام واستبدال علامات المقاييس بقيمها دون تحميل Qt."""
    selectors_path = ROOT / "theme" / "selectors.py"
    metrics_path = ROOT / "theme" / "metrics.py"
    selectors_tree = ast.parse(selectors_path.read_text(encoding="utf-8"))
    raw = None
    for node in selectors_tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "APPLICATION_SELECTORS"
            for target in node.targets
        ):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                raw = node.value.value
                break
    assert raw is not None

    metrics_tree = ast.parse(metrics_path.read_text(encoding="utf-8"))
    values = {
        node.target.id: node.value.value
        for node in metrics_tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    for name, value in values.items():
        raw = raw.replace(f"__{name}__", str(value))
    return raw


# شرح الدالة _selector_properties: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _selector_properties(qss: str) -> dict[str, dict[str, str]]:
    """تحويل كتل QSS إلى قاموس بسيط لتسهيل فحص الملكية."""
    result: dict[str, dict[str, str]] = {}
    for selector_text, body in re.findall(r"([^{}]+)\{([^{}]*)\}", qss, re.DOTALL):
        properties = {
            name.strip(): value.strip()
            for name, value in re.findall(r"([\w-]+)\s*:\s*([^;{}]+)", body)
        }
        for selector in selector_text.split(","):
            selector = selector.strip()
            if selector:
                result[selector] = properties
    return result


# شرح الدالة test_component_namespace_has_no_legacy_special_refs: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_component_namespace_has_no_legacy_special_refs():
    """التأكد من عدم وجود مراجع حيز special القديم في كود التشغيل."""
    legacy_at = "@" + "special."
    legacy_double = chr(34) + "special."
    legacy_single = chr(39) + "special."

    for path in ROOT.rglob("*.py"):
        if "__pycache__" in path.parts or path == Path(__file__):
            continue
        text = path.read_text(encoding="utf-8")
        assert legacy_at not in text
        assert legacy_double not in text
        assert legacy_single not in text


# شرح الدالة test_selector_registry_tokens_exist_and_match_qss: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_selector_registry_tokens_exist_and_match_qss():
    """التأكد من أن كل token في السجل موجود فعليًا داخل قاعدة QSS المقصودة."""
    mapping_tree = ast.parse((ROOT / "theme" / "mappings.py").read_text(encoding="utf-8"))
    registry = None
    for node in mapping_tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "SELECTOR_PROPERTY_TOKENS"
        ):
            if node.value is None:
                continue
            registry = ast.literal_eval(node.value)
            break
    assert registry is not None

    actual = _selector_properties(_application_qss())
    errors = []
    for registered_selector, properties in registry.items():
        for selector in (item.strip() for item in registered_selector.split(",") if item.strip()):
            if selector not in actual:
                errors.append(f"المحدد غير موجود: {selector}")
                continue
            for property_name, token in properties.items():
                value = actual[selector].get(property_name)
                if value is None:
                    errors.append(f"الخاصية غير موجودة: {selector} :: {property_name}")
                    continue
                placeholder = f"@{token}@"
                if placeholder not in value:
                    errors.append(
                        f"الـ token غير مطابق: {selector} :: {property_name} -> {token}"
                    )
    assert not errors, "\n".join(errors)

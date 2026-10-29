# ============================================================
# شرح الملف: tests/test_theme_integrity.py
# هذا الملف جزء من اختبارات السلامة والتكامل وصحة الوظائف.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: اختبارات نظام السمات والألوان فقط، دون لمس منطق الأعمال.
from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# شرح الدالة _load_theme_modules: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _load_theme_modules():
    """تحميل ملفات السمات مباشرة لتجنب اعتماد اختبارات الألوان على Qt."""
    package = types.ModuleType("theme_test_package")
    package.__path__ = [str(ROOT / "theme")]
    sys.modules[package.__name__] = package

    modules = {}
    for name in ("colors", "themes"):
        spec = importlib.util.spec_from_file_location(
            f"{package.__name__}.{name}", ROOT / "theme" / f"{name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        modules[name] = module
    return modules["colors"], modules["themes"]


COLORS, THEMES = _load_theme_modules()


# شرح الدالة _luminance: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _luminance(hex_color: str) -> float:
    values = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in values
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


# شرح الدالة _contrast: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _contrast(first: str, second: str) -> float:
    a, b = _luminance(first), _luminance(second)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


# شرح الدالة test_theme_catalog_is_complete_and_unique: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_theme_catalog_is_complete_and_unique():
    assert len(COLORS.ALL_TOKENS) == len(set(COLORS.ALL_TOKENS))
    assert not THEMES.validate_themes()


# شرح الدالة test_shared_qss_tokens_exist_in_catalog: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_shared_qss_tokens_exist_in_catalog():
    token_re = re.compile(r"@([A-Za-z0-9_.-]+)@")
    sources = [
        *ROOT.glob("theme/*.py"),
        *ROOT.glob("core/*.py"),
        *ROOT.glob("pages/*.py"),
        *ROOT.glob("dev_tools/*.py"),
    ]
    for path in sources:
        text = path.read_text(encoding="utf-8")
        tokens = set(token_re.findall(text))
        assert tokens <= set(COLORS.ALL_TOKENS), f"Unknown tokens in {path}: {tokens - set(COLORS.ALL_TOKENS)}"


# شرح الدالة test_no_legacy_color_aliases_remain_in_runtime_code: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_no_legacy_color_aliases_remain_in_runtime_code():
    legacy = re.compile(
        r"@(brand\.gold_light|charts\.(?:amber|apricot|aqua|azure|azure_dark|blush|brown|coffee|coral|crimson|cyan|cyan_alt|emerald|gold_alt|graphite|lavender|lemon|magenta|mint|navy_blue|peach|pink|plum|purple_alt|rose|rose_alt|silver|sky|slate|steel|steel_blue|steel_blue_alt|tan|teal|teal_alt|teal_bright|turquoise|violet_alt|yellow|purple))@"
    )
    runtime_files = [
        *ROOT.glob("theme/*.py"),
        ROOT / "pages" / "base_page.py",
        ROOT / "pages" / "dashboard_page.py",
        ROOT / "pages" / "statistics_page.py",
        ROOT / "pages" / "settings_page.py",
        ROOT / "pages" / "expenses_page.py",
        ROOT / "dev_tools" / "ui_color_inspector.py",
    ]
    leftovers = []
    for path in runtime_files:
        matches = legacy.findall(path.read_text(encoding="utf-8"))
        if matches:
            leftovers.append((str(path), matches))
    assert not leftovers, leftovers


# شرح الدالة test_actionable_button_contrast_in_both_themes: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_actionable_button_contrast_in_both_themes():
    pairs = (
        ("primary", "components.buttons.button_text"),
        ("components.buttons.primary_hover", "components.buttons.button_text"),
        ("components.buttons.button_success", "components.buttons.button_success_text"),
        ("components.buttons.button_danger", "components.buttons.button_danger_text"),
        ("components.theme.theme_checked_background", "components.theme.on_theme_checked"),
        ("selection_background", "selection_text"),
    )
    for theme in ("Dark", "Light"):
        for background, foreground in pairs:
            for option in COLORS.OPTIONS:
                ratio = _contrast(
                    THEMES.get_token_palette(theme, background)[option],
                    THEMES.get_token_palette(theme, foreground)[option],
                )
                assert ratio >= 4.5, f"{theme} {option}: {background} / {foreground} = {ratio:.2f}"


# شرح الدالة test_sensitive_component_contrast_in_both_themes: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_sensitive_component_contrast_in_both_themes():
    pairs = (
        ("text_primary", "surface", "groupbox title"),
        ("components.buttons.button_text", "primary", "kpi icon"),
        ("text_primary", "components.status_ui.status_background", "page status"),
        ("components.navigation.sidebar_text_primary", "components.navigation.sidebar", "tooltip"),
        ("components.navigation.sidebar_text_primary", "components.navigation.nav_hover_alt", "theme toggle hover"),
    )
    for theme in ("Dark", "Light"):
        for foreground, background, label in pairs:
            for option in COLORS.OPTIONS:
                ratio = _contrast(
                    THEMES.get_token_palette(theme, foreground)[option],
                    THEMES.get_token_palette(theme, background)[option],
                )
                assert ratio >= 4.5, f"{theme} {option}: {label} = {ratio:.2f}"


# شرح الدالة test_dashboard_has_no_unused_legacy_color_aliases: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_dashboard_has_no_unused_legacy_color_aliases():
    text = (ROOT / "pages" / "dashboard_page.py").read_text(encoding="utf-8")
    legacy = {
        "MINT", "CORAL", "ROSE", "CRIMSON", "APRICOT", "PEACH", "YELLOW",
        "LEMON", "SKY", "AZURE", "STEEL_BLUE", "NAVY_BLUE", "VIOLET",
        "LAVENDER", "PLUM", "PINK", "MAGENTA", "BLUSH", "CYAN", "AQUA",
        "TURQUOISE", "BROWN", "COFFEE", "TAN", "SLATE", "STEEL", "GRAPHITE", "SILVER",
    }
    aliases = set(re.findall(r'^([A-Z][A-Z0-9_]*)\s*=\s*"@', text, re.MULTILINE))
    assert not (aliases & legacy)


# شرح الدالة test_color_inspector_metadata_module_is_available: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_color_inspector_metadata_module_is_available():
    metadata = ROOT / "theme" / "token_metadata.py"
    assert metadata.exists()
    text = metadata.read_text(encoding="utf-8")
    assert "def describe_token" in text



# شرح الدالة test_selector_registry_matches_corrected_qss_ownership: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_selector_registry_matches_corrected_qss_ownership():
    """التحقق من أن سجل ملكية الخصائص يحوي القيم المصححة."""
    path = ROOT / "theme" / "mappings.py"
    spec = importlib.util.spec_from_file_location("theme_mappings_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    mappings = module.SELECTOR_PROPERTY_TOKENS
    assert mappings["QLabel#pageStatus"]["color"] == "text_primary"
    assert mappings["QProgressBar"]["background"] == "background"
    assert mappings["QToolTip"]["color"] == "components.navigation.sidebar_text_primary"
    assert mappings["QLabel"]["color"] == "components.labels.label_text"


# شرح الدالة test_expense_kpi_navy_uses_navigation_navy_token: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_expense_kpi_navy_uses_navigation_navy_token():
    text = (ROOT / "pages" / "expenses_page.py").read_text(encoding="utf-8")
    assert 'accent="navy"' in text
    assert "@components.navigation.navigation_deep@" in text


# شرح الدالة test_navigation_deep_is_blue_in_both_themes: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_navigation_deep_is_blue_in_both_themes():
    for theme in ("Dark", "Light"):
        for option in COLORS.OPTIONS:
            value = THEMES.get_token_palette(theme, "components.navigation.navigation_deep")[option]
            red, green, blue = (int(value[index : index + 2], 16) for index in (1, 3, 5))
            assert blue > red, f"{theme} {option} navigation_deep is not blue: {value}"


# شرح الدالة test_dark_and_light_core_surfaces_are_strictly_separated: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_dark_and_light_core_surfaces_are_strictly_separated():
    for token in ("background", "surface", "surface_alt", "border", "divider", "hover", "pressed", "disabled"):
        for option in COLORS.OPTIONS:
            dark = THEMES.get_token_palette("Dark", token)[option]
            light = THEMES.get_token_palette("Light", token)[option]
            assert dark != light, f"Theme isolation violation: {token}/{option}"


# شرح الدالة test_dark_light_luminance_contract: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_dark_light_luminance_contract():
    for option in COLORS.OPTIONS:
        dark_bg = THEMES.get_token_palette("Dark", "background")[option]
        light_bg = THEMES.get_token_palette("Light", "background")[option]
        assert _luminance(dark_bg) < 0.18
        assert _luminance(light_bg) > 0.55
        assert _contrast(THEMES.get_token_palette("Dark", "text_primary")[option], THEMES.get_token_palette("Dark", "surface")[option]) >= 4.5
        assert _contrast(THEMES.get_token_palette("Light", "text_primary")[option], THEMES.get_token_palette("Light", "surface")[option]) >= 4.5


# شرح الدالة test_unified_page_title_uses_on_colored_surface: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def test_unified_page_title_uses_on_colored_surface():
    """Page titles sit on the colored header and must remain readable in Light mode."""
    root = Path(__file__).resolve().parents[1]
    selectors = (root / "theme" / "selectors.py").read_text(encoding="utf-8")
    mappings = (root / "theme" / "mappings.py").read_text(encoding="utf-8")
    assert "QFrame#pageHeader[unified=\"true\"] QLabel#pageTitle" in selectors
    assert "color: @components.theme.on_colored_surface@;" in selectors
    assert '"QLabel#pageTitle": {"color": "components.theme.on_colored_surface"}' in mappings


def test_surface_specific_foregrounds_cover_mixed_theme_surfaces():
    """Foreground tokens must be validated against the surfaces they actually sit on."""
    pairs = (
        ("components.navigation.sidebar", "components.navigation.sidebar_text_primary"),
        ("components.navigation.sidebar", "components.navigation.sidebar_text_secondary"),
        ("components.navigation.nav_hover_alt", "components.navigation.sidebar_hover_text"),
        ("info", "components.navigation.sidebar_selected_text"),
        ("primary", "components.theme.on_primary"),
        ("accent", "components.theme.on_accent"),
        ("success", "components.theme.on_success"),
        ("warning", "components.theme.on_warning"),
        ("danger", "components.theme.on_danger"),
        ("info", "components.theme.on_info"),
        ("selection_background", "components.theme.on_selection"),
    )
    for theme in ("Dark", "Light"):
        for option in COLORS.OPTIONS:
            for background, foreground in pairs:
                ratio = _contrast(
                    THEMES.get_token_palette(theme, background)[option],
                    THEMES.get_token_palette(theme, foreground)[option],
                )
                assert ratio >= 4.5, f"{theme} {option}: {background} / {foreground} = {ratio:.2f}"

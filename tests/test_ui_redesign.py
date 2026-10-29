# ============================================================
# شرح الملف: tests/test_ui_redesign.py
# اختبارات حماية لإعادة تصميم الواجهة: التباين، الأيقونات، وصيغة الشفافية في الأنماط.
# ============================================================
from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    package = types.ModuleType("ui_redesign_theme")
    package.__path__ = [str(ROOT / "theme")]
    sys.modules[package.__name__] = package
    out = {}
    for name in ("colors", "themes", "metrics", "selectors"):
        spec = importlib.util.spec_from_file_location(f"{package.__name__}.{name}", ROOT / "theme" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        out[name] = module
    return out


MODS = _load()


def _lum(value: str) -> float:
    rgb = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    x, y = _lum(a), _lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def test_header_gradient_end_keeps_white_title_readable():
    for theme in ("Dark", "Light"):
        for option in MODS["colors"].OPTIONS:
            accent = MODS["themes"].get_token_palette(theme, "components.navigation.navigation_accent")[option]
            assert _contrast(accent, "#FFFFFF") >= 4.5, f"{theme}/{option}: {accent}"


def test_primary_hover_keeps_button_text_readable():
    for theme in ("Dark", "Light"):
        for option in MODS["colors"].OPTIONS:
            hover = MODS["themes"].get_token_palette(theme, "components.buttons.primary_hover")[option]
            text = MODS["themes"].get_token_palette(theme, "components.buttons.button_text")[option]
            assert _contrast(hover, text) >= 4.5


def test_every_qss_token_resolves_in_all_palettes():
    qss = MODS["selectors"].APPLICATION_SELECTORS
    tokens = {m.group(1) for m in re.finditer(r"@([A-Za-z0-9_.-]+)(?:\|\d{1,3})?@", qss)}
    for theme in ("Dark", "Light"):
        for token in tokens:
            palette = MODS["themes"].get_token_palette(theme, token)
            assert set(palette) == set(MODS["colors"].OPTIONS)


def test_icon_assets_exist_for_qss_rules():
    for name in ("check.png", "radio-dot.png", "chevron-down.png", "chevron-up.png"):
        assert (ROOT / "resources" / "ui" / name).is_file(), name


def test_qss_has_balanced_braces_and_no_unresolved_markers():
    qss = MODS["selectors"].APPLICATION_SELECTORS
    assert qss.count("{") == qss.count("}")
    assert not re.findall(r"__[A-Z_]+__", qss)

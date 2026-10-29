# ============================================================
# File description: dev_tools/diagnostics_suite.py
# This file is part of the development, diagnostics, and performance monitoring tools.
# The comments here are for clarification and maintenance only, and do not change the program's behavior.
# Object names, call interfaces, and database logic have been preserved as is.
# ============================================================
"""Developer diagnostics for localization, theme contrast, database health, and snapshots."""
from __future__ import annotations

import ast
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, ClassVar


# TranslationAudit Class description: Gathers data and functions related to this component.
class TranslationAudit:
    """Perform a conservative static audit of translation catalogs and UI strings."""

    UI_CONSTRUCTORS: ClassVar[set[str]] = {
        "QLabel", "QPushButton", "QToolButton", "QCheckBox", "QRadioButton",
        "QGroupBox", "QAction", "QMessageBox", "QInputDialog", "QDialog",
        "QTabWidget", "QLineEdit", "QComboBox", "QProgressBar",
    }
    UI_METHODS: ClassVar[set[str]] = {
        "setText", "setWindowTitle", "setPlaceholderText", "setToolTip",
        "setTitle", "setStatusTip", "setWhatsThis", "setAccessibleName",
        "setAccessibleDescription", "addItem", "addTab", "setTabText",
        "setFormat", "setSpecialValueText", "setPrefix", "setSuffix",
    }
    NON_UI_LITERALS: ClassVar[set[str]] = {
        "", "OK", "Cancel", "Yes", "No", "Save", "Close", "Apply", "Reset",
    }
    DYNAMIC_VALUE_NAMES: ClassVar[set[str]] = {
        "name", "description", "title", "text", "value", "label", "project_name",
        "full_name", "phone", "address", "notes", "reference", "category",
    }

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

# _load_catalog Function description: Executes a logical step related to this file's functionality.
    @staticmethod
    def _load_catalog(path: Path) -> dict[str, str]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}

# run Function description: Executes a logical step related to this file's functionality.
    def run(self) -> dict[str, Any]:
        catalogs = {
            language: self._load_catalog(self.root / "translations" / f"{language}.json")
            for language in ("en", "ar")
        }
        en_keys = set(catalogs["en"])
        ar_keys = set(catalogs["ar"])
        source_refs = self._source_references()
        hardcoded = self._hardcoded_ui_strings(en_keys)
        untranslated = [item for item in hardcoded if item["text"] not in en_keys]
        unused = sorted(key for key in en_keys | ar_keys if key not in source_refs)
        empty_ar = sorted(key for key in en_keys if not str(catalogs["ar"].get(key, "")).strip())
        same_value = sorted(
            key for key in en_keys & ar_keys
            if catalogs["en"].get(key, "") == catalogs["ar"].get(key, "")
            and len(str(key).strip()) > 2
        )
        return {
            "en_keys": len(en_keys),
            "ar_keys": len(ar_keys),
            "missing_ar": sorted(en_keys - ar_keys),
            "missing_en": sorted(ar_keys - en_keys),
            "empty_ar": empty_ar,
            "same_value": same_value,
            "unused": unused,
            "hardcoded": hardcoded,
            "untranslated_literals": untranslated,
            "source_references": len(source_refs),
        }

# _python_files Function description: Executes a logical step related to this file's functionality.
    def _python_files(self) -> list[Path]:
        return sorted(
            p for p in self.root.rglob("*.py")
            if ".venv" not in p.parts and "__pycache__" not in p.parts
        )

# _source_references Function description: Executes a logical step related to this file's functionality.
    def _source_references(self) -> set[str]:
        refs: set[str] = set()
        for path in self._python_files():
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
                if name not in {"translate_text", "tr", "translate"} or not node.args:
                    continue
                value = self._literal_text(node.args[0])
                if value and "{…}" not in value:
                    refs.add(value)
        return refs

# _literal_text Function description: Executes a logical step related to this file's functionality.
    @staticmethod
    def _literal_text(node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value.strip()
        if isinstance(node, ast.JoinedStr):
            parts: list[str] = []
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    parts.append(part.value)
                else:
                    parts.append("{…}")
            return "".join(parts).strip()
        return None

# _looks_like_data_expression Function description: Executes a logical step related to this file's functionality.
    @staticmethod
    def _looks_like_data_expression(node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id.lower() in TranslationAudit.DYNAMIC_VALUE_NAMES
        if isinstance(node, ast.Attribute):
            return node.attr.lower() in TranslationAudit.DYNAMIC_VALUE_NAMES
        return False

# _hardcoded_ui_strings Function description: Executes a logical step related to this file's functionality.
    def _hardcoded_ui_strings(self, catalog_keys: set[str]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for path in self._python_files():
            if path.parent.name != "pages":
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
            except (OSError, SyntaxError):
                continue
            relative = str(path.relative_to(self.root)).replace("\\", "/")
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue

                candidate: ast.AST | None = None
                kind = ""
                if isinstance(node.func, ast.Name) and node.func.id in self.UI_CONSTRUCTORS and node.args:
                    candidate, kind = node.args[0], f"constructor:{node.func.id}"
                elif isinstance(node.func, ast.Attribute) and node.func.attr in self.UI_METHODS and node.args:
                    candidate, kind = node.args[0], f"method:{node.func.attr}"

                if candidate is None or self._looks_like_data_expression(candidate):
                    continue
                value = self._literal_text(candidate)
                if not value or value in self.NON_UI_LITERALS:
                    continue
                if value in catalog_keys:
                    continue
                if value.startswith(("%", "{")):
                    continue
                if not any(ch.isalpha() for ch in value):
                    continue
                results.append({
                    "file": relative,
                    "line": node.lineno,
                    "kind": kind,
                    "text": value,
                    "severity": "review",
                })
        return results


# ThemeAudit Class description: Gathers data and functions related to this component.
class ThemeAudit:
    """Analyze real foreground/background token usage instead of all color pairs."""

    TOKEN_RE = re.compile(r"@([A-Za-z0-9_.-]+)@")
    PROPERTY_RE = re.compile(r"(?P<property>[A-Za-z-]+)\s*:\s*(?P<value>[^;{}]+)")
    BLOCK_RE = re.compile(r"(?P<selector>[^{}]+)\{(?P<body>[^{}]*)\}", re.MULTILINE)

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

# _rgb Function description: Executes a logical step related to this file's functionality.
    @staticmethod
    def _rgb(color: str) -> tuple[int, int, int] | None:
        value = str(color).strip().lstrip("#")
        if len(value) != 6 or not re.fullmatch(r"[0-9A-Fa-f]{6}", value):
            return None
        try:
            return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
        except ValueError:
            return None

# _luminance Function description: Executes a logical step related to this file's functionality.
    @classmethod
    def _luminance(cls, color: str) -> float:
        rgb = cls._rgb(color)
        if rgb is None:
            return 0.0
        values = []
        for channel in rgb:
            value = channel / 255.0
            values.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
        return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]

# contrast Function description: Executes a logical step related to this file's functionality.
    @classmethod
    def contrast(cls, foreground: str, background: str) -> float:
        fg, bg = cls._rgb(foreground), cls._rgb(background)
        if fg is None or bg is None:
            return 0.0
        light = max(cls._luminance(foreground), cls._luminance(background))
        dark = min(cls._luminance(foreground), cls._luminance(background))
        return (light + 0.05) / (dark + 0.05)

# _load_palette_file Function description: Executes a logical step related to this file's functionality.
    @staticmethod
    def _load_palette_file(path: Path) -> dict[str, Any]:
        """Read palette dictionaries without importing the Qt-dependent theme package."""
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, SyntaxError):
            return {}
        constants = {"OPTION_1": "option_1", "OPTION_2": "option_2", "OPTION_3": "option_3", "OPTION_4": "option_4"}
        result: dict[str, Any] = {}
# _Names Class description: Gathers data and functions related to this component.
        class _Names(ast.NodeTransformer):
# visit_Name Function description: Executes a logical step related to this file's functionality.
            def visit_Name(self, current):
                if current.id in constants:
                    return ast.copy_location(ast.Constant(constants[current.id]), current)
                return current
        for node in tree.body:
            if not isinstance(node, (ast.AnnAssign, ast.Assign)):
                continue
            targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets
            value_node = node.value
            if value_node is None or not any(isinstance(target, ast.Name) for target in targets):
                continue
            target_names = {target.id for target in targets if isinstance(target, ast.Name)}
            if not any(name.endswith(("_DARK", "_LIGHT")) or name in {"DARK", "LIGHT"} for name in target_names):
                continue
            converted = _Names().visit(value_node)
            ast.fix_missing_locations(converted)
            try:
                raw = ast.literal_eval(converted)
            except (ValueError, TypeError):
                continue
            if isinstance(raw, dict):
                result[next(name for name in target_names if name.endswith(("_DARK", "_LIGHT")) or name in {"DARK", "LIGHT"})] = raw
        return result

# _token_map Function description: Executes a logical step related to this file's functionality.
    @classmethod
    def _token_map(cls, palettes: dict[str, Any], theme_name: str) -> dict[str, dict[str, str]]:
        suffix = theme_name.upper()
        mapping: dict[str, dict[str, str]] = {}
        direct_groups = {
            "DARK": "", "LIGHT": "", "BRAND": "", "STATUS": "",
            "KPI": "kpi.", "CHARTS": "charts.", "TABLES": "tables.",
        }
        for variable, prefix in direct_groups.items():
            key = f"{variable}_{suffix}" if variable not in {"DARK", "LIGHT"} else suffix
            data = palettes.get(key, {})
            if isinstance(data, dict):
                for token, options in data.items():
                    if isinstance(options, dict):
                        mapping[f"{prefix}{token}"] = {str(k): str(v) for k, v in options.items()}
        for variable in (f"UI_COMPONENT_{suffix}", f"UI_COMPONENT_EXTRA_{suffix}"):
            data = palettes.get(variable, {})
            if not isinstance(data, dict):
                continue
            for token, options in data.items():
                if isinstance(options, dict):
                    group = cls._component_group(str(token))
                    mapping[f"components.{group}.{token}"] = {str(k): str(v) for k, v in options.items()}
        return mapping

# _literal_text Function description: Executes a logical step related to this file's functionality.
    @staticmethod
    def _literal_text(node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            parts: list[str] = []
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    parts.append(part.value)
                else:
                    parts.append("{…}")
            return "".join(parts)
        return None

# _component_group Function description: Executes a logical step related to this file's functionality.
    @staticmethod
    def _component_group(key: str) -> str:
        if key.startswith("brand_"): return "branding"
        if key.startswith("button") or key in {"primary_border", "primary_hover"}: return "buttons"
        if key.startswith(("input_", "search", "combo_popup")): return "forms"
        if key.startswith("kpi_"): return "kpi_detail"
        if key.startswith("inspector_"): return "inspector"
        if key.startswith(("nav_", "navigation", "sidebar", "scrollbar", "topbar_border")): return "navigation"
        if key.startswith("progress"): return "progress"
        if key.startswith("status_"): return "status_ui"
        if key.startswith("tab"): return "tabs"
        if key.startswith("theme_") or key in {"on_colored_surface", "on_colored_surface_muted", "on_colored_surface_border"}: return "theme"
        if key == "tooltip": return "tooltip"
        if key.startswith("danger_"): return "states"
        if key == "label_text": return "labels"
        if key == "dialog": return "dialogs"
        return "components"

# _styles Function description: Executes a logical step related to this file's functionality.
    def _styles(self) -> list[tuple[Path, str, str, str]]:
        styles: list[tuple[Path, str, str, str]] = []
        for path in sorted((self.root / "pages").glob("*.py")):
            try:
                source = path.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source)
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                    continue
                if node.func.id != "set_theme_style" or len(node.args) < 2:
                    continue
                style = self._literal_text(node.args[1])
                if not style:
                    continue
                for match in self.BLOCK_RE.finditer(style):
                    body = match.group("body")
                    if "@" in body and re.search(r"(?:color|background(?:-color)?|border(?:-[a-z-]+)?):", body):
                        styles.append((path, match.group("selector").strip(), body, "pages"))
        selector_file = self.root / "theme" / "selectors.py"
        if selector_file.exists():
            try:
                source = selector_file.read_text(encoding="utf-8", errors="ignore")
                for match in self.BLOCK_RE.finditer(source):
                    body = match.group("body")
                    if "@" in body and re.search(r"(?:color|background(?:-color)?|border(?:-[a-z-]+)?):", body):
                        styles.append((selector_file, match.group("selector").strip(), body, "theme"))
            except OSError:
                pass
        return styles

# run Function description: Executes a logical step related to this file's functionality.
    def run(self) -> dict[str, Any]:
        palettes = self._load_palette_file(self.root / "theme" / "themes.py")
        if not palettes:
            return {"status": "ERROR", "error": "Theme palette catalog could not be parsed"}
        options = ("option_1", "option_2", "option_3", "option_4")
        token_maps = {theme_name: self._token_map(palettes, theme_name) for theme_name in ("Dark", "Light")}
        all_tokens = set(token_maps["Dark"]) | set(token_maps["Light"])
        # Include catalog tokens that may not appear in a stylesheet yet.
        try:
            colors_source = (self.root / "theme" / "colors.py").read_text(encoding="utf-8", errors="ignore")
            for prefix, keys in re.findall(r'"(kpi|charts|tables)":\s*\((.*?)\)', colors_source, re.DOTALL):
                all_tokens.update(f"{prefix}.{name}" for name in re.findall(r'"([A-Za-z0-9_.-]+)"', keys))
        except OSError:
            pass
        usages: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        token_usage: set[str] = set()
        for path, selector, body, source_kind in self._styles():
            properties = {
                m.group("property").strip().lower(): m.group("value").strip()
                for m in self.PROPERTY_RE.finditer(body)
            }
            foreground_tokens = self.TOKEN_RE.findall(properties.get("color", ""))
            background_tokens = self.TOKEN_RE.findall(
                properties.get("background", "") or properties.get("background-color", "")
            )
            for token in foreground_tokens + background_tokens:
                token_usage.add(token)
            if not foreground_tokens or not background_tokens:
                continue
            for fg_token in foreground_tokens:
                for bg_token in background_tokens:
                    if fg_token == bg_token or fg_token not in all_tokens or bg_token not in all_tokens:
                        continue
                    for theme_name in ("Dark", "Light"):
                        for option in options:
                            palette = token_maps[theme_name]
                            fg = palette.get(fg_token, {}).get(option)
                            bg = palette.get(bg_token, {}).get(option)
                            if not fg or not bg:
                                continue
                            ratio = self.contrast(fg, bg)
                            record = {
                                "file": str(path.relative_to(self.root)).replace("\\", "/"),
                                "selector": selector[:160],
                                "foreground": fg_token,
                                "background": bg_token,
                                "theme": theme_name,
                                "option": option,
                                "ratio": round(ratio, 2),
                            }
                            usages.append(record)
                            if ratio < 4.5:
                                severity = "critical" if ratio < 3.0 else "warning"
                                warnings.append({**record, "severity": severity})
        return {
            "status": "WARN" if warnings else "PASS",
            "token_count": len(all_tokens),
            "tokens_used_in_styles": len(token_usage),
            "unused_theme_tokens": sorted(all_tokens - token_usage),
            "checked_pairs": len(usages),
            "warning_count": len(warnings),
            "warnings": warnings[:200],
        }


# DatabaseAudit Class description: Gathers data and functions related to this component.
class DatabaseAudit:
    """Run read-only SQLite health checks against the application's database."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

# _find_database Function description: Executes a logical step related to this file's functionality.
    def _find_database(self) -> Path | None:
        candidates = [p for p in self.root.rglob("*.db") if "__pycache__" not in p.parts]
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_mtime)

# run Function description: Executes a logical step related to this file's functionality.
    def run(self) -> dict[str, Any]:
        path = self._find_database()
        if path is None:
            return {"status": "NOT FOUND"}
        try:
            connection = sqlite3.connect(path, timeout=1.5)
        except sqlite3.Error as exc:
            return {"status": "ERROR", "error": str(exc), "path": str(path)}
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            return {
                "status": "PASS" if integrity and integrity[0] == "ok" and not foreign_keys else "WARN",
                "path": str(path.relative_to(self.root)),
                "size_mb": round(path.stat().st_size / 1048576.0, 2),
                "integrity": integrity[0] if integrity else "unknown",
                "foreign_key_errors": len(foreign_keys),
                "tables": len(tables),
            }
        except sqlite3.Error as exc:
            return {"status": "ERROR", "error": str(exc), "path": str(path)}
        finally:
            connection.close()


# DiagnosticSnapshot Class description: Gathers data and functions related to this component.
class DiagnosticSnapshot:
    """Build a compact JSON-ready health snapshot from the diagnostic suite."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

# build Function description: Executes a logical step related to this file's functionality.
    def build(self, runtime: dict[str, Any]) -> dict[str, Any]:
        return {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "application": "BuildOffice Pro",
            "runtime": runtime,
            "translation": TranslationAudit(self.root).run(),
            "theme": ThemeAudit(self.root).run(),
            "database": DatabaseAudit(self.root).run(),
        }

# save Function description: Executes a logical step related to this file's functionality.
    def save(self, data: dict[str, Any], destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return destination
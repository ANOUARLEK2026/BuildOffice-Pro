
"""Static localization audit for BuildOffice Pro.

Scans production Python code for common Qt UI literals and translate_text(...)
calls, then verifies that every literal source exists in both catalogs.

This tool is intended for development/CI only and is not imported by the app.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = ROOT / "translations"

EXCLUDED_PARTS = {
    "__pycache__",
    ".venv",
    ".git",
    "tests",
}

UI_CONSTRUCTORS = {
    "QLabel",
    "QPushButton",
    "QToolButton",
    "QCheckBox",
    "QRadioButton",
    "QGroupBox",
    "QLineEdit",
    "QComboBox",
    "QDialog",
}

UI_METHODS = {
    "setText",
    "setPlaceholderText",
    "setWindowTitle",
    "setToolTip",
    "setStatusTip",
    "setWhatsThis",
    "addTab",
    "setTitle",
    "addItem",
}

UI_COLLECTION_NAMES = {
    "cards",
    "items",
    "choices",
    "options",
    "modules",
    "status_rows",
    "menu_items",
    "tabs",
    "actions",
    "deadlines",
    "columns",
    "headers",
    "filters",
    "palette_options",
}


def is_user_facing_literal(value: str) -> bool:
    """Return True when a string looks like user-facing English UI text."""
    stripped = value.strip()

    return bool(
        stripped
        and len(stripped) > 1
        and any(ch.isalpha() for ch in stripped)
        and not any("\u0600" <= ch <= "\u06ff" for ch in stripped)
    )


def load_catalog(name: str) -> dict[str, str]:
    """Load a translation catalog from the translations directory."""
    catalog_path = TRANSLATIONS / f"{name}.json"

    return json.loads(
        catalog_path.read_text(encoding="utf-8")
    )


def get_call_name(node: ast.Call) -> str:
    """Return the callable name for an AST Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        return node.func.attr

    return ""


def scan_ui_collections(
    tree: ast.AST,
    rel_path: str,
) -> list[tuple[str, int, str, str]]:
    """Find English-looking literals stored in common UI collections."""
    candidates: list[tuple[str, int, str, str]] = []

    for owner in ast.walk(tree):
        if not isinstance(owner, (ast.Assign, ast.AnnAssign)):
            continue

        targets: list[ast.Name] = []

        if isinstance(owner, ast.Assign):
            targets = [
                target
                for target in owner.targets
                if isinstance(target, ast.Name)
            ]
            assigned_value = owner.value

        else:
            if isinstance(owner.target, ast.Name):
                targets = [owner.target]

            assigned_value = owner.value

        # AnnAssign.value may be None.
        if assigned_value is None:
            continue

        for target in targets:
            if target.id not in UI_COLLECTION_NAMES:
                continue

            for node in ast.walk(assigned_value):
                if not isinstance(node, ast.Constant):
                    continue

                if not isinstance(node.value, str):
                    continue

                value = node.value
                stripped = value.strip()

                if (
                    is_user_facing_literal(value)
                    and value == stripped
                    and any(ch.isspace() for ch in stripped)
                    and "\n" not in stripped
                    and not stripped.upper().startswith(
                        ("SELECT ", "PRAGMA ")
                    )
                    and not stripped.startswith(("Q", "%", "."))
                    and target.id not in {"headers"}
                ):
                    candidates.append(
                        (
                            str(rel_path),
                            node.lineno,
                            target.id,
                            stripped,
                        )
                    )

    return candidates


def scan_ui_calls(
    tree: ast.AST,
    rel_path: str,
    english_catalog: dict[str, str],
) -> tuple[
    list[tuple[str, int, str, str]],
    list[tuple[str, int, str]],
    list[tuple[str, int, str]],
]:
    """Scan Qt UI calls and translate_text() calls."""
    missing: list[tuple[str, int, str, str]] = []
    translate_missing: list[tuple[str, int, str]] = []
    dynamic_calls: list[tuple[str, int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = get_call_name(node)

        # Qt constructors and UI methods.
        if name in UI_CONSTRUCTORS or name in UI_METHODS:
            if (
                node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                value = node.args[0].value

                # Developer-console examples are not UI copy.
                if (
                    name == "setPlaceholderText"
                    and value.lstrip().startswith("Examples:")
                ):
                    continue

                if (
                    is_user_facing_literal(value)
                    and value not in english_catalog
                ):
                    missing.append(
                        (
                            str(rel_path),
                            node.lineno,
                            name,
                            value,
                        )
                    )

            elif (
                name in UI_METHODS
                and node.args
                and isinstance(node.args[0], ast.JoinedStr)
            ):
                dynamic_calls.append(
                    (
                        str(rel_path),
                        node.lineno,
                        name,
                    )
                )

        # translate_text(...) calls.
        if name == "translate_text" and node.args:
            argument = node.args[0]

            if (
                isinstance(argument, ast.Constant)
                and isinstance(argument.value, str)
            ):
                value = argument.value

                if (
                    is_user_facing_literal(value)
                    and value not in english_catalog
                ):
                    translate_missing.append(
                        (
                            str(rel_path),
                            node.lineno,
                            value,
                        )
                    )

            elif isinstance(argument, ast.JoinedStr):
                dynamic_calls.append(
                    (
                        str(rel_path),
                        node.lineno,
                        "translate_text(f-string)",
                    )
                )

    return missing, translate_missing, dynamic_calls


def audit_file(
    path: Path,
    english_catalog: dict[str, str],
) -> tuple[
    list[tuple[str, int, str, str]],
    list[tuple[str, int, str]],
    list[tuple[str, int, str]],
    list[tuple[str, int, str, str]],
]:
    """Parse and audit one Python source file."""
    source = path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(
            source,
            filename=str(path),
        )
    except SyntaxError as exc:
        print(f"SYNTAX ERROR: {path}: {exc}")
        raise

    rel_path = str(path.relative_to(ROOT))

    missing, translate_missing, dynamic_calls = scan_ui_calls(
        tree,
        rel_path,
        english_catalog,
    )

    collection_candidates = scan_ui_collections(
        tree,
        rel_path,
    )

    return (
        missing,
        translate_missing,
        dynamic_calls,
        collection_candidates,
    )


def print_section(
    title: str,
    entries: list[tuple],
) -> None:
    """Print a formatted audit section."""
    if not entries:
        return

    print(f"\n{title}:")

    for item in entries:
        print(" | ".join(map(str, item)))


def main() -> int:
    """Run the complete localization audit."""
    try:
        english_catalog = load_catalog("en")
        arabic_catalog = load_catalog("ar")
    except (OSError, json.JSONDecodeError) as exc:
        print(f"CATALOG ERROR: {exc}")
        return 2

    missing: list[tuple[str, int, str, str]] = []
    translate_missing: list[tuple[str, int, str]] = []
    dynamic_calls: list[tuple[str, int, str]] = []
    collection_candidates: list[tuple[str, int, str, str]] = []

    # Verify Arabic catalog coverage.
    missing_arabic = sorted(
        key
        for key in english_catalog
        if key not in arabic_catalog
        or not str(arabic_catalog[key]).strip()
    )

    # Scan every production Python file.
    for path in ROOT.rglob("*.py"):
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue

        try:
            (
                file_missing,
                file_translate_missing,
                file_dynamic_calls,
                file_collection_candidates,
            ) = audit_file(
                path,
                english_catalog,
            )
        except SyntaxError:
            return 2

        missing.extend(file_missing)
        translate_missing.extend(file_translate_missing)
        dynamic_calls.extend(file_dynamic_calls)
        collection_candidates.extend(file_collection_candidates)

    # Check collection literals against the English catalog.
    collection_missing = sorted(
        {
            item
            for item in collection_candidates
            if item[3] not in english_catalog
        }
    )

    # Summary.
    print(f"English catalog keys: {len(english_catalog)}")
    print(f"Arabic catalog keys:  {len(arabic_catalog)}")
    print(f"Missing/blank Arabic keys: {len(missing_arabic)}")
    print(f"Uncatalogued static UI literals: {len(missing)}")
    print(
        "Uncatalogued literal translate_text calls: "
        f"{len(translate_missing)}"
    )
    print(
        "Dynamic UI/translation calls reviewed by "
        f"source/pattern logic: {len(dynamic_calls)}"
    )
    print(
        f"UI collection literals reviewed: "
        f"{len(collection_candidates)}"
    )
    print(
        f"Uncatalogued UI collection literals: "
        f"{len(collection_missing)}"
    )

    # Detailed results.
    print_section(
        "MISSING/BLANK ARABIC KEYS",
        [(item,) for item in missing_arabic],
    )

    print_section(
        "STATIC UI LITERALS",
        missing,
    )

    print_section(
        "TRANSLATE_TEXT LITERALS",
        translate_missing,
    )

    print_section(
        "UI COLLECTION LITERALS",
        collection_missing,
    )

    print_section(
        "DYNAMIC CALLS",
        dynamic_calls,
    )

    # CI exit status.
    has_errors = bool(
        missing
        or translate_missing
        or missing_arabic
        or collection_missing
    )

    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

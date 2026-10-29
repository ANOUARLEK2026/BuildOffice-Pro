from __future__ import annotations

import ast
import importlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")
TOK = re.compile(r"@([A-Za-z0-9_.-]+)@")


def collect_python_files() -> list[Path]:
    """Return all Python source files belonging to the project."""
    excluded_parts = {
        "__pycache__",
        ".venv",
        ".git",
        "tests",
    }

    return [
        path
        for path in ROOT.rglob("*.py")
        if not any(part in excluded_parts for part in path.parts)
    ]


def check_python_syntax(
    py_files: list[Path],
) -> list[str]:
    """Check every Python source file for syntax errors."""
    errors: list[str] = []

    for path in py_files:
        try:
            source = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
            ast.parse(
                source,
                filename=str(path),
            )
        except SyntaxError as exc:
            relative = path.relative_to(ROOT)

            errors.append(
                f"Syntax: {relative}:{exc.lineno}: {exc.msg}"
            )
        except OSError as exc:
            relative = path.relative_to(ROOT)

            errors.append(
                f"Read error: {relative}: {exc}"
            )

    return errors


def find_literal_hex_outside_theme(
    py_files: list[Path],
) -> list[str]:
    """Find hard-coded six-digit color values outside the theme package."""
    outside: list[str] = []

    for path in py_files:
        if "theme" in path.parts:
            continue

        try:
            source = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except OSError:
            continue

        if HEX.search(source):
            outside.append(
                str(path.relative_to(ROOT))
            )

    return sorted(outside)


def load_theme_color_tokens() -> set[str]:
    """Load token names declared by theme/colors.py."""
    colors_path = ROOT / "theme" / "colors.py"

    if not colors_path.exists():
        return set()

    try:
        source = colors_path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return set()

    try:
        tree = ast.parse(
            source,
            filename=str(colors_path),
        )
    except SyntaxError:
        return set()

    tokens: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue

        if not isinstance(node.value, str):
            continue

        value = node.value.strip()

        if value and re.fullmatch(
            r"[A-Za-z0-9_.-]+",
            value,
        ):
            tokens.add(value)

    return tokens


def collect_theme_token_references(
    py_files: list[Path],
) -> set[str]:
    """Collect @token@ references used throughout Python source."""
    token_refs: set[str] = set()

    for path in py_files:
        try:
            source = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except OSError:
            continue

        token_refs.update(
            TOK.findall(source)
        )

    return token_refs


def check_theme_token_references(
    py_files: list[Path],
) -> list[str]:
    """Check that referenced theme tokens exist in the color registry."""
    errors: list[str] = []

    declared_tokens = load_theme_color_tokens()
    token_refs = collect_theme_token_references(py_files)

    if not declared_tokens:
        colors_path = ROOT / "theme" / "colors.py"

        if not colors_path.exists():
            errors.append(
                "Theme token validation: "
                f"missing {colors_path.relative_to(ROOT)}"
            )

        return errors

    # These families may be generated dynamically by the theme system.
    dynamic_families = {
        "primary",
        "secondary",
        "accent",
        "surface",
        "background",
        "text",
        "border",
        "danger",
        "success",
        "warning",
    }

    missing_tokens = sorted(
        token
        for token in token_refs
        if token not in declared_tokens
        and token.split(".", 1)[0] not in dynamic_families
    )

    for token in missing_tokens:
        errors.append(
            f"Unknown theme token: @{token}@"
        )

    return errors


def validate_themes() -> list[str]:
    """Run the project's runtime theme validation."""
    theme_module_path = ROOT / "theme" / "themes.py"

    if not theme_module_path.exists():
        return [
            (
                "Theme validation: missing "
                f"{theme_module_path.relative_to(ROOT)}"
            )
        ]

    root_string = str(ROOT)

    if root_string not in sys.path:
        sys.path.insert(0, root_string)

    try:
        theme_module = importlib.import_module(
            "theme.themes"
        )

    except ModuleNotFoundError as exc:
        # PySide6 may not be installed in the development environment.
        if exc.name == "PySide6":
            return validate_themes_static(
                theme_module_path
            )

        return [
            f"Theme validation import error: {exc}"
        ]

    except (
        ImportError,
        OSError,
        ValueError,
        AttributeError,
        SyntaxError,
    ) as exc:
        return [
            f"Theme validation import error: {exc}"
        ]

    validator = getattr(
        theme_module,
        "validate_themes",
        None,
    )

    if not callable(validator):
        return [
            (
                "Theme validation: "
                "theme.themes.validate_themes() is missing"
            )
        ]

    try:
        result = validator()

    except (
        ImportError,
        OSError,
        ValueError,
        AttributeError,
        TypeError,
    ) as exc:
        return [
            f"Theme validation runtime error: {exc}"
        ]

    if result is None:
        return []

    if isinstance(result, (list, tuple, set)):
        return [
            str(error)
            for error in result
        ]

    return [str(result)]


def validate_themes_static(
    theme_path: Path,
) -> list[str]:
    """Perform basic theme validation when Qt is unavailable."""
    errors: list[str] = []

    try:
        source = theme_path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError as exc:
        return [
            f"Theme validation read error: {exc}"
        ]

    try:
        ast.parse(
            source,
            filename=str(theme_path),
        )
    except SyntaxError as exc:
        errors.append(
                "themes.py syntax error: "
                f"{exc.lineno}: {exc.msg}"
        )
        return errors

    if source.count("{") != source.count("}"):
        errors.append(
            "themes.py brace mismatch"
        )

    if source.count("[") != source.count("]"):
        errors.append(
            "themes.py bracket mismatch"
        )

    if source.count("(") != source.count(")"):
        errors.append(
            "themes.py parenthesis mismatch"
        )

    return errors


def main() -> int:
    """Run the complete theme/static UI audit."""
    errors: list[str] = []

    py_files = collect_python_files()

    # Python syntax validation.
    errors.extend(
        check_python_syntax(py_files)
    )

    # Hard-coded colors outside the theme package.
    outside = find_literal_hex_outside_theme(
        py_files
    )

    if outside:
        errors.append(         
                "Literal UI hex outside theme/: "
                + ", ".join(outside)
        )

    # Theme token validation.
    errors.extend(
        check_theme_token_references(py_files)
    )

    # Runtime/static theme validation.
    errors.extend(
        validate_themes()
    )

    # Remove duplicate messages while preserving order.
    errors = list(
        dict.fromkeys(errors)
    )

    print(
        f"Python files: {len(py_files)}"
    )

    print(
        f"Literal hex outside theme/: "
        f"{len(outside)}"
    )

    print(
        f"Errors: {len(errors)}"
    )

    for error in errors:
        print(error)

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
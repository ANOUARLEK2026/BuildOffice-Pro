# ============================================================
# شرح الملف: theme/store.py
# هذا الملف جزء من نظام الألوان والثيمات وأنماط الواجهة.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Persistent, independent theme selections for BuildOffice Pro.

This module is deliberately independent from Qt and from the database.
The application can later plug it into its SQLite settings table without
changing the public API used by the UI and Color Inspector.
"""
from __future__ import annotations

import json
import os
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Final

from .colors import ALL_TOKENS, OPTION_1, OPTIONS
from .themes import DEFAULT_SELECTION, get_token_palette

SCHEMA_VERSION: Final[int] = 1
THEMES: Final[tuple[str, str]] = ("Dark", "Light")


# شرح الصنف ThemeStore: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class ThemeStore:
    """Hold and optionally persist independent token selections.

    A selection is stored as ``{"background": "option_2", ...}`` for each
    theme. No color value is stored here, only the selected option identifier.
    This is intentional: changing the catalog never requires migrating raw
    hexadecimal values stored in the user's settings.
    """

    def __init__(
        self,
        path: str | os.PathLike[str] | None = None,
        *,
        auto_load: bool = True,
    ) -> None:
        self.path = Path(path) if path else None
        self._selection: dict[str, dict[str, str]] = deepcopy(DEFAULT_SELECTION)
        self._listeners: list[Callable[[str, str, str], None]] = []
        if auto_load and self.path:
            self.load()

    # ------------------------------------------------------------------
    # Normalization / validation
    # ------------------------------------------------------------------
# شرح الدالة normalize_theme: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def normalize_theme(theme: str) -> str:
        return "Light" if str(theme).strip().lower() == "light" else "Dark"

# شرح الدالة validate_token: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def validate_token(token: str) -> None:
        if token not in ALL_TOKENS:
            raise KeyError(f"Unknown theme token: {token}")

# شرح الدالة validate_option: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def validate_option(option: str) -> None:
        if option not in OPTIONS:
            raise ValueError(f"Invalid option: {option!r}")

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------
# شرح الدالة get_option: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def get_option(self, theme: str, token: str) -> str:
        theme = self.normalize_theme(theme)
        self.validate_token(token)
        return self._selection[theme].get(token, OPTION_1)

# شرح الدالة get_color: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def get_color(self, theme: str, token: str) -> str:
        theme = self.normalize_theme(theme)
        option = self.get_option(theme, token)
        return get_token_palette(theme, token)[option]

# شرح الدالة resolve: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def resolve(self, theme: str, token: str) -> str:
        """Alias that keeps UI code expressive."""
        return self.get_color(theme, token)

# شرح الدالة all_options: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def all_options(self, theme: str, token: str) -> dict[str, str]:
        theme = self.normalize_theme(theme)
        self.validate_token(token)
        return get_token_palette(theme, token)

# شرح الدالة snapshot: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def snapshot(self) -> dict[str, dict[str, str]]:
        return deepcopy(self._selection)

    # ------------------------------------------------------------------
    # Write API
    # ------------------------------------------------------------------
# شرح الدالة set_option: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def set_option(self, theme: str, token: str, option: str, *, persist: bool = True) -> str:
        theme = self.normalize_theme(theme)
        self.validate_token(token)
        self.validate_option(option)

        old_option = self._selection[theme].get(token, OPTION_1)
        if old_option == option:
            return self.get_color(theme, token)

        self._selection[theme][token] = option
        if persist:
            self.save()
        self._emit(theme, token, option)
        return self.get_color(theme, token)

# شرح الدالة reset_token: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def reset_token(self, theme: str, token: str, *, persist: bool = True) -> str:
        return self.set_option(theme, token, OPTION_1, persist=persist)

# شرح الدالة set_palette: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def set_palette(self, theme: str, option: str, *, persist: bool = True) -> None:
        """Apply one coherent palette option to every token of a theme.

        The catalog provides four coordinated variants for every
        semantic/component token. This method turns that catalog into a
        user-facing palette selector without duplicating color definitions.
        """
        theme = self.normalize_theme(theme)
        self.validate_option(option)
        changed = []
        for token in ALL_TOKENS:
            if self._selection[theme].get(token, OPTION_1) != option:
                self._selection[theme][token] = option
                changed.append(token)
        if persist:
            self.save()
        for token in changed:
            self._emit(theme, token, option)

# شرح الدالة get_palette: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def get_palette(self, theme: str) -> str:
        """Return the dominant palette option used by the theme.

        If individual token selections differ, option 1 is returned because
        the theme is no longer represented by one coherent palette.
        """
        theme = self.normalize_theme(theme)
        values = {self._selection[theme].get(token, OPTION_1) for token in ALL_TOKENS}
        return next(iter(values)) if len(values) == 1 else OPTION_1

# شرح الدالة reset_theme: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def reset_theme(self, theme: str, *, persist: bool = True) -> None:
        theme = self.normalize_theme(theme)
        self._selection[theme] = {
            token: OPTION_1 for token in ALL_TOKENS
        }
        if persist:
            self.save()
        for token in ALL_TOKENS:
            self._emit(theme, token, OPTION_1)

# شرح الدالة reset_all: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def reset_all(self, *, persist: bool = True) -> None:
        self._selection = deepcopy(DEFAULT_SELECTION)
        if persist:
            self.save()
        for theme in THEMES:
            for token in ALL_TOKENS:
                self._emit(theme, token, OPTION_1)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
# شرح الدالة load: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def load(self) -> bool:
        if not self.path or not self.path.exists():
            return False

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            selection = raw.get("selection", {}) if isinstance(raw, dict) else {}
            self._selection = self._sanitize_selection(selection)
            return True
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            # Corrupt settings must never prevent the application from starting.
            self._selection = deepcopy(DEFAULT_SELECTION)
            return False

# شرح الدالة save: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def save(self) -> bool:
        if not self.path:
            return False

        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "selection": self.snapshot(),
        }

        temp_path = None
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=str(self.path.parent),
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temp:
                json.dump(payload, temp, ensure_ascii=False, indent=2, sort_keys=True)
                temp.write("\n")
                temp_path = Path(temp.name)
            os.replace(temp_path, self.path)
            return True
        except OSError:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            return False

# شرح الدالة export_json: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def export_json(self) -> str:
        """Return the current selections as JSON for backup/debug UI."""
        return json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "selection": self.snapshot(),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

# شرح الدالة import_json: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def import_json(self, text: str, *, persist: bool = True) -> bool:
        """Import selections defensively without allowing malformed JSON to break the UI."""
        try:
            raw = json.loads(text)
        except (TypeError, ValueError, json.JSONDecodeError):
            return False

        selection = raw.get("selection", {}) if isinstance(raw, dict) else {}
        self._selection = self._sanitize_selection(selection)
        if persist:
            self.save()
        return True

    # ------------------------------------------------------------------
    # Change notifications
    # ------------------------------------------------------------------
# شرح الدالة subscribe: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def subscribe(self, callback: Callable[[str, str, str], None]) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

# شرح الدالة unsubscribe: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def unsubscribe(self, callback: Callable[[str, str, str], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

# شرح الدالة _emit: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _emit(self, theme: str, token: str, option: str) -> None:
        for callback in tuple(self._listeners):
            try:
                callback(theme, token, option)
            except (RuntimeError, TypeError, AttributeError, ValueError):
                # A listener is UI glue. One broken listener must not corrupt
                # or interrupt the theme store itself.
                continue

    # ------------------------------------------------------------------
    # Defensive loading
    # ------------------------------------------------------------------
# شرح الدالة _sanitize_selection: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _sanitize_selection(raw: object) -> dict[str, dict[str, str]]:
        clean = deepcopy(DEFAULT_SELECTION)
        if not isinstance(raw, dict):
            return clean

        for theme in THEMES:
            values = raw.get(theme)
            if not isinstance(values, dict):
                continue
            for token in ALL_TOKENS:
                option = values.get(token)
                if option in OPTIONS:
                    clean[theme][token] = option
        return clean


__all__ = ["SCHEMA_VERSION", "ThemeStore"]

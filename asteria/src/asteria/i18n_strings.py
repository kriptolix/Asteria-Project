"""
Theme-owned UI string translations — and any other per-language data a theme
declares in its `i18n.yaml`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .config import deep_merge
from .errors import AsteriaError


def _base_language(code: str) -> str:
    """'pt-BR' -> 'pt' (also accepts 'pt_BR'); '' -> ''."""
    return re.split(r"[-_]", code, maxsplit=1)[0] if code else ""


def language_chain(lang: str, default_language: str) -> list[str]:
    """The languages to try, in order, for a reader of `lang`.
    """
    chain: list[str] = []
    for code in (lang, default_language):
        for candidate in (code, _base_language(code)):
            if candidate and candidate not in chain:
                chain.append(candidate)
    return chain


def load_theme_i18n(
    theme_dir: Path, site_overrides: dict[str, Any] | None = None
) -> dict[str, dict[str, Any]]:
    """Loads `<theme_dir>/i18n.yaml` and deep-merges `site_overrides`on top of it."""
    path = theme_dir / "i18n.yaml"
    if not path.exists():
        theme_strings: dict[str, Any] = {}
    else:
        try:
            theme_strings = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise AsteriaError(f"Invalid YAML in {path}: {exc}") from exc
        if not isinstance(theme_strings, dict):
            raise AsteriaError(f"The content of {path} must be a YAML mapping.")

    if site_overrides is not None and not isinstance(site_overrides, dict):
        raise AsteriaError("site.yaml: i18n.strings must be a mapping of language -> strings.")

    merged = deep_merge(theme_strings, site_overrides or {})
    for code, entries in merged.items():
        if entries is not None and not isinstance(entries, dict):
            raise AsteriaError(
                f"i18n strings: the entry for language '{code}' must be a mapping of "
                f"key -> text (in {path} or in site.yaml's i18n.strings)."
            )
    return merged


def lookup(
    strings: dict[str, dict[str, Any]], key: str, lang: str, default_language: str
) -> Any | None:
    """The value of `key` for a reader of `lang` — whatever its type: text,
    a list of month names... — or None when no language in the chain has it."""
    for code in language_chain(lang, default_language):
        value = (strings.get(code) or {}).get(key)
        if value is not None:
            return value
    return None


def translate(
    strings: dict[str, dict[str, Any]],
    key: str,
    lang: str,
    default_language: str,
    fallback: str | None = None,
    **kwargs: Any,
) -> Any:
    """Looks `key` up with `lookup`. Text has its `{placeholders}` filled
    from `kwargs`; anything else (a list, ...) is returned as it is.

    A key no language has renders `fallback`, or `??key??` — a visible marker
    so a missing translation is easy to find in the generated site."""
    value = lookup(strings, key, lang, default_language)
    if value is None:
        return fallback if fallback is not None else f"??{key}??"
    if not isinstance(value, str):
        return value
    try:
        return value.format(**kwargs)
    except (KeyError, IndexError):
        # A malformed template (referencing a placeholder that wasn't
        # passed) shouldn't break the page either — show it unformatted
        # so the problem is visible instead of raising.
        return value
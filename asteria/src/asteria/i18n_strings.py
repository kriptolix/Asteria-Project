"""
Theme-owned UI string translations.

Used in a template via the `t()` global (registered in
templating.create_environment):

    {{ t("reading_time", post.lang, minutes=post.reading_time) }}
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .config import deep_merge
from .errors import AsteriaError


def load_theme_i18n(
    theme_dir: Path, site_overrides: dict[str, Any] | None = None
) -> dict[str, dict[str, str]]:
    """Loads `<theme_dir>/i18n.yaml` and deep-merges `site_overrides`
    (site.yaml's `i18n.strings`) on top of it."""
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

    return deep_merge(theme_strings, site_overrides or {})


def translate(
    strings: dict[str, dict[str, str]],
    key: str,
    lang: str,
    default_language: str,
    fallback: str | None = None,
    **kwargs: Any,
) -> str:
    """Looks up `strings[lang][key]`, falling back to
    `strings[default_language][key]` when `lang` has no translation for
    that key."""
    template = strings.get(lang, {}).get(key) or strings.get(default_language, {}).get(key)
    if template is None:
        return fallback if fallback is not None else f"??{key}??"
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        # A malformed template (referencing a placeholder that wasn't
        # passed) shouldn't break the page either — show it unformatted
        # so the problem is visible instead of raising.
        return template
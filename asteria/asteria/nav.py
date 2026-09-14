"""
Configurable hierarchical navigation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import Diagnostics
from .references import build_translation_registry


@dataclass
class NavEntry:
    title: str
    url: str | None = None
    children: list["NavEntry"] = field(default_factory=list)


def _resolve_target(
    page_id: str,
    registry: dict[str, Any],
    translation_registry: dict[str, dict[str, Any]],
    lang: str,
    default_language: str,
) -> Any | None:
    """translation_key is checked FIRST, exact id second — same rationale
    as build._build_menu and references.resolve_references: a translated
    page's translation_key (e.g. "about") is usually identical to the
    untranslated/default page's own id, so checking id first would always
    match the default-language page and never reach the translation
    group. A dotted id used to pin one specific translation (e.g.
    "about.pt") is never itself a valid translation_key, so this order
    never breaks that escape hatch."""
    group = translation_registry.get(page_id)
    if group:
        return (
            group.get(lang)
            or group.get(default_language)
            or next(iter(group.values()))
        )
    return registry.get(page_id)


def _resolve(
    page_id: str,
    title_override: str | None,
    registry: dict[str, Any],
    translation_registry: dict[str, dict[str, Any]],
    lang: str,
    default_language: str,
    diagnostics: Diagnostics,
) -> NavEntry:
    target = _resolve_target(page_id, registry, translation_registry, lang, default_language)
    if target is None:
        diagnostics.warning(
            f"nav: Non-existent item reference ID: '{page_id}'.", source="site.yaml"
        )
        return NavEntry(title=title_override or page_id, url=None)
    return NavEntry(title=title_override or target.title, url=target.url)


def _resolve_url_only(
    page_id: str,
    registry: dict[str, Any],
    translation_registry: dict[str, dict[str, Any]],
    lang: str,
    default_language: str,
    diagnostics: Diagnostics,
) -> str | None:
    target = _resolve_target(page_id, registry, translation_registry, lang, default_language)
    if target is None:
        diagnostics.warning(
            f"nav: Non-existent item reference ID: '{page_id}'.", source="site.yaml"
        )
        return None
    return target.url


def _parse_items(
    items: list[Any],
    registry: dict[str, Any],
    translation_registry: dict[str, dict[str, Any]],
    lang: str,
    default_language: str,
    diagnostics: Diagnostics,
) -> list[NavEntry]:
    result: list[NavEntry] = []

    for raw in items:
        if isinstance(raw, str):
            result.append(
                _resolve(raw, None, registry, translation_registry, lang, default_language, diagnostics)
            )
            continue

        if not isinstance(raw, dict) or len(raw) != 1:
            diagnostics.warning(
                f"nav: malformed item, ignored: {raw!r}", source="site.yaml"
            )
            continue

        (title, value), = raw.items()

        if isinstance(value, str):
            result.append(
                _resolve(value, title, registry, translation_registry, lang, default_language, diagnostics)
            )
        elif isinstance(value, list):
            children_raw = list(value)
            own_url: str | None = None

            # "Section index page" convention: first standalone child
            # (string) becomes the section title link and disappears from the list.
            if children_raw and isinstance(children_raw[0], str):
                own_url = _resolve_url_only(
                    children_raw[0], registry, translation_registry, lang, default_language, diagnostics
                )
                children_raw = children_raw[1:]

            children = _parse_items(
                children_raw, registry, translation_registry, lang, default_language, diagnostics
            )
            result.append(NavEntry(title=title, url=own_url, children=children))
        else:
            diagnostics.warning(
                f"nav: invalid value for '{title}' (expected ID or list).",
                source="site.yaml",
            )

    return result


def build_nav(
    nav_config: list[Any],
    registry: dict[str, Any],
    diagnostics: Diagnostics,
    translation_registry: dict[str, dict[str, Any]] | None = None,
    lang: str = "",
    default_language: str = "",
) -> list[NavEntry]:
    """Builds the nav tree for a single language. `translation_registry`
    (see references.build_translation_registry) lets a plain page id in
    `nav_config` (e.g. "about") resolve to the translation matching
    `lang` when one exists, exactly like `[[references]]` and `menu:` —
    see build._build_menu. Omitting `translation_registry` (or `lang`)
    keeps the old, language-unaware behavior: every id is only looked up
    in `registry` by its exact key."""
    return _parse_items(
        nav_config or [], registry, translation_registry or {}, lang, default_language, diagnostics
    )
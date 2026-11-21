"""
Configurable hierarchical navigation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import Diagnostics
from .translations import TranslationIndex


@dataclass
class NavEntry:
    title: str
    url: str | None = None
    children: list["NavEntry"] = field(default_factory=list)


def _title_for(target: Any) -> str:
    """A  label exclusive to the nav, distinct from
    the document's real `title:`."""
    return getattr(target, "nav_title", None) or target.title


def _resolve(
    page_id: str,
    index: TranslationIndex,
    lang: str,
    diagnostics: Diagnostics,
) -> NavEntry:
    target = index.resolve(page_id, lang)
    if target is None:
        diagnostics.warning(
            f"nav: Non-existent item reference ID: '{page_id}'.", source="site.yaml"
        )
        return NavEntry(title=page_id, url=None)
    return NavEntry(title=_title_for(target), url=target.url)


def _parse_items(
    items: list[Any],
    index: TranslationIndex,
    lang: str,
    diagnostics: Diagnostics,
) -> list[NavEntry]:
    """`items` is `nav:` (or a nested branch of it): each entry is either
    a bare document id (a leaf), or a single-key mapping `{id: [...]}`
    whose key is a document id and whose value is a list of children (a
    branch) — nestable to any depth the same way."""
    result: list[NavEntry] = []

    for raw in items:
        if isinstance(raw, str):
            result.append(_resolve(raw, index, lang, diagnostics))
            continue

        if isinstance(raw, dict) and len(raw) == 1:
            (index_id, value), = raw.items()

            if not isinstance(index_id, str) or not isinstance(value, list):
                diagnostics.warning(
                    "nav: a branch must be a single page ID mapping to a "
                    f"list of children — ignored: {raw!r}",
                    source="site.yaml",
                )
                continue

            target = index.resolve(index_id, lang)
            if target is None:
                diagnostics.warning(
                    f"nav: Non-existent item reference ID: '{index_id}'.", source="site.yaml"
                )
                continue

            children = _parse_items(value, index, lang, diagnostics)
            result.append(NavEntry(title=_title_for(target), url=target.url, children=children))
            continue

        diagnostics.warning(f"nav: malformed item, ignored: {raw!r}", source="site.yaml")

    return result


def build_nav(
    nav_config: list[Any],
    index: TranslationIndex,
    diagnostics: Diagnostics,
    lang: str = "",
) -> list[NavEntry]:
    """Builds the nav tree for a single language.

    `index` should be built from pages and posts (plus raw pages as extra
    targets, reachable by exact id only).
    """
    return _parse_items(nav_config or [], index, lang, diagnostics)
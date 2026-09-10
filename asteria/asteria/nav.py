"""
Configurable hierarchical navigation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import Diagnostics


@dataclass
class NavEntry:
    title: str
    url: str | None = None
    children: list["NavEntry"] = field(default_factory=list)


def _resolve(
    page_id: str, title_override: str | None, registry: dict[str, Any], diagnostics: Diagnostics
) -> NavEntry:
    target = registry.get(page_id)
    if target is None:
        diagnostics.warning(
            f"nav: Non-existent item reference ID: '{page_id}'.", source="site.yaml"
        )
        return NavEntry(title=title_override or page_id, url=None)
    return NavEntry(title=title_override or target.title, url=target.url)


def _resolve_url_only(
    page_id: str, registry: dict[str, Any], diagnostics: Diagnostics
) -> str | None:
    target = registry.get(page_id)
    if target is None:
        diagnostics.warning(
            f"nav: Non-existent item reference ID: '{page_id}'.", source="site.yaml"
        )
        return None
    return target.url


def _parse_items(
    items: list[Any], registry: dict[str, Any], diagnostics: Diagnostics
) -> list[NavEntry]:
    result: list[NavEntry] = []

    for raw in items:
        if isinstance(raw, str):
            result.append(_resolve(raw, None, registry, diagnostics))
            continue

        if not isinstance(raw, dict) or len(raw) != 1:
            diagnostics.warning(
                f"nav: malformed item, ignored: {raw!r}", source="site.yaml"
            )
            continue

        (title, value), = raw.items()

        if isinstance(value, str):
            result.append(_resolve(value, title, registry, diagnostics))
        elif isinstance(value, list):
            children_raw = list(value)
            own_url: str | None = None

            # "Section index page" convention: first standalone child
            # (string) becomes the section title link and disappears from the list.
            if children_raw and isinstance(children_raw[0], str):
                own_url = _resolve_url_only(children_raw[0], registry, diagnostics)
                children_raw = children_raw[1:]

            children = _parse_items(children_raw, registry, diagnostics)
            result.append(NavEntry(title=title, url=own_url, children=children))
        else:
            diagnostics.warning(
                f"nav: invalid value for '{title}' (expected ID or list).",
                source="site.yaml",
            )

    return result


def build_nav(
    nav_config: list[Any], registry: dict[str, Any], diagnostics: Diagnostics
) -> list[NavEntry]:
    return _parse_items(nav_config or [], registry, diagnostics)

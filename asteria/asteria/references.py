"""
Semantic reference resolution.
"""

from __future__ import annotations

import re
from html import escape
from typing import Any

from .errors import Diagnostics

REFERENCE_RE = re.compile(r"(\\)?\[\[(embed:)?([A-Za-z0-9_\-]+)(?:\|([^\]]+))?\]\]")

DEFAULT_EMBED_HEIGHT = 600

MORE_MARKER = "more" 

_MORE_BLOCK_RE = re.compile(r"\s*<p>\s*\[\[more\]\]\s*</p>\s*", re.IGNORECASE)

_MORE_INLINE_RE = re.compile(r"\[\[more\]\]", re.IGNORECASE)



def build_registry(items: list[Any]) -> dict[str, Any]:
    
    return {item.id: item for item in items}


def resolve_references(
    html: str, registry: dict[str, Any], source: str, diagnostics: Diagnostics
) -> str:
    def _replace(match: re.Match) -> str:
        is_escaped = bool(match.group(1))
        is_embed = bool(match.group(2))
        ref_id = match.group(3)
        label = match.group(4)

        if is_escaped:
            suffix = f"|{label}" if label else ""
            return f"[[{'embed:' if is_embed else ''}{ref_id}{suffix}]]"

        target = registry.get(ref_id)

        if target is None:
            kind = "embed" if is_embed else "reference"
            diagnostics.error(
                f"[[{'embed:' if is_embed else ''}{ref_id}]]: Target of {kind} not found.",
                source=source,
            )
            # Keep it visible in the HTML to make it easier to spot the problem,
            # instead of silently making the author's text disappear.
            return f'<span class="broken-reference" title="Not found: {escape(ref_id)}">[[{escape(ref_id)}]]</span>'

        if is_embed:
            height = DEFAULT_EMBED_HEIGHT
            if label and label.strip().isdigit():
                height = int(label.strip())
            else:
                height = getattr(target, "height", DEFAULT_EMBED_HEIGHT)
            title_attr = escape(getattr(target, "title", ref_id))
            return (
                f'<iframe src="{target.url}" title="{title_attr}" loading="lazy" '
                f'style="width:100%;height:{height}px;border:0" '
                f'class="asteria-embed"></iframe>'
            )

        text = label.strip() if label else target.title
        return f'<a href="{target.url}">{escape(text)}</a>'

    return REFERENCE_RE.sub(_replace, html)


def resolve_references_for_all(
    documents: list[Any],
    diagnostics: Diagnostics,
    extra_targets: list[Any] | None = None,
) -> None:
    
    registry = build_registry(documents)
    if extra_targets:
        registry.update(build_registry(extra_targets))

    for doc in documents:
        doc.content_html = resolve_references(
            doc.content_html, registry, source=str(doc.source_path), diagnostics=diagnostics
        )


def split_at_more_marker(html: str) -> tuple[str, str | None]:
    """
    Manual preview of posts 
    """
    match = _MORE_BLOCK_RE.search(html)
    if match:
        preview_html = html[: match.start()]
        full_html = html[: match.start()] + html[match.end() :]
        return full_html, preview_html
 
    match = _MORE_INLINE_RE.search(html)
    if match:
        preview_html = html[: match.start()]
        full_html = html[: match.start()] + html[match.end() :]
        return full_html, preview_html
 
    return html, None

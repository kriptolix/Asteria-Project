"""
Handles [[id]] / [[id|Custom label]] cross-references between pages/posts.

Which document a reference points to is decided by
`translations.TranslationIndex.resolve`: the same rule `menu:`, `nav:` and
`home_page:` use.
"""

from __future__ import annotations

import re
from html import escape
from typing import Any

from .errors import Diagnostics
from .translations import TranslationIndex

# Allows a dot in the id (e.g. "hello-world.pt") so a specific translation
# can be pinned by its exact document id — see TranslationIndex.resolve for
# why that alone isn't the primary resolution path.
REFERENCE_RE = re.compile(r"(\\)?\[\[([A-Za-z0-9_.\-]+)(?:\|([^\]]+))?\]\]")

MORE_MARKER = "more" 

_MORE_BLOCK_RE = re.compile(r"\s*<p>\s*\[\[more\]\]\s*</p>\s*", re.IGNORECASE)

_MORE_INLINE_RE = re.compile(r"\[\[more\]\]", re.IGNORECASE)


def resolve_references(
    html: str,
    index: TranslationIndex,
    source: str,
    diagnostics: Diagnostics,
    lang: str = "",
) -> str:
    """Replaces every `[[ref]]` in `html` with a link, resolving `ref` for
    a reader in `lang` (the default language when empty)."""

    def _replace(match: re.Match) -> str:
        is_escaped = bool(match.group(1))
        ref_id = match.group(2)
        label = match.group(3)

        if is_escaped:
            suffix = f"|{label}" if label else ""
            return f"[[{ref_id}{suffix}]]"

        if ref_id.lower() == MORE_MARKER:
            # [[more]] is a reserved marker, not a cross-reference.
            return match.group(0)

        target = index.resolve(ref_id, lang)

        if target is None:
            diagnostics.error(
                f"[[{ref_id}]]: Target of reference not found.",
                source=source,
            )
            # Keep it visible in the HTML to make it easier to spot the problem,
            # instead of silently making the author's text disappear.
            return f'<span class="broken-reference" title="Not found: {escape(ref_id)}">[[{escape(ref_id)}]]</span>'

        text = label.strip() if label else target.title
        return f'<a href="{target.url}">{escape(text)}</a>'

    return REFERENCE_RE.sub(_replace, html)


def resolve_references_for_all(
    documents: list[Any],
    index: TranslationIndex,
    diagnostics: Diagnostics,
) -> None:
    """Resolves the references of every document, each one in its own
    language. `index` should already include any extra targets (raw
    pages) that may be referenced by exact id."""
    for doc in documents:
        doc.content_html = resolve_references(
            doc.content_html,
            index,
            source=str(doc.source_path),
            diagnostics=diagnostics,
            lang=getattr(doc, "lang", "") or index.default_language,
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
"""Resolução de referências semânticas (spec seção 7):

- `[[id]]` / `[[id|texto]]` → vira `<a href="...">` (páginas, posts ou
  páginas HTML "cruas" — ver `asteria/raw.py`).
- `\\[[id]]` (com barra invertida antes) → escapa a sintaxe: produz o texto
  literal `[[id]]` no HTML final, sem tentar resolver. Útil para escrever
  *sobre* a própria sintaxe de referência (documentação, tutoriais).

Roda depois que todos os documentos/páginas cruas já têm `id` e `url`
definidos, para que uma referência possa apontar para qualquer tipo de
conteúdo, e para que a estrutura de URLs do site possa mudar sem que os
documentos de origem precisem ser editados.
"""

from __future__ import annotations

import re
from html import escape
from typing import Any

from .errors import Diagnostics

REFERENCE_RE = re.compile(r"(\\)?\[\[(embed:)?([A-Za-z0-9_\-]+)(?:\|([^\]]+))?\]\]")

DEFAULT_EMBED_HEIGHT = 600


def build_registry(items: list[Any]) -> dict[str, Any]:
    """`items` pode misturar `Document` e `RawPage` — qualquer objeto com
    `.id`, `.url` e `.title` serve como alvo de referência/embed."""
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
            kind = "embed" if is_embed else "referência"
            diagnostics.error(
                f"[[{'embed:' if is_embed else ''}{ref_id}]]: alvo da {kind} não encontrado.",
                source=source,
            )
            # Mantém visível no HTML para facilitar encontrar o problema,
            # em vez de silenciosamente sumir com o texto do autor.
            return f'<span class="broken-reference" title="Não encontrado: {escape(ref_id)}">[[{escape(ref_id)}]]</span>'

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
    """Resolve `[[id]]`/`[[embed:id]]` em `content_html` de cada documento
    de `documents`, in-place. `extra_targets` (ex: páginas HTML cruas)
    entram no registro de resolução mas não têm seu próprio conteúdo
    escaneado (não têm `content_html`)."""
    registry = build_registry(documents)
    if extra_targets:
        registry.update(build_registry(extra_targets))

    for doc in documents:
        doc.content_html = resolve_references(
            doc.content_html, registry, source=str(doc.source_path), diagnostics=diagnostics
        )

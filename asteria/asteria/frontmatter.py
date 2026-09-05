"""Interpretação do bloco de front matter padronizado (spec seção 5.2/5.3).

Responsabilidade do SSG (não da biblioteca de conversão): ler o
``<div class="ssg-frontmatter" data-ssg="frontmatter">...</div>`` produzido
pelo conversor, extrair os pares chave/valor, aplicar valores padrão e
remover o bloco do HTML de conteúdo final (ele não deve aparecer na página).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser

from .errors import Diagnostics

KNOWN_FIELDS = {
    "title",
    "date",
    "author",
    "tags",
    "categories",
    "description",
    "slug",
    "variant",
    "toc",
    "navigation",
}

FRONTMATTER_BLOCK_RE = re.compile(
    r'<div[^>]*class="ssg-frontmatter"[^>]*>(?P<inner>.*?)</div>',
    re.DOTALL,
)
META_TAG_RE = re.compile(
    r'<meta[^>]*data-key="(?P<key>[^"]*)"[^>]*content="(?P<value>[^"]*)"[^>]*>',
    re.DOTALL,
)


@dataclass
class Frontmatter:
    title: str | None = None
    date: str | None = None
    author: str | None = None
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    description: str = ""
    slug: str | None = None
    variant: str | None = None  # variante de CSS a usar para este documento
    toc: bool = True  # sumário automático (TOC) desta página; toc:false desativa
    navigation: bool = False  # sidebar de navegação (nav:); navigation:true ativa
    extra: dict[str, str] = field(default_factory=dict)

    def get(self, key: str, default=None):
        return getattr(self, key, self.extra.get(key, default))


def _split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() not in ("false", "no", "0", "off")


def extract_frontmatter(
    html: str, source: str, diagnostics: Diagnostics
) -> tuple[Frontmatter, str]:
    """Retorna (frontmatter, html_sem_o_bloco)."""

    match = FRONTMATTER_BLOCK_RE.search(html)
    if not match:
        return Frontmatter(), html

    inner = match.group("inner")
    raw_fields: dict[str, str] = {}
    for meta_match in META_TAG_RE.finditer(inner):
        key = unescape(meta_match.group("key")).strip().lower()
        value = unescape(meta_match.group("value")).strip()
        if key in raw_fields:
            diagnostics.warning(f"Campo de front matter duplicado: '{key}'.", source=source)
        raw_fields[key] = value

    for key in raw_fields:
        if key not in KNOWN_FIELDS:
            diagnostics.warning(
                f"Campo de front matter desconhecido: '{key}' (preservado em extra).",
                source=source,
            )

    fm = Frontmatter(
        title=raw_fields.get("title"),
        date=raw_fields.get("date"),
        author=raw_fields.get("author"),
        tags=_split_list(raw_fields.get("tags", "")),
        categories=_split_list(raw_fields.get("categories", "")),
        description=raw_fields.get("description", ""),
        slug=raw_fields.get("slug"),
        variant=raw_fields.get("variant"),
        toc=_parse_bool(raw_fields.get("toc"), default=True),
        navigation=_parse_bool(raw_fields.get("navigation"), default=False),
        extra={k: v for k, v in raw_fields.items() if k not in KNOWN_FIELDS},
    )

    html_without_block = html[: match.start()] + html[match.end() :]
    return fm, html_without_block.strip()

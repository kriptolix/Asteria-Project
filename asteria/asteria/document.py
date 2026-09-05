"""Modelo de documento exposto aos templates (spec seção 19).

`Document` é a base comum entre `Page` e `Post`. Os atributos aqui formam o
"modelo de dados para templates": os temas nunca devem depender de
implementação interna do compilador, apenas destes campos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_type
from pathlib import Path

from .converter import ExtractedImage
from .frontmatter import Frontmatter
from .urls import slugify


@dataclass
class TocEntry:
    id: str
    title: str
    level: int
    children: list["TocEntry"] = field(default_factory=list)


@dataclass
class Document:
    """Campos comuns a páginas e posts."""

    id: str  # nome do arquivo sem extensão — identificador único (spec 6)
    kind: str  # "page" ou "post"
    source_path: Path
    frontmatter: Frontmatter
    content_html: str  # HTML final (sem o bloco de frontmatter, refs resolvidas)
    raw_content_html: str  # HTML logo após a conversão, antes de resolver refs

    slug: str = ""
    url: str = ""
    toc: list[TocEntry] = field(default_factory=list)
    images: list[ExtractedImage] = field(default_factory=list)

    previous: "Document | None" = None
    next: "Document | None" = None

    def __post_init__(self) -> None:
        if not self.slug:
            self.slug = self.frontmatter.slug or slugify(self.id)

    # -- propriedades expostas aos templates (spec 19) -----------------------
    @property
    def title(self) -> str:
        return self.frontmatter.title or self.id

    @property
    def date(self) -> str | None:
        return self.frontmatter.date

    @property
    def author(self) -> str | None:
        return self.frontmatter.author

    @property
    def tags(self) -> list[str]:
        return self.frontmatter.tags

    @property
    def categories(self) -> list[str]:
        return self.frontmatter.categories

    @property
    def description(self) -> str:
        return self.frontmatter.description

    @property
    def variant(self) -> str | None:
        """Variante de CSS a usar para este documento (ex: 'dark'), ou
        None para usar a variante padrão do site (`theme.default_variant`
        em `site.yaml`)."""
        return self.frontmatter.variant

    @property
    def toc_enabled(self) -> bool:
        """Sumário automático (TOC) desta página. Ativo por padrão;
        `toc: false` no front matter desativa. Não confundir com o campo
        `toc` (a árvore de títulos já construída) desta mesma classe."""
        return self.frontmatter.toc

    @property
    def navigation_enabled(self) -> bool:
        """Sidebar de navegação (`nav:` do site.yaml) nesta página.
        Desativada por padrão; `navigation: true` no front matter ativa."""
        return self.frontmatter.navigation

    @property
    def content(self) -> str:
        return self.content_html

    @property
    def excerpt(self) -> str:
        if self.frontmatter.description:
            return self.frontmatter.description
        # fallback simples: primeiras palavras do texto sem HTML.
        import re

        text = re.sub(r"<[^>]+>", " ", self.content_html)
        text = re.sub(r"\s+", " ", text).strip()
        return (text[:280] + "…") if len(text) > 280 else text

    def sort_key(self):
        return self.frontmatter.date or ""


@dataclass
class Page(Document):
    def __post_init__(self) -> None:
        self.kind = "page"
        super().__post_init__()


@dataclass
class Post(Document):
    def __post_init__(self) -> None:
        self.kind = "post"
        super().__post_init__()

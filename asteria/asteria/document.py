"""
Document model exposed to templates.
`Document` is the common base between `Page` and `Post`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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

    id: str  # filename without extension — unique identifier
    kind: str  # "page" or "post"
    source_path: Path
    frontmatter: Frontmatter
    content_html: str  # Final HTML final
    raw_content_html: str  # HTML before resolve refs

    slug: str = ""
    url: str = ""
    toc: list[TocEntry] = field(default_factory=list)
    images: list[ExtractedImage] = field(default_factory=list)

    previous: "Document | None" = None
    next: "Document | None" = None
    manual_excerpt: str | None = None
    excerpt_length: int = 280
    excerpt_enabled: bool = True

    # -- i18n -----------------------------------------------------------
    lang: str = ""    
    translation_key: str = ""    
    translations: dict[str, "Document"] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if not self.translation_key:
            self.translation_key = self.id
        if not self.slug:            
            self.slug = self.frontmatter.slug or slugify(self.translation_key)

    
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
        """CSS variant to use for this document (e.g., 'dark'), or
        None to use the site's default variant."""
        return self.frontmatter.variant

    @property
    def toc_enabled(self) -> bool:
        """Automatic table of contents (TOC) for this page. Do not confuse it with the `toc` 
        field (the already constructed tree of headings) of this same class."""
        return self.frontmatter.toc

    @property
    def navigation_enabled(self) -> bool:
        """Navigation sidebar (`nav:` from site.yaml) on this page."""
        return self.frontmatter.navigation

    @property
    def content(self) -> str:
        return self.content_html

    @property
    def excerpt(self) -> str:
        if not self.excerpt_enabled:
            # Desligado: description se houver, senão apenas o título.
            return self.frontmatter.description or self.title

        # Ligado: se houver marcação [[more]] explícita, respeita o autor.
        if self.manual_excerpt is not None:
            return self.manual_excerpt

        # Sem marcação: sempre gera o excerpt padrão, mesmo que haja description.
        import re
        text = re.sub(r"<[^>]+>", " ", self.content_html)
        text = re.sub(r"\s+", " ", text).strip()
        length = self.excerpt_length
        return (text[:length] + "…") if len(text) > length else text

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

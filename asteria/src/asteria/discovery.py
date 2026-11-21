"""
Scans `content/pages` and `content/posts`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cache import cached_html
from .config import SiteConfig
from .converter import ODTConverter
from .document import Document, Page, Post
from .errors import Diagnostics
from .frontmatter import extract_frontmatter
from .highlight import highlight_code_blocks, load_languages
from .raw import RawPage, load_raw_page
from .translations import detect_lang, validate_translations


def _walk_pages(
    directory: Path, diagnostics: Diagnostics
) -> tuple[list[Path], list[Path]]:
    
    odt_paths: list[Path] = []
    raw_dirs: list[Path] = []
    _walk_pages_rec(directory, odt_paths, raw_dirs, diagnostics)
    return odt_paths, raw_dirs


def _walk_pages_rec(
    directory: Path,
    odt_paths: list[Path],
    raw_dirs: list[Path],
    diagnostics: Diagnostics,
) -> None:
    
    if not directory.exists():
        return
    for entry in sorted(directory.iterdir()):
        if entry.is_file() and entry.suffix == ".odt":
            odt_paths.append(entry)
        elif entry.is_dir():
            if any(entry.rglob("*.odt")):
                # Organizational folder: contains (at some level) .odt files —
                # recurses normally, without affecting page IDs/URLs.
                _walk_pages_rec(entry, odt_paths, raw_dirs, diagnostics)
            elif (entry / "index.html").exists():
                raw_dirs.append(entry)
            else:
                diagnostics.warning(
                    f"Folder in content/pages/ without .odt or index.html, ignored: '{entry.name}'.",
                    source=str(entry),
                )


def _walk_posts(
    directory: Path, diagnostics: Diagnostics
) -> tuple[list[Path], list[Path]]:
    
    odt_paths: list[Path] = []
    raw_dirs: list[Path] = []
    if not directory.exists():
        return odt_paths, raw_dirs

    for entry in sorted(directory.iterdir()):
        if entry.is_file() and entry.suffix == ".odt":
            odt_paths.append(entry)
        elif entry.is_dir():
            if (entry / "index.html").exists():
                raw_dirs.append(entry)
            else:
                diagnostics.warning(
                    f"Folder in content/posts/ without index.html, ignored: '{entry.name}' "
                    "(content/posts/ is not recursive for .odt).",
                    source=str(entry),
                )

    return odt_paths, raw_dirs


def _load_document(
    path: Path,
    kind: str,
    converter: ODTConverter,
    diagnostics: Diagnostics,
    code_languages: dict[str, dict[str, Any]],
    lang: str = "",
    translation_key: str = "",
) -> Document:
    
    doc_id = path.stem
    # A language suffix ("welcome.pt-BR") is not part of the identifier the
    # author chose, so check the translation_key (the stem without it).
    check_id = translation_key or doc_id
    if not check_id or not check_id.replace("-", "").replace("_", "").isalnum():
        diagnostics.warning(
            f"Unusual document identifier derived from the filename: '{check_id}'.",
            source=str(path),
        )

    result = converter.convert(path, diagnostics)

    if result.metadata is not None:        
        fm = result.metadata
        content_html = result.html
    else:        
        fm, content_html = extract_frontmatter(
            result.html, source=str(path), diagnostics=diagnostics
        )
        if not fm.title:
            diagnostics.warning(
                "Document without a 'title' in the front matter; using the filename.",
                source=str(path),
            )
    
    content_html = highlight_code_blocks(content_html, code_languages)

    # The `lang:` field in the front matter, when present, takes precedence
    # over the language detected from the filename. 
    final_lang = fm.lang or lang

    cls = Page if kind == "page" else Post
    return cls(
        id=doc_id,
        kind=kind,
        source_path=path,
        frontmatter=fm,
        content_html=content_html,
        raw_content_html=content_html,
        images=result.images,
        lang=final_lang,
        translation_key=translation_key or doc_id,
    )


def discover_content(
    config: SiteConfig, converter: ODTConverter, diagnostics: Diagnostics
) -> tuple[list[Page], list[Post], list[RawPage]]:
    pages: list[Page] = []
    posts: list[Post] = []
    raw_pages: list[RawPage] = []
    
    code_languages = load_languages(config.root)

    page_odts, page_raw_dirs = _walk_pages(config.pages_dir, diagnostics)
    for path in page_odts:
        
        translation_key, detected_lang = detect_lang(
            path.stem, config.languages, config.default_language
        )
        pages.append(
            _load_document(
                path, "page", converter, diagnostics, code_languages,
                lang=detected_lang, translation_key=translation_key,
            )
        )  # type: ignore[arg-type]
    for raw_dir in page_raw_dirs:
        raw_pages.append(
            load_raw_page(raw_dir, config.url_patterns["pages"], diagnostics)
        )

    post_odts, post_raw_dirs = _walk_posts(config.posts_dir, diagnostics)
    for path in post_odts:
        translation_key, detected_lang = detect_lang(
            path.stem, config.languages, config.default_language
        )
        posts.append(
            _load_document(
                path, "post", converter, diagnostics, code_languages,
                lang=detected_lang, translation_key=translation_key,
            )
        )  # type: ignore[arg-type]
    for raw_dir in post_raw_dirs:
        raw_pages.append(
            load_raw_page(raw_dir, config.url_patterns["posts"], diagnostics)
        )

    _validate_unique_ids(pages, posts, raw_pages, diagnostics)
    validate_translations([*pages, *posts], config.languages, diagnostics)
    return pages, posts, raw_pages


@dataclass
class PageInfo:
    """What a UI needs to list or pick a document, without a full build."""

    id: str
    kind: str  # "page" or "post"
    translation_key: str  # what menu:/nav: entries should reference
    lang: str
    title: str  # front matter `title`, or the id when it has none
    menu_title: str | None
    nav_title: str | None
    cached: bool  # True: read from a fresh cache entry; False: not known, or converted just now

    @property
    def menu_label(self) -> str:
        """The label the menu shows (same rule as menu.build_menu)."""
        return self.menu_title or self.title

    @property
    def nav_label(self) -> str:
        """The label the navigation shows (same rule as nav._title_for)."""
        return self.nav_title or self.title


def page_info(
    config: SiteConfig,
    entries: dict[str, Any],
    path: Path,
    kind: str = "page",
    converter: ODTConverter | None = None,
) -> PageInfo:
    """Describes one `.odt` document using the conversion cache.

    The cache holds the converted HTML, front matter block included, so the
    titles come from the same `extract_frontmatter` the build uses and never
    go stale when the parser changes. Without a fresh cache entry (never
    built, or edited since): with no `converter` the titles are unknown (the
    id is used); with one, that single file is converted on demand (pass a
    `CachingConverter` so the result lands in `entries`).
    """
    translation_key, lang = detect_lang(
        path.stem, config.languages, config.default_language
    )
    html = cached_html(entries, path)
    from_cache = html is not None

    if html is None and converter is not None:
        html = converter.convert(path, Diagnostics()).html

    if html is None:
        return PageInfo(
            path.stem, kind, translation_key, lang, path.stem, None, None, False
        )

    # Throwaway diagnostics: the build already reports front matter issues.
    fm, _html = extract_frontmatter(html, source=str(path), diagnostics=Diagnostics())
    return PageInfo(
        id=path.stem,
        kind=kind,
        translation_key=translation_key,
        lang=fm.lang or lang,
        title=fm.title or path.stem,
        menu_title=fm.menu_title,
        nav_title=fm.nav_title,
        cached=from_cache,
    )


def peek_pages(
    config: SiteConfig, entries: dict[str, Any], diagnostics: Diagnostics
) -> list[PageInfo]:
    """Lists the project's `.odt` pages with their titles, read from the
    cache only (see `page_info`); pages without a fresh entry come back with
    `cached=False` and the id as title."""
    page_odts, _raw_dirs = _walk_pages(config.pages_dir, diagnostics)
    return [page_info(config, entries, path, "page") for path in page_odts]


def _validate_unique_ids(
    pages: list[Page],
    posts: list[Post],
    raw_pages: list[RawPage],
    diagnostics: Diagnostics,
) -> None:
    seen: dict[str, str] = {}  # id -> source path (str) already seen
    for item in [*pages, *posts, *raw_pages]:
        source = str(getattr(item, "source_path", None) or getattr(item, "source_dir", ""))
        if item.id in seen:
            diagnostics.error(
                f"Duplicate ID '{item.id}': used by '{seen[item.id]}' and '{source}'.",
                source=source,
            )
        else:
            seen[item.id] = source
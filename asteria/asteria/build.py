"""
Build pipeline orchestration
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from markupsafe import Markup

from .cache import CachingConverter, load_cache, save_cache
from .config import SiteConfig, load_config
from .converter import get_converter
from .discovery import discover_content
from .document import Document, Page, Post
from .errors import AsteriaError, Diagnostics
from .feed import render_atom, render_rss
from .nav import build_nav
from .pagination import paginate
from .references import build_registry, resolve_references_for_all, split_at_more_marker
from .sitemap import SitemapEntry, render_sitemap
from .social import build_social_links
from .taxonomy import Term, collect_categories, collect_tags
from .templating import apply_asset_manifest, create_environment, make_site_view, render_template
from .theme_config import load_theme_config
from .toc import inject_heading_ids_and_build_toc
from .urls import build_url, prefix_lang, url_to_output_dir, url_to_output_path
from .writer import (
    clean_output,
    copy_raw_pages,
    copy_static_assets,
    fingerprint_assets,
    list_generated_files,
    write_document_images,
    write_page,
    write_text_file,
)


@dataclass
class BuildResult:
    diagnostics: Diagnostics
    pages: list[Page]
    posts: list[Post]
    output_dir: Path
    generated_files: list[str] = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def success(self) -> bool:
        return not self.diagnostics.has_errors


def _assign_urls(config: SiteConfig, pages: list[Page], posts: list[Post]) -> None:
    patterns = config.url_patterns
    for page in pages:
        page.url = build_url(patterns["pages"], slug=page.slug)
    for post in posts:
        base_url = build_url(patterns["posts"], slug=post.slug)
        post.url = prefix_lang(base_url, post.lang, config.default_language)


def _link_translations(posts: list[Post]) -> None:
    """Populates `post.translations` with the other versions (in other languages) 
    of each post, grouped by `translation_key`."""
    groups: dict[str, list[Post]] = {}
    for post in posts:
        groups.setdefault(post.translation_key, []).append(post)

    for group in groups.values():
        for post in group:
            post.translations = {p.lang: p for p in group if p is not post}


def _build_toc_for_all(documents: list[Document]) -> None:
    for doc in documents:
        html_with_ids, toc = inject_heading_ids_and_build_toc(doc.content_html)
        doc.content_html = html_with_ids
        doc.toc = toc


def _assign_prev_next(posts: list[Post]) -> None:
    """Chronological: from oldest to most recent, within each language
    (a post never points to a previous/next post in a different
    language)."""
    by_lang: dict[str, list[Post]] = {}
    for post in posts:
        by_lang.setdefault(post.lang, []).append(post)

    for group in by_lang.values():
        ordered = sorted(group, key=lambda p: p.sort_key())
        for i, post in enumerate(ordered):
            post.previous = ordered[i - 1] if i > 0 else None
            post.next = ordered[i + 1] if i < len(ordered) - 1 else None


def _build_menu(
    menu_config: list[dict],
    config: SiteConfig,
    pages_by_id: dict[str, Page],
    posts: list[Post],
) -> list[dict[str, str]]:
    blog_keys = {"blog", config.blog_prefix.strip("/")}
    menu_items = []
    referenced_ids: set[str] = set()

    for entry in menu_config:
        page_id = entry.get("page")
        referenced_ids.add(page_id)
        title = entry.get("title", page_id)
        if page_id in blog_keys:
            url = config.blog_index_url
        else:
            page = pages_by_id.get(page_id)
            url = "#" if page is None else page.url
        menu_items.append({"title": title, "url": url, "page_id": page_id})

    # If there are posts, the blog is not the home page, and the user has not
    # yet manually added 'blog' to the menu, add it automatically
    # — otherwise, there would be no way to reach the blog from the site.
    if (
        posts
        and config.home_page not in blog_keys
        and not (referenced_ids & blog_keys)
    ):
        menu_items.append(
            {"title": "Blog", "url": config.blog_index_url, "page_id": "blog"}
        )

    return menu_items


def _breadcrumbs_for_page(config: SiteConfig, page: Page) -> list[dict[str, str]]:
    crumbs = [{"title": config.title, "url": "/"}]
    if page.id != config.home_page:
        crumbs.append({"title": page.title, "url": page.url})
    return crumbs


def _breadcrumbs_for_post(config: SiteConfig, post: Post) -> list[dict[str, str]]:
    return [
        {"title": config.title, "url": "/"},
        {"title": "Blog", "url": config.blog_index_url},
        {"title": post.title, "url": post.url},
    ]


def _document_context(
    config: SiteConfig,
    site_view,
    theme_ns: dict,
    doc: Document,
    breadcrumbs: list[dict[str, str]],
) -> dict:
    return {
        "site": site_view,
        "theme": theme_ns,
        "page": doc,
        "post": doc,
        "content": Markup(doc.content_html),
        "breadcrumbs": breadcrumbs,
        "theme_css": doc.variant or theme_ns["default_variant"],
        "canonical_path": doc.url,
        "og_type": "article" if doc.kind == "post" else "website",
        "show_toc": theme_ns["sidebar_toc"] and doc.toc_enabled,
        "show_navigation": bool(theme_ns["nav"]) and doc.navigation_enabled,
        "lang": doc.lang or config.default_language,
    }


def _feed_filename(config: SiteConfig) -> str:
    return "rss.xml" if config.data["feeds"].get("format", "rss") == "rss" else "atom.xml"


def _finalize_html(html: str, live_reload_script: str | None) -> str:
    """Injects the live reload script (only in `asteria serves`, never in 
    `build`/`check`) right before `</body>`. Never called to pages 
    "Raw" HTML — these continue byte by byte as the author wrote."""

    if not live_reload_script:
        return html
    marker = "</body>"
    if marker in html:
        return html.replace(marker, live_reload_script + marker, 1)
    return html + live_reload_script


def run_build(
    project_root: Path,
    config_filename: str = "site.yaml",
    converter_name: str = "auto",
    dry_run: bool = False,
    live_reload_script: str | None = None,
) -> BuildResult:
    
    diagnostics = Diagnostics()
    config_path = project_root / "source" /config_filename
    config = load_config(config_path)

    if not config.theme_dir.exists():
        raise AsteriaError(
            f"Theme '{config.theme_name}' not founded in {config.theme_dir}."
        )

    raw_converter = get_converter(converter_name)
    if raw_converter.name == "fallback":
        diagnostics.warning(
            "Using the FallbackConverter (restricted to tests)"            
        )

    cache_entries = load_cache(project_root)
    converter = CachingConverter(raw_converter, cache_entries)

    pages, posts, raw_pages = discover_content(config, converter, diagnostics)

    if diagnostics.has_errors:
        return BuildResult(diagnostics, pages, posts, config.output_dir)

    _link_translations(posts)
    _assign_urls(config, pages, posts)
    resolve_references_for_all([*pages, *posts], diagnostics, extra_targets=raw_pages)

    if diagnostics.has_errors:
        return BuildResult(diagnostics, pages, posts, config.output_dir)

    _build_toc_for_all([*pages, *posts])
    _assign_prev_next(posts)

    pages_by_id = {p.id: p for p in pages}
    theme_config_raw = load_theme_config(config.theme_dir)
    menu_items = _build_menu(theme_config_raw.get("menu", []), config, pages_by_id, posts)
    feed_url = f"/{_feed_filename(config)}" if config.feeds_enabled else None
    nav_registry = build_registry([*pages, *posts, *raw_pages])
    nav_items = build_nav(theme_config_raw.get("nav", []), nav_registry, diagnostics)
    social_links = build_social_links(theme_config_raw.get("social", []))
    
    theme_ns: dict = dict(theme_config_raw)
    theme_ns["menu"] = menu_items
    theme_ns["nav"] = nav_items
    theme_ns["social"] = social_links   
    theme_ns.setdefault("sidebar_toc", True)
    theme_ns.setdefault("default_variant", "light")

    site_view = make_site_view(config, feed_url=feed_url)

    env = create_environment(config)

    # Excerpt [[more]]
   
    for post in posts:
        post.excerpt_length = config.excerpt_length
        post.excerpt_enabled = config.excerpt_enabled
        post.content_html, manual_excerpt = split_at_more_marker(post.content_html)
        post.manual_excerpt = manual_excerpt

    _build_toc_for_all([*pages, *posts])

    if not dry_run:
        clean_output(config)

    # Assets estáticos (css/js/fonts/images do tema + static/) são
    # copiados e, opcionalmente, "fingerprinted" (nome com hash do
    # conteúdo) ANTES de renderizar qualquer página: os templates usam o
    # global `asset()` para resolver o nome final, então o manifesto
    # precisa existir antes do primeiro render_template.
    if not dry_run:
        copy_static_assets(config)
        asset_manifest = (
            fingerprint_assets(config.output_dir) if config.fingerprint_assets_enabled else {}
        )
        if asset_manifest:
            write_text_file(
                config.output_dir,
                "asset-manifest.json",
                json.dumps(asset_manifest, indent=2, sort_keys=True) + "\n",
            )
        apply_asset_manifest(env, asset_manifest)

    home_candidates: dict[str, str] = {}
    home_candidate_images: dict[str, list] = {}
    sitemap_entries: list[SitemapEntry] = []

    # -- pages --------------------------------------------------------------
    for page in pages:
        context = _document_context(
            config, site_view, theme_ns, page, _breadcrumbs_for_page(config, page)
        )
        html = _finalize_html(render_template(env, "page.html", context), live_reload_script)
        if not dry_run:
            write_page(config.output_dir, url_to_output_path(page.url), html)
            write_document_images(
                config.output_dir, page.images, subdir=url_to_output_dir(page.url)
            )
        home_candidates[page.id] = html
        home_candidate_images[page.id] = page.images
        sitemap_entries.append(SitemapEntry(path=page.url))

    # -- posts ------------------------------------------------------------
    for post in posts:
        context = _document_context(
            config, site_view, theme_ns, post, _breadcrumbs_for_post(config, post)
        )
        html = _finalize_html(render_template(env, "post.html", context), live_reload_script)
        if not dry_run:
            write_page(config.output_dir, url_to_output_path(post.url), html)
            write_document_images(
                config.output_dir, post.images, subdir=url_to_output_dir(post.url)
            )
        sitemap_entries.append(SitemapEntry(path=post.url, lastmod=post.date))

    # -- paginated blog index, taxonomies and feed, per language ----------
    # Idioma padrão mantém as URLs de hoje (/blog/, /tags/, /rss.xml, sem
    # prefixo). Idiomas extras (i18n.languages) ganham as mesmas
    # estruturas sob um prefixo '/{lang}/', para não misturar posts de
    # idiomas diferentes num mesmo índice/feed/nuvem de tags.
    for lang in config.languages:
        is_default_lang = lang == config.default_language
        lang_posts = [p for p in posts if p.lang == lang]
        lang_posts_desc = sorted(lang_posts, key=lambda p: p.sort_key(), reverse=True)

        blog_index_url = prefix_lang(config.blog_index_url, lang, config.default_language)
        blog_pages = paginate(lang_posts_desc, config.posts_per_page, blog_index_url)
        for blog_page in blog_pages:
            html = _finalize_html(
                render_template(
                    env,
                    "blog.html",
                    {
                        "site": site_view,
                        "theme": theme_ns,
                        "posts": blog_page.items,
                        "pagination": blog_page,
                        "theme_css": theme_ns["default_variant"],
                        "canonical_path": blog_page.url,
                        "og_type": "website",
                        "show_navigation": False,
                        "lang": lang,
                        "breadcrumbs": [
                            {"title": config.title, "url": "/"},
                            {"title": "Blog", "url": blog_index_url},
                        ],
                    },
                ),
                live_reload_script,
            )
            if not dry_run:
                write_page(config.output_dir, url_to_output_path(blog_page.url), html)
            sitemap_entries.append(SitemapEntry(path=blog_page.url))
            # A home page ('blog' no site.yaml) só pode apontar para o
            # índice do idioma padrão — os demais idiomas não disputam a
            # raiz do site.
            if blog_page.number == 1 and is_default_lang:
                home_candidates["blog"] = html
                home_candidates[config.blog_prefix.strip("/")] = html

        tags_index_url = prefix_lang(
            config.data["urls"]["tags_index"], lang, config.default_language
        )
        categories_index_url = prefix_lang(
            config.data["urls"]["categories_index"], lang, config.default_language
        )
        lang_tags = collect_tags(lang_posts, config)
        lang_categories = collect_categories(lang_posts, config)
        if not is_default_lang:
            for term in [*lang_tags, *lang_categories]:
                term.url = prefix_lang(term.url, lang, config.default_language)

        sitemap_entries += _write_taxonomy(
            config, env, site_view, theme_ns, lang_tags,
            kind_label="Tags", index_url=tags_index_url,
            dry_run=dry_run, live_reload_script=live_reload_script,
        )
        sitemap_entries += _write_taxonomy(
            config, env, site_view, theme_ns, lang_categories,
            kind_label="Categorias", index_url=categories_index_url,
            dry_run=dry_run, live_reload_script=live_reload_script,
        )

        if config.feeds_enabled and not dry_run:
            feed_format = config.data["feeds"].get("format", "rss")
            feed_xml = (
                render_rss(config, lang_posts_desc)
                if feed_format == "rss"
                else render_atom(config, lang_posts_desc)
            )
            # Idioma padrão preserva o nome de arquivo de sempre
            # (rss.xml/atom.xml); os demais ganham um prefixo ('pt-rss.xml').
            feed_filename = (
                _feed_filename(config) if is_default_lang else f"{lang}-{_feed_filename(config)}"
            )
            write_text_file(config.output_dir, feed_filename, feed_xml)

    # --home page: can point to a page, to the
    # blog index ('blog'), or to another generated index that has been
    # registered in home_candidates. -------------------------------------------
    home_html = home_candidates.get(config.home_page)
    if home_html is not None:
        if not dry_run:
            write_page(config.output_dir, "index.html", home_html)
            # The duplicated page at / needs its images at the root as well,
            # since the HTML uses relative paths (the image is located next to
            # the index.html in its own folder, e.g., /pages/inicio/foo.png).
            extra_images = home_candidate_images.get(config.home_page, [])
            if extra_images:
                write_document_images(config.output_dir, extra_images, subdir="")
        sitemap_entries.append(SitemapEntry(path="/"))
    elif pages or posts:
        diagnostics.warning(
            f"Home page '{config.home_page}' not found among the "
            "generated pages or indexes (use a page ID, or 'blog' "
            "to use the blog index); no root index.html was generated.",
        )

    # -- page 404 --------------------------------------------------------------
    not_found_html = _finalize_html(
        render_template(
            env,
            "404.html",
            {
                "site": site_view,
                "theme": theme_ns,
                "theme_css": theme_ns["default_variant"],
                "canonical_path": "/404.html",
                "og_type": "website",
                "show_navigation": False,
                "breadcrumbs": [],
            },
        ),
        live_reload_script,
    )
    if not dry_run:
        write_page(config.output_dir, "404.html", not_found_html)

    if not dry_run:
        copy_raw_pages(config.output_dir, raw_pages)
    sitemap_entries += [SitemapEntry(path=p.url) for p in raw_pages]

    # -- sitemap.xml ---------------------------------------------------
    if config.sitemap_enabled and not dry_run:
        sitemap_xml = render_sitemap(sitemap_entries, config.url)
        write_text_file(config.output_dir, "sitemap.xml", sitemap_xml)

    # -- robots.txt  ------------------------------------------------------
    if config.robots_enabled and not dry_run:
        robots_lines = ["User-agent: *", "Allow: /"]
        if config.sitemap_enabled:
            robots_lines += ["", f"Sitemap: {config.url}/sitemap.xml"]
        write_text_file(config.output_dir, "robots.txt", "\n".join(robots_lines) + "\n")

    # -- incremental cache ----------------------------------------------
    if not dry_run:
        save_cache(project_root, cache_entries)

    generated_files = [] if dry_run else list_generated_files(config.output_dir)
    return BuildResult(
        diagnostics, pages, posts, config.output_dir, generated_files,
        cache_hits=converter.hits, cache_misses=converter.misses,
    )


def _write_taxonomy(
    config: SiteConfig,
    env,
    site_view,
    theme_ns: dict,
    terms: list[Term],
    kind_label: str,
    index_url: str,
    dry_run: bool = False,
    live_reload_script: str | None = None,
) -> list[SitemapEntry]:
    entries = [SitemapEntry(path=index_url)]

    index_html = _finalize_html(
        render_template(
            env,
            "taxonomy_index.html",
            {
                "site": site_view,
                "theme": theme_ns,
                "terms": terms,
                "kind_label": kind_label,
                "theme_css": theme_ns["default_variant"],
                "canonical_path": index_url,
                "og_type": "website",
                "show_navigation": False,
                "breadcrumbs": [
                    {"title": config.title, "url": "/"},
                    {"title": kind_label, "url": index_url},
                ],
            },
        ),
        live_reload_script,
    )
    if not dry_run:
        write_page(config.output_dir, url_to_output_path(index_url), index_html)

    for term in terms:
        term_html = _finalize_html(
            render_template(
                env,
                "taxonomy_term.html",
                {
                    "site": site_view,
                    "theme": theme_ns,
                    "term": term,
                    "posts": term.posts,
                    "kind_label": kind_label,
                    "theme_css": theme_ns["default_variant"],
                    "canonical_path": term.url,
                    "og_type": "website",
                    "show_navigation": False,
                    "breadcrumbs": [
                        {"title": config.title, "url": "/"},
                        {"title": kind_label, "url": index_url},
                        {"title": term.name, "url": term.url},
                    ],
                },
            ),
            live_reload_script,
        )
        if not dry_run:
            write_page(config.output_dir, url_to_output_path(term.url), term_html)
        entries.append(SitemapEntry(path=term.url))

    return entries

"""
Build pipeline orchestration
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, replace
from pathlib import Path

from jinja2 import TemplateNotFound
from markupsafe import Markup

from .cache import CachingConverter, load_cache, save_cache
from .config import SiteConfig, load_config
from .converter import get_converter
from .discovery import discover_content
from .document import Document, Page, Post, TocEntry
from .errors import AsteriaError, Diagnostics
from .feed import render_atom, render_rss
from .i18n_strings import load_theme_i18n, translate
from .menu import BLOG_KEY, build_menu, menu_references
from .nav import NavEntry, build_nav
from .pagination import paginate
from .references import resolve_references_for_all, split_at_more_marker
from .sitemap import SitemapEntry, render_sitemap
from .social import build_social_links
from .taxonomy import Term, collect_categories, collect_tags
from .templating import (
    SiteView,
    apply_asset_manifest,
    create_environment,
    make_site_view,
    render_template,
)
from .theme_config import load_theme_config, resolve_theme_feature
from .toc import inject_heading_ids_and_build_toc
from .translations import SiteLanguages, TranslationIndex, link_translations
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
class _LangSiteData:   

    menu: list[dict[str, str]]
    nav: list[NavEntry]
    categories: list[Term]
    tags: list[Term]
    featured_pages: list[Page]
    featured_posts: list[Post]
    pages: list[Page]
    posts: list[Post]
    tocs: dict[str, list[TocEntry]]


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
        base_url = build_url(patterns["pages"], slug=page.slug)
        page.url = prefix_lang(base_url, page.lang, config.default_language)
    for post in posts:
        base_url = build_url(patterns["posts"], slug=post.slug)
        post.url = prefix_lang(base_url, post.lang, config.default_language)


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


def _site_view_for_lang(
    site_view: SiteView,
    lang_site_data: dict[str, _LangSiteData],
    lang: str,
    default_language: str,
) -> SiteView:
    
    data = lang_site_data.get(lang) or lang_site_data.get(default_language)
    if data is None:
        return site_view
    
    updates = {f.name: getattr(data, f.name) for f in fields(_LangSiteData)}
    if all(getattr(site_view, name) is value for name, value in updates.items()):
        return site_view
    return replace(site_view, **updates)


def _home_crumb(config: SiteConfig, lang: str) -> dict[str, str]:
    """First breadcrumb: the site's root *in the page's language* ("/" or
    "/en/"), so an English page doesn't send the reader to the default
    language's home. A language the site doesn't list gets the root."""
    langs = SiteLanguages.from_config(config)
    return {"title": config.title, "url": langs.root_path(lang if lang in langs.all else "")}


def _breadcrumbs_for_page(config: SiteConfig, page: Page) -> list[dict[str, str]]:
    crumbs = [_home_crumb(config, page.lang)]
    
    if page.translation_key != config.home_page:
        crumbs.append({"title": page.title, "url": page.url})
    return crumbs


def _ui_label(
    theme_strings: dict[str, dict[str, str]],
    config: SiteConfig,
    key: str,
    lang: str,
    fallback: str,
) -> str:
    """Translates a built-in UI label (breadcrumb/taxonomy names)"""
    return translate(
        theme_strings, key, lang or config.default_language,
        config.default_language, fallback=fallback,
    )


def _breadcrumbs_for_post(
    config: SiteConfig, post: Post, theme_strings: dict[str, dict[str, str]]
) -> list[dict[str, str]]:
    blog_url = prefix_lang(config.blog_index_url, post.lang, config.default_language)
    blog_label = _ui_label(theme_strings, config, "blog_menu_label", post.lang, "Blog")
    return [
        _home_crumb(config, post.lang),
        {"title": blog_label, "url": blog_url},
        {"title": post.title, "url": post.url},
    ]


def _base_context(
    config: SiteConfig,
    site_view: SiteView,
    theme_ns: dict,
    lang: str,
    canonical_path: str,
    breadcrumbs: list[dict[str, str]],
    *,
    og_type: str = "website",
    show_navigation: bool = False,
    **extra,
) -> dict:
    """The context EVERY template is rendered with, whatever its layout
    (page, post, blog, taxonomy, 404). Building them all here is what
    guarantees a theme can use any of these keys in a shared partial: the
    environment uses StrictUndefined, so a key missing from just one
    layout's context breaks the build only for that layout.

    `lang` is the language of the page being rendered (`page.lang` for a
    document, the language of the listing otherwise).
    """
    return {
        "site": site_view,
        "theme": theme_ns,
        "lang": lang or config.default_language,
        "canonical_path": canonical_path,
        "og_type": og_type,
        "show_navigation": show_navigation,
        "breadcrumbs": breadcrumbs,
        **extra,
    }


def _document_context(
    config: SiteConfig,
    site_view: SiteView,
    theme_ns: dict,
    doc: Document,
    breadcrumbs: list[dict[str, str]],
) -> dict:
    return _base_context(
        config, site_view, theme_ns, doc.lang, doc.url, breadcrumbs,
        og_type="article" if doc.kind == "post" else "website",
        # Both features are opt-in by the theme (see resolve_theme_feature);
        # the nav *data* still comes from `nav:` in site.yaml.
        show_navigation=bool(site_view.nav)
        and resolve_theme_feature(theme_ns, "navigation", doc.navigation_enabled),
        page=doc,
        post=doc,
        content=Markup(doc.content_html),
        show_toc=resolve_theme_feature(theme_ns, "toc", doc.toc_enabled),
    )


def _resolve_template_name(
    env, doc: Document, default_name: str, diagnostics: Diagnostics
) -> str:
    
    name = doc.template or default_name
    if name == default_name:
        return name
    try:
        env.get_template(name)
    except TemplateNotFound:
        diagnostics.error(
            f"template: '{name}' not found in the theme; using the default template "
            f"('{default_name}').",
            source=str(doc.source_path),
        )
        return default_name
    return name


def _feed_filename(config: SiteConfig) -> str:
    return "rss.xml" if config.data["feeds"].get("format", "rss") == "rss" else "atom.xml"


def _write_search_index(
    config: SiteConfig,
    documents: list[Document],
    filename: str,
) -> None:
    entries = [
        {
            "title": doc.title,
            "url": doc.url,
            "date": doc.date,
            "excerpt": doc.excerpt,
        }
        for doc in documents
    ]
    write_text_file(
        config.output_dir,
        filename,
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
    )


def _finalize_html(html: str, live_reload_script: str | None) -> str:
    """Injects the live reload script """

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
        if not dry_run:
            save_cache(project_root, cache_entries)  # keep the conversions already done
        return BuildResult(diagnostics, pages, posts, config.output_dir)

    link_translations(pages)
    link_translations(posts)
    _assign_urls(config, pages, posts)

    langs = SiteLanguages.from_config(config)
    # Everything a [[reference]] or a nav: entry can point to. Raw pages
    # have no language, so they're reachable by their exact id only.
    content_index = TranslationIndex(
        [*pages, *posts], config.default_language, extra_targets=raw_pages
    )
    resolve_references_for_all([*pages, *posts], content_index, diagnostics)

    if diagnostics.has_errors:
        if not dry_run:
            save_cache(project_root, cache_entries)  # keep the conversions already done
        return BuildResult(diagnostics, pages, posts, config.output_dir)

    _build_toc_for_all([*pages, *posts])
    _assign_prev_next(posts)

    # Menus and the home page only point to pages (not posts, not raw pages).
    page_index = TranslationIndex(pages, config.default_language)
    
    theme_ns = load_theme_config(config.theme_dir)
    
    if config.home_page != BLOG_KEY:
        if config.home_page not in menu_references(config.menu_config):
            diagnostics.warning(
                f"home_page: '{config.home_page}' is not referenced by any "
                "item in menu: in site.yaml. This may be intentional (e.g. "
                "the home page is reached via a logo or site title instead "
                "of a menu entry) — if it isn't, add it to menu: to keep "
                "them in sync.",
                source="site.yaml",
            )

    theme_strings = load_theme_i18n(config.theme_dir, config.i18n_string_overrides)

    menus_by_lang: dict[str, list[dict[str, str]]] = {
        lang: build_menu(
            config.menu_config, config.default_language, config.blog_index_url,
            page_index, lang, diagnostics, theme_strings,
        )
        for lang in config.languages
    }
    feed_url = f"/{_feed_filename(config)}" if config.feeds_enabled else None
    navs_by_lang: dict[str, list[NavEntry]] = {
        lang: build_nav(config.nav_config, content_index, diagnostics, lang=lang)
        for lang in config.languages
    }
    social_links = build_social_links(config.social_config, diagnostics)
   
    lang_site_data: dict[str, _LangSiteData] = {}
    for lang in config.languages:
        lang_pages_all = [p for p in pages if p.lang == lang]
        lang_posts_all = [p for p in posts if p.lang == lang]
        lang_posts_sorted = sorted(lang_posts_all, key=lambda p: p.sort_key(), reverse=True)

        lang_categories = collect_categories(lang_posts_all, config)
        lang_tags = collect_tags(lang_posts_all, config)
        if lang != config.default_language:
            for term in [*lang_categories, *lang_tags]:
                term.url = langs.prefix(term.url, lang)

        lang_site_data[lang] = _LangSiteData(
            menu=menus_by_lang[lang],
            nav=navs_by_lang[lang],
            categories=lang_categories,
            tags=lang_tags,
            featured_pages=[p for p in lang_pages_all if p.featured],
            featured_posts=[p for p in lang_posts_all if p.featured],
            pages=lang_pages_all,
            posts=lang_posts_sorted,
           
            tocs={
                doc.url: doc.toc
                for doc in [*lang_pages_all, *lang_posts_all]
                if doc.toc and resolve_theme_feature(theme_ns, "toc", doc.toc_enabled)
            },
        )

    default_lang_data = lang_site_data.get(config.default_language)
    site_view = make_site_view(
        config,
        feed_url=feed_url,
        menu=default_lang_data.menu if default_lang_data else [],
        nav=default_lang_data.nav if default_lang_data else [],
        social=social_links,
        categories=default_lang_data.categories if default_lang_data else [],
        tags=default_lang_data.tags if default_lang_data else [],
        featured_pages=default_lang_data.featured_pages if default_lang_data else [],
        featured_posts=default_lang_data.featured_posts if default_lang_data else [],
        pages=default_lang_data.pages if default_lang_data else [],
        posts=default_lang_data.posts if default_lang_data else [],
        tocs=default_lang_data.tocs if default_lang_data else {},
    )

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
    # Preenchido no laço por idioma abaixo, apenas quando `home_page:` no
    # site.yaml é 'blog': página 1 do índice do blog de cada idioma.
    blog_home_html: dict[str, str] = {}
    sitemap_entries: list[SitemapEntry] = []

    # -- pages --------------------------------------------------------------
    for page in pages:
        page_site_view = _site_view_for_lang(
            site_view, lang_site_data, page.lang, config.default_language,
        )
        context = _document_context(
            config, page_site_view, theme_ns, page, _breadcrumbs_for_page(config, page)
        )
        template_name = _resolve_template_name(env, page, "layouts/page.html", diagnostics)
        html = _finalize_html(render_template(env, template_name, context), live_reload_script)
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
        post_site_view = _site_view_for_lang(
            site_view, lang_site_data, post.lang, config.default_language,
        )
        context = _document_context(
            config, post_site_view, theme_ns, post,
            _breadcrumbs_for_post(config, post, theme_strings),
        )
        template_name = _resolve_template_name(env, post, "layouts/post.html", diagnostics)
        html = _finalize_html(render_template(env, template_name, context), live_reload_script)
        if not dry_run:
            write_page(config.output_dir, url_to_output_path(post.url), html)
            write_document_images(
                config.output_dir, post.images, subdir=url_to_output_dir(post.url)
            )
        sitemap_entries.append(SitemapEntry(path=post.url, lastmod=post.date))
    
    for lang in config.languages:
        lang_data = lang_site_data[lang]
        lang_site_view = _site_view_for_lang(
            site_view, lang_site_data, lang, config.default_language,
        )
      
        lang_posts_desc = lang_data.posts

        blog_index_url = langs.prefix(config.blog_index_url, lang)
        blog_label = _ui_label(theme_strings, config, "blog_menu_label", lang, "Blog")
        blog_pages = paginate(lang_posts_desc, config.posts_per_page, blog_index_url)
        for blog_page in blog_pages:
            html = _finalize_html(
                render_template(
                    env,
                    "layouts/blog.html",
                    _base_context(
                        config, lang_site_view, theme_ns, lang, blog_page.url,
                        [
                            _home_crumb(config, lang),
                            {"title": blog_label, "url": blog_index_url},
                        ],
                        posts=blog_page.items,
                        pagination=blog_page,
                    ),
                ),
                live_reload_script,
            )
            if not dry_run:
                write_page(config.output_dir, url_to_output_path(blog_page.url), html)
            sitemap_entries.append(SitemapEntry(path=blog_page.url))
            if blog_page.number == 1:
                blog_home_html[lang] = html

        tags_index_url = langs.prefix(config.data["urls"]["tags_index"], lang)
        categories_index_url = langs.prefix(config.data["urls"]["categories_index"], lang)
        
        lang_tags = lang_data.tags
        lang_categories = lang_data.categories

        sitemap_entries += _write_taxonomy(
            config, env, lang_site_view, theme_ns, lang_tags,
            kind_label=_ui_label(theme_strings, config, "tags_label", lang, "Tags"),
            index_url=tags_index_url, lang=lang,
            dry_run=dry_run, live_reload_script=live_reload_script,
        )
        sitemap_entries += _write_taxonomy(
            config, env, lang_site_view, theme_ns, lang_categories,
            kind_label=_ui_label(
                theme_strings, config, "categories_label", lang, "Categories"
            ),
            index_url=categories_index_url, lang=lang,
            dry_run=dry_run, live_reload_script=live_reload_script,
        )

        if config.feeds_enabled and not dry_run:
            feed_format = config.data["feeds"].get("format", "rss")
            feed_xml = (
                render_rss(config, lang_posts_desc)
                if feed_format == "rss"
                else render_atom(config, lang_posts_desc)
            )
            
            feed_filename = langs.localized_filename(_feed_filename(config), lang)
            write_text_file(config.output_dir, feed_filename, feed_xml)

        if config.search_enabled and not dry_run:
            _write_search_index(
                config,
                [*lang_data.pages, *lang_posts_desc],
                langs.localized_filename("search-index.json", lang),
            )

    
    is_blog_home = config.home_page == "blog"
    
    # {lang: page} for every version of the home page.
    home_pages_by_lang: dict[str, Page] = (
        {} if is_blog_home else page_index.versions(config.home_page)
    )

    for lang in config.languages:
        is_default_lang = langs.is_default(lang)
        root_path = langs.root_path(lang)

        if is_blog_home:
            home_html = blog_home_html.get(lang)
            extra_images: list = []
        else:
            home_page_for_lang = home_pages_by_lang.get(lang)
            home_html = home_candidates.get(home_page_for_lang.id) if home_page_for_lang else None
            extra_images = (
                home_candidate_images.get(home_page_for_lang.id, []) if home_page_for_lang else []
            )

        if home_html is None:
            
            if is_default_lang and (pages or posts):
                diagnostics.warning(
                    f"Home page '{config.home_page}' not found among the "
                    "generated pages or indexes (use a page ID, or 'blog' "
                    "to use the blog index); no root index.html was generated.",
                )
            continue

        if not dry_run:
            write_page(config.output_dir, url_to_output_path(root_path), home_html)
            
            if extra_images:
                write_document_images(
                    config.output_dir, extra_images, subdir=url_to_output_dir(root_path)
                )
        sitemap_entries.append(SitemapEntry(path=root_path))

    # -- page 404 --------------------------------------------------------------
    not_found_html = _finalize_html(
        render_template(
            env,
            "layouts/404.html",
            _base_context(
                config, site_view, theme_ns, config.default_language, "/404.html", [],
            ),
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
    lang: str = "",
    dry_run: bool = False,
    live_reload_script: str | None = None,
) -> list[SitemapEntry]:
    entries = [SitemapEntry(path=index_url)]

    index_html = _finalize_html(
        render_template(
            env,
            "layouts/taxonomy_index.html",
            _base_context(
                config, site_view, theme_ns, lang, index_url,
                [
                    _home_crumb(config, lang),
                    {"title": kind_label, "url": index_url},
                ],
                terms=terms,
                kind_label=kind_label,
            ),
        ),
        live_reload_script,
    )
    if not dry_run:
        write_page(config.output_dir, url_to_output_path(index_url), index_html)

    for term in terms:
        term_html = _finalize_html(
            render_template(
                env,
                "layouts/taxonomy_term.html",
                _base_context(
                    config, site_view, theme_ns, lang, term.url,
                    [
                        _home_crumb(config, lang),
                        {"title": kind_label, "url": index_url},
                        {"title": term.name, "url": term.url},
                    ],
                    term=term,
                    posts=term.posts,
                    kind_label=kind_label,
                ),
            ),
            live_reload_script,
        )
        if not dry_run:
            write_page(config.output_dir, url_to_output_path(term.url), term_html)
        entries.append(SitemapEntry(path=term.url))

    return entries
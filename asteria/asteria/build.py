"""
Build pipeline orchestration
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from markupsafe import Markup

from .cache import CachingConverter, load_cache, save_cache
from .config import SiteConfig, load_config
from .converter import get_converter
from .discovery import discover_content
from .document import Document, Page, Post
from .errors import AsteriaError, Diagnostics
from .feed import render_atom, render_rss
from .nav import NavEntry, build_nav
from .pagination import paginate
from .references import (
    build_registry,
    build_translation_registry,
    resolve_references_for_all,
    split_at_more_marker,
)
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
        base_url = build_url(patterns["pages"], slug=page.slug)
        page.url = prefix_lang(base_url, page.lang, config.default_language)
    for post in posts:
        base_url = build_url(patterns["posts"], slug=post.slug)
        post.url = prefix_lang(base_url, post.lang, config.default_language)


def _link_translations(documents: list[Document]) -> None:
    """Preenche `doc.translations` com as demais versões (em outros
    idiomas) de cada documento, agrupadas por `translation_key`. Chame
    separadamente para `pages` e `posts` — uma página e um post nunca
    devem ser considerados tradução um do outro, mesmo que, por
    coincidência, compartilhem a mesma translation_key."""
    groups: dict[str, list[Document]] = {}
    for doc in documents:
        groups.setdefault(doc.translation_key, []).append(doc)

    for group in groups.values():
        for doc in group:
            doc.translations = {d.lang: d for d in group if d is not doc}


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
    pages_by_translation_key: dict[str, dict[str, Page]],
    posts: list[Post],
    lang: str,
    diagnostics: Diagnostics,
) -> list[dict[str, str]]:
    """Builds the menu for a single language.

    `page:` in a menu entry is resolved as a translation_key first (e.g.
    "about" — the common case, matches any translated page sharing that
    translation_key, picking the version in `lang`, falling back to the
    site's default language, and finally to whatever translation happens
    to exist). If no translation_key matches, it's tried as an exact
    document id instead (e.g. "about.pt") — an escape hatch to pin one
    specific translation regardless of the current language, or to
    reference a document that has no translations at all.
    """
    # "blog" is the one reserved keyword that means "the blog index" in
    # `page:` (here) and `home_page:` (see run_build) — there's no
    # separate url_prefix-based alias anymore, since the blog's URL is
    # fully derived from `urls.posts` (see SiteConfig.blog_index_url).
    blog_keys = {"blog"}
    menu_items = []
    referenced_ids: set[str] = set()

    for entry in menu_config:
        page_id = entry.get("page")
        referenced_ids.add(page_id)
        title = entry.get("title", page_id)

        if page_id in blog_keys:
            url = prefix_lang(config.blog_index_url, lang, config.default_language)
        else:
            # translation_key is checked FIRST, exact id second — not the
            # other way around. A translated page's translation_key (e.g.
            # "sobre") is usually identical to the untranslated/default
            # document's own id, so checking id first would always match
            # the default-language page and never reach the translation
            # group. A dotted id used to pin one specific translation
            # (e.g. "sobre.pt") is never itself a valid translation_key,
            # so this order never breaks that escape hatch.
            page = None
            translations = pages_by_translation_key.get(page_id)
            if translations:
                page = (
                    translations.get(lang)
                    or translations.get(config.default_language)
                    or next(iter(translations.values()))
                )
            if page is None:
                page = pages_by_id.get(page_id)
            if page is None:
                diagnostics.warning(
                    f"menu: page '{page_id}' not found (checked both as an "
                    "exact page id and as a translation_key).",
                    # `menu:` now lives in site.yaml, not theme.yaml — see
                    # SiteConfig.menu_config.
                    source="site.yaml",
                )
                url = "#"
            else:
                url = page.url
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
            {
                "title": "Blog",
                "url": prefix_lang(config.blog_index_url, lang, config.default_language),
                "page_id": "blog",
            }
        )

    return menu_items


def _site_view_for_lang(
    site_view: SiteView,
    menus_by_lang: dict[str, list[dict[str, str]]],
    navs_by_lang: dict[str, list[NavEntry]],
    lang: str,
    default_language: str,
) -> SiteView:
    """Returns the SiteView to use for content in `lang`: a shallow copy
    of `site_view` with `menu` and `nav` swapped for the versions built
    for that language (falling back to the default language's version if
    `lang` has none of its own — e.g. a document whose language isn't
    listed in i18n.languages). Everything else (social, title, ...) stays
    shared, since only menu/nav are currently built per language.

    Mirrors what `_theme_ns_for_lang` used to do before `menu`/`nav`
    moved from `theme` to `site` — see templating.SiteView.

    Returns `site_view` itself, unmodified, when both already match the
    target — avoids a pointless copy for the common case (most documents
    are in the default language, which is what `site_view` is
    pre-populated with)."""
    menu = menus_by_lang.get(lang) or menus_by_lang.get(default_language, [])
    nav = navs_by_lang.get(lang) or navs_by_lang.get(default_language, [])
    if menu is site_view.menu and nav is site_view.nav:
        return site_view
    return replace(site_view, menu=menu, nav=nav)


def _breadcrumbs_for_page(config: SiteConfig, page: Page) -> list[dict[str, str]]:
    crumbs = [{"title": config.title, "url": "/"}]
    # Compara por translation_key (não por id): a versão traduzida da home
    # ("sobre.pt") tem um id diferente da página padrão ("sobre"), mas
    # ambas compartilham a mesma translation_key e são igualmente "a home"
    # em seu idioma.
    if page.translation_key != config.home_page:
        crumbs.append({"title": page.title, "url": page.url})
    return crumbs


def _breadcrumbs_for_post(config: SiteConfig, post: Post) -> list[dict[str, str]]:
    blog_url = prefix_lang(config.blog_index_url, post.lang, config.default_language)
    return [
        {"title": config.title, "url": "/"},
        {"title": "Blog", "url": blog_url},
        {"title": post.title, "url": post.url},
    ]


def _document_context(
    config: SiteConfig,
    site_view: SiteView,
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
        "show_navigation": bool(site_view.nav) and doc.navigation_enabled,
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

    print(config.theme_dir) 

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

    _link_translations(pages)
    _link_translations(posts)
    _assign_urls(config, pages, posts)
    resolve_references_for_all(
        [*pages, *posts], diagnostics, extra_targets=raw_pages,
        default_language=config.default_language,
    )

    if diagnostics.has_errors:
        return BuildResult(diagnostics, pages, posts, config.output_dir)

    _build_toc_for_all([*pages, *posts])
    _assign_prev_next(posts)

    pages_by_id = {p.id: p for p in pages}
    pages_by_translation_key: dict[str, dict[str, Page]] = {}
    for page in pages:
        pages_by_translation_key.setdefault(page.translation_key, {})[page.lang] = page

    # `nav`, `menu`, and `social` are read from site.yaml (SiteConfig), not
    # from theme.yaml: they reference this site's page/post ids and
    # accounts, which is site data — see the note on config.DEFAULTS and
    # SiteConfig.nav_config/menu_config/social_config. theme.yaml is only
    # merged with the site's `theme.params` override (theme-exclusive,
    # content-agnostic settings like colors or layout toggles) — see
    # theme_config.load_theme_config.
    theme_config_raw = load_theme_config(config.theme_dir, config.theme_params)
    menus_by_lang: dict[str, list[dict[str, str]]] = {
        lang: _build_menu(
            config.menu_config, config, pages_by_id,
            pages_by_translation_key, posts, lang, diagnostics,
        )
        for lang in config.languages
    }
    feed_url = f"/{_feed_filename(config)}" if config.feeds_enabled else None
    nav_registry = build_registry([*pages, *posts, *raw_pages])
    # Raw pages are excluded here (same as menus/[[references]]): they have
    # no lang/translation_key, so they're only reachable by their exact id.
    nav_translation_registry = build_translation_registry([*pages, *posts])
    navs_by_lang: dict[str, list[NavEntry]] = {
        lang: build_nav(
            config.nav_config, nav_registry, diagnostics,
            translation_registry=nav_translation_registry,
            lang=lang, default_language=config.default_language,
        )
        for lang in config.languages
    }
    social_links = build_social_links(config.social_config)

    theme_ns: dict = dict(theme_config_raw)
    # `menu`/`nav`/`social` no longer live here — they're on `site_view`
    # now (see templating.SiteView). `theme_ns` only carries genuinely
    # theme-exclusive, content-agnostic settings.
    theme_ns.setdefault("sidebar_toc", True)
    theme_ns.setdefault("default_variant", "light")

    # Default-language menu/nav; per-document/per-page renders below swap
    # these for the right language via `_site_view_for_lang`. `social`
    # isn't built per language, so it's set once here.
    site_view = make_site_view(
        config,
        feed_url=feed_url,
        menu=menus_by_lang.get(config.default_language, []),
        nav=navs_by_lang.get(config.default_language, []),
        social=social_links,
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
    # Preenchido no laço por idioma abaixo, apenas quando `home_page:` no
    # site.yaml é 'blog': página 1 do índice do blog de cada idioma.
    blog_home_html: dict[str, str] = {}
    sitemap_entries: list[SitemapEntry] = []

    # -- pages --------------------------------------------------------------
    for page in pages:
        page_site_view = _site_view_for_lang(site_view, menus_by_lang, navs_by_lang, page.lang, config.default_language)
        context = _document_context(
            config, page_site_view, theme_ns, page, _breadcrumbs_for_page(config, page)
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
        post_site_view = _site_view_for_lang(site_view, menus_by_lang, navs_by_lang, post.lang, config.default_language)
        context = _document_context(
            config, post_site_view, theme_ns, post, _breadcrumbs_for_post(config, post)
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
        lang_site_view = _site_view_for_lang(site_view, menus_by_lang, navs_by_lang, lang, config.default_language)
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
                        "site": lang_site_view,
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
            if blog_page.number == 1:
                blog_home_html[lang] = html

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
            config, env, lang_site_view, theme_ns, lang_tags,
            kind_label="Tags", index_url=tags_index_url,
            dry_run=dry_run, live_reload_script=live_reload_script,
        )
        sitemap_entries += _write_taxonomy(
            config, env, lang_site_view, theme_ns, lang_categories,
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

    # -- home page, por idioma: a home pode ser uma página (identificada
    # por config.home_page) ou o índice do blog ('blog'). Para o idioma
    # padrão a URL fica em "/", exatamente como antes; para os demais
    # idiomas (i18n.languages), em "/{lang}/", usando a home traduzida
    # correspondente — se ela existir. ---------------------------------
    is_blog_home = config.home_page == "blog"

    # Todas as versões (por idioma) da página escolhida como home,
    # indexadas pelo próprio idioma — vazio se a home for o blog, ou se
    # a página referenciada em `home_page:` não existir.
    home_pages_by_lang: dict[str, Page] = {}
    if not is_blog_home:
        home_page_default = pages_by_id.get(config.home_page)
        if home_page_default is not None:
            home_pages_by_lang[home_page_default.lang] = home_page_default
            home_pages_by_lang.update(home_page_default.translations)

    for lang in config.languages:
        is_default_lang = lang == config.default_language
        root_path = "/" if is_default_lang else f"/{lang}/"

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
            # Só avisamos para o idioma padrão: para os demais, a
            # ausência de uma home traduzida é esperada (nem toda página
            # precisa ter versão em todos os idiomas) e não é um erro.
            if is_default_lang and (pages or posts):
                diagnostics.warning(
                    f"Home page '{config.home_page}' not found among the "
                    "generated pages or indexes (use a page ID, or 'blog' "
                    "to use the blog index); no root index.html was generated.",
                )
            continue

        if not dry_run:
            write_page(config.output_dir, url_to_output_path(root_path), home_html)
            # A home duplicada precisa das suas imagens também na raiz (ou
            # em '/{lang}/'), já que o HTML usa caminhos relativos (a
            # imagem fica ao lado do index.html original, em sua própria
            # pasta, ex: /pages/sobre/foo.png).
            if extra_images:
                write_document_images(
                    config.output_dir, extra_images, subdir=url_to_output_dir(root_path)
                )
        sitemap_entries.append(SitemapEntry(path=root_path))

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
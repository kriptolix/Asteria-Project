"""Jinja2 template rendering."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from .config import SiteConfig
from .dates import format_date, validate_date_strings
from .i18n_strings import load_theme_i18n, translate
from .nav import NavEntry
from .urls import prefix_lang, slugify


@dataclass
class SiteView:
    """`site` object exposed to the templates."""

    title: str
    description: str
    url: str
    language: str
    blog_index_url: str
    feed_url: str | None = None
    # -- i18n -------------------------------------------------------------
    languages: list[str] = field(default_factory=list)
    default_language: str = ""    
    blog_index_urls: dict[str, str] = field(default_factory=dict)
   
    menu: list[dict[str, str]] = field(default_factory=list)
    nav: list[NavEntry] = field(default_factory=list)
    social: list[Any] = field(default_factory=list)    
    
    categories: list[Any] = field(default_factory=list)
    tags: list[Any] = field(default_factory=list)
   
    featured_pages: list[Any] = field(default_factory=list)
    featured_posts: list[Any] = field(default_factory=list)
 
    pages: list[Any] = field(default_factory=list)
    posts: list[Any] = field(default_factory=list)
 
    tocs: dict[str, Any] = field(default_factory=dict)


def make_site_view(
    config: SiteConfig,
    feed_url: str | None = None,
    menu: list[dict[str, str]] | None = None,
    nav: list[NavEntry] | None = None,
    social: list[Any] | None = None,
    categories: list[Any] | None = None,
    tags: list[Any] | None = None,
    featured_pages: list[Any] | None = None,
    featured_posts: list[Any] | None = None,
    pages: list[Any] | None = None,
    posts: list[Any] | None = None,
    tocs: dict[str, Any] | None = None,
) -> SiteView:
    return SiteView(
        title=config.title,
        description=config.description,
        url=config.url,
        language=config.language,
        blog_index_url=config.blog_index_url,
        feed_url=feed_url,
        languages=config.languages,
        default_language=config.default_language,
        blog_index_urls={
            lang: prefix_lang(config.blog_index_url, lang, config.default_language)
            for lang in config.languages
        },
        menu=menu or [],
        nav=nav or [],
        social=social or [],
        categories=categories or [],
        tags=tags or [],
        featured_pages=featured_pages or [],
        featured_posts=featured_posts or [],
        pages=pages or [],
        posts=posts or [],
        tocs=tocs or {},
    )


def create_environment(config: SiteConfig) -> Environment:
    theme_dir = config.theme_dir
    env = Environment(
        loader=FileSystemLoader(str(theme_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        # Content HTML is trustworthy only when it comes from the pipeline itself
        #, the auto-escaping above protects any other variable.
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    
    env.filters["safe_content"] = lambda value: Markup(value)
    env.filters["slug"] = slugify
    env.globals["nav_branch_active"] = _nav_branch_contains
    env.globals["menu_item_active"] = _menu_item_active
   
    theme_strings = load_theme_i18n(theme_dir, config.i18n_string_overrides)
    validate_date_strings(theme_strings)
    
    env.filters["format_date"] = lambda raw, lang="", style="long": format_date(
        theme_strings, config.default_language, raw, lang, style,
    )
    env.globals["t"] = lambda key, lang="", **kwargs: translate(
        theme_strings, key, lang or config.default_language,
        config.default_language, **kwargs,
    )
   
    env.globals["asset"] = lambda path: path

    env.globals["current_year"] = datetime.date.today().year
    return env


def apply_asset_manifest(env: Environment, manifest: dict[str, str]) -> None:
    """Connects the template `asset()` filter/global to
      the asset fingerprint manifest ({"/css/style.css": "/css/style.a1b2c3.css", ...}).   
    """

    def _asset(path: str) -> str:
        lookup = path if path.startswith("/") else f"/{path}"
        return manifest.get(lookup, path)

    env.globals["asset"] = _asset


def _nav_branch_contains(entry: Any, path: str) -> bool:
    
    if entry.url == path:
        return True

    for child in entry.children:
        if _nav_branch_contains(child, path):
            return True

    return False


def _menu_item_active(item: dict, path: str) -> bool:

    return item.get("url") == path


def render_template(env: Environment, template_name: str, context: dict[str, Any]) -> str:
    template = env.get_template(template_name)
    return template.render(**context)
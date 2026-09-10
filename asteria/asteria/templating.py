"""Jinja2 template rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from .config import SiteConfig
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


def make_site_view(
    config: SiteConfig,
    feed_url: str | None = None,
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
    # `content` (and other document fields that are already trusted HTML from
    # the pipeline) must be inserted without extra escaping: templates use
    # `{{ post.content }}` directly, so we mark it as safe here via a
    # dedicated filter instead of using a global autoescape=False.
    env.filters["safe_content"] = lambda value: Markup(value)
    env.filters["slug"] = slugify
    env.globals["nav_branch_active"] = _nav_branch_contains
    # Fallback identity: until `apply_asset_manifest` runs (after static
    # assets are copied and fingerprinted), `asset('/css/style.css')` just
    # returns the path unchanged. Templates can call it unconditionally.
    env.globals["asset"] = lambda path: path
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


def render_template(env: Environment, template_name: str, context: dict[str, Any]) -> str:
    template = env.get_template(template_name)
    return template.render(**context)

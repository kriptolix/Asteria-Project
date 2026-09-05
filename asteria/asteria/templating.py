"""Renderização de templates Jinja2 (spec seção 18-19)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from .config import SiteConfig
from .urls import slugify


@dataclass
class SiteView:
    """Objeto `site` exposto aos templates (spec 19) — namespace fixo das
    configurações do SSG (`site.yaml`). Menu, nav, links sociais e
    qualquer chave customizada de apresentação ficam no namespace `theme`
    (`theme/<nome>/theme.yaml`), não aqui — ver `asteria.theme_config`."""

    title: str
    description: str
    url: str
    language: str
    blog_index_url: str
    feed_url: str | None = None


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
    )


def create_environment(config: SiteConfig) -> Environment:
    theme_dir = config.theme_dir
    env = Environment(
        loader=FileSystemLoader(str(theme_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        # HTML de conteúdo é confiável apenas quando vem do próprio pipeline
        # (spec seção 27); o autoescape acima protege qualquer outra variável.
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # `content` (e outros campos de documento que já são HTML confiável do
    # pipeline) deve ser inserido sem escaping extra: os templates usam
    # `{{ post.content }}` diretamente, então marcamos como seguro aqui via
    # filtro dedicado em vez de autoescape=False global.
    env.filters["safe_content"] = lambda value: Markup(value)
    env.filters["slug"] = slugify
    env.globals["nav_branch_active"] = _nav_branch_contains
    return env


def _nav_branch_contains(entry: Any, path: str) -> bool:
    """True se `entry` ou algum descendente aponta para `path` — usado
    para expandir automaticamente o ramo do nav que contém a página atual
    (ver `themes/minimal/_nav.html`)."""
    if entry.url == path:
        return True
    return any(_nav_branch_contains(child, path) for child in entry.children)


def render_template(env: Environment, template_name: str, context: dict[str, Any]) -> str:
    template = env.get_template(template_name)
    return template.render(**context)

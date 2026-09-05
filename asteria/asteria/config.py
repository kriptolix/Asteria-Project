"""Leitura de `site.yaml` — configurações do SSG, estrutura fixa e sempre
presente, com defaults sensatos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .errors import AsteriaError

DEFAULTS: dict[str, Any] = {
    "site": {
        "title": "Meu Site",
        "description": "",
        "url": "http://localhost:8000",
        "language": "pt-BR",
        "home_page": "inicio",  # id da página usada como index.html
    },
    "content": {
        "pages": "content/pages",
        "posts": "content/posts",
    },
    "output": {
        "directory": "build",
    },
    "static": {
        "directory": "static",
    },
    "theme": {
        "name": "minimal",
        "directory": "theme",
    },
    "blog": {
        "posts_per_page": 10,
        "url_prefix": "blog",
    },
    "urls": {
        "pages": "/pages/{slug}/",
        "posts": "/blog/{slug}/",
        "tags": "/tags/{slug}/",
        "categories": "/categories/{slug}/",
        "tags_index": "/tags/",
        "categories_index": "/categories/",
    },
    "feeds": {
        "enabled": True,
        "format": "rss",  # rss | atom
    },
    "sitemap": {
        "enabled": True,
    },
    "robots": {
        "enabled": True,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@dataclass
class SiteConfig:
    """Configuração do site, já mesclada com os padrões."""

    data: dict[str, Any]
    root: Path

    # --- acessores convenientes -------------------------------------------------
    @property
    def title(self) -> str:
        return self.data["site"]["title"]

    @property
    def description(self) -> str:
        return self.data["site"]["description"]

    @property
    def url(self) -> str:
        return self.data["site"]["url"].rstrip("/")

    @property
    def language(self) -> str:
        return self.data["site"]["language"]

    @property
    def home_page(self) -> str:
        """Identificador da 'home': o `id` de uma página, ou a palavra
        especial 'blog' para usar a primeira página do índice do blog
        como conteúdo de `/`."""
        return self.data["site"].get("home_page", "inicio")

    @property
    def pages_dir(self) -> Path:
        return self.root / self.data["content"]["pages"]

    @property
    def posts_dir(self) -> Path:
        return self.root / self.data["content"]["posts"]

    @property
    def output_dir(self) -> Path:
        return self.root / self.data["output"]["directory"]

    @property
    def static_dir(self) -> Path:
        return self.root / self.data["static"]["directory"]

    @property
    def theme_name(self) -> str:
        return self.data["theme"]["name"]

    @property
    def theme_dir(self) -> Path:
        """Diretório efetivo do tema a usar.

        Se o projeto tiver sua própria pasta `theme/<nome>/`, ela é usada
        (permite customizar/sobrescrever completamente). Caso contrário,
        cai para o tema mínimo embutido no pacote Asteria
        (`asteria/themes/<nome>/`), que serve como tema padrão pronto para
        uso sem exigir que todo projeto crie o seu.
        """
        project_theme = self.root / self.data["theme"]["directory"] / self.theme_name
        if project_theme.exists():
            return project_theme

        bundled_theme = Path(__file__).parent / "themes" / self.theme_name
        return bundled_theme

    @property
    def theme_source(self) -> str:
        """'project' ou 'bundled' — útil para diagnósticos/CLI."""
        project_theme = self.root / self.data["theme"]["directory"] / self.theme_name
        return "project" if project_theme.exists() else "bundled"

    @property
    def posts_per_page(self) -> int:
        return int(self.data["blog"]["posts_per_page"])

    @property
    def blog_prefix(self) -> str:
        return self.data["blog"].get("url_prefix", "blog")

    @property
    def blog_index_url(self) -> str:
        return f"/{self.blog_prefix.strip('/')}/"

    @property
    def url_patterns(self) -> dict[str, str]:
        return self.data["urls"]

    @property
    def feeds_enabled(self) -> bool:
        return bool(self.data["feeds"].get("enabled", True))

    @property
    def sitemap_enabled(self) -> bool:
        return bool(self.data["sitemap"].get("enabled", True))

    @property
    def robots_enabled(self) -> bool:
        return bool(self.data["robots"].get("enabled", True))


def load_config(config_path: Path) -> SiteConfig:
    if not config_path.exists():
        raise AsteriaError(f"Arquivo de configuração não encontrado: {config_path}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise AsteriaError(f"YAML inválido em {config_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise AsteriaError(f"O conteúdo de {config_path} deve ser um mapeamento YAML.")

    merged = _deep_merge(DEFAULTS, raw)
    return SiteConfig(data=merged, root=config_path.parent.resolve())

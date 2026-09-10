"""
Reads SSG configurations from `site.yaml` and merges them with the defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import AsteriaError

DEFAULTS: dict[str, Any] = {
    "site": {
        "title": "My Site",
        "description": "",
        "url": "http://localhost:8000",
        "language": "en",
        "home_page": "welcome",  # id da página usada como index.html
    },
    "content": {
        "pages": "content/pages",
        "posts": "content/posts",
    },
    "output": {
        "directory": "../result",
    },
    "static": {
        "directory": "static",
    },
    "theme": {
        "name": "minimal",
        "directory": "themes",
    },
    "blog": {
        "posts_per_page": 10,
        "url_prefix": "blog",
        "excerpt_enabled": True,
        "excerpt_length": 280,
    },
    "i18n": {        
        "languages": [],        
        "default_language": "en",
    },
    "assets": {        
        "fingerprint": True,
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
    """Site configuration, already merged with the standards."""

    data: dict[str, Any]
    root: Path
    
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
        """
        Home identifier: the `id` of a page, or the word 
        special 'blog'
        """
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
        
        project_theme = self.root / "themes" / self.theme_name        

        if project_theme.exists():
            return project_theme

        bundled_theme = Path(__file__).parent / "site" / "source" / "themes" / "minimal"
        return bundled_theme

    @property
    def theme_source(self) -> str:
        """'project' ou 'bundled' — useful for diagnostics/CLI."""

        project_theme = self.root / self.data["themes"]["directory"] / self.theme_name
        return "project" if project_theme.exists() else "bundled"

    @property
    def posts_per_page(self) -> int:
        return int(self.data["blog"]["posts_per_page"])

    @property
    def excerpt_enabled(self) -> bool:
        return self.data["blog"]["excerpt_enabled"]

    @property
    def excerpt_length(self) -> int:
        return int(self.data["blog"]["excerpt_length"])

    @property
    def default_language(self) -> str:
        
        return self.data["i18n"].get("default_language") or self.language

    @property
    def languages(self) -> list[str]:
        """All languages ​​supported by the site, including the default."""

        default = self.default_language
        extra = [lang for lang in (self.data["i18n"].get("languages") or []) if lang != default]
        return [default, *extra]

    @property
    def fingerprint_assets_enabled(self) -> bool:
        return bool(self.data.get("assets", {}).get("fingerprint", True))

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
        raise AsteriaError(f"Configuration file not found: {config_path}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise AsteriaError(f"Invalid YAML in {config_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise AsteriaError(f"The content of {config_path} must be a YAML mapping.")

    merged = _deep_merge(DEFAULTS, raw)
    return SiteConfig(data=merged, root=config_path.parent.resolve())

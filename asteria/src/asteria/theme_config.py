"""
Theme-specific settings
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .config import SiteConfig
from .errors import AsteriaError


def load_theme_config(theme_dir: Path) -> dict[str, Any]:
    """Reads `theme.yaml` from `theme_dir`. Returns {} if the file is absent.

    This is the only source of theme options: there is no site-level
    override layer. A theme opts in to optional features (`toc`,
    `navigation`) by declaring them here.
    """
    path = theme_dir / "theme.yaml"
    if not path.exists():
        return {}

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise AsteriaError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise AsteriaError(f"The content of {path} must be a YAML mapping.")
    return data


@dataclass
class ThemeConfig:
    """What the active theme's own `theme.yaml` contains.

    `data` is simply the file's key/value pairs; nothing is assumed about
    which keys exist, since each theme declares its own options.
    """

    name: str
    source: str  # "project" or "bundled" (see SiteConfig.theme_source)
    directory: Path
    data: dict[str, Any] = field(default_factory=dict)


def theme_config_from_site(config: SiteConfig) -> ThemeConfig:
    """Builds the ThemeConfig for the theme selected by `config`."""
    theme_dir = config.theme_dir
    return ThemeConfig(
        name=config.theme_name,
        source=config.theme_source,
        directory=theme_dir,
        data=load_theme_config(theme_dir),
    )

def resolve_theme_feature(
    theme_data: dict[str, Any], name: str, document_value: bool | None
) -> bool:
    """Decides whether an optional theme feature (e.g. "toc", "navigation")
    is on for one document.

    - The theme opts in by declaring `name` in its `theme.yaml`; a missing
      or null key means the theme does not support the feature, so it is
      off whatever the document says.
    - The declared value is the global switch.
    - A document can override that switch (`document_value` is not None).
      `None` means "inherit the global switch".
    """
    global_value = theme_data.get(name)
    if global_value is None:
        return False
    if document_value is not None:
        return bool(document_value)
    return bool(global_value)
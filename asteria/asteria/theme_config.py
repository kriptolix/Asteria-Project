"""
Theme-specific settings
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .errors import AsteriaError


def load_theme_config(theme_dir: Path) -> dict[str, Any]:
    
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

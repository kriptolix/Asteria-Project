"""
Public, frontend-agnostic API for Asteria.

`cli.py` is a thin wrapper around this module. Any other frontend 
(a GTK4 app, a script, a test) should
import straight from here instead of going through the CLI or shelling
out to `asteria ...` as a subprocess.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .build import BuildResult, run_build
from .cache import clear_cache
from .config import SiteConfig, load_config
from .config import reset_theme as _reset_bundled_theme
from .errors import AsteriaError
from .scaffold import create_project
from .server import (
    DevServer,
    DevServerStatus,
    discover_watch_paths,
    watch_backend_available,
)
from .writer import clean_output

__all__ = [
    "AsteriaError",
    "BuildResult",
    "SiteConfig",
    "CleanResult",
    "DevServer",
    "DevServerStatus",
    "build_project",
    "check_project",
    "clean_project",
    "clear_project_cache",
    "create_new_project",
    "discover_watch_paths",
    "load_project_config",
    "reset_project_theme",
    "watch_backend_available",
]


def load_project_config(project_root: Path, config_filename: str = "site.yaml") -> SiteConfig:
    """Loads and returns a project's parsed `site.yaml` (merged with the
    built-in defaults). Raises AsteriaError if the file is missing or not valid YAML.
    """
    return load_config(project_root / "source" / config_filename)


def build_project(
    project_root: Path,
    converter_name: str = "odt2web",
    config_filename: str = "site.yaml",
) -> BuildResult:
    """Runs a full build and writes the output to disk.   
    """
    return run_build(project_root, config_filename=config_filename, converter_name=converter_name)


def check_project(
    project_root: Path,
    converter_name: str = "auto",
    config_filename: str = "site.yaml",
) -> BuildResult:
    """Validates the project (YAML, ODT files, ids, references) without
    writing anything to disk.
    """
    return run_build(
        project_root,
        config_filename=config_filename,
        converter_name=converter_name,
        dry_run=True,
    )


@dataclass
class CleanResult:
    """What `clean_project` actually did, so a UI can report it without
    re-deriving it from a SiteConfig itself."""

    output_dir: Path
    output_removed: bool
    cache_removed: bool


def clean_project(
    project_root: Path,
    remove_cache: bool = False,
    config_filename: str = "site.yaml",
) -> CleanResult:
    """Removes the generated site (`config.output_dir`) and, optionally,
    the incremental conversion cache.
    """
    config = load_config(project_root / "source" / config_filename)
    output_removed = config.output_dir.exists()
    clean_output(config)
    cache_removed = remove_cache and clear_cache(project_root)
    return CleanResult(
        output_dir=config.output_dir,
        output_removed=output_removed,
        cache_removed=cache_removed,
    )


def clear_project_cache(project_root: Path) -> bool:
    
    return clear_cache(project_root)


def create_new_project(target_dir: Path) -> list[str]:
    
    return create_project(target_dir)


def reset_project_theme(project_root: Path) -> Path:
    """Overwrites `source/themes/minimal` with Asteria's bundled
    'minimal' theme, discarding any local edits to it.
    """
    return _reset_bundled_theme(project_root)
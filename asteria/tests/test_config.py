from pathlib import Path

import pytest

from asteria.config import load_config
from asteria.errors import AsteriaError


def test_load_config_applies_defaults(tmp_path: Path):
    (tmp_path / "site.yaml").write_text(
        "site:\n  title: Teste\n", encoding="utf-8"
    )
    config = load_config(tmp_path / "site.yaml")
    assert config.title == "Teste"
    assert config.language == "pt-BR"  # default
    assert config.output_dir == tmp_path / "build"


def test_load_config_missing_file_raises(tmp_path: Path):
    with pytest.raises(AsteriaError):
        load_config(tmp_path / "nao-existe.yaml")


def test_load_config_invalid_yaml_raises(tmp_path: Path):
    (tmp_path / "site.yaml").write_text("site: [unclosed", encoding="utf-8")
    with pytest.raises(AsteriaError):
        load_config(tmp_path / "site.yaml")


def test_theme_name_defaults_to_minimal(tmp_path: Path):
    (tmp_path / "site.yaml").write_text("site:\n  title: Teste\n", encoding="utf-8")
    config = load_config(tmp_path / "site.yaml")
    assert config.theme_name == "minimal"


def test_site_yaml_has_no_theme_presentation_properties(tmp_path: Path):
    """menu/nav/social/sidebar_toc/default_variant não existem mais em
    SiteConfig — migraram pro namespace do tema (theme.yaml)."""
    (tmp_path / "site.yaml").write_text("site:\n  title: Teste\n", encoding="utf-8")
    config = load_config(tmp_path / "site.yaml")
    for attr in ("menu", "nav", "social", "sidebar_toc", "theme_default_variant", "extra"):
        assert not hasattr(config, attr), f"SiteConfig não deveria ter '{attr}'"

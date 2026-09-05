from pathlib import Path

import pytest

from asteria.errors import AsteriaError
from asteria.theme_config import load_theme_config


def test_load_theme_config_missing_file_returns_empty_dict(tmp_path: Path):
    assert load_theme_config(tmp_path) == {}


def test_load_theme_config_reads_arbitrary_keys(tmp_path: Path):
    (tmp_path / "theme.yaml").write_text(
        "sidebar_toc: false\nsubtitulo: Um blog\nnumero: 42\n", encoding="utf-8"
    )
    data = load_theme_config(tmp_path)
    assert data == {"sidebar_toc": False, "subtitulo": "Um blog", "numero": 42}


def test_load_theme_config_invalid_yaml_raises(tmp_path: Path):
    (tmp_path / "theme.yaml").write_text("chave: [nao fechado", encoding="utf-8")
    with pytest.raises(AsteriaError):
        load_theme_config(tmp_path)


def test_load_theme_config_non_mapping_raises(tmp_path: Path):
    (tmp_path / "theme.yaml").write_text("- item1\n- item2\n", encoding="utf-8")
    with pytest.raises(AsteriaError):
        load_theme_config(tmp_path)

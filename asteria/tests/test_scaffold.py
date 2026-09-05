from pathlib import Path

import pytest

from asteria.build import run_build
from asteria.errors import AsteriaError
from asteria.scaffold import create_project


def test_create_project_generates_expected_structure(tmp_path: Path):
    target = tmp_path / "meu-site"
    created = create_project(target, title="Site de Teste")

    assert (target / "site.yaml").exists()
    assert (target / ".gitignore").exists()
    assert (target / "content" / "pages").is_dir()
    assert (target / "content" / "posts").is_dir()
    assert (target / "static").is_dir()
    assert (target / "content" / "pages" / "bem-vindo.odt").exists()
    assert (target / "theme" / "minimal" / "base.html").exists()
    assert (target / "theme" / "minimal" / "css" / "light.css").exists()

    assert "site.yaml" in created
    assert "content/pages/bem-vindo.odt" in created


def test_create_project_site_yaml_uses_given_title(tmp_path: Path):
    target = tmp_path / "meu-site"
    create_project(target, title="Título Customizado")
    content = (target / "site.yaml").read_text(encoding="utf-8")
    assert "Título Customizado" in content


def test_create_project_refuses_existing_nonempty_dir(tmp_path: Path):
    target = tmp_path / "ocupado"
    target.mkdir()
    (target / "arquivo.txt").write_text("x", encoding="utf-8")

    with pytest.raises(AsteriaError):
        create_project(target)


def test_create_project_allows_existing_empty_dir(tmp_path: Path):
    target = tmp_path / "vazio"
    target.mkdir()
    create_project(target)
    assert (target / "site.yaml").exists()


def test_scaffolded_project_builds_successfully(tmp_path: Path):
    target = tmp_path / "meu-site"
    create_project(target, title="Site de Teste")

    result = run_build(target, converter_name="fallback")

    assert result.success
    assert len(result.pages) == 1
    home_html = (result.output_dir / "index.html").read_text(encoding="utf-8")
    assert "Bem-vindo ao Asteria" in home_html
    # A sintaxe de exemplo escapada (\[[id]]) deve aparecer literal, não
    # como um link/erro de referência quebrada.
    assert "[[id]]" in home_html
    assert "broken-reference" not in home_html

from pathlib import Path

from asteria.config import load_config
from asteria.converter import FallbackConverter
from asteria.discovery import discover_content
from asteria.errors import Diagnostics
from asteria.raw import load_raw_page

from .odt_factory import frontmatter_block, h, make_odt, p


def _config(tmp_path: Path):
    (tmp_path / "site.yaml").write_text("site:\n  title: T\n", encoding="utf-8")
    return load_config(tmp_path / "site.yaml")


def test_load_raw_page_reads_optional_meta(tmp_path: Path):
    raw_dir = tmp_path / "ficha"
    raw_dir.mkdir()
    (raw_dir / "index.html").write_text("<p>ficha</p>", encoding="utf-8")
    (raw_dir / "raw.yaml").write_text("title: Minha Ficha\nheight: 500\n", encoding="utf-8")

    diagnostics = Diagnostics()
    page = load_raw_page(raw_dir, "/pages/{slug}/", diagnostics)

    assert page.id == "ficha"
    assert page.title == "Minha Ficha"
    assert page.height == 500
    assert page.url == "/pages/ficha/"
    assert not diagnostics.has_errors


def test_load_raw_page_defaults_without_raw_yaml(tmp_path: Path):
    raw_dir = tmp_path / "simples"
    raw_dir.mkdir()
    (raw_dir / "index.html").write_text("<p>x</p>", encoding="utf-8")

    diagnostics = Diagnostics()
    page = load_raw_page(raw_dir, "/pages/{slug}/", diagnostics)

    assert page.title == "simples"
    assert page.height == 600


def test_discover_content_finds_raw_page_inside_pages_dir(tmp_path: Path):
    make_odt(
        tmp_path / "content/pages/sobre.odt",
        frontmatter_block({"title": "Sobre"}) + p("x"),
    )
    raw_dir = tmp_path / "content/pages/ficha"
    raw_dir.mkdir(parents=True)
    (raw_dir / "index.html").write_text("<p>ficha</p>", encoding="utf-8")

    config = _config(tmp_path)
    diagnostics = Diagnostics()
    pages, posts, raw_pages = discover_content(config, FallbackConverter(), diagnostics)

    assert [p.id for p in pages] == ["sobre"]
    assert [rp.id for rp in raw_pages] == ["ficha"]
    assert raw_pages[0].url == "/pages/ficha/"
    assert not diagnostics.has_errors


def test_discover_content_finds_raw_page_inside_posts_dir(tmp_path: Path):
    raw_dir = tmp_path / "content/posts/landing"
    raw_dir.mkdir(parents=True)
    (raw_dir / "index.html").write_text("<p>landing</p>", encoding="utf-8")

    config = _config(tmp_path)
    diagnostics = Diagnostics()
    pages, posts, raw_pages = discover_content(config, FallbackConverter(), diagnostics)

    assert [rp.id for rp in raw_pages] == ["landing"]
    assert raw_pages[0].url == "/blog/landing/"  # usa o padrão de urls.posts


def test_discover_content_pages_dir_is_recursive_for_organization(tmp_path: Path):
    make_odt(
        tmp_path / "content/pages/guia/instalacao.odt",
        frontmatter_block({"title": "Instalação"}) + h("Instalação", 1) + p("x"),
    )
    make_odt(
        tmp_path / "content/pages/guia/config/avancado.odt",
        frontmatter_block({"title": "Avançado"}) + h("Avançado", 1) + p("y"),
    )

    config = _config(tmp_path)
    diagnostics = Diagnostics()
    pages, posts, raw_pages = discover_content(config, FallbackConverter(), diagnostics)

    ids = sorted(p.id for p in pages)
    assert ids == ["avancado", "instalacao"]
    assert not diagnostics.has_errors


def test_discover_content_posts_dir_is_not_recursive_for_odt(tmp_path: Path):
    make_odt(
        tmp_path / "content/posts/serie/parte1.odt",
        frontmatter_block({"title": "Parte 1", "date": "2026-01-01"}) + p("x"),
    )

    config = _config(tmp_path)
    diagnostics = Diagnostics()
    pages, posts, raw_pages = discover_content(config, FallbackConverter(), diagnostics)

    # .odt dentro de subpasta de posts/ não é descoberto (posts não é
    # recursivo), e a subpasta não tem index.html, então gera warning.
    assert posts == []
    assert raw_pages == []
    assert any("posts" in w.message for w in diagnostics.warnings)


def test_discover_content_raw_id_colliding_with_page_id_errors(tmp_path: Path):
    make_odt(
        tmp_path / "content/pages/sobre.odt",
        frontmatter_block({"title": "Sobre"}) + p("x"),
    )
    raw_dir = tmp_path / "content/pages/sobre"  # mesmo id
    raw_dir.mkdir(parents=True)
    (raw_dir / "index.html").write_text("<p>conflito</p>", encoding="utf-8")

    config = _config(tmp_path)
    diagnostics = Diagnostics()
    discover_content(config, FallbackConverter(), diagnostics)

    assert diagnostics.has_errors
    assert any("ID duplicado" in e.message for e in diagnostics.errors)

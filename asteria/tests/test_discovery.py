from pathlib import Path

from asteria.config import load_config
from asteria.converter import FallbackConverter
from asteria.discovery import discover_content
from asteria.errors import Diagnostics

from .odt_factory import frontmatter_block, h, make_odt, p


def _make_project(tmp_path: Path) -> Path:
    (tmp_path / "site.yaml").write_text("site:\n  title: T\n", encoding="utf-8")
    make_odt(
        tmp_path / "content/pages/sobre.odt",
        frontmatter_block({"title": "Sobre"}) + h("Sobre", 1) + p("Texto."),
    )
    make_odt(
        tmp_path / "content/posts/artigo.odt",
        frontmatter_block({"title": "Artigo", "date": "2026-01-01"})
        + h("Intro", 2)
        + p("Conteúdo."),
    )
    return tmp_path


def test_discover_content_basic(tmp_path: Path):
    root = _make_project(tmp_path)
    config = load_config(root / "site.yaml")
    diagnostics = Diagnostics()
    pages, posts, raw_pages = discover_content(config, FallbackConverter(), diagnostics)

    assert not diagnostics.has_errors
    assert [p.id for p in pages] == ["sobre"]
    assert [p.id for p in posts] == ["artigo"]
    assert pages[0].title == "Sobre"
    assert posts[0].date == "2026-01-01"
    assert raw_pages == []


def test_discover_content_duplicate_id_errors(tmp_path: Path):
    (tmp_path / "site.yaml").write_text("site:\n  title: T\n", encoding="utf-8")
    make_odt(
        tmp_path / "content/pages/sobre.odt",
        frontmatter_block({"title": "Sobre A"}) + p("x"),
    )
    make_odt(
        tmp_path / "content/posts/sobre.odt",
        frontmatter_block({"title": "Sobre B", "date": "2026-01-01"}) + p("y"),
    )
    config = load_config(tmp_path / "site.yaml")
    diagnostics = Diagnostics()
    discover_content(config, FallbackConverter(), diagnostics)

    assert diagnostics.has_errors
    assert any("ID duplicado" in e.message for e in diagnostics.errors)

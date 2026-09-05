from asteria.errors import Diagnostics
from asteria.frontmatter import extract_frontmatter


def test_extract_frontmatter_basic():
    html = (
        '<div class="ssg-frontmatter" data-ssg="frontmatter">'
        '<meta data-key="title" content="Meu artigo">'
        '<meta data-key="tags" content="Python, Web">'
        "</div>"
        "<h1>Meu artigo</h1><p>Conteúdo</p>"
    )
    diagnostics = Diagnostics()
    fm, remaining = extract_frontmatter(html, "teste.odt", diagnostics)

    assert fm.title == "Meu artigo"
    assert fm.tags == ["Python", "Web"]
    assert "ssg-frontmatter" not in remaining
    assert "<h1>Meu artigo</h1>" in remaining
    assert not diagnostics.has_errors


def test_extract_frontmatter_unknown_field_warns():
    html = (
        '<div class="ssg-frontmatter" data-ssg="frontmatter">'
        '<meta data-key="title" content="X">'
        '<meta data-key="campo_novo" content="valor">'
        "</div><p>x</p>"
    )
    diagnostics = Diagnostics()
    fm, _ = extract_frontmatter(html, "teste.odt", diagnostics)
    assert fm.extra == {"campo_novo": "valor"}
    assert any("desconhecido" in w.message for w in diagnostics.warnings)


def test_extract_frontmatter_absent_returns_empty():
    html = "<h1>Sem frontmatter</h1>"
    diagnostics = Diagnostics()
    fm, remaining = extract_frontmatter(html, "teste.odt", diagnostics)
    assert fm.title is None
    assert remaining == html


def test_extract_frontmatter_toc_and_navigation_defaults():
    html = (
        '<div class="ssg-frontmatter" data-ssg="frontmatter">'
        '<meta data-key="title" content="X">'
        "</div><p>x</p>"
    )
    diagnostics = Diagnostics()
    fm, _ = extract_frontmatter(html, "teste.odt", diagnostics)
    assert fm.toc is True  # ativo por padrão
    assert fm.navigation is False  # desativado por padrão


def test_extract_frontmatter_toc_false_disables():
    html = (
        '<div class="ssg-frontmatter" data-ssg="frontmatter">'
        '<meta data-key="title" content="X">'
        '<meta data-key="toc" content="false">'
        "</div><p>x</p>"
    )
    diagnostics = Diagnostics()
    fm, _ = extract_frontmatter(html, "teste.odt", diagnostics)
    assert fm.toc is False



def test_extract_frontmatter_variant_field():
    html = (
        '<div class="ssg-frontmatter" data-ssg="frontmatter">'
        '<meta data-key="title" content="X">'
        '<meta data-key="variant" content="dark">'
        "</div><p>x</p>"
    )
    diagnostics = Diagnostics()
    fm, _ = extract_frontmatter(html, "teste.odt", diagnostics)
    assert fm.variant == "dark"


def test_extract_frontmatter_variant_absent_is_none():
    html = (
        '<div class="ssg-frontmatter" data-ssg="frontmatter">'
        '<meta data-key="title" content="X">'
        "</div><p>x</p>"
    )
    diagnostics = Diagnostics()
    fm, _ = extract_frontmatter(html, "teste.odt", diagnostics)
    assert fm.variant is None

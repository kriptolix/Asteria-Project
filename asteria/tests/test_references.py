from pathlib import Path

from asteria.document import Page
from asteria.errors import Diagnostics
from asteria.frontmatter import Frontmatter
from asteria.references import resolve_references, resolve_references_for_all


def _doc(doc_id: str, title: str, url: str) -> Page:
    return Page(
        id=doc_id,
        kind="page",
        source_path=Path(f"{doc_id}.odt"),
        frontmatter=Frontmatter(title=title),
        content_html="",
        raw_content_html="",
        url=url,
    )


def test_resolve_reference_uses_title_as_default_text():
    sobre = _doc("sobre", "Sobre nós", "/sobre/")
    registry = {"sobre": sobre}
    diagnostics = Diagnostics()

    html = resolve_references("<p>Veja [[sobre]].</p>", registry, "x.odt", diagnostics)

    assert '<a href="/sobre/">Sobre nós</a>' in html
    assert not diagnostics.has_errors


def test_resolve_reference_with_custom_label():
    sobre = _doc("sobre", "Sobre nós", "/sobre/")
    registry = {"sobre": sobre}
    diagnostics = Diagnostics()

    html = resolve_references(
        "<p>[[sobre|saiba mais]]</p>", registry, "x.odt", diagnostics
    )

    assert '<a href="/sobre/">saiba mais</a>' in html


def test_resolve_reference_to_missing_document_errors():
    diagnostics = Diagnostics()
    html = resolve_references("<p>[[nao-existe]]</p>", {}, "x.odt", diagnostics)

    assert diagnostics.has_errors
    assert "nao-existe" in diagnostics.errors[0].message
    assert "broken-reference" in html


def test_resolve_references_for_all_updates_content_in_place():
    a = _doc("a", "Página A", "/a/")
    b = _doc("b", "Página B", "/b/")
    a.content_html = "<p>Veja [[b]].</p>"
    diagnostics = Diagnostics()

    resolve_references_for_all([a, b], diagnostics)

    assert '<a href="/b/">Página B</a>' in a.content_html


class _FakeRawPage:
    def __init__(self, id_, url, title, height=600):
        self.id = id_
        self.url = url
        self.title = title
        self.height = height


def test_resolve_embed_reference_creates_iframe():
    raw_page = _FakeRawPage("ficha", "/raw/ficha/", "Minha Ficha", height=500)
    registry = {"ficha": raw_page}
    diagnostics = Diagnostics()

    html = resolve_references("<p>[[embed:ficha]]</p>", registry, "x.odt", diagnostics)

    assert '<iframe src="/raw/ficha/"' in html
    assert 'title="Minha Ficha"' in html
    assert "height:500px" in html
    assert not diagnostics.has_errors


def test_resolve_embed_reference_with_height_override():
    raw_page = _FakeRawPage("ficha", "/raw/ficha/", "Minha Ficha", height=500)
    registry = {"ficha": raw_page}
    diagnostics = Diagnostics()

    html = resolve_references(
        "<p>[[embed:ficha|900]]</p>", registry, "x.odt", diagnostics
    )

    assert "height:900px" in html


def test_resolve_embed_reference_missing_target_errors():
    diagnostics = Diagnostics()
    html = resolve_references("<p>[[embed:nao-existe]]</p>", {}, "x.odt", diagnostics)

    assert diagnostics.has_errors
    assert "broken-reference" in html


def test_resolve_references_for_all_accepts_extra_targets():
    a = _doc("a", "Página A", "/a/")
    raw_page = _FakeRawPage("ficha", "/raw/ficha/", "Minha Ficha")
    a.content_html = "<p>[[embed:ficha]]</p>"
    diagnostics = Diagnostics()

    resolve_references_for_all([a], diagnostics, extra_targets=[raw_page])

    assert "<iframe" in a.content_html
    assert not diagnostics.has_errors


def test_escaped_reference_renders_literally_without_resolving():
    diagnostics = Diagnostics()
    html = resolve_references("<p>Digite \\[[sobre]] no texto.</p>", {}, "x.odt", diagnostics)

    assert "[[sobre]]" in html
    assert "<a href" not in html
    assert not diagnostics.has_errors  # não deveria tentar resolver, então sem erro


def test_escaped_embed_reference_renders_literally():
    diagnostics = Diagnostics()
    html = resolve_references(
        "<p>Use \\[[embed:ficha|500]] assim.</p>", {}, "x.odt", diagnostics
    )

    assert "[[embed:ficha|500]]" in html
    assert "<iframe" not in html
    assert not diagnostics.has_errors


def test_escaped_reference_does_not_affect_real_references_nearby():
    a = _doc("a", "Página A", "/a/")
    b = _doc("b", "Página B", "/b/")
    registry = {"a": a, "b": b}
    diagnostics = Diagnostics()

    html = resolve_references(
        "<p>Escreva \\[[b]] para linkar, tipo [[b]].</p>", registry, "x.odt", diagnostics
    )

    assert "[[b]]" in html  # o texto literal, escapado
    assert '<a href="/b/">Página B</a>' in html  # a referência real, resolvida

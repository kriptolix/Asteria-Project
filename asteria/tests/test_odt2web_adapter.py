"""Testa o adapter Odt2WebConverter sem depender da lib real instalada,
usando um módulo `odt2web` falso injetado em sys.modules.

Confirmado pelo usuário testando a lib real: o odt2web materializa o front
matter como o bloco HTML padronizado (`div.ssg-frontmatter`) dentro do
próprio `result.html`, não como um objeto `result.metadata` separado
confiável. Por isso `Odt2WebConverter` sempre retorna `metadata=None` e
deixa `discovery.py` extrair o front matter do HTML (mesmo caminho do
`FallbackConverter`) — estes testes validam exatamente isso, além da
extração de imagens via `output_dir`.
"""
import sys
import types
from pathlib import Path

import pytest

from asteria.errors import Diagnostics
from asteria.frontmatter import extract_frontmatter


class _FakeWarning:
    def __init__(self, message):
        self.message = message


class _FakeResult:
    def __init__(self, html, warnings=None):
        self.html = html
        self.css = "/* ignorado */"
        self.warnings = warnings or []


FRONTMATTER_HTML = (
    '<div class="ssg-frontmatter" data-ssg="frontmatter">\n'
    '  <meta data-key="title" content="Meu primeiro artigo">\n'
    '  <meta data-key="date" content="2026-08-10">\n'
    '  <meta data-key="author" content="Autora">\n'
    '  <meta data-key="tags" content="Python, Web">\n'
    '  <meta data-key="categories" content="Tecnologia">\n'
    "</div>\n"
    '<h2>Introdução</h2><p>Conteúdo</p><img src="assets/img1.png">'
)


@pytest.fixture
def fake_odt2web(monkeypatch):
    module = types.ModuleType("odt2web")

    def convert(path, output_dir=None, css=True, extract_images=True, document=True, allow_raw_html=True):
        if output_dir:
            assets_dir = Path(output_dir) / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            (assets_dir / "img1.png").write_bytes(b"fake-bytes")
        return _FakeResult(
            html=FRONTMATTER_HTML,
            warnings=[_FakeWarning("estilo desconhecido ignorado")],
        )

    module.convert = convert
    monkeypatch.setitem(sys.modules, "odt2web", module)
    yield module


def test_odt2web_converter_returns_metadata_none_and_frontmatter_in_html(
    fake_odt2web, tmp_path: Path
):
    from asteria.converter import Odt2WebConverter

    converter = Odt2WebConverter()
    diagnostics = Diagnostics()
    result = converter.convert(tmp_path / "artigo.odt", diagnostics)

    # O adapter não tenta interpretar result.metadata: front matter fica no
    # HTML, a cargo de extract_frontmatter (chamado por discovery.py).
    assert result.metadata is None
    assert "ssg-frontmatter" in result.html

    fm, remaining_html = extract_frontmatter(result.html, "artigo.odt", diagnostics)
    assert fm.title == "Meu primeiro artigo"
    assert fm.date == "2026-08-10"
    assert fm.tags == ["Python", "Web"]
    assert fm.categories == ["Tecnologia"]
    assert "ssg-frontmatter" not in remaining_html

    assert len(result.images) == 1
    assert result.images[0].output_name == "img1.png"
    assert result.images[0].data == b"fake-bytes"
    assert 'src="img1.png"' in result.html
    assert "assets/img1.png" not in result.html

    assert any("estilo desconhecido" in w.message for w in diagnostics.warnings)


def test_odt2web_converter_without_assets_dir(monkeypatch, tmp_path: Path):
    module = types.ModuleType("odt2web")

    def convert(path, output_dir=None, css=True, extract_images=True, document=True, allow_raw_html=True):
        return _FakeResult(html="<p>Sem imagens</p>")

    module.convert = convert
    monkeypatch.setitem(sys.modules, "odt2web", module)

    from asteria.converter import Odt2WebConverter

    converter = Odt2WebConverter()
    diagnostics = Diagnostics()
    result = converter.convert(tmp_path / "sem-imagem.odt", diagnostics)

    assert result.images == []
    assert not diagnostics.has_errors

import textwrap

import pytest

import odt2web
from odt2web import convert_bytes, register_renderer, unregister_renderer
from odt2web.reader import InvalidOdtError

from odt_builder import TINY_PNG, build_odt


# ---------------------------------------------------------------------------
# 1. documento simples
# ---------------------------------------------------------------------------

def test_simple_document():
    odt = build_odt('<text:p text:style-name="Text_20_Body">Ola mundo</text:p>')
    result = convert_bytes(odt)
    assert "<p>Ola mundo</p>" in result.html
    assert result.css is not None


def test_fragment_vs_document_mode():
    odt = build_odt('<text:p>texto</text:p>')
    fragment = convert_bytes(odt, document=False)
    full = convert_bytes(odt, document=True)
    assert not fragment.html.strip().startswith("<!doctype")
    assert full.html.strip().lower().startswith("<!doctype html>")
    assert "<html" in full.html and "<body>" in full.html


def test_css_false_still_semantic():
    odt = build_odt('<text:p text:style-name="Quotation">citacao</text:p>')
    result = convert_bytes(odt, css=False)
    assert result.css is None
    assert "<blockquote>" in result.html


# ---------------------------------------------------------------------------
# 2. titulos
# ---------------------------------------------------------------------------

def test_headings_use_style_map_and_outline_level():
    body = """
    <text:h text:style-name="Title" text:outline-level="1">Titulo Principal</text:h>
    <text:h text:style-name="Heading_20_1" text:outline-level="1">Secao 1</text:h>
    <text:h text:style-name="Heading_20_2" text:outline-level="2">Sub 1.1</text:h>
    """
    odt = build_odt(body)
    result = convert_bytes(odt)
    assert "<h1>Titulo Principal</h1>" in result.html
    assert "<h2>Secao 1</h2>" in result.html
    assert "<h3>Sub 1.1</h3>" in result.html


def test_heading_fallback_when_style_not_mapped():
    body = '<text:h text:style-name="MinhaSecaoCustom" text:outline-level="3">Foo</text:h>'
    odt = build_odt(body)
    result = convert_bytes(odt)
    # outline-level 3 sem mapeamento cai para h(level+1) = h4
    assert "<h4>Foo</h4>" in result.html


# ---------------------------------------------------------------------------
# 3. formatacao inline
# ---------------------------------------------------------------------------

def test_inline_formatting():
    automatic_styles = """
    <style:style style:name="Tb" style:family="text">
      <style:text-properties fo:font-weight="bold"/>
    </style:style>
    <style:style style:name="Ti" style:family="text">
      <style:text-properties fo:font-style="italic"/>
    </style:style>
    <style:style style:name="Tu" style:family="text">
      <style:text-properties style:text-underline-style="solid"/>
    </style:style>
    <style:style style:name="Ts" style:family="text">
      <style:text-properties style:text-line-through-style="solid"/>
    </style:style>
    <style:style style:name="Tsup" style:family="text">
      <style:text-properties style:text-position="super 58%"/>
    </style:style>
    <style:style style:name="Tsub" style:family="text">
      <style:text-properties style:text-position="sub 58%"/>
    </style:style>
    """
    body = """
    <text:p>
      <text:span text:style-name="Tb">negrito</text:span>
      <text:span text:style-name="Ti">italico</text:span>
      <text:span text:style-name="Tu">sublinhado</text:span>
      <text:span text:style-name="Ts">tachado</text:span>
      <text:span text:style-name="Tsup">sobrescrito</text:span>
      <text:span text:style-name="Tsub">subscrito</text:span>
      <text:a xlink:href="https://example.com">link</text:a>
    </text:p>
    """
    odt = build_odt(body, automatic_styles=automatic_styles)
    result = convert_bytes(odt)
    assert "<strong>negrito</strong>" in result.html
    assert "<em>italico</em>" in result.html
    assert "<u>sublinhado</u>" in result.html
    assert "<s>tachado</s>" in result.html
    assert "<sup>sobrescrito</sup>" in result.html
    assert "<sub>subscrito</sub>" in result.html
    assert '<a href="https://example.com">link</a>' in result.html


def test_special_characters_are_escaped():
    body = '<text:p>&lt;tag&gt; &amp; "aspas"</text:p>'
    odt = build_odt(body)
    result = convert_bytes(odt)
    assert "&lt;tag&gt;" in result.html
    assert "<tag>" not in result.html


# ---------------------------------------------------------------------------
# 4. listas (simples, ordenadas, aninhadas)
# ---------------------------------------------------------------------------

def test_unordered_list():
    extra_automatic_styles = """
    <text:list-style style:name="LB">
      <text:list-level-style-bullet text:level="1" text:bullet-char="-"/>
    </text:list-style>
    """
    body = """
    <text:list text:style-name="LB">
      <text:list-item><text:p>item um</text:p></text:list-item>
      <text:list-item><text:p>item dois</text:p></text:list-item>
    </text:list>
    """
    odt = build_odt(body, extra_automatic_styles=extra_automatic_styles)
    result = convert_bytes(odt)
    assert "<ul>" in result.html
    assert "<li><p>item um</p>\n</li>" in result.html


def test_ordered_list():
    extra_automatic_styles = """
    <text:list-style style:name="LN">
      <text:list-level-style-number text:level="1" style:num-format="1"/>
    </text:list-style>
    """
    body = """
    <text:list text:style-name="LN">
      <text:list-item><text:p>primeiro</text:p></text:list-item>
      <text:list-item><text:p>segundo</text:p></text:list-item>
    </text:list>
    """
    odt = build_odt(body, extra_automatic_styles=extra_automatic_styles)
    result = convert_bytes(odt)
    assert "<ol>" in result.html


def test_nested_list():
    extra_automatic_styles = """
    <text:list-style style:name="LB">
      <text:list-level-style-bullet text:level="1" text:bullet-char="-"/>
      <text:list-level-style-bullet text:level="2" text:bullet-char="-"/>
    </text:list-style>
    """
    body = """
    <text:list text:style-name="LB">
      <text:list-item>
        <text:p>pai</text:p>
        <text:list text:style-name="LB">
          <text:list-item><text:p>filho</text:p></text:list-item>
        </text:list>
      </text:list-item>
    </text:list>
    """
    odt = build_odt(body, extra_automatic_styles=extra_automatic_styles)
    result = convert_bytes(odt)
    # a lista aninhada deve aparecer dentro do <li> do item pai
    assert result.html.count("<ul>") == 2
    assert "filho" in result.html


# ---------------------------------------------------------------------------
# 5. tabelas
# ---------------------------------------------------------------------------

def test_table_header_colspan_rowspan():
    body = """
    <table:table table:style-name="Tab1">
      <table:table-header-rows>
        <table:table-row>
          <table:table-cell table:number-columns-spanned="2">
            <text:p>Cabecalho</text:p>
          </table:table-cell>
          <table:covered-table-cell/>
        </table:table-row>
      </table:table-header-rows>
      <table:table-row>
        <table:table-cell table:number-rows-spanned="2"><text:p>A</text:p></table:table-cell>
        <table:table-cell><text:p>B</text:p></table:table-cell>
      </table:table-row>
      <table:table-row>
        <table:covered-table-cell/>
        <table:table-cell><text:p>C</text:p></table:table-cell>
      </table:table-row>
    </table:table>
    """
    odt = build_odt(body)
    result = convert_bytes(odt)
    assert "<table>" in result.html
    assert "<thead>" in result.html
    assert '<th colspan="2">' in result.html
    assert '<td rowspan="2">' in result.html
    assert "table {" in result.css


# ---------------------------------------------------------------------------
# 6. imagens (embutidas, alt, legenda, extracao)
# ---------------------------------------------------------------------------

def test_embedded_image_with_alt_and_caption():
    body = """
    <text:p>
      <draw:frame svg:width="8cm" svg:height="4cm">
        <draw:image xlink:href="Pictures/foo.png"/>
        <svg:desc>Uma descricao</svg:desc>
      </draw:frame>
    </text:p>
    <text:p text:style-name="Caption">Figura 1: legenda da imagem</text:p>
    """
    odt = build_odt(body, pictures={"foo.png": TINY_PNG})
    result = convert_bytes(odt, extract_images=True)
    assert len(result.assets) == 1
    asset = result.assets[0]
    assert asset.data == TINY_PNG
    assert asset.output_path in result.html
    assert 'alt="Uma descricao"' in result.html
    assert "<figcaption>Figura 1: legenda da imagem</figcaption>" in result.html
    assert "width:8cm" in result.html


def test_image_extraction_can_be_disabled():
    body = """
    <text:p>
      <draw:frame svg:width="8cm" svg:height="4cm">
        <draw:image xlink:href="Pictures/foo.png"/>
      </draw:frame>
    </text:p>
    """
    odt = build_odt(body, pictures={"foo.png": TINY_PNG})
    result = convert_bytes(odt, extract_images=False)
    assert result.assets == []
    assert any("extract_images=False" in w.message for w in result.warnings)


# ---------------------------------------------------------------------------
# 7. notas de rodape
# ---------------------------------------------------------------------------

def test_footnotes():
    body = """
    <text:p>Texto com nota<text:note text:id="ftn1" text:note-class="footnote">
        <text:note-citation>1</text:note-citation>
        <text:note-body><text:p>Conteudo da nota</text:p></text:note-body>
      </text:note>.</text:p>
    """
    odt = build_odt(body)
    result = convert_bytes(odt)
    assert '<sup id="fnref-note-1"' in result.html
    assert 'class="odt-notes"' in result.html
    assert "Conteudo da nota" in result.html
    assert "odt-note-backref" in result.html


# ---------------------------------------------------------------------------
# 8. links
# ---------------------------------------------------------------------------

def test_links_sanitize_dangerous_schemes():
    body = """
    <text:p>
      <text:a xlink:href="javascript:alert(1)">malicioso</text:a>
      <text:a xlink:href="https://example.com/ok">seguro</text:a>
    </text:p>
    """
    odt = build_odt(body)
    result = convert_bytes(odt)
    assert "javascript:" not in result.html
    assert "malicioso" in result.html and "<a href=\"javascript" not in result.html
    assert '<a href="https://example.com/ok">seguro</a>' in result.html


# ---------------------------------------------------------------------------
# 9/10. duas e tres colunas
# ---------------------------------------------------------------------------

def test_two_columns_section():
    extra_automatic_styles = """
    <style:style style:name="Sect2" style:family="section">
      <style:section-properties>
        <style:columns fo:column-count="2" fo:column-gap="1.27cm"/>
      </style:section-properties>
    </style:style>
    """
    body = """
    <text:section text:style-name="Sect2" text:name="Secao1">
      <text:p>coluna dupla</text:p>
    </text:section>
    """
    odt = build_odt(body, extra_automatic_styles=extra_automatic_styles)
    result = convert_bytes(odt)
    assert 'class="odt-columns odt-columns-2"' in result.html
    assert ".odt-columns-2 {" in result.css
    assert "column-count: 2;" in result.css
    assert "column-gap: 1.27cm;" in result.css


def test_three_columns_section():
    extra_automatic_styles = """
    <style:style style:name="Sect3" style:family="section">
      <style:section-properties>
        <style:columns fo:column-count="3" fo:column-gap="0.5cm"/>
      </style:section-properties>
    </style:style>
    """
    body = """
    <text:section text:style-name="Sect3">
      <text:p>coluna tripla</text:p>
    </text:section>
    """
    odt = build_odt(body, extra_automatic_styles=extra_automatic_styles)
    result = convert_bytes(odt)
    assert 'class="odt-columns odt-columns-3"' in result.html
    assert ".odt-columns-3 {" in result.css


# ---------------------------------------------------------------------------
# 11. estilos personalizados (secao 7)
# ---------------------------------------------------------------------------

def test_custom_style_map():
    extra_styles = '<style:style style:name="Lead" style:family="paragraph" style:parent-style-name="Standard"/>'
    body = '<text:p text:style-name="Lead">Paragrafo de destaque</text:p>'
    odt = build_odt(body, extra_styles=extra_styles)
    result = convert_bytes(
        odt, style_map={"Lead": {"tag": "p", "class": "lead"}},
    )
    assert '<p class="lead">Paragrafo de destaque</p>' in result.html


def test_custom_renderer_extension():
    extra_styles = '<style:style style:name="Warning" style:family="paragraph" style:parent-style-name="Standard"/>'
    body = '<text:p text:style-name="Warning">Cuidado!</text:p>'
    odt = build_odt(body, extra_styles=extra_styles)

    @register_renderer("custom:note")
    def render_note(node, context):
        from odt2web.renderer import render_inline
        return f'<aside class="note">{render_inline(node.children, context)}</aside>\n'

    try:
        result = convert_bytes(odt, style_map={"Warning": {"tag": "custom:note"}})
        assert '<aside class="note">Cuidado!</aside>' in result.html
    finally:
        unregister_renderer("custom:note")


# ---------------------------------------------------------------------------
# 12. documentos multilingues (idioma nos metadados)
# ---------------------------------------------------------------------------

def test_metadata_extraction():
    odt = build_odt(
        '<text:p>ola</text:p>',
        title="Meu Artigo", author="Fulano de Tal", description="Uma descricao",
    )
    result = convert_bytes(odt, document=True)
    assert result.metadata.title == "Meu Artigo"
    assert result.metadata.author == "Fulano de Tal"
    assert '<title>Meu Artigo</title>' in result.html
    assert 'name="author" content="Fulano de Tal"' in result.html


# ---------------------------------------------------------------------------
# 13. recursos ausentes/invalidos
# ---------------------------------------------------------------------------

def test_missing_image_resource_is_skipped_gracefully():
    body = """
    <text:p>
      <draw:frame svg:width="8cm" svg:height="4cm">
        <draw:image xlink:href="Pictures/nao-existe.png"/>
      </draw:frame>
    </text:p>
    """
    odt = build_odt(body)  # sem 'pictures' -> recurso ausente no pacote
    result = convert_bytes(odt)
    assert result.assets == []
    # nao deve lancar excecao; a imagem ainda aparece referenciando o
    # caminho original (o usuario decide o que fazer)
    assert "img" in result.html


def test_invalid_odt_raises():
    with pytest.raises(InvalidOdtError):
        convert_bytes(b"isso nao e' um odt")


def test_check_function_reports_warnings_without_raising():
    import tempfile, os
    body = """
    <text:p>
      <draw:frame svg:width="1cm" svg:height="1cm">
        <draw:image xlink:href="Pictures/x.png"/>
      </draw:frame>
    </text:p>
    """
    odt = build_odt(body)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "doc.odt")
        with open(path, "wb") as fh:
            fh.write(odt)
        warnings = odt2web.check(path)
    assert isinstance(warnings, list)


# ---------------------------------------------------------------------------
# extra: convert() de arquivo real gravado em disco (fluxo completo -> dist/)
# ---------------------------------------------------------------------------

def test_convert_writes_output_dir(tmp_path):
    body = """
    <text:h text:style-name="Title" text:outline-level="1">Titulo</text:h>
    <text:p>Paragrafo com <text:span>span simples</text:span>.</text:p>
    """
    odt_bytes = build_odt(body)
    odt_path = tmp_path / "artigo.odt"
    odt_path.write_bytes(odt_bytes)

    dist = tmp_path / "dist"
    result = odt2web.convert(str(odt_path), output_dir=str(dist))

    assert (dist / "index.html").exists()
    assert (dist / "style.css").exists()
    html_content = (dist / "index.html").read_text(encoding="utf-8")
    assert "Titulo" in html_content


# ---------------------------------------------------------------------------
# front matter (extensao para uso com SSGs)
# ---------------------------------------------------------------------------

EXPECTED_FRONTMATTER_HTML = textwrap.dedent("""\
    <div class="ssg-frontmatter" data-ssg="frontmatter">
      <meta data-key="title" content="Meu primeiro artigo">
      <meta data-key="date" content="2026-08-20">
      <meta data-key="author" content="Autor">
      <meta data-key="tags" content="Python, Web">
      <meta data-key="categories" content="Tecnologia">
    </div>
    """)


def test_front_matter_as_consecutive_paragraphs():
    # forma mais comum ao digitar no LibreOffice: Enter cria um paragrafo
    # novo a cada linha.
    body = """
    <text:p>---</text:p>
    <text:p>title: Meu primeiro artigo</text:p>
    <text:p>date: 2026-08-20</text:p>
    <text:p>author: Autor</text:p>
    <text:p>tags: Python, Web</text:p>
    <text:p>categories: Tecnologia</text:p>
    <text:p>---</text:p>
    <text:h text:style-name="Title" text:outline-level="1">Meu primeiro artigo</text:h>
    <text:p>Corpo do artigo.</text:p>
    """
    odt = build_odt(body)
    result = convert_bytes(odt)

    assert result.front_matter == {
        "title": "Meu primeiro artigo",
        "date": "2026-08-20",
        "author": "Autor",
        "tags": "Python, Web",
        "categories": "Tecnologia",
    }
    assert EXPECTED_FRONTMATTER_HTML in result.html
    # o bloco --- ... --- nao deve sobrar no corpo do documento
    assert "<p>---</p>" not in result.html
    assert "<h1>Meu primeiro artigo</h1>" in result.html
    assert "<p>Corpo do artigo.</p>" in result.html


def test_front_matter_as_single_paragraph_with_line_breaks():
    # forma alternativa: Shift+Enter dentro de um unico paragrafo.
    body = """
    <text:p>---<text:line-break/>title: Meu primeiro artigo<text:line-break/>date: 2026-08-20<text:line-break/>author: Autor<text:line-break/>tags: Python, Web<text:line-break/>categories: Tecnologia<text:line-break/>---</text:p>
    <text:p>Corpo do artigo.</text:p>
    """
    odt = build_odt(body)
    result = convert_bytes(odt)

    assert result.front_matter == {
        "title": "Meu primeiro artigo",
        "date": "2026-08-20",
        "author": "Autor",
        "tags": "Python, Web",
        "categories": "Tecnologia",
    }
    assert EXPECTED_FRONTMATTER_HTML in result.html
    assert "<p>Corpo do artigo.</p>" in result.html


def test_no_front_matter_when_absent():
    body = '<text:p>Documento sem front matter.</text:p>'
    odt = build_odt(body)
    result = convert_bytes(odt)
    assert result.front_matter is None
    assert "ssg-frontmatter" not in result.html


def test_front_matter_present_in_document_mode_too():
    body = """
    <text:p>---</text:p>
    <text:p>title: Ola</text:p>
    <text:p>---</text:p>
    <text:p>Corpo.</text:p>
    """
    odt = build_odt(body)
    result = convert_bytes(odt, document=True)
    assert '<div class="ssg-frontmatter" data-ssg="frontmatter">' in result.html
    assert result.html.index("ssg-frontmatter") < result.html.index("Corpo")


def test_front_matter_survives_leading_blank_header_paragraphs():
    # Regressao: documentos reais frequentemente tem paragrafos vazios
    # (e ate um estilo com quebra de pagina) antes do front matter, por
    # causa de templates de editor. Isso nao pode impedir a deteccao.
    extra_styles = (
        '<style:style style:name="P1" style:family="paragraph" '
        'style:parent-style-name="Standard">'
        '<style:paragraph-properties fo:break-before="page"/>'
        "</style:style>"
    )
    body = """
    <text:p text:style-name="P1"/>
    <text:p/>
    <text:p>---</text:p>
    <text:p>title: Meu terceiro artigo</text:p>
    <text:p>date: 2026-08-10</text:p>
    <text:p>author: Autora</text:p>
    <text:p>---</text:p>
    <text:p>Nome</text:p>
    """
    odt = build_odt(body, extra_styles=extra_styles)
    result = convert_bytes(odt)

    assert result.front_matter == {
        "title": "Meu terceiro artigo",
        "date": "2026-08-10",
        "author": "Autora",
    }
    assert '<div class="ssg-frontmatter" data-ssg="frontmatter">' in result.html
    assert "<p>---</p>" not in result.html
    assert "<p>Nome</p>" in result.html
    # o cabecalho vazio nao precisa virar front matter, so nao pode
    # quebrar a deteccao - ele segue sendo ignorado/preservado como antes
    assert '<hr class="odt-page-break">' in result.html


def test_front_matter_not_detected_when_real_content_precedes_it():
    # se houver conteudo real (nao vazio) antes do bloco --- ---, nao
    # deve ser tratado como front matter (evita falsos positivos).
    body = """
    <text:p>Um paragrafo de verdade.</text:p>
    <text:p>---</text:p>
    <text:p>title: Nao deveria contar</text:p>
    <text:p>---</text:p>
    """
    odt = build_odt(body)
    result = convert_bytes(odt)
    assert result.front_matter is None
    assert "ssg-frontmatter" not in result.html


# ---------------------------------------------------------------------------
# HTML bruto embutido (:::html ... :::)
# ---------------------------------------------------------------------------

def test_raw_html_block_disabled_by_default():
    body = """
    <text:p>Antes.</text:p>
    <text:p>:::html</text:p>
    <text:p>&lt;iframe src="https://exemplo.com"&gt;&lt;/iframe&gt;</text:p>
    <text:p>:::</text:p>
    <text:p>Depois.</text:p>
    """
    odt = build_odt(body)
    result = convert_bytes(odt)  # allow_raw_html nao informado -> False
    assert "<iframe" not in result.html
    assert "odt-raw-html-disabled" in result.html
    assert "&lt;iframe" in result.html  # escapado, nao executado
    assert any("allow_raw_html=False" in w.message for w in result.warnings)


def test_raw_html_block_consecutive_paragraphs():
    body = """
    <text:p>Antes.</text:p>
    <text:p>:::html</text:p>
    <text:p>&lt;iframe src="https://exemplo.com/mapa" width="600"&gt;&lt;/iframe&gt;</text:p>
    <text:p>:::</text:p>
    <text:p>Depois.</text:p>
    """
    odt = build_odt(body)
    result = convert_bytes(odt, allow_raw_html=True)
    assert '<iframe src="https://exemplo.com/mapa" width="600"></iframe>' in result.html
    assert "<p>Antes.</p>" in result.html
    assert "<p>Depois.</p>" in result.html
    assert ":::html" not in result.html
    assert "iframe {" in result.css


def test_raw_html_block_single_paragraph_with_line_breaks():
    body = (
        '<text:p>:::html<text:line-break/>'
        '&lt;iframe src="https://exemplo.com"&gt;&lt;/iframe&gt;<text:line-break/>'
        ':::</text:p>'
        '<text:p>Depois.</text:p>'
    )
    odt = build_odt(body)
    result = convert_bytes(odt, allow_raw_html=True)
    assert '<iframe src="https://exemplo.com"></iframe>' in result.html
    assert "<p>Depois.</p>" in result.html


def test_raw_html_block_normalizes_smart_quotes():
    # o autocorretor do LibreOffice costuma trocar aspas retas por curvas;
    # dentro de um bloco :::html isso deve ser revertido, pois quebraria
    # atributos HTML.
    body = (
        '<text:p>:::html</text:p>'
        '<text:p>&lt;iframe src=\u201chttps://exemplo.com\u201d&gt;&lt;/iframe&gt;</text:p>'
        '<text:p>:::</text:p>'
    )
    odt = build_odt(body)
    result = convert_bytes(odt, allow_raw_html=True)
    assert '<iframe src="https://exemplo.com"></iframe>' in result.html


def test_raw_html_block_without_closing_marker_is_left_as_paragraphs():
    body = """
    <text:p>:::html</text:p>
    <text:p>conteudo sem fechamento</text:p>
    """
    odt = build_odt(body)
    result = convert_bytes(odt, allow_raw_html=True)
    assert "<p>:::html</p>" in result.html
    assert "<p>conteudo sem fechamento</p>" in result.html


# ---------------------------------------------------------------------------
# resolucao de estilos via estilos automaticos (regressao critica: em
# documentos reais, o paragrafo quase nunca usa o nome semantico
# diretamente - o editor cria um estilo automatico "P1", "P2" etc. cujo
# style:parent-style-name aponta para o estilo nomeado de verdade).
# ---------------------------------------------------------------------------

def test_style_resolution_through_automatic_style_chain():
    extra_automatic_styles = (
        '<style:style style:name="P1" style:family="paragraph" '
        'style:parent-style-name="Heading_20_1"/>'
    )
    body = '<text:h text:style-name="P1" text:outline-level="1">Titulo via P1</text:h>'
    odt = build_odt(body, extra_automatic_styles=extra_automatic_styles)
    result = convert_bytes(odt)
    # "Heading_20_1" decodifica para "Heading 1", que o DEFAULT_STYLE_MAP
    # mapeia para h2 - mesmo o paragrafo usando o estilo automatico "P1".
    assert "<h2>Titulo via P1</h2>" in result.html


def test_custom_style_map_through_automatic_style_chain():
    extra_styles = (
        '<style:style style:name="Lead" style:family="paragraph" '
        'style:parent-style-name="Standard"/>'
    )
    extra_automatic_styles = (
        '<style:style style:name="P5" style:family="paragraph" '
        'style:parent-style-name="Lead"/>'
    )
    body = '<text:p text:style-name="P5">Destaque via estilo automatico</text:p>'
    odt = build_odt(body, extra_styles=extra_styles, extra_automatic_styles=extra_automatic_styles)
    result = convert_bytes(odt, style_map={"Lead": {"tag": "p", "class": "lead"}})
    assert '<p class="lead">Destaque via estilo automatico</p>' in result.html


def test_page_break_inherited_through_style_chain():
    extra_automatic_styles = (
        '<style:style style:name="P1" style:family="paragraph" '
        'style:parent-style-name="Standard">'
        '<style:paragraph-properties fo:break-before="page"/>'
        "</style:style>"
    )
    body = '<text:p text:style-name="P1">Depois da quebra</text:p>'
    odt = build_odt(body, extra_automatic_styles=extra_automatic_styles)
    result = convert_bytes(odt)
    assert '<hr class="odt-page-break">' in result.html


# ---------------------------------------------------------------------------
# blocos e trechos de codigo
# ---------------------------------------------------------------------------

def test_code_block_merges_consecutive_preformatted_paragraphs():
    body = """
    <text:p text:style-name="Preformatted_20_Text">def ola():</text:p>
    <text:p text:style-name="Preformatted_20_Text">    return 42</text:p>
    <text:p>Paragrafo normal depois.</text:p>
    """
    odt = build_odt(body)
    result = convert_bytes(odt)
    assert "<pre><code>def ola():\n    return 42</code></pre>" in result.html
    assert "<p>Paragrafo normal depois.</p>" in result.html
    # nao pode sobrar um <pre> por linha
    assert result.html.count("<pre>") == 1


def test_code_block_language_via_fence_marker():
    body = """
    <text:p text:style-name="Preformatted_20_Text">```python</text:p>
    <text:p text:style-name="Preformatted_20_Text">print("oi")</text:p>
    """
    odt = build_odt(body)
    result = convert_bytes(odt)
    assert '<pre><code class="language-python">print("oi")</code></pre>' in result.html
    assert "```python" not in result.html


def test_code_block_language_via_style_map_class():
    extra_styles = (
        '<style:style style:name="CodeJS" style:family="paragraph" '
        'style:parent-style-name="Standard"/>'
    )
    body = """
    <text:p text:style-name="CodeJS">function ola() {</text:p>
    <text:p text:style-name="CodeJS">  return 42;</text:p>
    <text:p text:style-name="CodeJS">}</text:p>
    """
    odt = build_odt(body, extra_styles=extra_styles)
    result = convert_bytes(
        odt, style_map={"CodeJS": {"tag": "pre", "class": "language-javascript"}},
    )
    assert '<pre><code class="language-javascript">function ola() {\n  return 42;\n}</code></pre>' in result.html


def test_code_block_does_not_apply_inline_formatting():
    body = (
        '<text:p text:style-name="Preformatted_20_Text">'
        '<text:span text:style-name="Tb">nao</text:span> deveria virar negrito'
        "</text:p>"
    )
    automatic_styles = (
        '<style:style style:name="Tb" style:family="text">'
        '<style:text-properties fo:font-weight="bold"/>'
        "</style:style>"
    )
    odt = build_odt(body, automatic_styles=automatic_styles)
    result = convert_bytes(odt)
    assert "<strong>" not in result.html
    assert "<pre><code>nao deveria virar negrito</code></pre>" in result.html


def test_inline_code_via_source_text_style():
    extra_styles = '<style:style style:name="Source_20_Text" style:display-name="Source Text" style:family="text"/>'
    automatic_styles = (
        '<style:style style:name="T1" style:family="text" '
        'style:parent-style-name="Source_20_Text"/>'
    )
    body = '<text:p>Use <text:span text:style-name="T1">minha_funcao()</text:span> aqui.</text:p>'
    odt = build_odt(body, extra_styles=extra_styles, automatic_styles=automatic_styles)
    result = convert_bytes(odt)
    assert "<code>minha_funcao()</code>" in result.html
    assert "code {" in result.css


# ---------------------------------------------------------------------------
# configuracao YAML (secao 16)
# ---------------------------------------------------------------------------

def test_yaml_config_overrides_defaults(tmp_path):
    body = '<text:h text:style-name="Title" text:outline-level="1">Titulo</text:h>'
    odt_bytes = build_odt(body)
    odt_path = tmp_path / "artigo.odt"
    odt_path.write_bytes(odt_bytes)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "output:\n"
        "  document: true\n"
        "  assets: img\n"
        "styles:\n"
        "  Title: h1\n",
        encoding="utf-8",
    )

    result = odt2web.convert(str(odt_path), config=str(config_path))
    assert result.html.strip().lower().startswith("<!doctype html>")


def test_yaml_config_explicit_argument_wins_over_file(tmp_path):
    body = '<text:p>ola</text:p>'
    odt_bytes = build_odt(body)
    odt_path = tmp_path / "artigo.odt"
    odt_path.write_bytes(odt_bytes)

    config_path = tmp_path / "config.yaml"
    config_path.write_text("output:\n  document: true\n", encoding="utf-8")

    # document=False passado explicitamente deve vencer o config
    result = odt2web.convert(str(odt_path), config=str(config_path), document=False)
    assert not result.html.strip().startswith("<!doctype")


def test_yaml_config_disable_columns(tmp_path):
    extra_automatic_styles = """
    <style:style style:name="Sect2" style:family="section">
      <style:section-properties>
        <style:columns fo:column-count="2" fo:column-gap="1.27cm"/>
      </style:section-properties>
    </style:style>
    """
    body = """
    <text:section text:style-name="Sect2">
      <text:p>texto</text:p>
    </text:section>
    """
    odt_bytes = build_odt(body, extra_automatic_styles=extra_automatic_styles)
    odt_path = tmp_path / "artigo.odt"
    odt_path.write_bytes(odt_bytes)

    config_path = tmp_path / "config.yaml"
    config_path.write_text("columns:\n  enabled: false\n", encoding="utf-8")

    result = odt2web.convert(str(odt_path), config=str(config_path))
    assert "odt-columns" not in result.html

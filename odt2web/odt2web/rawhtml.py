"""HTML bruto embutido no ODT (escape-hatch generico, ver discussao no
README - "por que nao inventar uma sintaxe por funcionalidade").

Reconhece um bloco delimitado por marcadores em qualquer ponto do fluxo
do documento:

    :::html
    <iframe src="https://exemplo.com/mapa" width="600" height="400"></iframe>
    :::

posicionado como parágrafos proprios (um marcador por paragrafo) ou,
alternativamente, como um unico paragrafo com quebras de linha manuais
(Shift+Enter) entre o marcador de abertura, o conteudo e o marcador de
fechamento - exatamente como o bloco de front matter (ver frontmatter.py).

O conteudo entre os marcadores e' extraido como texto literal e
convertido em um no RawHtml, que o renderer emite sem escaping *somente*
quando o chamador habilita allow_raw_html=True (default False - trata-se
de um escape-hatch de seguranca, ver security.py / secao 13).
"""
from __future__ import annotations

from .model import LineBreak, Link, Paragraph, RawHtml, Span, Text

START_MARKER = ":::html"
END_MARKER = ":::"

# substituicoes tipograficas comuns que o autocorretor do LibreOffice
# aplica ao digitar (aspas retas -> curvas, etc.) e que quebrariam HTML
# como atributos de tag (href="...") se nao fossem revertidas dentro de
# um bloco explicitamente marcado como codigo/HTML.
_TYPOGRAPHY_FIXUPS = {
    "\u201c": '"', "\u201d": '"',  # aspas duplas curvas -> retas
    "\u2018": "'", "\u2019": "'",  # aspas simples curvas -> retas
    "\u00a0": " ",  # espaco nao separavel -> espaco normal
    "\u2026": "...",  # reticencias -> tres pontos
}


def _normalize_typography(text: str) -> str:
    for src, dst in _TYPOGRAPHY_FIXUPS.items():
        text = text.replace(src, dst)
    return text


def _plain_text(nodes: list, *, line_break_as_newline: bool = False) -> str:
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, Text):
            parts.append(node.value)
        elif isinstance(node, (Span, Link)):
            parts.append(_plain_text(node.children, line_break_as_newline=line_break_as_newline))
        elif isinstance(node, LineBreak):
            parts.append("\n" if line_break_as_newline else " ")
    return "".join(parts)


def extract_raw_html_blocks(children: list) -> list:
    """Percorre uma lista de BlockNode substituindo blocos delimitados por
    ':::html' / ':::' por um unico no RawHtml. Nao muta a lista original;
    retorna uma nova lista."""
    result: list = []
    i = 0
    n = len(children)

    while i < n:
        node = children[i]

        if isinstance(node, Paragraph):
            text = _plain_text(node.children).strip()

            # --- Caso 1: paragrafos consecutivos ------------------------
            if text == START_MARKER:
                end_idx = None
                for j in range(i + 1, n):
                    sibling = children[j]
                    if not isinstance(sibling, Paragraph):
                        break
                    if _plain_text(sibling.children).strip() == END_MARKER:
                        end_idx = j
                        break
                if end_idx is not None:
                    lines = [
                        _plain_text(c.children)
                        for c in children[i + 1:end_idx]
                        if isinstance(c, Paragraph)
                    ]
                    content = _normalize_typography("\n".join(lines))
                    result.append(RawHtml(content=content))
                    i = end_idx + 1
                    continue

            # --- Caso 2: um unico paragrafo com quebras de linha --------
            text_with_breaks = _plain_text(node.children, line_break_as_newline=True)
            lines = text_with_breaks.split("\n")
            if len(lines) >= 3 and lines[0].strip() == START_MARKER:
                for j in range(1, len(lines)):
                    if lines[j].strip() == END_MARKER:
                        content = _normalize_typography("\n".join(lines[1:j]))
                        result.append(RawHtml(content=content))
                        break
                else:
                    result.append(node)
                i += 1
                continue

        result.append(node)
        i += 1

    return result

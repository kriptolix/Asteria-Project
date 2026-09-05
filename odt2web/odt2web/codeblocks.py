"""Blocos de codigo (secao 5 'estrutura' / secao 7 'estilos personalizados').

Trata blocos de codigo como um caso especial de paragrafo com o estilo
mapeado (via style_map, secoes 6/7) para a tag "pre" - por padrao, o
estilo nativo do LibreOffice "Preformatted Text". Diferente de um
paragrafo comum:

- varios paragrafos consecutivos com o mesmo estilo "pre" sao mesclados
  em um unico bloco <pre><code>...</code></pre> (uma linha por
  paragrafo), em vez de virarem varios <pre> separados;
- o conteudo e' extraido como texto literal (formatacao inline como
  negrito/italico e' ignorada) - aplicar <strong>/<em> dentro de um
  bloco de codigo quebraria copy-paste e a maioria dos syntax
  highlighters;
- a linguagem pode ser indicada de duas formas: (a) a classe CSS do
  style_map, se seguir a convencao "language-xxx" (ex: estilos ODT
  dedicados por linguagem, como "Code Python" -> {"tag": "pre",
  "class": "language-python"}); ou (b) uma marcacao no estilo Markdown
  na primeira linha do bloco (```python), removida do conteudo final -
  util para quem nao quer criar um estilo ODT por linguagem.

O HTML gerado (<pre><code class="language-xxx">) segue a convencao
adotada por bibliotecas de syntax highlighting client-side (highlight.js,
Prism) e por highlighters server-side de SSGs (ex: Chroma no Hugo,
Shiki/PrismJS em plugins do Eleventy/11ty) - a biblioteca nao faz
highlighting ela mesma, apenas entrega a marcacao no formato que essas
ferramentas esperam.
"""
from __future__ import annotations

from .model import CodeBlock, LineBreak, Link, Paragraph, Section, Span, Text
from .styles import resolve_style_mapping


def _literal_text(nodes: list) -> str:
    """Extrai o texto literal de um paragrafo, ignorando formatacao
    inline (negrito/italico/links) mas preservando quebras de linha
    manuais como '\\n' - usado para nao corromper codigo."""
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, Text):
            parts.append(node.value)
        elif isinstance(node, (Span, Link)):
            parts.append(_literal_text(node.children))
        elif isinstance(node, LineBreak):
            parts.append("\n")
    return "".join(parts)


def _strip_language_fence(lines: list[str]) -> tuple[str | None, list[str]]:
    """Se a primeira linha for uma marcacao estilo Markdown ('```python'),
    remove-a e retorna a linguagem indicada."""
    if lines and lines[0].strip().startswith("```"):
        lang = lines[0].strip()[3:].strip()
        return (lang or None), lines[1:]
    return None, lines


def _language_from_css_class(css_class: str | None) -> str | None:
    if css_class and css_class.startswith("language-"):
        return css_class[len("language-"):]
    return None


def _merge_children(children: list, style_map: dict) -> list:
    result: list = []
    i = 0
    n = len(children)

    while i < n:
        node = children[i]

        if isinstance(node, Paragraph):
            mapping = resolve_style_mapping(node.style_candidates, style_map)
            tag, attrs = mapping if mapping is not None else ("p", {})
            if tag == "pre":
                css_class = attrs.get("class")
                j = i
                paragraph_lines: list[str] = []
                while j < n and isinstance(children[j], Paragraph):
                    m2 = resolve_style_mapping(children[j].style_candidates, style_map)
                    t2, a2 = m2 if m2 is not None else ("p", {})
                    if t2 != "pre" or a2.get("class") != css_class:
                        break
                    paragraph_lines.append(_literal_text(children[j].children))
                    j += 1

                # cada paragrafo pode conter multiplas linhas internas
                # (quebras de linha manuais); achata tudo em uma lista de
                # linhas antes de procurar a marcacao de linguagem.
                lines: list[str] = []
                for para_text in paragraph_lines:
                    lines.extend(para_text.split("\n"))

                fence_lang, lines = _strip_language_fence(lines)
                language = fence_lang or _language_from_css_class(css_class)

                result.append(CodeBlock(
                    code="\n".join(lines), language=language, css_class=css_class,
                ))
                i = j
                continue

        result.append(node)
        i += 1

    return result


def merge_code_blocks(sections: list[Section], style_map: dict) -> None:
    """Aplica a mesclagem em todas as secoes do documento, in-place."""
    for section in sections:
        section.children = _merge_children(section.children, style_map)

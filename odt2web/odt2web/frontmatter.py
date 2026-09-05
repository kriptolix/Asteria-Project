"""Front matter (extensao para uso com SSGs).

Reconhece um bloco de front matter no formato:

    ---
    title: Meu primeiro artigo
    date: 2026-08-20
    author: Autor
    tags: Python, Web
    categories: Tecnologia
    ---

posicionado como o primeiro elemento do documento ODT. No ODT, esse bloco
pode chegar de duas formas, dependendo de como foi digitado:

1. Como varios paragrafos consecutivos, um por linha (o mais comum ao
   digitar no LibreOffice, onde Enter cria um novo paragrafo); ou
2. Como um unico paragrafo com quebras de linha manuais
   (Shift+Enter / text:line-break) entre cada linha.

O bloco reconhecido é removido do fluxo normal do documento e retornado
como um dict ordenado (chave -> valor bruto, sem interpretação YAML),
para ser renderizado como:

Parágrafos vazios antes do bloco (ex: um "cabeçalho" em branco deixado
por um template do editor) são apenas ignorados na busca pelo
delimitador - eles não são interpretados como front matter, mas também
não podem impedir que o bloco seguinte seja reconhecido.

    <div class="ssg-frontmatter" data-ssg="frontmatter">
      <meta data-key="title" content="Meu primeiro artigo">
      ...
    </div>
"""
from __future__ import annotations

from .model import LineBreak, Link, Paragraph, PageBreak, Section, Span, Text

DELIMITER = "---"


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


def _parse_kv_lines(lines: list[str]) -> dict[str, str] | None:
    """Faz o parsing das linhas 'chave: valor' entre os delimitadores.
    Retorna None se nenhuma linha valida for encontrada (bloco vazio nao
    e' considerado front matter)."""
    data: dict[str, str] = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            # linha fora do padrao chave: valor -> nao e' front matter valido
            return None
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if not key:
            return None
        data[key] = value
    return data or None


def extract_front_matter(section: Section) -> dict[str, str] | None:
    """Tenta extrair e remover um bloco de front matter do inicio da
    (primeira) secao do documento. Muta `section.children` in-place quando
    encontra um bloco valido.

    Paragrafos vazios que antecedem o bloco (comuns em cabecalhos/
    templates do documento, ex: paragrafos em branco deixados pelo autor
    antes do titulo) sao ignorados na busca pelo delimitador, mas
    permanecem intocados no documento - apenas nao podem impedir a
    deteccao do front matter que vem em seguida.
    """
    children = section.children

    start_idx = 0
    while start_idx < len(children):
        node = children[start_idx]
        if isinstance(node, PageBreak):
            # quebras de pagina antes do conteudo (comuns quando o
            # primeiro paragrafo do documento tem "quebrar antes" no
            # estilo) sao apenas puladas na busca.
            start_idx += 1
            continue
        if not isinstance(node, Paragraph):
            # algo alem de paragrafo/quebra de pagina (lista, tabela,
            # imagem...) antes de qualquer texto: nao ha' front matter
            # a procurar aqui.
            return None
        if _plain_text(node.children).strip() != "":
            break
        start_idx += 1
    else:
        return None  # todos os nos iniciais eram vazios/quebras de pagina

    if start_idx >= len(children):
        return None

    # --- Caso 1: paragrafos consecutivos, um por linha -----------------
    first_text = _plain_text(children[start_idx].children).strip()
    if first_text == DELIMITER:
        end_idx = None
        for i in range(start_idx + 1, len(children)):
            node = children[i]
            if not isinstance(node, Paragraph):
                break
            if _plain_text(node.children).strip() == DELIMITER:
                end_idx = i
                break
        if end_idx is not None:
            lines = [
                _plain_text(node.children)
                for node in children[start_idx + 1:end_idx]
                if isinstance(node, Paragraph)
            ]
            data = _parse_kv_lines(lines)
            if data is not None:
                del children[start_idx:end_idx + 1]
                return data

    # --- Caso 2: um unico paragrafo com quebras de linha manuais -------
    text_with_breaks = _plain_text(children[start_idx].children, line_break_as_newline=True)
    lines = text_with_breaks.split("\n")
    if len(lines) >= 3 and lines[0].strip() == DELIMITER:
        for j in range(1, len(lines)):
            if lines[j].strip() == DELIMITER:
                data = _parse_kv_lines(lines[1:j])
                if data is not None:
                    del children[start_idx]
                    return data
                break

    return None

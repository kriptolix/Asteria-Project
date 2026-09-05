"""Modelo de documento intermediário.

O parser ODT nunca gera HTML diretamente: primeiro constrói esta
representação própria (independente de formato de saída), que depois
pode ser consumida por diferentes renderers (HTML, e futuramente
Markdown, JSON, etc. - ver secao 4 da especificacao).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union


# ---------------------------------------------------------------------------
# Nos inline (formatacao de texto)
# ---------------------------------------------------------------------------

@dataclass
class Text:
    """Texto simples, sem formatacao adicional."""
    value: str


@dataclass
class Span:
    """Trecho de texto com formatacao ou estilo de caractere nomeado."""
    children: list["InlineNode"] = field(default_factory=list)
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    superscript: bool = False
    subscript: bool = False
    code: bool = False  # estilo de caractere "Source Text" (codigo inline)
    style_name: Optional[str] = None  # nome do estilo ODT original, se houver


@dataclass
class Link:
    href: str
    children: list["InlineNode"] = field(default_factory=list)


@dataclass
class LineBreak:
    pass


@dataclass
class NoteRef:
    """Referencia inline a uma nota de rodape (marcador numerado)."""
    note_id: str
    label: str  # numero/simbolo exibido, ex: "1"


InlineNode = Union[Text, Span, Link, LineBreak, NoteRef]


# ---------------------------------------------------------------------------
# Nos de bloco
# ---------------------------------------------------------------------------

@dataclass
class Paragraph:
    children: list[InlineNode] = field(default_factory=list)
    style_name: Optional[str] = None
    # cadeia de identificadores candidatos (nome bruto + nomes decodificados
    # de cada ancestral via parent-style-name) usada para resolver contra
    # style_map/DEFAULT_STYLE_MAP - ver StyleRegistry.resolve_style_candidates
    style_candidates: list[str] = field(default_factory=list)
    # estilo semantico resolvido (ex: "Text Body", "Quotation")
    resolved_style: Optional[str] = None


@dataclass
class Heading:
    level: int  # 1..6, ja normalizado
    children: list[InlineNode] = field(default_factory=list)
    style_name: Optional[str] = None
    style_candidates: list[str] = field(default_factory=list)


@dataclass
class ListItem:
    children: list["BlockNode"] = field(default_factory=list)


@dataclass
class List:
    ordered: bool
    items: list[ListItem] = field(default_factory=list)
    style_name: Optional[str] = None


@dataclass
class TableCell:
    children: list["BlockNode"] = field(default_factory=list)
    colspan: int = 1
    rowspan: int = 1
    is_header: bool = False
    covered: bool = False  # celula coberta por rowspan/colspan anterior


@dataclass
class TableRow:
    cells: list[TableCell] = field(default_factory=list)
    is_header: bool = False


@dataclass
class Table:
    rows: list[TableRow] = field(default_factory=list)
    style_name: Optional[str] = None
    caption: Optional[str] = None
    column_widths: list[Optional[float]] = field(default_factory=list)  # cm


@dataclass
class Image:
    src: str  # caminho original dentro do pacote ODT (ex: Pictures/foo.png)
    alt: Optional[str] = None
    caption: Optional[str] = None
    width: Optional[str] = None  # ja em unidade CSS (ex: "8.5cm")
    height: Optional[str] = None
    linked: bool = False  # True = imagem referenciada (externa), nao incorporada


@dataclass
class PageBreak:
    pass


@dataclass
class Note:
    """Uma nota de rodape/final, com seu conteudo, indexada por id."""
    note_id: str
    label: str
    children: list["BlockNode"] = field(default_factory=list)
    kind: str = "footnote"  # "footnote" | "endnote"


@dataclass
class CustomNode:
    """No de extensao, tratado por um renderer registrado (secao 17)."""
    name: str  # ex: "custom:note"
    attributes: dict = field(default_factory=dict)
    children: list["BlockNode"] = field(default_factory=list)


@dataclass
class RawHtml:
    """Bloco de HTML literal, escrito pelo autor dentro do ODT entre
    marcadores (ex: ':::html' ... ':::') e passado adiante sem escaping.
    So e' emitido quando o chamador habilita explicitamente essa
    funcionalidade (allow_raw_html=True), por ser um escape-hatch de
    seguranca (ver security.py / secao 13)."""
    content: str


@dataclass
class CodeBlock:
    """Bloco de codigo (varios paragrafos com estilo mapeado para <pre>
    mesclados em um unico bloco, ver codeblocks.py). Renderizado como
    <pre><code class="language-xxx">...</code></pre>, sem aplicar
    formatacao inline (negrito/italico/etc.) ao conteudo - codigo e'
    tratado como texto literal, para nao quebrar syntax highlighting."""
    code: str
    language: Optional[str] = None
    css_class: Optional[str] = None


BlockNode = Union[
    Paragraph, Heading, List, Table, Image, PageBreak, CustomNode, RawHtml,
    CodeBlock,
]


# ---------------------------------------------------------------------------
# Estrutura de secoes / documento
# ---------------------------------------------------------------------------

@dataclass
class Section:
    children: list[BlockNode] = field(default_factory=list)
    columns: int = 1
    column_gap: Optional[str] = None  # unidade CSS, ex: "1.27cm"
    column_rule: Optional[str] = None  # ex: "1px solid #000"
    style_name: Optional[str] = None
    name: Optional[str] = None


@dataclass
class Metadata:
    title: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    keywords: list[str] = field(default_factory=list)
    created: Optional[str] = None
    modified: Optional[str] = None
    language: Optional[str] = None


@dataclass
class Document:
    sections: list[Section] = field(default_factory=list)
    notes: dict[str, Note] = field(default_factory=dict)
    metadata: Metadata = field(default_factory=Metadata)
    front_matter: Optional[dict] = None
    warnings: list[str] = field(default_factory=list)

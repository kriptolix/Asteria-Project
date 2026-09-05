"""Sistema de estilos (secoes 6, 7 e 8 da especificacao).

Interpreta styles.xml e os estilos automaticos de content.xml, resolvendo
cada style-name ODT para uma representacao semantica que o renderer usa
para decidir qual tag/classe HTML gerar.
"""
from __future__ import annotations

import re

from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

from .ns import NS, q

# Mapeamento padrao (secao 6) - o usuario pode sobrescrever/estender.
DEFAULT_STYLE_MAP: dict[str, str | dict] = {
    "Title": "h1",
    "Subtitle": "h2",
    "Heading 1": "h2",
    "Heading 2": "h3",
    "Heading 3": "h4",
    "Heading 4": "h5",
    "Heading 5": "h6",
    "Heading 6": "h6",
    "Quotation": "blockquote",
    "Quotations": "blockquote",
    "Text Body": "p",
    "Preformatted Text": "pre",
    "Caption": {"tag": "figcaption"},
}


@dataclass
class ColumnInfo:
    count: int = 1
    gap: str | None = None  # unidade CSS
    rule: str | None = None  # "1px solid #rrggbb"


@dataclass
class StyleInfo:
    name: str
    family: str  # "paragraph" | "text" | "table" | "table-cell" | "section" | "graphic"
    parent: str | None = None
    display_name: str | None = None
    text_align: str | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    superscript: bool = False
    subscript: bool = False
    break_before: bool = False
    break_after: bool = False
    columns: ColumnInfo | None = None


CM_PER_UNIT = {"cm": 1.0, "mm": 0.1, "in": 2.54, "pt": 2.54 / 72, "px": 2.54 / 96}


def _to_css_length(value: str | None) -> str | None:
    """ODF ja usa unidades CSS-compativeis (cm, mm, in, pt, px) na maioria
    dos casos; apenas repassamos o valor, validando o formato."""
    if not value:
        return None
    return value


_ODF_ESCAPE_RE = re.compile(r"_([0-9A-Fa-f]{2})_")


def decode_odf_style_name(name: str) -> str:
    """Decodifica o escaping de caracteres reservados usado pelo
    LibreOffice/OpenOffice em style:name (ex: 'Heading_20_1' -> 'Heading 1',
    'Normal_20__28_Web_29_' -> 'Normal (Web)'). O style:name e' um NCName
    XML e nao pode conter certos caracteres (espaco, parenteses, etc.);
    esses caracteres sao codificados como '_XX_' (hex de 2 digitos).
    Quando style:display-name esta ausente, este e' o unico jeito de obter
    o nome "humano" do estilo (usado para casar contra style_map/
    DEFAULT_STYLE_MAP)."""
    return _ODF_ESCAPE_RE.sub(lambda m: chr(int(m.group(1), 16)), name)


class StyleRegistry:
    """Registro consolidado de todos os estilos nomeados e automaticos
    encontrados em styles.xml e content.xml."""

    def __init__(self) -> None:
        self._styles: dict[str, StyleInfo] = {}

    def add(self, info: StyleInfo) -> None:
        self._styles[info.name] = info

    def get(self, name: str | None) -> StyleInfo | None:
        if name is None:
            return None
        return self._styles.get(name)

    def resolve_columns(self, name: str | None) -> ColumnInfo | None:
        """Segue a cadeia parent-style-name ate achar informacao de colunas."""
        seen = set()
        current = name
        while current and current not in seen:
            seen.add(current)
            info = self.get(current)
            if info is None:
                return None
            if info.columns is not None:
                return info.columns
            current = info.parent
        return None

    def resolve_break_before(self, name: str | None) -> bool:
        """Segue a cadeia parent-style-name ate achar 'quebrar antes' (a
        propriedade e' herdada quando o estilo automatico do paragrafo nao
        a redefine, o que e' o caso mais comum)."""
        seen = set()
        current = name
        while current and current not in seen:
            seen.add(current)
            info = self.get(current)
            if info is None:
                return False
            if info.break_before:
                return True
            current = info.parent
        return False

    def display_name(self, name: str | None) -> str | None:
        if name is None:
            return None
        info = self.get(name)
        if info is None:
            return decode_odf_style_name(name)
        if info.display_name:
            return info.display_name
        return decode_odf_style_name(info.name)

    def resolve_style_candidates(self, name: str | None) -> list[str]:
        """Retorna a lista ordenada de identificadores a tentar para
        resolver um style_name contra style_map/DEFAULT_STYLE_MAP: o nome
        bruto e o nome "humano" (decodificado/display-name) de cada nivel
        da cadeia parent-style-name, do mais especifico ao mais geral.

        Isso e' necessario porque documentos reais quase sempre aplicam
        estilos automaticos gerados pelo editor (ex: 'P1', 'P2') cujo
        style:parent-style-name aponta para o estilo nomeado de verdade
        (ex: 'Heading_20_1' -> 'Heading 1') - o style_name do proprio
        paragrafo quase nunca e' literalmente 'Heading 1'."""
        candidates: list[str] = []
        seen_names = set()
        current = name
        while current and current not in seen_names:
            seen_names.add(current)
            candidates.append(current)
            display = self.display_name(current)
            if display and display != current:
                candidates.append(display)
            info = self.get(current)
            current = info.parent if info else None
        # remove duplicatas preservando a ordem
        return list(dict.fromkeys(candidates))


def _parse_column_props(section_props: ET.Element) -> ColumnInfo | None:
    columns_el = section_props.find(q("style:columns"))
    if columns_el is None:
        return None
    count_raw = columns_el.get(q("fo:column-count"))
    try:
        count = int(count_raw) if count_raw else 1
    except ValueError:
        count = 1
    gap = _to_css_length(columns_el.get(q("fo:column-gap")))

    rule = None
    sep_el = columns_el.find(q("style:column-sep"))
    if sep_el is not None:
        width = _to_css_length(sep_el.get(q("style:width"))) or "1px"
        color = sep_el.get(q("style:color")) or "#000000"
        style = sep_el.get(q("style:style")) or "solid"
        rule = f"{width} {style} {color}"

    return ColumnInfo(count=count, gap=gap, rule=rule)


def _parse_style_element(style_el: ET.Element, family_override: str | None = None) -> StyleInfo | None:
    name = style_el.get(q("style:name"))
    if not name:
        return None
    family = family_override or style_el.get(q("style:family")) or "paragraph"
    parent = style_el.get(q("style:parent-style-name"))
    display_name = style_el.get(q("style:display-name"))

    info = StyleInfo(name=name, family=family, parent=parent, display_name=display_name)

    para_props = style_el.find(q("style:paragraph-properties"))
    if para_props is not None:
        info.text_align = para_props.get(q("fo:text-align"))
        columns = _parse_column_props(para_props)
        if columns is not None:
            info.columns = columns
        if para_props.get(q("fo:break-before")) == "page":
            info.break_before = True
        if para_props.get(q("fo:break-after")) == "page":
            info.break_after = True

    text_props = style_el.find(q("style:text-properties"))
    if text_props is not None:
        weight = text_props.get(q("fo:font-weight"))
        if weight and weight != "normal":
            info.bold = True
        posture = text_props.get(q("fo:font-style"))
        if posture and posture != "normal":
            info.italic = True
        underline_style = text_props.get(q("style:text-underline-style"))
        if underline_style and underline_style != "none":
            info.underline = True
        strike_style = text_props.get(q("style:text-line-through-style"))
        if strike_style and strike_style != "none":
            info.strikethrough = True
        position = text_props.get(q("style:text-position"))
        if position:
            first = position.split(" ")[0]
            if first == "super":
                info.superscript = True
            elif first == "sub":
                info.subscript = True

    # section-properties (usado por style:style family="section" e por
    # page-layout-properties para colunas no nivel de pagina)
    section_props = style_el.find(q("style:section-properties"))
    if section_props is not None:
        columns = _parse_column_props(section_props)
        if columns is not None:
            info.columns = columns

    return info


def build_style_registry(styles_root: ET.Element | None, content_root: ET.Element | None) -> StyleRegistry:
    registry = StyleRegistry()

    def scan(root: ET.Element | None):
        if root is None:
            return
        # office:styles (estilos nomeados), office:automatic-styles
        for container_tag in ("office:styles", "office:automatic-styles", "office:master-styles"):
            container = root.find(q(container_tag))
            if container is None:
                continue
            for style_el in container.findall(q("style:style")):
                info = _parse_style_element(style_el)
                if info:
                    registry.add(info)
            # page-layout tambem pode carregar colunas (raras vezes usado
            # como fallback quando a secao nao define as suas)
            for layout_el in container.findall(q("style:page-layout")):
                info = _parse_style_element(layout_el, family_override="page-layout")
                if info:
                    registry.add(info)

    scan(styles_root)
    scan(content_root)

    return registry


def build_list_style_registry(styles_root: ET.Element | None, content_root: ET.Element | None) -> dict[str, bool]:
    """Mapeia nome de list-style -> True (ordenada) / False (nao ordenada),
    olhando o primeiro nivel definido (secao 5 'listas')."""
    result: dict[str, bool] = {}

    def scan(root: ET.Element | None):
        if root is None:
            return
        for container_tag in ("office:styles", "office:automatic-styles"):
            container = root.find(q(container_tag))
            if container is None:
                continue
            for list_style_el in container.findall(q("text:list-style")):
                name = list_style_el.get(q("style:name"))
                if not name:
                    continue
                ordered = list_style_el.find(q("text:list-level-style-number")) is not None
                result[name] = ordered

    scan(styles_root)
    scan(content_root)
    return result


def _mapping_to_tag_attrs(mapping) -> tuple[str, dict]:
    if isinstance(mapping, str):
        return mapping, {}
    tag = mapping.get("tag", "p")
    attrs = {}
    if "class" in mapping:
        attrs["class"] = mapping["class"]
    return tag, attrs


def resolve_style_mapping(candidates: list[str], style_map: dict) -> tuple[str, dict] | None:
    """Resolve a lista de identificadores candidatos (ver
    StyleRegistry.resolve_style_candidates) contra o style_map do usuario
    (secao 7) e, na sequencia, contra o padrao (secao 6).

    Retorna None se nenhum candidato casar com nada (o chamador decide o
    fallback - paragrafos comuns caem em <p>, headings caem em h(N) pelo
    outline-level).

    O style_map do usuario tem prioridade total sobre o padrao, mas
    ambos sao tentados em toda a cadeia de heranca antes de desistir.
    Uma segunda passada case-insensitive cobre variacoes de capitalizacao
    entre versoes/idiomas do LibreOffice (ex: 'Text Body' vs 'Text body').
    """
    if not candidates:
        return None

    for name in candidates:
        if name in style_map:
            return _mapping_to_tag_attrs(style_map[name])
    for name in candidates:
        if name in DEFAULT_STYLE_MAP:
            return _mapping_to_tag_attrs(DEFAULT_STYLE_MAP[name])

    lower_style_map = {k.lower(): v for k, v in style_map.items()}
    for name in candidates:
        if name.lower() in lower_style_map:
            return _mapping_to_tag_attrs(lower_style_map[name.lower()])
    lower_default = {k.lower(): v for k, v in DEFAULT_STYLE_MAP.items()}
    for name in candidates:
        if name.lower() in lower_default:
            return _mapping_to_tag_attrs(lower_default[name.lower()])

    return None

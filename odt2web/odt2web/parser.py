"""Parser: content.xml -> Document Model (spec sections 4 and 5).

The parser never generates HTML directly; it produces the intermediate
model defined in model.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

from .model import (
    CustomNode, Document, Heading, Image, Link, LineBreak, List, ListItem,
    Note, NoteRef, PageBreak, Paragraph, Section, Span, Table, TableCell,
    TableRow, Text,
)
from .ns import q
from .reader import OdtPackage
from .styles import (
    ColumnInfo, StyleRegistry, build_list_style_registry, build_style_registry,
)
from .frontmatter import extract_front_matter
from .rawhtml import extract_raw_html_blocks

BLOCK_P = q("text:p")
BLOCK_H = q("text:h")
BLOCK_LIST = q("text:list")
BLOCK_TABLE = q("table:table")
BLOCK_SOFT_PAGE_BREAK = q("text:soft-page-break")
BLOCK_SECTION = q("text:section")


@dataclass
class ParseContext:
    registry: StyleRegistry
    list_styles: dict[str, bool]
    document: Document
    custom_renderers: dict = field(default_factory=dict)

    @property
    def warnings(self) -> list[str]:
        return self.document.warnings


# ---------------------------------------------------------------------------
# Inline
# ---------------------------------------------------------------------------

def _inline_from_element(el: ET.Element, ctx: ParseContext) -> list:
    result: list = []
    if el.text:
        result.append(Text(el.text))
    for child in el:
        result.extend(_convert_child_inline(child, ctx))
        if child.tail:
            result.append(Text(child.tail))
    return result


def _convert_child_inline(child: ET.Element, ctx: ParseContext) -> list:
    tag = child.tag

    if tag == q("text:span"):
        style_name = child.get(q("text:style-name"))
        info = ctx.registry.get(style_name)
        span = Span(children=_inline_from_element(child, ctx), style_name=style_name)
        if info:
            span.bold = info.bold
            span.italic = info.italic
            span.underline = info.underline
            span.strikethrough = info.strikethrough
            span.superscript = info.superscript
            span.subscript = info.subscript
        display_name = ctx.registry.display_name(style_name)
        candidates = ctx.registry.resolve_style_candidates(style_name)
        if display_name in ("Source Text", "Teletype", "Typewriter") or any(
            c in ("Source Text", "Teletype", "Typewriter") for c in candidates
        ):
            # native LibreOffice/ODF character styles conventionally used
            # for inline code (may arrive via an intermediate automatic
            # style, e.g. 'T1' -> 'Source Text').
            span.code = True
        return [span]

    if tag == q("text:a"):
        href = child.get(q("xlink:href")) or ""
        return [Link(href=href, children=_inline_from_element(child, ctx))]

    if tag == q("text:line-break"):
        return [LineBreak()]

    if tag == q("text:s"):
        count_raw = child.get(q("text:c"), "1")
        try:
            count = max(int(count_raw), 1)
        except (TypeError, ValueError):
            count = 1
        return [Text(" " * count)]

    if tag == q("text:tab"):
        return [Text("\t")]

    if tag == q("text:note"):
        return [_handle_note(child, ctx)]

    if tag == q("draw:frame"):
        # images embedded in the middle of a paragraph with other text
        # are not supported as an Image (which is a BlockNode); we just
        # record a warning so the rest of the text isn't lost.
        ctx.warnings.append(
            "Image embedded in the middle of a paragraph with text was "
            "ignored (only images in their own paragraph are supported)"
        )
        return []

    # "transparent" elements (bookmarks, tracked changes, etc.): we
    # descend into the children, preserving the text.
    return _inline_from_element(child, ctx)


def _handle_note(note_el: ET.Element, ctx: ParseContext) -> NoteRef:
    note_class = note_el.get(q("text:note-class"), "footnote")
    citation_el = note_el.find(q("text:note-citation"))
    label = (citation_el.text if citation_el is not None and citation_el.text else None) or str(
        len(ctx.document.notes) + 1
    )
    body_el = note_el.find(q("text:note-body"))
    note_id = f"note-{len(ctx.document.notes) + 1}"
    children = []
    if body_el is not None:
        for child in body_el:
            children.extend(_parse_block_element(child, ctx))
    note = Note(note_id=note_id, label=label, children=children, kind=note_class)
    ctx.document.notes[note_id] = note
    return NoteRef(note_id=note_id, label=label)


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------

def _find_solo_image_frame(p_el: ET.Element) -> ET.Element | None:
    """If the paragraph contains only an image (draw:frame > draw:image)
    and no other significant text, returns the draw:frame element."""
    if p_el.text and p_el.text.strip():
        return None
    frame = None
    count = 0
    for child in p_el:
        if child.tag == q("draw:frame") and child.find(q("draw:image")) is not None:
            frame = child
            count += 1
        if child.tail and child.tail.strip():
            return None
    if count == 1:
        return frame
    return None


# ODF horizontal-pos values that map cleanly onto a left/center/right
# alignment class; "from-left" (an absolute offset), "inside" and
# "outside" (mirrored-page positions) don't translate to a fixed side,
# so frames using them are left without an alignment class.
_ALIGN_VALUES = {"left", "center", "right"}


def _build_image_node(frame_el: ET.Element, ctx: ParseContext) -> Image:
    image_el = frame_el.find(q("draw:image"))
    href = image_el.get(q("xlink:href")) if image_el is not None else None
    linked = bool(href) and (href.startswith("http://") or href.startswith("https://"))

    width = frame_el.get(q("svg:width"))
    height = frame_el.get(q("svg:height"))

    alt = None
    title_el = frame_el.find(q("svg:title"))
    desc_el = frame_el.find(q("svg:desc"))
    if title_el is not None and title_el.text:
        alt = title_el.text
    elif desc_el is not None and desc_el.text:
        alt = desc_el.text

    frame_style_name = frame_el.get(q("draw:style-name"))
    horizontal_pos = ctx.registry.resolve_horizontal_pos(frame_style_name)
    align = horizontal_pos if horizontal_pos in _ALIGN_VALUES else None

    return Image(src=href or "", alt=alt, width=width, height=height, linked=linked, align=align)


def _plain_text(nodes: list) -> str:
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, Text):
            parts.append(node.value)
        elif isinstance(node, (Span, Link)):
            parts.append(_plain_text(node.children))
        elif isinstance(node, LineBreak):
            parts.append(" ")
    return "".join(parts).strip()


def _parse_paragraph_or_image(el: ET.Element, ctx: ParseContext):
    frame = _find_solo_image_frame(el)
    if frame is not None:
        return _build_image_node(frame, ctx)

    style_name = el.get(q("text:style-name"))
    resolved = ctx.registry.display_name(style_name) or style_name
    candidates = ctx.registry.resolve_style_candidates(style_name)
    return Paragraph(
        children=_inline_from_element(el, ctx), style_name=style_name,
        style_candidates=candidates, resolved_style=resolved,
    )


def _parse_heading(el: ET.Element, ctx: ParseContext) -> Heading:
    level_raw = el.get(q("text:outline-level"), "1")
    try:
        level = min(max(int(level_raw), 1), 6)
    except (TypeError, ValueError):
        level = 1
    style_name = el.get(q("text:style-name"))
    candidates = ctx.registry.resolve_style_candidates(style_name)
    return Heading(
        level=level, children=_inline_from_element(el, ctx), style_name=style_name,
        style_candidates=candidates,
    )


def _parse_list(el: ET.Element, ctx: ParseContext) -> List:
    style_name = el.get(q("text:style-name"))
    ordered = ctx.list_styles.get(style_name, False) if style_name else False
    items: list[ListItem] = []
    for item_el in el.findall(q("text:list-item")):
        children = []
        for child in item_el:
            children.extend(_parse_block_element(child, ctx))
        items.append(ListItem(children=children))
    return List(ordered=ordered, items=items, style_name=style_name)


def _parse_table(el: ET.Element, ctx: ParseContext) -> Table:
    style_name = el.get(q("table:style-name"))
    rows: list[TableRow] = []

    def parse_row(row_el: ET.Element, is_header: bool) -> None:
        cells: list[TableCell] = []
        for cell_el in row_el:
            if cell_el.tag == q("table:covered-table-cell"):
                cells.append(TableCell(covered=True))
                continue
            if cell_el.tag != q("table:table-cell"):
                continue
            try:
                colspan = int(cell_el.get(q("table:number-columns-spanned"), "1") or "1")
            except ValueError:
                colspan = 1
            try:
                rowspan = int(cell_el.get(q("table:number-rows-spanned"), "1") or "1")
            except ValueError:
                rowspan = 1
            block_children = []
            for child in cell_el:
                block_children.extend(_parse_block_element(child, ctx))
            cells.append(
                TableCell(
                    children=block_children, colspan=colspan, rowspan=rowspan,
                    is_header=is_header,
                )
            )
        rows.append(TableRow(cells=cells, is_header=is_header))

    header_rows_el = el.find(q("table:table-header-rows"))
    if header_rows_el is not None:
        for row_el in header_rows_el.findall(q("table:table-row")):
            parse_row(row_el, True)

    for row_el in el.findall(q("table:table-row")):
        parse_row(row_el, False)

    column_widths: list[float | None] = []
    for col_el in el.findall(q("table:table-column")):
        width = None
        col_style_name = col_el.get(q("table:style-name"))
        col_info = ctx.registry.get(col_style_name) if col_style_name else None
        repeat_raw = col_el.get(q("table:number-columns-repeated"), "1")
        try:
            repeat = max(int(repeat_raw), 1)
        except ValueError:
            repeat = 1
        column_widths.extend([width] * repeat)
        _ = col_info  # detailed column width is out of scope for the MVP

    return Table(rows=rows, style_name=style_name, column_widths=column_widths)


def _attach_captions(nodes: list) -> list:
    """Merges an Image followed by a paragraph styled 'Caption' into
    Image.caption (section 5 'images' - caption)."""
    result: list = []
    i = 0
    while i < len(nodes):
        node = nodes[i]
        if isinstance(node, Image) and i + 1 < len(nodes):
            nxt = nodes[i + 1]
            if isinstance(nxt, Paragraph) and "Caption" in nxt.style_candidates:
                node.caption = _plain_text(nxt.children)
                result.append(node)
                i += 2
                continue
        result.append(node)
        i += 1
    return result


def _parse_block_element(el: ET.Element, ctx: ParseContext) -> list:
    tag = el.tag

    if tag == BLOCK_P:
        node = _parse_paragraph_or_image(el, ctx)
        nodes = []
        if isinstance(node, Paragraph):
            if ctx.registry.resolve_break_before(node.style_name):
                nodes.append(PageBreak())
        nodes.append(node)
        return nodes

    if tag == BLOCK_H:
        return [_parse_heading(el, ctx)]

    if tag == BLOCK_LIST:
        return [_parse_list(el, ctx)]

    if tag == BLOCK_TABLE:
        return [_parse_table(el, ctx)]

    if tag == BLOCK_SOFT_PAGE_BREAK:
        return [PageBreak()]

    if tag in ctx.custom_renderers:
        return [CustomNode(name=tag, attributes=dict(el.attrib), children=[])]

    return []


# ---------------------------------------------------------------------------
# Sections / document
# ---------------------------------------------------------------------------

def _parse_section_element(section_el: ET.Element, ctx: ParseContext) -> Section:
    style_name = section_el.get(q("text:style-name"))
    columns = ctx.registry.resolve_columns(style_name)
    children: list = []
    for child in section_el:
        tag = child.tag
        if tag == BLOCK_SECTION:
            ctx.warnings.append(
                "Nested ODT sections are not fully supported; the "
                "content was merged into the parent section"
            )
            nested = _parse_section_element(child, ctx)
            children.extend(nested.children)
        else:
            children.extend(_parse_block_element(child, ctx))

    name = section_el.get(q("text:name"))
    return Section(
        children=extract_raw_html_blocks(_attach_captions(children)),
        columns=columns.count if columns else 1,
        column_gap=columns.gap if columns else None,
        column_rule=columns.rule if columns else None,
        style_name=style_name,
        name=name,
    )


def _parse_top_sections(text_root: ET.Element, ctx: ParseContext) -> list[Section]:
    sections: list[Section] = []
    current: list = []

    def flush():
        if current:
            sections.append(Section(children=extract_raw_html_blocks(_attach_captions(list(current))), columns=1))
            current.clear()

    for child in text_root:
        tag = child.tag
        if tag == BLOCK_SECTION:
            flush()
            sections.append(_parse_section_element(child, ctx))
        elif tag in (BLOCK_P, BLOCK_H, BLOCK_LIST, BLOCK_TABLE, BLOCK_SOFT_PAGE_BREAK):
            current.extend(_parse_block_element(child, ctx))
        else:
            # text:sequence-decls, text:tracked-changes,
            # text:table-of-content (indexes) and other elements out of
            # scope for the MVP are silently ignored.
            continue

    flush()
    return sections


def parse_document(package: OdtPackage, custom_renderers: dict | None = None) -> Document:
    """Builds the Document Model from an already-read OdtPackage."""
    registry = build_style_registry(package.styles_xml, package.content_xml)
    list_styles = build_list_style_registry(package.styles_xml, package.content_xml)

    document = Document()
    ctx = ParseContext(
        registry=registry, list_styles=list_styles, document=document,
        custom_renderers=custom_renderers or {},
    )

    body = package.content_xml.find(q("office:body"))
    if body is None:
        document.warnings.append("content.xml does not contain office:body")
        return document

    text_root = body.find(q("office:text"))
    if text_root is None:
        document.warnings.append(
            "Document does not contain office:text (it may not be an "
            "ODF text document, e.g. a spreadsheet or presentation)"
        )
        return document

    document.sections = _parse_top_sections(text_root, ctx)

    if document.sections:
        document.front_matter = extract_front_matter(document.sections[0])

    return document
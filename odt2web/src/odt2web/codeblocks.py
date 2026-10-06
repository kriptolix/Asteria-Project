"""Code blocks. 
"""
from __future__ import annotations

from .model import CodeBlock, LineBreak, Link, Paragraph, Section, Span, Text
from .styles import resolve_style_mapping


def _literal_text(nodes: list) -> str:
    """Extracts the literal text of a paragraph, ignoring inline
    formatting (bold/italic/links) but preserving manual line breaks as
    '\\n' - used to avoid corrupting code."""
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
    """If the first line is a Markdown-style marker ('```python'),
    removes it and returns the indicated language."""
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

                # each paragraph may contain multiple internal lines
                # (manual line breaks); flatten everything into a list of
                # lines before looking for the language marker.
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
    
    for section in sections:
        section.children = _merge_children(section.children, style_map)

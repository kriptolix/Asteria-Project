"""
Basic, dependency-free highlighting for `<pre><code class="language-x">` blocks.
"""

from __future__ import annotations

import re
from html import escape, unescape
from pathlib import Path
from typing import Any

import yaml

from .config import deep_merge

DEFAULT_LANGUAGES_PATH = Path(__file__).parent / "highlight-languages.yaml"

CODE_BLOCK_RE = re.compile(
    r'<pre(?P<pre_attrs>[^>]*)><code(?P<code_attrs>[^>]*)>(?P<code>.*?)</code></pre>',
    re.DOTALL,
)
LANGUAGE_CLASS_RE = re.compile(r'\blanguage-([\w+-]+)\b')

_NUMBER_RE = r'\b\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?\b'
_BRACKETS = "()[]{}"

_TOKEN_CLASS = {
    "comment": "tok-com",
    "string": "tok-str",
    "number": "tok-num",
    "keyword": "tok-kw",
    "call": "tok-fn",
    "bracket": "tok-punc",
}


def load_languages(project_root: Path | None = None) -> dict[str, dict[str, Any]]:
    
    bundled: dict[str, Any] = {}
    if DEFAULT_LANGUAGES_PATH.exists():
        bundled = yaml.safe_load(DEFAULT_LANGUAGES_PATH.read_text(encoding="utf-8")) or {}

    overrides: dict[str, Any] = {}
    if project_root is not None:
        override_path = project_root / "source" / "highlight.yaml"
        if override_path.exists():
            overrides = yaml.safe_load(override_path.read_text(encoding="utf-8")) or {}

    merged = deep_merge(bundled, overrides) if overrides else bundled

    by_key: dict[str, dict[str, Any]] = {}
    for name, spec in merged.items():
        if not isinstance(spec, dict):
            continue
        by_key[name] = spec
        for alias in spec.get("aliases", []) or []:
            by_key[alias] = spec
    return by_key


def _build_master_pattern(lang: dict[str, Any] | None) -> re.Pattern:
    
    comment_alts: list[str] = []
    if lang:
        for start, end in lang.get("block_comments", []) or []:
            comment_alts.append(rf'{re.escape(start)}.*?{re.escape(end)}')
        line_comment = lang.get("line_comment")
        if line_comment:
            comment_alts.append(rf'{re.escape(line_comment)}[^\n]*')

    string_alts: list[str] = []
    for q in (lang.get("triple_quotes") if lang else []) or []:
        string_alts.append(
            rf'{re.escape(q)}(?:\\.|(?!{re.escape(q)})[\s\S])*?{re.escape(q)}'
        )
    # Generic single/double quotes — always available,
    # even without a recognized language.
    string_alts.append(r'"(?:\\.|[^"\\\n])*"')
    string_alts.append(r"'(?:\\.|[^'\\\n])*'")

    parts: list[str] = []
    if comment_alts:
        parts.append(rf'(?P<comment>{"|".join(comment_alts)})')
    parts.append(rf'(?P<string>{"|".join(string_alts)})')
    parts.append(rf'(?P<number>{_NUMBER_RE})')

    if lang and lang.get("keywords"):
        kw_alt = "|".join(re.escape(str(k)) for k in lang["keywords"])
        parts.append(rf'\b(?P<keyword>{kw_alt})\b')
    
    if lang and lang.get("assignment_style") == "equals":
        parts.append(
            r'(?:(?<=\n)|^)(?P<indent>[ \t]*)(?P<assign>[A-Za-z_]\w*)'
            r'(?=[ \t]*=(?![=~]))'
        )

    # Identifier followed by "(" — function call heuristic.    
    parts.append(r'(?P<call>[A-Za-z_]\w*)(?=\()')

    # Parentheses/brackets/braces.
    parts.append(rf'(?P<bracket>[{re.escape(_BRACKETS)}])')

    # Any other character — plain text, consumed one by one (ensures
    # that the combined regex covers 100% of the text, without gaps).
    parts.append(r'(?P<plain>[\s\S])')

    return re.compile("|".join(parts))


def _highlight_code(code_text: str, lang: dict[str, Any] | None) -> str:
    """`code_text` is the source code with escapes already removed (HTML entities
    reverted). It returns HTML with `<span class="tok-...">` around the
    recognized tokens; the rest is returned escaped as plain text."""
    pattern = _build_master_pattern(lang)
    out: list[str] = []
    for m in pattern.finditer(code_text):
        kind = m.lastgroup
        if kind == "assign":
            indent = m.group("indent")
            if indent:
                out.append(escape(indent))
            out.append(f'<span class="tok-var">{escape(m.group("assign"))}</span>')
            continue
        text = m.group(kind)
        css_class = _TOKEN_CLASS.get(kind)
        if css_class:
            out.append(f'<span class="{css_class}">{escape(text)}</span>')
        else:
            out.append(escape(text))
    return "".join(out)


def _wrap_lines(highlighted_html: str) -> str:
    
    lines = highlighted_html.split("\n")
    return "\n".join(f'<span class="hl-line">{line}</span>' for line in lines)


def _inject_class(attrs: str, extra: str) -> str:
    
    match = re.search(r'class="([^"]*)"', attrs)
    if match:
        classes = f'{match.group(1)} {extra}'.strip()
        return attrs[: match.start()] + f'class="{classes}"' + attrs[match.end():]
    return f'{attrs} class="{extra}"'


def highlight_code_blocks(html: str, languages: dict[str, dict[str, Any]]) -> str:
    """Finds every `<pre><code ...>...</code></pre>` block in `html` and
    replaces its content with a version that is syntax-highlighted and
    line-numbered. 
    """

    def _replace(match: re.Match) -> str:
        pre_attrs = match.group("pre_attrs")
        code_attrs = match.group("code_attrs")
        raw_code = unescape(match.group("code"))
    
        if raw_code.endswith("\n"):
            raw_code = raw_code[:-1]

        lang_match = LANGUAGE_CLASS_RE.search(code_attrs)
        lang_key = lang_match.group(1).lower() if lang_match else None
        lang = languages.get(lang_key) if lang_key else None

        highlighted = _highlight_code(raw_code, lang)
        numbered = _wrap_lines(highlighted)
        new_code_attrs = _inject_class(code_attrs, "hl")

        return f'<pre{pre_attrs}><code{new_code_attrs}>{numbered}</code></pre>'

    return CODE_BLOCK_RE.sub(_replace, html)
"""
Locale-aware date formatting for front matter `date:` strings.
"""

from __future__ import annotations

from datetime import date, datetime

# Tried in order; the first one that parses wins. 
_PARSE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d",
)

# Full month names, 1-indexed (index 0 unused, so _LONG_MONTH_NAMES[lang][3]
# is "March"/"março" directly, matching date.month). Add a language here
# to get long-format support for it; anything not listed falls back to
# English (_DEFAULT_LANG below).
_LONG_MONTH_NAMES: dict[str, tuple[str, ...]] = {
    "pt-BR": (
            "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
        ),
    "pt": (
        "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ),
    "es": (
        "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ),
    "en": (
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ),
    "fr": (
        "", "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ),
}

# "{day} de {month} de {year}" vs. "{month} {day}, {year}", etc. — the
# word order itself is locale-specific, not just the month name.
_LONG_DATE_TEMPLATES: dict[str, str] = {
    "pt-BR": "{day} de {month} de {year}",
    "pt": "{day} de {month} de {year}",
    "es": "{day} de {month} de {year}",
    "en": "{month} {day}, {year}",
    "fr": "{day} {month} {year}",
}

# dd/mm/yyyy is the common short form outside the US; en gets mm/dd/yyyy,
# matching the reading order English speakers expect from "1/14/2026".
_SHORT_DATE_FORMATS: dict[str, str] = {
    "pt-BR": "%d/%m/%Y",
    "pt": "%d/%m/%Y",
    "es": "%d/%m/%Y",
    "en": "%m/%d/%Y",
    "fr": "%d/%m/%Y",
}

_DEFAULT_LANG = "en"


def parse_date(raw: str | None) -> date | None:
    """Parses a front matter `date:` string into a `date`."""
    if not raw:
        return None
    for fmt in _PARSE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def format_date(raw: str | None, lang: str = "", style: str = "long") -> str:
    """Jinja filter: `{{ post.date | format_date(post.lang) }}`.   
    """
    parsed = parse_date(raw)
    if parsed is None:
        return raw or ""

    lang = lang or _DEFAULT_LANG

    if style == "short":
        pattern = _SHORT_DATE_FORMATS.get(lang, _SHORT_DATE_FORMATS[_DEFAULT_LANG])
        return parsed.strftime(pattern)

    if style == "long":
        months = _LONG_MONTH_NAMES.get(lang, _LONG_MONTH_NAMES[_DEFAULT_LANG])
        template = _LONG_DATE_TEMPLATES.get(lang, _LONG_DATE_TEMPLATES[_DEFAULT_LANG])
        return template.format(day=parsed.day, month=months[parsed.month], year=parsed.year)

    # Anything else: treat `style` itself as a strftime pattern, for
    # themes that want a format the two named styles above don't cover.
    return parsed.strftime(style)